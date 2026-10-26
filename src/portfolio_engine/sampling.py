"""Frozen initial holdings only. This sampler never receives prices or future returns."""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from .data import utc

GROUPS=('diversified','concentrated','sector_heavy','stock_etf_mix','cash_boundary')
VERIFICATION=('identity','tradability','point_in_time','corporate_actions','delistings','session_calendar','adjustment_policy','usage_rights','daily_usd_total_returns')


def sample_portfolios(universe,start_at,seed=42,max_attempts=1000):
    """Accept externally verified dated metadata; return all 250 definitions or BLOCKED.

    External verification is an attestation, not authenticated by this local library.
    Required schema is documented in README. No performance-dependent sampling exists.
    """
    start=utc(start_at)
    result={'status':'BLOCKED','portfolios':[],'groups':list(GROUPS),'holdings_seed':seed,'start_at':start.isoformat(),'initial_nav_usd':100000.,'max_attempts_per_portfolio':max_attempts,'provenance':universe,'verification_limit':'External attestations are not independently authenticated by the sampler.'}
    v=universe.get('verification',{})
    try:
        valid=all(v.get(key) is True for key in VERIFICATION) and bool(v.get('source')) and utc(v['available_at'])<=start and bool(universe.get('provider')) and bool(universe.get('permitted_usage')) and bool(universe.get('source_hashes')) and isinstance(universe['source_hashes'],dict) and all(isinstance(h,str) and re.fullmatch(r'[0-9a-fA-F]{64}',h) for h in universe['source_hashes'].values())
    except (ValueError,TypeError,KeyError): valid=False
    if not valid:
        result['reason']='Missing or future-dated independent universe verification, rights, or provenance'
        return result
    if not isinstance(seed,int) or seed<0 or not isinstance(max_attempts,int) or max_attempts<1: raise ValueError('Invalid sampler seed/attempt limit')
    assets=[]; exclusions=[]; seen=set(); identifiers=set(); duplicate_identity=False
    for asset in universe.get('assets',[]):
        try:
            symbol=asset['symbol']
            eligible=isinstance(symbol,str) and bool(symbol.strip()) and symbol==symbol.strip() and symbol!='CASH' and symbol not in seen and bool(asset['permanent_id']) and asset.get('currency')=='USD' and asset.get('market')=='US' and asset.get('asset_type') in {None,'STOCK','ETF'} and utc(asset['known_at'])<=start and utc(asset['history_asof'])<=start and pd.Timestamp(asset['eligible_from']).date()<=start.date() and isinstance(asset['history_observations_asof'],int) and asset['history_observations_asof']>=504
            if asset.get('eligible_until'): eligible=eligible and pd.Timestamp(asset['eligible_until']).date()>=start.date()
            if asset.get('permanent_id') in identifiers: duplicate_identity=True
            identifiers.add(asset.get('permanent_id')); seen.add(symbol)
        except (KeyError,ValueError,TypeError): eligible=False
        if eligible: assets.append(dict(asset))
        else: exclusions.append({'symbol':asset.get('symbol'),'reason':'Identity, dated eligibility, or pre-start 504-observation coverage not established'})
    result['exclusions']=exclusions
    if len(assets)<2:
        result['reason']='Fewer than two dated eligible assets; mandate cannot be sampled'
        return result
    if duplicate_identity or len(seen)!=len(universe.get('assets',[])):
        result['reason']='Duplicate or malformed universe symbols'
        return result
    rng=np.random.default_rng(np.random.SeedSequence(seed,spawn_key=(0,)))
    result['scenario_seed']=int(np.random.SeedSequence(seed,spawn_key=(1,)).generate_state(1)[0])
    result['rng_streams']={'holdings_spawn_key':[0],'scenario_spawn_key':[1]}
    sectors={}
    for i,a in enumerate(assets):
        if a.get('sector'): sectors.setdefault(a['sector'],[]).append(i)
    sectors={s:idx for s,idx in sectors.items() if len(idx)>=2}
    stocks=[i for i,a in enumerate(assets) if a.get('asset_type')=='STOCK']; etfs=[i for i,a in enumerate(assets) if a.get('asset_type')=='ETF']
    result['held_asset_count_range']=[min(5,len(assets)),min(10,len(assets))]
    result['asset_count_adaptation']='Fewer than five eligible assets; use every available risky name' if len(assets)<5 else None
    result['fallbacks']=[]
    if not sectors: result['fallbacks'].append({'group':'sector_heavy','alternative':'concentrated','reason':'Dated sector stratum unavailable'})
    if not stocks or not etfs: result['fallbacks'].append({'group':'stock_etf_mix','alternative':'concentrated','reason':'Dated STOCK/ETF stratum unavailable'})
    definitions=[]
    for group in GROUPS:
        for number in range(50):
            accepted=False
            for attempt in range(1,max_attempts+1):
                count=int(rng.integers(min(5,len(assets)),min(10,len(assets))+1))
                selected=list(rng.choice(len(assets),count,replace=False)); stratum=group
                if group=='sector_heavy' and sectors:
                    sector=sorted(sectors)[int(rng.integers(len(sectors)))]
                    chosen=list(rng.choice(sectors[sector],min(count,len(sectors[sector])),replace=False))
                    remaining=[i for i in range(len(assets)) if i not in chosen]
                    selected=chosen+list(rng.choice(remaining,count-len(chosen),replace=False))
                elif group=='sector_heavy': stratum='concentrated_fallback'
                if group=='stock_etf_mix' and stocks and etfs:
                    chosen=[int(rng.choice(stocks)),int(rng.choice(etfs))]
                    selected=chosen+list(rng.choice([i for i in range(len(assets)) if i not in chosen],count-2,replace=False))
                elif group=='stock_etf_mix': stratum='concentrated_fallback'
                sector_count=len(chosen) if group=='sector_heavy' and sectors else 0
                cash=float(rng.choice([0.,.1])) if group=='cash_boundary' else float(rng.uniform(0,.1))
                profile=.35 if stratum in {'concentrated','concentrated_fallback'} else 3.
                weights=rng.dirichlet(np.full(count,profile))*(1-cash)
                if group=='sector_heavy' and sectors and sector_count<count:
                    weights=np.r_[rng.dirichlet(np.full(sector_count,3.))*.75,rng.dirichlet(np.full(count-sector_count,3.))*.25]*(1-cash)
                if group=='cash_boundary': weights=np.r_[.6,rng.dirichlet(np.full(count-1,3.))*(.4-cash)]
                if np.max(weights)<=.6 and np.min(weights)>=0 and abs(weights.sum()+cash-1)<1e-12:
                    accepted=True; break
            if not accepted:
                result['reason']=f'Finite rejection limit reached in {group}; no partial primary sample returned'
                return result
            symbols=[assets[i]['symbol'] for i in selected]
            definitions.append({'portfolio_id':f'{group}-{number:03d}','group':group,'stratum':stratum,'symbols':symbols,'permanent_ids':[assets[i]['permanent_id'] for i in selected],'weights':weights.tolist(),'cash_weight':cash,'initial_nav_usd':100000.,'hhi_including_cash':float(weights@weights+cash*cash),'eligibility_timestamp':start.isoformat(),'attempts':attempt,'holdings_seed':seed,'history_observations_asof':{a['symbol']:a['history_observations_asof'] for a in (assets[i] for i in selected)}})
    result.update(status='READY',portfolios=definitions,eligible_symbols=[a['symbol'] for a in assets],sampling_policy='Initial state once only; no resampling at any rebalance. Held universe plus cash only. No prices/returns supplied to sampler.')
    result['definitions_sha256']=hashlib.sha256(json.dumps(definitions,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result


def save_definitions(result,path):
    """Exclusive-create a saved result; existing experiment definitions are immutable."""
    with Path(path).open('x') as stream:
        json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False)
