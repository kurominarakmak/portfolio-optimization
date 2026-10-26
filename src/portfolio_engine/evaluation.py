"""Frozen walk-forward comparisons with drift, transition costs and visible failures."""
from dataclasses import asdict, replace
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .data import validate_returns
from .models import covariance, scenarios, empirical_es, max_drawdown, stationary_indices, black_litterman
from .optimize import Constraints, optimize

STRATEGIES=('buy_hold','equal_weight','min_variance','risk_parity','bl_mv','min_cvar','bl_cvar','no_bl','variance_risk','sample_covariance','gaussian','no_cost_control')


def _erc(sigma):
    n=len(sigma)
    def objective(w):
        rc=w*(sigma@w); return np.sum((rc-rc.mean())**2)/(np.trace(sigma)**2)
    fit=minimize(objective,np.full(n,1/n),method='SLSQP',bounds=[(.000001,1)]*n,constraints={'type':'eq','fun':lambda w:w.sum()-1},options={'ftol':1e-12,'maxiter':500})
    if not fit.success or abs(fit.x.sum()-1)>1e-6: raise ValueError('Risk parity fit failed')
    rc=fit.x*(sigma@fit.x)
    if np.max(np.abs(rc/rc.sum()-1/n))>1e-3: raise ValueError('Risk parity residual failed')
    return fit.x


def evaluate(returns,metadata,train=504,step=63,constraints=None,initial=None,seed=42,scenario_count=1000,alpha=.95,risk_aversion=1.,expanding=False,ci_samples=500,cash_rate=0.):
    frame=validate_returns(returns,metadata); n=len(frame.columns); c=constraints or Constraints(cost_budget=.01)
    if train<max(60,5*n) or train>=len(frame) or step<1 or ci_samples<1: raise ValueError('Invalid walk-forward window')
    if not np.isfinite(cash_rate) or cash_rate < -1: raise ValueError('Invalid cash rate')
    initial=np.r_[np.full(n,.9/n),.1] if initial is None else np.asarray(initial,float)
    if initial.shape!=(n+1,) or (initial<0).any() or not np.isclose(initial.sum(),1): raise ValueError('Invalid initial weights')
    r=frame.to_numpy(); states={name:initial.copy() for name in STRATEGIES}
    paths={name:[] for name in STRATEGIES}; diagnostics={name:[] for name in STRATEGIES}; failures={name:[] for name in STRATEGIES}; folds=[]
    for fold,start in enumerate(range(train,len(r),step)):
        stop=min(start+step,len(r)); fit=r[0 if expanding else start-train:start]; train_end=frame.index[start-1]
        sigma=covariance(fit); sample=covariance(fit,'sample'); full=np.pad(sigma,((0,1),(0,1)))
        prior=np.zeros(n); bl=black_litterman(sigma,prior)
        sims=scenarios(fit,bl['mean']+cash_rate,sigma,scenario_count,seed+fold,'bootstrap'); R=np.c_[sims,np.full(scenario_count,cash_rate)]
        folds.append({'fold':fold,'train_start':str(frame.index[0 if expanding else start-train].date()),'train_end':str(train_end.date()),'test_start':str(frame.index[start].date()),'test_end':str(frame.index[stop-1].date()),'training_observations':len(fit),'prior':'user-labelled zero excess return; no market prior, no views','test_tail_warning':(stop-start)*(1-alpha)<20,'weights':{}})
        for name in STRATEGIES:
            w=states[name]; before=w.copy(); cost=0.; turn=0.; x=w.copy(); forecast_R=R; used_sigma=full
            try:
                mu=np.r_[prior+cash_rate,cash_rate]; method='cvar'; cfg=c; target=None
                if name=='buy_hold':
                    # shortcut: buy-and-hold is exempt from rebalance bounds; disclose separately.
                    result=None
                else:
                    if name=='equal_weight': method='target'; target=np.r_[np.full(n,.9/n),.1]
                    elif name=='risk_parity': method='target'; target=np.r_[.9*_erc(sigma),.1]
                    elif name=='min_variance': method='min_variance'; cfg=replace(c,cost_rate=0.)
                    elif name in {'bl_mv','variance_risk'}: method='mv'
                    elif name=='min_cvar': method='min_cvar'
                    elif name=='no_bl':
                        mu=np.r_[fit.mean(axis=0),cash_rate]
                        forecast_R=np.c_[scenarios(fit,fit.mean(axis=0),sigma,scenario_count,seed+fold),np.full(scenario_count,cash_rate)]
                    elif name=='sample_covariance':
                        used_sigma=np.pad(sample,((0,1),(0,1)))
                        forecast_R=np.c_[scenarios(fit,prior+cash_rate,sample,scenario_count,seed+fold,'gaussian'),np.full(scenario_count,cash_rate)]
                    elif name=='gaussian': forecast_R=np.c_[scenarios(fit,prior+cash_rate,sigma,scenario_count,seed+fold,'gaussian'),np.full(scenario_count,cash_rate)]
                    elif name=='no_cost_control': cfg=replace(c,cost_rate=0.)
                    result=optimize(forecast_R,mu,w,used_sigma,cfg,alpha,risk_aversion,method,target)
                    if name in {'no_cost_control','min_variance'}: result=optimize(forecast_R,mu,w,used_sigma,c,alpha,risk_aversion,'target',result['weights'])
                    x=result['pre_nav_fractions']; cost=result['cost']; turn=result['turnover']
            except (ValueError,np.linalg.LinAlgError) as exc:
                failures[name].append({'fold':fold,'reason':str(exc),'fallback':'held existing weights; no relaxed optimization'})
                x=w.copy(); cost=0.; turn=0.
            folds[-1]['weights'][name]=(x/(1-cost)).tolist()
            for day in range(start,stop):
                rr=np.r_[r[day],cash_rate]
                exposure=x.copy() if day==start else w.copy()
                day_cost=cost if day==start else 0.
                forecast_loss=day_cost-forecast_R@exposure
                var=float(np.quantile(forecast_loss,alpha,method='higher')); es=empirical_es(forecast_loss,alpha)
                # First day starts from pre-NAV holdings; cost is debited exactly once.
                holdings=x*(1+rr) if day==start else w*(1+rr)
                net=float(holdings.sum()-1); w=holdings/holdings.sum()
                paths[name].append(net)
                risky_w=exposure[:-1]
                realized_var=(r[day]-fit.mean(axis=0))**2
                diagnostics[name].append({'date':str(frame.index[day].date()),'net_return':net,'cost':cost if day==start else 0.,'turnover':turn if day==start else 0.,'hhi':float(w@w),'weight_change':float(np.abs(w-before).sum()) if day==start else float(np.abs(w-previous_w).sum()),'start_weights':exposure.tolist(),'forecast_includes_transition_cost':day==start,'forecast_daily_var':var,'var_exceedance':bool(-net>var),'forecast_daily_es':es,'tail_loss':max(0.,-net-var),'variance_forecast_squared_error':float((float(risky_w@used_sigma[:-1,:-1]@risky_w)-float((r[day]@risky_w)**2))**2),'covariance_forecast_mse':float(np.mean((used_sigma[:-1,:-1]-np.outer(r[day]-fit.mean(axis=0),r[day]-fit.mean(axis=0)))**2))})
                previous_w=w.copy()
            states[name]=w
    results={}
    for name,series in paths.items():
        a=np.array(series); d=diagnostics[name]; vol=a.std(ddof=1); downside=np.sqrt(np.mean(np.minimum(a,0)**2)); gross=np.prod(1+a)
        results[name]={'net_total_return':float(gross-1),'daily_mean':float(a.mean()),'annualized_arithmetic_mean':float(a.mean()*252),'annualized_volatility':float(vol*np.sqrt(252)),'sharpe_zero_rate':float(a.mean()/vol*np.sqrt(252)) if vol>1e-12 else None,'sortino_zero_rate':float(a.mean()/downside*np.sqrt(252)) if downside>1e-12 else None,'maximum_drawdown':max_drawdown(a),'daily_realized_es':empirical_es(-a,alpha),'var_exceedance_frequency':float(np.mean([z['var_exceedance'] for z in d])),'tail_excess_loss_mean':float(np.mean([z['tail_loss'] for z in d])),'mean_forecast_daily_es':float(np.mean([z['forecast_daily_es'] for z in d])),'variance_forecast_mse':float(np.mean([z['variance_forecast_squared_error'] for z in d])),'covariance_forecast_mse':float(np.mean([z['covariance_forecast_mse'] for z in d])),'total_cost_fraction':float(sum(z['cost'] for z in d)),'two_sided_risky_turnover':float(sum(z['turnover'] for z in d)),'mean_hhi':float(np.mean([z['hhi'] for z in d])),'mean_daily_weight_change':float(np.mean([z['weight_change'] for z in d])),'failed_folds':failures[name],'daily':d}
    rng=np.random.default_rng(seed); intervals={}; base=np.array(paths['bl_cvar'])
    for name in STRATEGIES:
        if name=='bl_cvar': continue
        difference=base-np.array(paths[name]); draws=[float(difference[stationary_indices(len(base),len(base),rng,10)].mean()) for _ in range(ci_samples)]
        intervals[name]={'contrast':'bl_cvar minus '+name,'daily_mean_difference':float(difference.mean()),'paired_stationary_block_95_ci':np.quantile(draws,[.025,.975]).tolist()}
    return {'claims':'Exploratory comparison only; no demonstrated investment superiority.','data_kind':metadata['kind'],'provenance':metadata,'horizon':'one trading day; annualized moments use 252, no ES scaling','initial_allocation':'hypothetical identical starting weights; current holdings are not historical holdings','constraints':asdict(c),'configuration':{'train':train,'step':step,'expanding':expanding,'seed':seed,'scenario_count':scenario_count,'alpha':alpha,'risk_aversion':risk_aversion,'cash_rate':cash_rate,'initial':initial.tolist()},'mandates':'Buy-and-hold exempt from rebalance bounds. Equal-weight/ERC retain 10% cash; optimized strategies may choose all cash. Initial transitions charged. Continuous fractions, no execution.','limitations':['No point-in-time historical universe or corporate-action reconstruction supplied.','Zero prior may produce all-cash optimizer outcomes; no invented alpha.','CIs assume stationarity/dependence captured by block length 10; no multiple-testing adjustment.','Per-fold short tails are descriptive; pooled realized tails still uncertain.','no_bl replaces zero BL prior with historical sample mean. sample_covariance and gaussian compare Gaussian families to isolate shrinkage; bootstrap does not use fitted covariance.','No historical views, capitalization, or actual holdings reconstructed.', 'Minimum variance fits a pure covariance target without cost penalty, then realizes actual costs under common constraints. BL MV/variance ablation includes linear costs in objective.'],'folds':folds,'strategies':results,'paired_uncertainty':intervals}
