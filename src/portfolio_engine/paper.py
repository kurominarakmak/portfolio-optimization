"""Immutable first decision plus hash-chained, append-only statistical paper replay.

Total-return unit prices are anchored to snapshot prices. They are not subsequent
raw executable quotes: reinvested distributions/corporate actions are represented
by supplied total returns. No order or brokerage connection exists here.
"""
from dataclasses import asdict
import fcntl
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from .cli import analyze,json_value
from .data import read_portfolio,validate_returns,utc
from .models import empirical_es,max_drawdown,scenarios
from .optimize import Constraints,optimize,preview_shares,residuals


def _canonical(value):
    return json.dumps(value,default=json_value,sort_keys=True,separators=(',',':'),allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _utc_now():
    return pd.Timestamp.now(tz='UTC')


def _commit_head(directory,event):
    # Journal is fsynced first. Any interrupted commit leaves a detectable mismatch.
    head={'snapshot_id':event['snapshot_id'],'sequence':event['sequence'],'event_hash':event['event_hash']}
    with tempfile.NamedTemporaryFile(mode='w',dir=directory,prefix='.head-',delete=False) as stream:
        temporary=stream.name; stream.write(_canonical(head)+'\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary,Path(directory)/'committed_head.json')
    descriptor=os.open(directory,os.O_RDONLY)
    try: os.fsync(descriptor)
    finally: os.close(descriptor)


def _book(quantity,cash,prices,original,cost=0.,failure=None):
    q=np.asarray(quantity,float); price=np.asarray(prices,float)
    nav=float(q@price+cash)
    if not np.isfinite(q).all() or not np.isfinite(cash) or not np.isfinite(nav) or (q<0).any() or cash<0 or nav<=0: raise ValueError('Invalid paper accounting')
    if not np.isclose(nav+cost,original,atol=.01,rtol=0): raise ValueError('Paper initial cash/cost does not reconcile')
    return {'quantity':q.tolist(),'cash_usd':float(cash),'nav_usd':nav,'initial_nav_usd':float(original),'initial_cost_usd':float(cost),'initial_turnover_usd':None,'failure':failure}


def start_paper(directory,portfolio,returns,metadata,holdings_provenance,as_of,constraints=None,seed=42,scenario_count=1000,alpha=.95,risk_aversion=1.,cash_rate=0.,prior=None,views=None,evidence=None):
    """Freeze a first decision before future observations. Creates a NEW directory.

    Benchmark: one initial 90% equal-risky/10% cash target, then hold. Optimized
    book: one initial feasible whole-share preview, then hold, always exploratory.
    Failed initial target/preview is recorded and that book holds original shares.
    """
    stamp=utc(as_of); c=constraints or Constraints(max_cash=.1,cost_budget=.01)
    c.validate(len(portfolio['symbols']))
    if not holdings_provenance.get('source') or holdings_provenance.get('kind') not in {'observed','synthetic'}: raise ValueError('Explicit holdings provenance required')
    # Recheck the existing normalized portfolio trust boundary before freezing it.
    cols=['quantity','price','currency','valuation_timestamp','nav']
    if 'cost_basis' in portfolio['positions']: cols.append('cost_basis')
    normalized=read_portfolio(io.StringIO(portfolio['positions'][cols].reset_index().to_csv(index=False)),as_of)
    if normalized['symbols']!=portfolio['symbols'] or not np.allclose(normalized['weights'],portfolio['weights'],atol=1e-12): raise ValueError('Normalized portfolio was modified')
    portfolio=normalized
    r=validate_returns(returns,metadata,portfolio['symbols'][:-1])
    if utc(metadata['retrieved_at'])>stamp or r.index[-1].date()>utc(portfolio['timestamp']).date(): raise ValueError('Cannot freeze model with future or post-valuation observations')
    report=analyze(portfolio,r,metadata,c,seed,scenario_count,alpha,risk_aversion,prior,views,evidence,cash_rate,as_of)
    genuine=holdings_provenance.get('kind')=='observed' and holdings_provenance.get('genuine_holdings_verified') is True
    if not genuine:
        report['decision']='NO_TRADE'; report['reason']='Genuine verified holdings absent; paper infrastructure fixture only'
    price=portfolio['positions'].price.to_numpy()[:-1]; old=portfolio['positions'].quantity.to_numpy()[:-1]; cash=float(portfolio['positions'].quantity.iloc[-1]); nav=portfolio['nav']
    hold=_book(old,cash,price,nav)
    books={'hold':hold}
    for name in ('equal_weight','optimized_exploratory'):
        try:
            if name=='equal_weight':
                n=len(old); target=np.r_[np.full(n,.9/n),.1]
                candidate=optimize(np.zeros((1,n+1)),np.zeros(n+1),portfolio['weights'],np.zeros((n+1,n+1)),c,alpha,risk_aversion,'target',target)
                if np.allclose(target,portfolio['weights'],atol=1e-12,rtol=0) and residuals(portfolio['weights'],portfolio['weights'],c)[0]<=1e-6:
                    preview={'quantity':old,'cash_usd':cash,'cost_usd':0.}
                else: preview=preview_shares(candidate,portfolio,c)
            else:
                preview=report.get('whole_share_preview',{})
                if 'quantity' not in preview: raise ValueError(preview.get('error',report.get('reason','No feasible optimized preview')))
            book=_book(preview['quantity'],preview['cash_usd'],price,nav,preview['cost_usd'])
            book['initial_turnover_usd']=float(np.abs(np.array(book['quantity'])-old)@price)
        except ValueError as exc:
            book=_book(old,cash,price,nav,failure=str(exc)); book['initial_turnover_usd']=0.
        books[name]=book
    books['hold']['initial_turnover_usd']=0.
    for book in books.values(): book['initial_trades_quantity']=(np.array(book['quantity'])-old).tolist()
    config={'constraints':asdict(c),'seed':seed,'scenario_count':scenario_count,'alpha':alpha,'risk_aversion':risk_aversion,'cash_rate':cash_rate,'prior':prior,'views':views,'policies':'Hold original; equal-weight once then hold; optimized exploratory once then hold. No resampling/rebalancing on updates.'}
    market={'dates':[str(d.date()) for d in r.index],'symbols':list(r.columns),'returns':r.to_numpy().tolist(),'provenance':metadata}
    payload={'format_version':1,'decision_at':stamp.isoformat(),'valuation_timestamp':portfolio['timestamp'],'initial_nav_usd':nav,'symbols':portfolio['symbols'],'initial_unit_prices':price.tolist(),'original_positions':portfolio['positions'].reset_index().to_dict(orient='records'),'holdings_provenance':holdings_provenance,'market_snapshot':market,'config':config,'config_sha256':_digest(config),'model_sha256':_digest(report['bl']),'data_sha256':_digest(market),'first_decision':report,'proposal_id':report.get('proposal_id'),'books':books,'genuine_holdings':genuine,'live_forward_status':'NOT_STARTED','mode':'Statistical total-return unit replay; snapshot-date hypothetical trades only, no executable-price verification and no real orders.'}
    wrapper={'snapshot_id':_digest(payload),'payload':payload}
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=False)
    with (directory/'snapshot.json').open('x') as stream: stream.write(_canonical(wrapper)+'\n'); stream.flush(); os.fsync(stream.fileno())
    with (directory/'events.jsonl').open('x') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        event={'sequence':0,'snapshot_id':wrapper['snapshot_id'],'previous_hash':wrapper['snapshot_id'],'date':stamp.isoformat(),'type':'initial','books':books,'unit_prices':price.tolist()}
        event['event_hash']=_digest(event); stream.write(_canonical(event)+'\n'); stream.flush(); os.fsync(stream.fileno())
        _commit_head(directory,event)
    return read_paper(directory)


def _load(directory,stream):
    directory=Path(directory); wrapper=json.loads((directory/'snapshot.json').read_text()); snapshot=wrapper['payload']; identifier=wrapper['snapshot_id']
    if _digest(snapshot)!=identifier or _digest(snapshot['first_decision']['bl'])!=snapshot['model_sha256'] or _digest(snapshot['config'])!=snapshot['config_sha256'] or _digest(snapshot['market_snapshot'])!=snapshot['data_sha256']: raise ValueError('Snapshot fingerprint mismatch; immutable state modified')
    text=stream.read()
    events=[]; previous=identifier
    for number,line in enumerate(text.splitlines()):
        event=json.loads(line); claimed=event.pop('event_hash')
        if claimed!=_digest(event) or event['previous_hash']!=previous or event['snapshot_id']!=identifier or event['sequence']!=number: raise ValueError('Paper ledger fingerprint or sequence mismatch')
        event['event_hash']=claimed; events.append(event); previous=claimed
    if not events or events[0]['type']!='initial' or events[0]['books']!=snapshot['books']: raise ValueError('Missing or modified initial paper ledger')
    try: head=json.loads((directory/'committed_head.json').read_text())
    except FileNotFoundError: raise ValueError('Missing independent committed head; ledger cannot be trusted') from None
    expected={'snapshot_id':identifier,'sequence':events[-1]['sequence'],'event_hash':events[-1]['event_hash']}
    if head!=expected: raise ValueError('Paper ledger does not match independent committed head; possible truncation or interrupted commit')
    return identifier,snapshot,events


def _summary(identifier,snapshot,events):
    books=json.loads(_canonical(events[-1]['books'])); alpha=snapshot['config']['alpha']; future=[e for e in events if e['type']=='observation']
    for name,book in books.items():
        values=np.array([e['books'][name]['net_return'] for e in future])
        book['net_return_from_initial_nav']=float(book['nav_usd']/snapshot['initial_nav_usd']-1)
        book['observations']=len(values)
        # Include initial costs in drawdown, but do not pretend a trade instant is a trading day.
        initial=events[0]['books'][name]['nav_usd']/snapshot['initial_nav_usd']-1
        book['maximum_drawdown_including_initial_cost']=max_drawdown(np.r_[initial,values])
        book['realized_daily_volatility']=float(np.std(values,ddof=1)) if len(values)>1 else None
        book['realized_daily_es']=empirical_es(-values,alpha) if len(values)*(1-alpha)>=20 else None
        book['tail_warning']='Insufficient forward tail observations' if book['realized_daily_es'] is None else 'Empirical forward ES remains sampling-uncertain'
        book['forecast_var_exceedance_frequency']=float(np.mean([e['books'][name]['var_exceedance'] for e in future])) if future else None
        book['forecast_mean_squared_error']=float(np.mean([e['books'][name]['forecast_squared_error'] for e in future])) if future else None
        book['total_transaction_cost_usd']=book['initial_cost_usd']
    qualified=all(e.get('observation_verified') is True for e in future) and snapshot['genuine_holdings'] and snapshot['market_snapshot']['provenance'].get('kind')=='observed' and snapshot['market_snapshot']['provenance'].get('investable') is True and snapshot['market_snapshot']['provenance'].get('session_coverage_verified') is True and bool(snapshot['market_snapshot']['provenance'].get('calendar_source')) and bool(snapshot['market_snapshot']['provenance'].get('expected_sessions'))
    return {'snapshot_id':identifier,'first_decision':snapshot['first_decision'],'proposal_id':snapshot['proposal_id'],'config_sha256':snapshot['config_sha256'],'model_sha256':snapshot['model_sha256'],'data_sha256':snapshot['data_sha256'],'books':books,'observations':len(future),'last_date':events[-1]['date'],'live_forward_status':'OBSERVING_PAPER_ONLY' if qualified and future else 'NOT_STARTED','mode':snapshot['mode'],'ledger_hash':events[-1]['event_hash'],'committed_sequence':events[-1]['sequence'],'last_update_at':events[-1].get('updated_at'),'no_execution':True}


def read_paper(directory):
    """Verify frozen snapshot and entire hash chain before returning current state."""
    with (Path(directory)/'events.jsonl').open('r') as stream:
        fcntl.flock(stream,fcntl.LOCK_SH)
        return _summary(*_load(directory,stream))


def update_paper(directory,returns,metadata,synthetic_replay=False):
    """Append new dated total-return observations, never refit or modify decisions.

    Supply the full validated cumulative snapshot (original history plus updates).
    Revisions to any previously stored return are rejected. Repeated inputs are
    idempotent; any missing previously observed date is rejected. Local writers
    are serialized with an exclusive POSIX file lock.
    """
    directory=Path(directory)
    with (directory/'events.jsonl').open('r+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        identifier,snapshot,events=_load(directory,stream)
        cutoff=_utc_now()
        symbols=snapshot['symbols'][:-1]; r=validate_returns(returns,metadata,symbols)
        original=snapshot['market_snapshot']; previous=pd.DataFrame(original['returns'],index=pd.to_datetime(original['dates']),columns=symbols)
        for event in events[1:]: previous.loc[pd.Timestamp(event['date'])]=event['returns']
        if not previous.index.isin(r.index).all() or not np.array_equal(r.loc[previous.index].to_numpy(),previous.to_numpy()): raise ValueError('Previously observed history revised or removed')
        if metadata['kind']!=original['provenance']['kind']: raise ValueError('Cannot relabel synthetic history as observed')
        if synthetic_replay and (metadata['kind']!='synthetic' or original['provenance']['kind']!='synthetic' or snapshot['genuine_holdings']): raise ValueError('Synthetic replay is restricted to explicitly synthetic, nongenuine cohorts')
        if not synthetic_replay and (utc(metadata['retrieved_at'])>cutoff or r.index[-1].tz_localize('UTC')>cutoff): raise ValueError('Future retrieval or observation exceeds actual UTC update cutoff')
        if utc(metadata['retrieved_at']).date()<r.index[-1].date(): raise ValueError('Observation retrieval precedes future data')
        decision=utc(snapshot['decision_at']); last=pd.Timestamp(events[-1]['date'])
        if last.tzinfo is not None: last=last.tz_convert('UTC').tz_localize(None)
        unknown_before_decision=[d for d in r.index if d not in previous.index and d.date()<=decision.date()]
        if unknown_before_decision: raise ValueError('New past observations cannot revise the frozen decision snapshot')
        fresh=r.loc[r.index>last.normalize()]
        if len(fresh) and fresh.index[0].date()<=decision.date(): raise ValueError('Future observations must strictly follow decision snapshot')
        state=json.loads(_canonical(events[-1]['books'])); prices=np.array(events[-1]['unit_prices']); additions=[]; predecessor=events[-1]['event_hash']
        history=np.array(original['returns']); model=snapshot['first_decision']['bl']; cfg=snapshot['config']
        mu=np.r_[np.array(model['mean'])+cfg['cash_rate'],cfg['cash_rate']]
        S=scenarios(history,mu[:-1],np.array(model['innovation_covariance']),cfg['scenario_count'],cfg['seed'])
        R=np.c_[S,np.full(len(S),cfg['cash_rate'])]
        for date,row in fresh.iterrows():
            old_prices=prices.copy(); rr=row.to_numpy(); prices=prices*(1+rr)
            if not np.isfinite(prices).all() or (prices<=0).any(): raise ValueError('Unsupported zero/nonfinite total-return unit price')
            next_books={}
            for name,book in state.items():
                quantity=np.array(book['quantity']); cash=book['cash_usd']*(1+snapshot['config']['cash_rate']); nav=float(quantity@prices+cash)
                if not np.isfinite(nav) or nav<=0 or cash<0: raise ValueError('Paper cash/NAV failed reconciliation')
                net=nav/book['nav_usd']-1
                start_weights=np.r_[quantity*old_prices,book['cash_usd']]/book['nav_usd']
                losses=-R@start_weights; var=float(np.quantile(losses,cfg['alpha'],method='higher'))
                forecast={'forecast_daily_var':var,'forecast_daily_es':empirical_es(losses,cfg['alpha']),'var_exceedance':bool(-net>var),'forecast_squared_error':float((net-mu@start_weights)**2),'forecast_basis':'Frozen first-decision conditional model at drifted start weights; initial costs already debited, no repeated cost'}
                next_books[name]={**book,**forecast,'cash_usd':float(cash),'nav_usd':nav,'net_return':float(net),'weights':(np.r_[quantity*prices,cash]/nav).tolist(),'transaction_cost_usd':0.,'turnover_usd':0.}
            event={'sequence':len(events)+len(additions),'snapshot_id':identifier,'previous_hash':predecessor,'type':'observation','date':str(date.date()),'returns':rr.tolist(),'unit_prices':prices.tolist(),'books':next_books,'updated_at':cutoff.isoformat(),'update_cutoff_utc':cutoff.isoformat(),'synthetic_replay':synthetic_replay,'observation_metadata_sha256':_digest(metadata),'observation_verified':not synthetic_replay and metadata.get('kind')=='observed' and metadata.get('investable') is True and metadata.get('session_coverage_verified') is True and bool(metadata.get('calendar_source')) and bool(metadata.get('expected_sessions'))}
            if not additions: event['observation_metadata']=metadata
            event['event_hash']=_digest(event); predecessor=event['event_hash']; additions.append(event); state=next_books
        # Validate the whole batch before appending, so bad later rows do not partly update it.
        stream.seek(0,2)
        if additions:
            stream.write(''.join(_canonical(event)+'\n' for event in additions)); stream.flush(); os.fsync(stream.fileno())
            _commit_head(directory,additions[-1])
        return _summary(identifier,snapshot,events+additions)
