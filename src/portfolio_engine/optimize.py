"""Convex continuous allocation; separately reconciled whole-share preview."""
from dataclasses import dataclass, field
import cvxpy as cp
import numpy as np
from .models import empirical_es, psd

@dataclass
class Constraints:
    max_weight: float = .6
    min_weight: float = 0.
    min_cash: float = 0.
    max_cash: float = 1.
    max_turnover: float = 2.
    cost_budget: float = .02
    cost_rate: float = .001
    sector_caps: dict = field(default_factory=dict)
    sectors: tuple = ()

    def validate(self,n):
        vals=[self.max_weight,self.min_weight,self.min_cash,self.max_cash,self.max_turnover,self.cost_budget,self.cost_rate]
        if not np.isfinite(vals).all() or not 0<=self.min_weight<=self.max_weight<=1 or not 0<=self.min_cash<=self.max_cash<=1 or self.max_turnover<0 or not 0<=self.cost_budget<1 or not 0<=self.cost_rate<1:
            raise ValueError('Invalid constraints')
        if self.sector_caps and len(self.sectors)!=n-1: raise ValueError('Require sector per risky symbol')
        if self.sectors and (len(self.sectors)!=n-1 or any(not isinstance(s,str) or not s.strip() for s in self.sectors)): raise ValueError('Sector labels must be nonempty for every risky symbol')
        if set(self.sector_caps)-set(self.sectors): raise ValueError('Sector cap label absent from sector mapping')
        if any(not 0<=v<=1 for v in self.sector_caps.values()): raise ValueError('Invalid sector cap')


def residuals(x,w0,c):
    cost=c.cost_rate*np.abs(x[:-1]-w0[:-1]).sum(); wealth=1-cost
    violations=[abs(x.sum()+cost-1),max(0.,-x.min()),max(0.,c.min_cash*wealth-x[-1]),max(0.,x[-1]-c.max_cash*wealth),max(0.,np.abs(x[:-1]-w0[:-1]).sum()-c.max_turnover),max(0.,cost-c.cost_budget),max(0.,np.max(x[:-1]-c.max_weight*wealth)),max(0.,np.max(c.min_weight*wealth-x[:-1]))]
    for sector,cap in c.sector_caps.items():
        idx=[i for i,s in enumerate(c.sectors) if s==sector]
        violations.append(max(0.,x[idx].sum()-cap*wealth))
    return float(max(violations)),float(cost)


def optimize(returns,mean,current,sigma,constraints=None,alpha=.95,risk_aversion=1.,method='cvar',target=None):
    c=constraints or Constraints(); r=np.asarray(returns,float); mu=np.asarray(mean,float); w0=np.asarray(current,float); n=len(w0); c.validate(n)
    if n<2 or r.ndim!=2 or r.shape[1]!=n or mu.shape!=(n,) or not np.isfinite(r).all() or not np.isfinite(mu).all() or not np.isfinite(w0).all() or (w0<0).any() or not np.isclose(w0.sum(),1) or not 0<alpha<1 or risk_aversion<0: raise ValueError('Invalid optimization inputs')
    s=psd(sigma)
    x=cp.Variable(n); t=cp.Variable(n-1,nonneg=True); k=c.cost_rate*cp.sum(t); wealth=1-k
    cons=[x>=0,t>=x[:-1]-w0[:-1],t>=w0[:-1]-x[:-1],cp.sum(x)+k==1,x[:-1]<=c.max_weight*wealth,x[:-1]>=c.min_weight*wealth,x[-1]>=c.min_cash*wealth,x[-1]<=c.max_cash*wealth,cp.sum(t)<=c.max_turnover,k<=c.cost_budget]
    for sector,cap in c.sector_caps.items():
        idx=[i for i,z in enumerate(c.sectors) if z==sector]
        cons.append(cp.sum(x[idx])<=cap*wealth)
    if method in {'cvar','min_cvar'}:
        z=cp.Variable(); u=cp.Variable(len(r),nonneg=True)
        cons.append(u>=k-r@x-z)
        risk=z+cp.sum(u)/(len(r)*(1-alpha))
        objective=k+(-mu@x if method=='cvar' else 0)+risk_aversion*risk
    elif method in {'mv','min_variance'}:
        objective=k+(-mu@x if method=='mv' else 0)+risk_aversion*cp.quad_form(x,cp.psd_wrap(s))
    elif method=='target':
        if target is None or np.asarray(target).shape!=(n,): raise ValueError('Target required')
        cons.append(x==np.asarray(target)*wealth)
        objective=k
    else: raise ValueError('Unknown optimization method')
    problem=cp.Problem(cp.Minimize(objective),cons)
    try: problem.solve(solver='CLARABEL',tol_gap_abs=1e-9,tol_feas=1e-9,tol_gap_rel=1e-9)
    except cp.SolverError: raise ValueError('Solver failed') from None
    if problem.status!='optimal' or x.value is None: raise ValueError('Optimization failed: '+str(problem.status))
    value=np.asarray(x.value); error,actual=residuals(value,w0,c)
    if error>1e-6 or abs(float(k.value)-actual)>1e-6: raise ValueError('Accounting/constraint residual or loose cost epigraph')
    # Solver boundary noise is removed only after verifying the raw solution.
    value[:-1]=np.maximum(value[:-1],0.)
    actual=float(c.cost_rate*np.abs(value[:-1]-w0[:-1]).sum())
    value[-1]=1-actual-value[:-1].sum()
    if -1e-12<value[-1]<0: value[-1]=0.
    error,actual=residuals(value,w0,c)
    if error>1e-6 or (value<0).any(): raise ValueError('Cleaned allocation violates accounting/constraints')
    loss=actual-r@value
    return {'pre_nav_fractions':value,'weights':value/(1-actual),'cost':actual,'turnover':float(np.abs(value[:-1]-w0[:-1]).sum()),'daily_es_net':empirical_es(loss,alpha),'daily_expected_net_return':float(mu@value-actual),'utility':float(mu@value-actual-risk_aversion*empirical_es(loss,alpha)),'max_residual':error,'solver_status':problem.status}


def preview_shares(candidate,portfolio,constraints,min_trade_value=0):
    frame=portfolio['positions']; nav=portfolio['nav']; price=frame.price.to_numpy()[:-1]; old=frame.quantity.to_numpy()[:-1]
    if (old!=np.floor(old)).any(): raise ValueError('Whole-share preview requires whole current quantities')
    qty=np.floor(candidate['pre_nav_fractions'][:-1]*nav/price)
    trade=(qty-old)*price
    if ((np.abs(trade)>0)&(np.abs(trade)<min_trade_value)).any(): raise ValueError('Minimum ticket violated')
    cost=constraints.cost_rate*np.abs(trade).sum(); cash=nav-qty@price-cost
    x=np.r_[qty*price,cash]/nav
    error,_=residuals(x,portfolio['weights'],constraints)
    if cash<0 or error>1e-6: raise ValueError('Rounded preview violates cash or allocation constraints')
    return {'quantity':qty,'pre_nav_fractions':x,'cash_usd':float(cash),'cost_usd':float(cost),'weights':x/(1-cost/nav),'max_residual':error,'execution':'PREVIEW ONLY; no orders'}


def decide(improvement,current_feasible,history_count,scenario_count,evidence,alpha=.95,threshold=.0001,preview_valid=True):
    reason=None
    if not preview_valid: reason='Whole-share preview failed'
    elif min(history_count,scenario_count)*(1-alpha)<20: reason='Insufficient historical or simulated tail observations'
    elif not evidence or not evidence.get('independent') or not evidence.get('source'): reason='Independent uncertainty evidence missing'
    elif not evidence.get('sensitivity_stable'): reason='Sensitivity unstable'
    elif not np.isfinite(improvement): reason='Invalid estimated improvement'
    elif improvement<=threshold and current_feasible: return {'decision':'HOLD','reason':'Current allocation feasible; improvement below materiality threshold'}
    elif improvement<=threshold: reason='Current constraints violated and no material supported improvement'
    elif not np.isfinite(evidence.get('lower_bound',np.nan)) or evidence['lower_bound']<=threshold: reason='Independent lower uncertainty bound does not clear threshold'
    if reason: return {'decision':'NO_TRADE','reason':reason}
    return {'decision':'REBALANCE','reason':'Feasible candidate clears explicit cost, uncertainty and sensitivity policy'}
