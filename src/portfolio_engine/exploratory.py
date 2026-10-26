"""Frozen, nonactionable Alpaca/Tiingo close-return replay; no VALIDATED admission."""
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from .models import covariance,black_litterman,scenarios,empirical_es,max_drawdown
from .optimize import Constraints,optimize,residuals
from .evaluation import _erc

FROZEN_SYMBOLS=('CHTR','ADBE','ADSK','AKAM','ALGN','AMD','CDNS','DLTR','FFIV','HOLX','HSIC','IDXX','INCY','LULU','MELI','MRNA','SNPS','TTWO','UAL','ULTA','VRTX','WDAY','ZBRA')
START='2020-07-27';END='2025-12-31';PRICE_SESSION_COUNT=1366
STRATEGIES=('buy_hold','equal_weight','min_variance','risk_parity','bl_mv','min_cvar','bl_cvar')
GROUPS=('diversified','concentrated','training_correlated','cash_boundary','breadth')


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def read_price_series(path,dates,provider,expected_symbol=None,expected_security_id=None):
    rows={}; dates=pd.DatetimeIndex(dates); first=str(dates[0].date()); last=str(dates[-1].date())
    with Path(path).open() as stream:
        for line in stream:
            row=json.loads(line); date=row['session_date']
            if first<=date<=last:
                if date in rows: raise ValueError('Duplicate price session: '+str(path))
                if provider=='alpaca' and (row.get('source')!='alpaca' or row.get('feed')!='iex' or row.get('price_basis')!='RAW' or row.get('adjustment')!='raw'): raise ValueError('Expected Alpaca raw IEX provenance: '+str(path))
                if provider=='tiingo' and row.get('source')!='tiingo': raise ValueError('Expected Tiingo provenance: '+str(path))
                if expected_symbol and row.get('vendor_ticker' if provider=='alpaca' else 'symbol')!=expected_symbol: raise ValueError('Embedded symbol mismatch: '+str(path))
                if expected_security_id and provider=='alpaca' and row.get('security_id')!=expected_security_id: raise ValueError('Embedded security identity mismatch: '+str(path))
                if provider=='tiingo' and (row.get('div_cash')!=0 or row.get('split_factor')!=1): raise ValueError('Recorded corporate action or missing action fields: '+str(path))
                value=row.get('close' if provider=='alpaca' else 'vendor_adjusted_close')
                if not isinstance(value,(int,float)) or not np.isfinite(value) or value<=0: raise ValueError('Nonpositive/missing price: '+str(path))
                rows[date]=float(value)
    if set(rows)!=set(str(d.date()) for d in dates): raise ValueError('Price session coverage mismatch: '+str(path))
    return pd.Series([rows[str(d.date())] for d in dates],index=dates)


def price_returns(prices):
    values=prices.to_numpy(float)
    if len(prices)<2 or not np.isfinite(values).all() or (values<=0).any() or prices.index.has_duplicates or not prices.index.is_monotonic_increasing: raise ValueError('Invalid positive aligned prices')
    # Direct ratios prevent pandas missing-value filling and retain decimal simple units.
    return pd.DataFrame(values[1:]/values[:-1]-1,index=prices.index[1:],columns=prices.columns)


def load_matched_data(root):
    root=Path(root); calendars=sorted((root/'data/verification').glob('xnys_calendar_*.json'))
    if len(calendars)!=1: raise ValueError('Expected one frozen local XNYS calendar')
    calendar=json.loads(calendars[0].read_text())
    if calendar.get('calendar')!='XNYS': raise ValueError('Wrong exchange calendar')
    dates=pd.DatetimeIndex([r['session_date'] for r in calendar['sessions'] if START<=r['session_date']<=END])
    if len(dates)!=PRICE_SESSION_COUNT or dates.has_duplicates or not dates.is_monotonic_increasing or str(dates[0].date())!=START or str(dates[-1].date())!=END: raise ValueError('Frozen 1366-session calendar mismatch')
    mapping_path=root/'alpaca_security_mapping.csv'; mapping=pd.read_csv(mapping_path,keep_default_na=False)
    feeds={name:pd.DataFrame(index=dates) for name in ('alpaca','tiingo')}; records=[]
    for symbol in FROZEN_SYMBOLS:
        candidates=set()
        for row in mapping.loc[mapping.historical_ticker.eq(symbol)].to_dict('records'):
            for interval in row['effective_prototype_interval'].split(';'):
                if not interval.startswith(symbol+':'): continue
                left,right=interval.split(':',1)[1].split('..')
                if left<=START<right: candidates.add(row['security_id'])
        if len(candidates)!=1: raise ValueError('Ambiguous local security mapping at start: '+symbol)
        security_id=candidates.pop()
        paths={'alpaca':root/'data/normalized/alpaca/membership_pit'/f'{security_id}.jsonl','tiingo':root/'data/normalized/membership_pit'/f'{symbol}.jsonl'}
        for provider,path in paths.items(): feeds[provider][symbol]=read_price_series(path,dates,provider,symbol,security_id)
        discrepancy=float(np.abs(np.diff(np.log(feeds['alpaca'][symbol]))-np.diff(np.log(feeds['tiingo'][symbol]))).max())
        if discrepancy>=.05: raise ValueError('Cross-source log-return discrepancy exceeds frozen threshold: '+symbol)
        records.append({'symbol':symbol,'local_security_id':security_id,'observations_per_feed':len(dates),'max_daily_log_return_discrepancy':discrepancy,'files':{name:{'path':str(path),'sha256':file_hash(path)} for name,path in paths.items()}})
    alpaca_files=list((root/'data/normalized/alpaca/membership_pit').glob('SEC*.jsonl')); tiingo_files=list((root/'data/normalized/membership_pit').glob('*.jsonl'))
    outside=sorted(set(mapping.historical_ticker)-set(FROZEN_SYMBOLS))
    manifest={'lane':'EXPLORATORY_REAL_MARKET','status':'HISTORICAL_RETURN_REPLAY','decision':'NO_TRADE','validated':False,'root':str(root),'price_start':START,'price_end':END,'price_sessions':len(dates),'return_sessions':len(dates)-1,'files':records,'mapping_sha256':file_hash(mapping_path),'calendar':{'path':str(calendars[0]),'sha256':file_hash(calendars[0]),'basis':calendar.get('calendar_basis')},'candidate_counts':{'alpaca_security_files':len(alpaca_files),'alpaca_nonempty_files':sum(p.stat().st_size>0 for p in alpaca_files),'tiingo_ticker_files':len(tiingo_files),'tiingo_nonempty_files':sum(p.stat().st_size>0 for p in tiingo_files),'mapping_historical_symbols':len(set(mapping.historical_ticker)),'runtime_screened_frozen_symbols':len(FROZEN_SYMBOLS),'admitted_matched_symbols':len(records)},'exclusions':[{'symbol':s,'reason':'Outside pre-frozen 23-name restricted cohort; not reranked using strategy outcomes'} for s in outside],'selection_limit':'Only the frozen 23 symbols are runtime price/action checked here. Full-window quality selection creates future-coverage and survivorship bias; no point-in-time asset-selection certification.','return_definitions':{'alpaca':'Raw IEX close-to-close decimal price returns, not total returns; action completeness unverified','tiingo':'Vendor-adjusted-close ratios captured in 2026; no recorded dividend/split in selected window, not PIT back-adjustment or executable quotes'},'limitations':['Restricted common survivors with complete full-window coverage selected before strategy outcomes, but with future coverage knowledge.','Zero recorded Tiingo dividends/splits does not establish complete corporate-action or identity correctness.','Rights, execution prices and full PIT validity are not certified; strict VALIDATED gates unchanged.']}
    return {provider:price_returns(prices) for provider,prices in feeds.items()},manifest


def make_portfolios(training,seed=42,max_attempts=1000):
    if len(training)!=504 or len(training.columns)<10 or not np.isfinite(training).all().all(): raise ValueError('Sampling requires exactly pretest 504 aligned returns and at least 10 stocks')
    rng=np.random.default_rng(np.random.SeedSequence(seed,spawn_key=(0,))); scenario_seed=int(np.random.SeedSequence(seed,spawn_key=(1,)).generate_state(1)[0]); symbols=list(training.columns); corr=training.corr()
    if not np.isfinite(corr).all().all(): raise ValueError('Invalid training correlation')
    definitions=[]
    for group in GROUPS:
        for number in range(50):
            count=(5 if number<25 else 10) if group=='breadth' else int(rng.integers(5,11))
            for attempt in range(1,max_attempts+1):
                if group=='training_correlated':
                    anchor=str(rng.choice(symbols)); neighbors=corr[anchor].drop(anchor).sort_values(ascending=False,kind='stable').index[:count-1].tolist(); selected=[anchor]+neighbors
                else: selected=[str(x) for x in rng.choice(symbols,count,replace=False)]
                cash=float(rng.choice([0.,.1])) if group=='cash_boundary' else float(rng.uniform(0,.1))
                alpha=.35 if group=='concentrated' else 3.
                w=rng.dirichlet(np.full(count,alpha))*(1-cash)
                if group=='cash_boundary': w=np.r_[.6,rng.dirichlet(np.full(count-1,3.))*(.4-cash)]
                if np.max(w)<=.6: break
            else: raise ValueError('Frozen sampler rejection limit exhausted; no partial cohort')
            definitions.append({'portfolio_id':f'{group}-{number:03d}','group':group,'symbols':selected,'weights':np.r_[w,cash].tolist(),'initial_nav_usd':100000.,'hhi':float(w@w+cash*cash),'attempts':attempt,'sampling_seed':seed,'selection_basis':'Alpaca pretest 504-return correlation only' if group=='training_correlated' else 'Seeded holdings draw independent of test returns'})
    return {'lane':'EXPLORATORY_REAL_MARKET','validated':False,'requested_count':250,'groups':list(GROUPS),'holdings_seed':seed,'scenario_seed':scenario_seed,'streams':{'holdings_spawn_key':[0],'scenario_spawn_key':[1]},'training_start':str(training.index[0].date()),'training_end':str(training.index[-1].date()),'definitions_sha256':hashlib.sha256(json.dumps(definitions,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'portfolios':definitions,'no_resampling':'Definitions drawn once and reused for both feeds and every rebalance; only held names plus cash.'}


def _tail_columns(losses,alpha):
    ordered=np.sort(losses,axis=0)[::-1]; mass=len(ordered)*(1-alpha); whole=int(mass)
    return (ordered[:whole].sum(axis=0)+(mass-whole)*ordered[min(whole,len(ordered)-1)])/mass


def replay_account(returns,definition,scenario_seed,fit_cache=None,max_folds=None,scenario_count=1000):
    """Research-only close-return replay. Cache fit inputs only, never trade solutions."""
    selected=definition['symbols']
    if not 5<=len(selected)<=10 or len(set(selected))!=len(selected): raise ValueError('Expected 5-10 distinct held symbols')
    if max_folds is not None and (not isinstance(max_folds,int) or max_folds<1): raise ValueError('Invalid smoke fold count')
    frame=returns.loc[:,selected]; data=frame.to_numpy(float); n=len(selected); alpha=.95; c=Constraints(max_weight=.6,max_cash=.1,max_turnover=2,cost_budget=.01,cost_rate=.001)
    if len(frame)<=504 or not np.isfinite(data).all() or (data< -1).any() or frame.index.has_duplicates or not frame.index.is_monotonic_increasing: raise ValueError('Invalid exploratory replay returns')
    initial=np.array(definition['weights'],float); c.validate(n+1)
    if initial.shape!=(n+1,) or not np.isfinite(initial).all() or (initial<0).any() or not np.isclose(initial.sum(),1) or residuals(initial,initial,c)[0]>1e-6: raise ValueError('Initial definition violates frozen mandate')
    nav0=float(definition['initial_nav_usd'])
    if not np.isfinite(nav0) or nav0<=0: raise ValueError('Invalid initial NAV')
    cache={} if fit_cache is None else fit_cache
    states={name:initial.copy() for name in STRATEGIES}; navs={name:nav0 for name in STRATEGIES}; strategy={name:{'initial_nav_usd':nav0,'folds':[],'failures':[],'daily':{key:[] for key in ('nav_usd','net_return','forecast_daily_var','forecast_daily_es','forecast_daily_volatility','var_exceedance','tail_excess_loss','cost_fraction','turnover','hhi','weight_change','variance_forecast_squared_error')}} for name in STRATEGIES}; folds=[]; date_labels=[]
    starts=list(range(504,len(frame),63)); starts=starts if max_folds is None else starts[:max_folds]
    if not starts: raise ValueError('No exploratory test folds')
    for fold,start in enumerate(starts):
        stop=min(start+63,len(frame)); train=data[start-504:start]; test=np.c_[data[start:stop],np.zeros(stop-start)]; key=(hashlib.sha256(train.tobytes()).hexdigest(),tuple(selected),str(frame.index[start-504]),str(frame.index[start-1]),(scenario_seed+fold)%(2**32),scenario_count)
        if key not in cache:
            sigma=covariance(train); bl=black_litterman(sigma,np.zeros(n)); R=np.c_[scenarios(train,bl['mean'],sigma,scenario_count,(scenario_seed+fold)%(2**32)),np.zeros(scenario_count)]
            cache[key]={'sigma':np.pad(sigma,((0,1),(0,1))),'scenarios':R,'mean':np.r_[bl['mean'],0.]}
        fitted=cache[key]; sigma=fitted['sigma']; R=fitted['scenarios']; mu=fitted['mean']; growth=np.cumprod(1+test,axis=0)
        folds.append({'fold':fold,'train_start':str(frame.index[start-504].date()),'train_end':str(frame.index[start-1].date()),'test_start':str(frame.index[start].date()),'test_end':str(frame.index[stop-1].date()),'test_tail_warning':len(test)*.05<20})
        date_labels.extend(str(d.date()) for d in frame.index[start:stop])
        for name in STRATEGIES:
            current=states[name]; x=current.copy(); cost=0.; turnover=0.; pre_nav=navs[name]; failure=None; maximum=0.
            try:
                if name!='buy_hold':
                    method={'equal_weight':'target','risk_parity':'target','min_variance':'min_variance','bl_mv':'mv','min_cvar':'min_cvar','bl_cvar':'cvar'}[name]
                    target=np.r_[np.full(n,.9/n),.1] if name=='equal_weight' else np.r_[.9*_erc(sigma[:-1,:-1]),.1] if name=='risk_parity' else None
                    cfg=replace(c,cost_rate=0.) if name=='min_variance' else c
                    result=optimize(R,mu,current,sigma,cfg,alpha,1.,method,target)
                    if name=='min_variance': result=optimize(R,mu,current,sigma,c,alpha,1.,'target',result['weights'])
                    x=result['pre_nav_fractions']; cost=result['cost']; turnover=result['turnover']; maximum=result['max_residual']
            except (ValueError,np.linalg.LinAlgError) as exc:
                failure={'fold':fold,'reason':str(exc),'fallback':'Hold existing state, retain every test date; no constraint relaxation'};strategy[name]['failures'].append(failure)
            if name!='buy_hold': maximum=residuals(x,current,c)[0]
            values=growth@x
            if not np.isfinite(values).all() or (values<=0).any(): raise ValueError('Nonpositive or nonfinite realized account wealth')
            exposures=np.vstack([x,growth[:-1]*x/values[:-1,None]]); daily_cost=np.r_[cost,np.zeros(len(test)-1)]
            losses=-R@exposures.T+daily_cost
            vars=np.quantile(losses,alpha,axis=0,method='higher'); es=_tail_columns(losses,alpha)
            net=values/np.r_[1.,values[:-1]]-1; end_weights=growth*x/values[:,None]; predicted_var=np.einsum('ij,jk,ik->i',exposures,sigma,exposures)
            path=pre_nav*values; changes=np.abs(end_weights-np.vstack([current,end_weights[:-1]])).sum(axis=1)
            daily={'nav_usd':path,'net_return':net,'forecast_daily_var':vars,'forecast_daily_es':es,'forecast_daily_volatility':np.sqrt(np.maximum(predicted_var,0)),'var_exceedance':-net>vars,'tail_excess_loss':np.maximum(0,-net-vars),'cost_fraction':daily_cost,'turnover':np.r_[turnover,np.zeros(len(test)-1)],'hhi':np.sum(end_weights**2,axis=1),'weight_change':changes,'variance_forecast_squared_error':(predicted_var-np.sum(test*exposures,axis=1)**2)**2}
            for key,array in daily.items(): strategy[name]['daily'][key].extend(array.tolist())
            strategy[name]['folds'].append({'fold':fold,'pre_trade_nav_usd':pre_nav,'current_weights':current.tolist(),'pre_nav_fractions':x.tolist(),'post_cost_weights':(x/(1-cost)).tolist(),'risky_trades_usd':((x[:-1]-current[:-1])*pre_nav).tolist(),'cost_usd':float(cost*pre_nav),'two_sided_turnover':float(turnover),'max_residual':maximum,'failure':failure,'constraint_exemption':name=='buy_hold'})
            states[name]=end_weights[-1];navs[name]=float(path[-1])
    for name,result in strategy.items():
        d=result['daily']; a=np.array(d['net_return']); vol=float(np.std(a,ddof=1)); downside=float(np.sqrt(np.mean(np.minimum(a,0)**2)))
        result['metrics']={'net_total_return':navs[name]/nav0-1,'annualized_volatility':vol*np.sqrt(252),'sharpe_zero_rate':float(a.mean()/vol*np.sqrt(252)) if vol>1e-12 else None,'sortino_zero_rate':float(a.mean()/downside*np.sqrt(252)) if downside>1e-12 else None,'maximum_drawdown':max_drawdown(a),'daily_realized_es95':empirical_es(-a,alpha),'var_exceedance_frequency':float(np.mean(d['var_exceedance'])),'mean_tail_excess_loss':float(np.mean(d['tail_excess_loss'])),'two_sided_turnover':float(sum(d['turnover'])),'total_cost_usd':sum(f['cost_usd'] for f in result['folds']),'mean_hhi':float(np.mean(d['hhi'])),'mean_weight_change':float(np.mean(d['weight_change'])),'variance_forecast_mse':float(np.mean(d['variance_forecast_squared_error'])),'failed_folds':len(result['failures']),'constraint_violations':sum(f['max_residual']>1e-6 for f in result['folds']),'tail_warning':len(a)*.05<20}
    return {'portfolio_id':definition['portfolio_id'],'group':definition['group'],'lane':'EXPLORATORY_REAL_MARKET','status':'HISTORICAL_RETURN_REPLAY','decision':'NO_TRADE','validated':False,'definition':definition,'dates':date_labels,'folds':folds,'strategies':strategy,'configuration':{'train':504,'step':63,'scenario_count':scenario_count,'scenario_seed':scenario_seed,'alpha':alpha,'risk_aversion':1.,'cash_rate':0.,'prior':'zero excess, no views','constraints':asdict(c)},'mandates':'Same initial holdings/NAV. Buy-and-hold exempt from rebalance caps. Equal-weight/ERC retain 10% cash; constrained optimizers may use 0-10%. Minvariance fits pure variance target then pays actual costs. All fractions continuous, not shares or executable fills.','inference':'No per-account bootstrap or independent-market claim; date-block aggregation belongs to the matched report.'}
