"""Verify and summarize completed frozen exploratory runs; never consumes partial files."""
import argparse
import gc
import hashlib
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from portfolio_engine.exploratory import STRATEGIES,GROUPS,START,END,file_hash
from portfolio_engine.models import empirical_es,stationary_indices

BASELINES=('buy_hold','equal_weight','min_variance','min_cvar','bl_mv')
METRICS=('net_total_return','annualized_volatility','sharpe_zero_rate','sortino_zero_rate','maximum_drawdown','daily_realized_es95','var_exceedance_frequency','two_sided_turnover','total_cost_usd','mean_hhi','mean_weight_change','variance_forecast_mse','failed_folds','constraint_violations')


def distribution(values):
    valid=np.array([v for v in values if v is not None],float)
    if len(valid) and not np.isfinite(valid).all(): raise ValueError('Nonfinite summary metric')
    result={'n':len(valid),'missing':len(values)-len(valid)}
    if len(valid):
        result.update(mean=float(valid.mean()),median=float(np.median(valid)),minimum=float(valid.min()),maximum=float(valid.max()),lower_decile_mean=float(np.sort(valid)[:max(1,int(np.ceil(.1*len(valid))))].mean()))
        result.update(zip(('p5','p25','p75','p95'),np.quantile(valid,[.05,.25,.75,.95]).tolist()))
    return result


def paired_date_block_ci(daily_difference,seed=42,draws=500,block_length=10):
    series=np.asarray(daily_difference,float)
    if series.ndim!=1 or not len(series) or not np.isfinite(series).all(): raise ValueError('Invalid aligned daily contrast')
    rng=np.random.default_rng(seed)
    boot=[float(series[stationary_indices(len(series),len(series),rng,block_length)].mean()) for _ in range(draws)]
    return {'daily_mean_difference':float(series.mean()),'conditional_95_interval':np.quantile(boot,[.025,.975]).tolist(),'draws':draws,'block_length':block_length,'seed':seed,'unit':'daily decimal net return; not cumulative-return CI','sampling_unit':'Synchronized date blocks of the portfolio-mean paired daily difference; accounts are not independent histories'}


def verify_definitions(definitions):
    if definitions.get('lane')!='EXPLORATORY_REAL_MARKET' or definitions.get('validated') is not False or definitions.get('requested_count')!=250 or definitions.get('holdings_seed')!=42: raise ValueError('Frozen exploratory definition metadata mismatch')
    portfolios=definitions['portfolios']
    digest=hashlib.sha256(json.dumps(portfolios,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest!=definitions['definitions_sha256'] or len(portfolios)!=250 or len({p['portfolio_id'] for p in portfolios})!=250: raise ValueError('250 unique frozen definitions/hash required')
    if any(sum(p['group']==g for p in portfolios)!=50 for g in GROUPS): raise ValueError('Frozen five-group counts mismatch')
    return {p['portfolio_id']:p for p in portfolios}


def expected_grid(manifest,smoke):
    calendar=manifest['calendar'];path=Path(calendar['path'])
    if file_hash(path)!=calendar['sha256']: raise ValueError('Calendar source hash changed')
    rows=json.loads(path.read_text())['sessions']; prices=pd.DatetimeIndex([r['session_date'] for r in rows if START<=r['session_date']<=END])
    if len(prices)!=1366 or prices.has_duplicates or not prices.is_monotonic_increasing: raise ValueError('1366 frozen XNYS prices required')
    returns=prices[1:]; folds=[]
    for fold,start in enumerate(range(504,len(returns),63)):
        stop=min(start+63,len(returns));folds.append({'fold':fold,'train_start':str(returns[start-504].date()),'train_end':str(returns[start-1].date()),'test_start':str(returns[start].date()),'test_end':str(returns[stop-1].date())})
    return [str(d.date()) for d in (returns[504:567] if smoke else returns[504:])],folds[:1] if smoke else folds


def condense_provider(payload,definitions,dates,folds,smoke=False):
    config=payload['configuration']; expected=2 if smoke else 250
    if config.get('smoke') is not smoke or config.get('requested_portfolios_per_provider')!=250 or config.get('evaluated_portfolios_per_provider')!=expected or config.get('definitions_sha256')!=definitions['definitions_sha256']: raise ValueError('Full/smoke count or definition hash mismatch')
    for key,value in {'lane':'EXPLORATORY_REAL_MARKET','status':'HISTORICAL_RETURN_REPLAY','decision':'NO_TRADE','validated':False,'train':504,'step':63,'scenario_count':1000,'alpha':.95,'risk_aversion':1,'cost_rate':.001,'max_risky_weight':.6,'max_cash':.1,'cost_budget':.01,'seed':42}.items():
        if config.get(key)!=value: raise ValueError('Frozen configuration mismatch: '+key)
    all_defs=verify_definitions(definitions); wanted=list(all_defs)[:expected]; accounts=payload['accounts']
    if len(accounts)!=expected or len({a['portfolio_id'] for a in accounts})!=expected or set(a['portfolio_id'] for a in accounts)!=set(wanted): raise ValueError(f'{expected} matched account IDs required')
    if not smoke and (len(dates)!=861 or len(folds)!=14): raise ValueError('Full replay requires exactly 861 dates/14 folds')
    ordered={a['portfolio_id']:a for a in accounts}; summaries={};failed=[];failure_ledger=[];metrics={s:[] for s in STRATEGIES};arrays={s:{key:[] for key in ('net_return','forecast_daily_es','forecast_daily_var','post_cost_weights')} for s in STRATEGIES};valid=[]
    for identifier in wanted:
        account=ordered[identifier]
        if account.get('definition')!=all_defs[identifier]: raise ValueError('Account definition changed: '+identifier)
        if account.get('status')=='ACCOUNT_FAILED':
            failed.append({'portfolio_id':identifier,'reason':account.get('reason','Unspecified account failure')});continue
        if account.get('status')!='HISTORICAL_RETURN_REPLAY' or account.get('decision')!='NO_TRADE' or account.get('validated') is not False: raise ValueError('Unexpected actionable or invalid account status')
        if account.get('dates')!=dates or len(account.get('folds',[]))!=len(folds) or set(account.get('strategies',{}))!=set(STRATEGIES): raise ValueError('Account date/fold/strategy alignment mismatch: '+identifier)
        for actual,expected_fold in zip(account['folds'],folds):
            if any(actual.get(k)!=v for k,v in expected_fold.items()): raise ValueError('Fold chronology mismatch: '+identifier)
        for key,value in {'train':504,'step':63,'scenario_count':1000,'alpha':.95,'risk_aversion':1.,'scenario_seed':definitions['scenario_seed']}.items():
            if account.get('configuration',{}).get(key)!=value: raise ValueError('Account frozen model configuration mismatch')
        for key,value in {'max_weight':.6,'min_weight':0.,'min_cash':0.,'max_cash':.1,'max_turnover':2.,'cost_budget':.01,'cost_rate':.001,'sector_caps':{}}.items():
            if account['configuration'].get('constraints',{}).get(key)!=value: raise ValueError('Account constraint mismatch')
        if account['configuration'].get('cash_rate')!=0 or account['configuration'].get('constraints',{}).get('sectors'): raise ValueError('Cash-rate or sector mandate mismatch')
        valid.append(identifier); summaries[identifier]={'group':all_defs[identifier]['group'],'metrics':{}}
        for strategy in STRATEGIES:
            result=account['strategies'][strategy];daily=result['daily'];reported=result['metrics']
            if result['initial_nav_usd']!=100000 or len(result['folds'])!=len(folds): raise ValueError('Starting NAV/folds mismatch')
            for key,values in daily.items():
                if len(values)!=len(dates) or not np.isfinite(np.asarray(values,float)).all(): raise ValueError('Incomplete/nonfinite daily series: '+key)
            for key in ('net_return','nav_usd','forecast_daily_es','forecast_daily_var','cost_fraction','turnover'): 
                if key not in daily: raise ValueError('Missing daily field: '+key)
            r=np.asarray(daily['net_return']);nav=np.asarray(daily['nav_usd']); recomputed=100000*np.cumprod(1+r)
            if not np.allclose(nav,recomputed,atol=.001,rtol=1e-9): raise ValueError('Daily NAV/return reconciliation mismatch')
            if not np.isclose(reported['net_total_return'],nav[-1]/100000-1,atol=1e-10) or not np.isclose(reported['daily_realized_es95'],empirical_es(-r,.95),atol=1e-10): raise ValueError('Reported return/ES mismatch')
            if reported['failed_folds']!=len(result['failures']): raise ValueError('Failure count mismatch')
            actual_failed={f['fold'] for f in result['failures']};fold_failed={f['fold'] for f in result['folds'] if f.get('failure') is not None}
            if actual_failed!=fold_failed: raise ValueError('Failure ledger does not match fold state')
            for f in result['failures']: failure_ledger.append({'portfolio_id':identifier,'strategy':strategy,**f})
            for f in result['folds']:
                trades=np.abs(f['risky_trades_usd']).sum()
                if not np.isclose(f['cost_usd'],.001*trades,atol=.001,rtol=0): raise ValueError('Fold trade/cost reconciliation mismatch')
            item={key:reported[key] for key in METRICS};metrics[strategy].append(item);summaries[identifier]['metrics'][strategy]=item
            for key in ('net_return','forecast_daily_es','forecast_daily_var'): arrays[strategy][key].append(daily[key])
            arrays[strategy]['post_cost_weights'].append([f['post_cost_weights'] for f in result['folds']])
    for strategy in STRATEGIES:
        for key in arrays[strategy]:
            arrays[strategy][key]=[np.array(rows,float) for rows in arrays[strategy][key]] if key=='post_cost_weights' else np.array(arrays[strategy][key],float)
    dist={s:{m:distribution([v[m] for v in metrics[s]]) for m in METRICS} for s in STRATEGIES};paired={}; groups={};years={}
    for baseline in BASELINES:
        candidate=np.array([v['net_total_return'] for v in metrics['bl_cvar']]);base=np.array([v['net_total_return'] for v in metrics[baseline]])
        es=np.array([v['daily_realized_es95'] for v in metrics[baseline]])-np.array([v['daily_realized_es95'] for v in metrics['bl_cvar']]);delta=candidate-base
        paired[baseline]={'net_return_difference':distribution(delta.tolist()),'es_reduction':distribution(es.tolist()),'fraction_higher_net_return':float(np.mean(delta>1e-10)) if len(delta) else None,'fraction_lower_es':float(np.mean(es>1e-10)) if len(es) else None,'fraction_return_ties':float(np.mean(np.abs(delta)<=1e-10)) if len(delta) else None,'date_block_uncertainty':paired_date_block_ci((arrays['bl_cvar']['net_return']-arrays[baseline]['net_return']).mean(axis=0)) if valid else None}
    for group in GROUPS:
        idx=[i for i,k in enumerate(valid) if summaries[k]['group']==group]
        groups[group]={'valid_accounts':len(idx),'strategies':{s:{metric:distribution([metrics[s][i][metric] for i in idx]) for metric in ('net_total_return','daily_realized_es95','two_sided_turnover','total_cost_usd','failed_folds')} for s in STRATEGIES},'paired_vs_buy_hold':distribution([metrics['bl_cvar'][i]['net_total_return']-metrics['buy_hold'][i]['net_total_return'] for i in idx])}
    grid=pd.DatetimeIndex(dates)
    for year in sorted(set(grid.year)):
        mask=grid.year==year
        years[str(year)]={'observations':int(mask.sum()),'tail_warning':int(mask.sum())*.05<20,'strategies':{s:{'period_net_return':distribution((np.prod(1+arrays[s]['net_return'][:,mask],axis=1)-1).tolist()) if valid else distribution([]),'daily_realized_es95':distribution([empirical_es(-row,.95) for row in arrays[s]['net_return'][:,mask]]) if valid else distribution([])} for s in STRATEGIES}}
    return {'provider':payload['provider'],'return_definition':payload['return_definition'],'smoke':smoke,'attempted_accounts':expected,'valid_accounts':len(valid),'failed_accounts':failed,'failure_ledger':failure_ledger,'dates':dates,'fold_count':len(folds),'configuration':config,'distributions':dist,'paired':paired,'groups':groups,'calendar_year_slices':years,'accounts':summaries,'_ids':valid,'_attempted_ids':wanted,'_arrays':arrays}


def cross_source(alpaca,tiingo):
    if alpaca['dates']!=tiingo['dates']: raise ValueError('Cross-provider dates differ')
    ids=sorted(set(alpaca['_ids'])&set(tiingo['_ids'])); ai=[alpaca['_ids'].index(i) for i in ids];ti=[tiingo['_ids'].index(i) for i in ids];result={'matched_valid_accounts':len(ids),'unavailable_ids':sorted((set(alpaca['_attempted_ids'])|set(tiingo['_attempted_ids']))-set(ids)),'strategies':{}}
    for s in STRATEGIES:
        av=np.array([alpaca['accounts'][i]['metrics'][s]['net_total_return'] for i in ids]);tv=np.array([tiingo['accounts'][i]['metrics'][s]['net_total_return'] for i in ids]);es=[tiingo['accounts'][i]['metrics'][s]['daily_realized_es95']-alpaca['accounts'][i]['metrics'][s]['daily_realized_es95'] for i in ids]
        a=alpaca['_arrays'][s];t=tiingo['_arrays'][s]
        if ids:
            risk=t['forecast_daily_es'][ti]-a['forecast_daily_es'][ai]; var=t['forecast_daily_var'][ti]-a['forecast_daily_var'][ai]; l1=np.array([np.abs(t['post_cost_weights'][j]-a['post_cost_weights'][i]).sum(axis=1) for i,j in zip(ai,ti)]);daily=t['net_return'][ti]-a['net_return'][ai];rank_a=pd.Series(av).rank(method='average').to_numpy();rank_t=pd.Series(tv).rank(method='average').to_numpy()
            correlation=float(spearmanr(av,tv).statistic) if np.ptp(av)>0 and np.ptp(tv)>0 else None
        result['strategies'][s]={'net_return_tiingo_minus_alpaca':distribution((tv-av).tolist()),'es_tiingo_minus_alpaca':distribution(es),'mean_forecast_es_difference':distribution(risk.mean(axis=1).tolist()) if ids else distribution([]),'mean_absolute_forecast_es_difference':distribution(np.abs(risk).mean(axis=1).tolist()) if ids else distribution([]),'mean_forecast_var_difference':distribution(var.mean(axis=1).tolist()) if ids else distribution([]),'mean_fold_allocation_l1_difference':distribution(l1.mean(axis=1).tolist()) if ids else distribution([]),'max_fold_allocation_l1_difference':distribution(l1.max(axis=1).tolist()) if ids else distribution([]),'rank_difference_tiingo_minus_alpaca':distribution((rank_t-rank_a).tolist()) if ids else distribution([]),'spearman_net_return_ranking':correlation,'date_block_uncertainty':paired_date_block_ci(daily.mean(axis=0)) if ids else None}
    return result


def _escape(value):return html.escape(str(value)).replace('|','\\|').replace('\n',' ')
def _number(value):return 'unavailable' if value is None else f'{value:.8g}'


def _distribution_rows(label,stats):
    return '| '+_escape(label)+' | '+' | '.join(_number(stats.get(k)) for k in ('n','missing','mean','median','p5','p25','p75','p95','minimum','lower_decile_mean'))+' |\n'


def _distribution_header():
    return '| Metric | n | Missing | Mean | Median | p5 | p25 | p75 | p95 | Minimum | Lower-decile mean |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'


def _join_markdown(parts):
    return '\n'.join(part.rstrip('\n') if part.startswith('|') else part for part in parts)


def provider_markdown(summary):
    lines=[f"# {_escape(summary['provider'])} randomized portfolio replay\n",'**EXPLORATORY_REAL_MARKET / HISTORICAL_RETURN_REPLAY — NO_TRADE, not VALIDATED.**\n',f"Smoke: {summary['smoke']}. Attempted {summary['attempted_accounts']}; valid {summary['valid_accounts']}; failed {len(summary['failed_accounts'])}. Dates {summary['dates'][0]} through {summary['dates'][-1]}, {len(summary['dates'])} aligned returns, {summary['fold_count']} folds.\n",_escape(summary['return_definition'])+'\n','Values below are decimal returns/losses, USD costs, two-sided turnover, or explicitly named metrics. ES is one day; volatility and zero-rate ratios use 252. Lower-decile means are descriptive; a low value is not worse for every risk metric.\n','## All-strategy distributions\n']
    for strategy in STRATEGIES:
        lines+=['\n### '+strategy+'\n',_distribution_header()]
        lines.extend(_distribution_rows(metric,stats) for metric,stats in summary['distributions'][strategy].items())
    lines+=['\n## Paired BL-CVaR differences\n','Positive net-return differences and positive ES reductions favor BL-CVaR. Worst-decile underperformance is the lower-decile mean of net-return differences. Fractions use 1e-10 numerical tie tolerance.\n']
    for baseline,pair in summary['paired'].items():
        lines+=['\n### BL-CVaR versus '+baseline+'\n',_distribution_header(),_distribution_rows('Net cumulative return difference',pair['net_return_difference']),_distribution_rows('One-day ES reduction',pair['es_reduction']),f"\nFraction higher net return: {_number(pair['fraction_higher_net_return'])}; lower ES: {_number(pair['fraction_lower_es'])}; return ties: {_number(pair['fraction_return_ties'])}.\n"]
        ci=pair['date_block_uncertainty']
        if ci: lines.append(f"Daily mean paired difference {_number(ci['daily_mean_difference'])}; conditional date-block 95% interval [{_number(ci['conditional_95_interval'][0])}, {_number(ci['conditional_95_interval'][1])}]. This is not a cumulative-return interval.\n")
    lines+=['\n## Initial profile groups\n']
    for group,item in summary['groups'].items():
        lines+=['\n### '+group+f" ({item['valid_accounts']} valid)\n",_distribution_header()]
        for strategy,values in item['strategies'].items():
            lines.extend(_distribution_rows(strategy+' / '+metric,stats) for metric,stats in values.items())
        lines.append(_distribution_rows('BL-CVaR minus buy-and-hold net return',item['paired_vs_buy_hold']))
    lines+=['\n## Calendar-year slices\n','Predeclared calendar slices only; no ex-post bull/bear regime classification. Per-year ES tails are sparse/descriptive and not separate evidence of calibration.\n']
    for year,item in summary['calendar_year_slices'].items():
        lines+=['\n### '+year+f" ({item['observations']} sessions; insufficient ES-tail flag: {item['tail_warning']})\n",_distribution_header()]
        for strategy,values in item['strategies'].items(): lines.extend(_distribution_rows(strategy+' / '+metric,stats) for metric,stats in values.items())
    lines+=['\n## Complete failure ledger\n','Account failures are not imputed; reported distributions condition on available valid accounts and list missing accounts explicitly. Fit failures retain holding fallback returns and all dates.\n','| Account | Strategy | Fold | Reason / fallback |\n|---|---|---:|---|\n']
    for item in summary['failed_accounts']:lines.append('| '+_escape(item['portfolio_id'])+' | ACCOUNT_FAILED | — | '+_escape(item['reason'])+' |\n')
    for item in summary['failure_ledger']:lines.append('| '+_escape(item['portfolio_id'])+' | '+item['strategy']+' | '+str(item['fold'])+' | '+_escape(item.get('reason',''))+'; '+_escape(item.get('fallback',''))+' |\n')
    if not summary['failed_accounts'] and not summary['failure_ledger']: lines.append('| None | — | — | No recorded account or fit failures |\n')
    lines.append('\n## Inference limits\n500 stationary date-block draws, expected block length 10, seed 42. Each draw resamples the same dates across the portfolio-mean paired daily contrast; 250 accounts are not 250 independent histories. Intervals are conditional/descriptive, sensitive to stationarity, common survivors and prior research choices. Multiple contrasts are unadjusted; no invented significance or guaranteed superiority. Zero-prior/no-view BL provides no identified incremental BL signal. Buy-and-hold is cap-exempt; equal weight/ERC retain 10% cash. Source file hashes, exclusions and full-window selection bias remain in data_manifest.json; configuration/environment hashes remain in the completed run.\n')
    return _join_markdown(lines)


def cross_markdown(cross):
    lines=['# Matched cross-source comparison\n','**EXPLORATORY_REAL_MARKET / HISTORICAL_RETURN_REPLAY — NO_TRADE.**\n',f"Matched valid accounts: {cross['matched_valid_accounts']}; unmatched/unavailable valid IDs: {_escape(cross['unavailable_ids'])}. Same definitions, dates, initial weights and mandate verified before comparisons. Differences are Tiingo minus Alpaca; differing return definitions are retained, not treated as equivalent executable prices.\n"]
    for strategy,values in cross['strategies'].items():
        lines+=['\n## '+strategy+'\n',_distribution_header()]
        for key,value in values.items():
            if isinstance(value,dict) and 'n' in value: lines.append(_distribution_rows(key,value))
        lines.append('\nSpearman cumulative-return ranking correlation: '+_number(values['spearman_net_return_ranking'])+'.\n')
        ci=values['date_block_uncertainty']
        if ci:lines.append(f"Portfolio-mean daily return difference {_number(ci['daily_mean_difference'])}; conditional date-block interval [{_number(ci['conditional_95_interval'][0])}, {_number(ci['conditional_95_interval'][1])}].\n")
    lines.append('\nMean/max fold L1 differences compare matched normalized post-cost allocations. Forecast ES/VaR differences use matched daily exposures and dates. Ranking uses average ranks for ties. No source is declared correct merely because its outcome is better. Date-block intervals use 500 draws, block length10, seed42; multiple comparisons unadjusted. Both sources share selected survivors, local identity assumptions and full-window coverage selection bias.\n')
    return _join_markdown(lines)


def summarize(input_directory,output_directory,smoke=False):
    source=Path(input_directory);out=Path(output_directory)
    definitions=json.loads((source/'portfolio_definitions.json').read_text());verify_definitions(definitions)
    manifest=json.loads((source/'data_manifest.json').read_text());dates,folds=expected_grid(manifest,smoke)
    summaries={}
    for provider in ('alpaca','tiingo'):
        filename=provider+('_smoke.json' if smoke else '_randomized_250.json')
        with (source/filename).open() as stream: payload=json.load(stream)
        if payload['provider']!=provider: raise ValueError('Provider label mismatch')
        summaries[provider]=condense_provider(payload,definitions,dates,folds,smoke)
        del payload;gc.collect()
    if summaries['alpaca']['configuration']!=summaries['tiingo']['configuration']: raise ValueError('Cross-source frozen configurations differ')
    cross=cross_source(summaries['alpaca'],summaries['tiingo'])
    # Validate both providers completely before creating any report directory.
    out.mkdir(parents=True,exist_ok=False)
    for provider,summary in summaries.items():
        with (out/f'{provider}_randomized_250.md').open('x') as stream:stream.write(provider_markdown(summary))
    with (out/'cross_source_comparison.md').open('x') as stream:stream.write(cross_markdown(cross))
    overview=['# Portfolio robustness summary\n','**EXPLORATORY_REAL_MARKET / HISTORICAL_RETURN_REPLAY — NO_TRADE, not VALIDATED.**\n',f'Completed input directory: `{source.resolve()}`.\n\nSmoke-only structural report: {smoke}. Both feeds use identical initial definitions and aligned dates; no independent-account inference.\n','| Provider | Attempted | Valid | Account failures | Fit failures | BL-CVaR minus buy-and-hold mean / median net return | Fraction higher net return | Fraction lower ES |\n|---|---:|---:|---:|---:|---|---:|---:|\n']
    for provider,s in summaries.items():
        p=s['paired']['buy_hold'];d=p['net_return_difference'];overview.append(f"| {provider} | {s['attempted_accounts']} | {s['valid_accounts']} | {len(s['failed_accounts'])} | {len(s['failure_ledger'])} | {_number(d.get('mean'))} / {_number(d.get('median'))} | {_number(p['fraction_higher_net_return'])} | {_number(p['fraction_lower_es'])} |\n")
    overview.append('\nRead all strategy distributions, paired intervals, initial-group/year slices and the complete failure ledgers in the provider reports. Zero-prior/no-view BL does not identify incremental Bayesian signal; compare minimum CVaR explicitly. No favorable statistic is selected as proof. All reported results are conditional on full-window common-survivor selection, differing close definitions, unresolved action/PIT/rights/execution limitations, and unadjusted multiple comparisons. Actual user holdings/forward evaluation are not established by this replay.\n')
    with (out/'portfolio_robustness_summary.md').open('x') as stream:stream.write(_join_markdown(overview))
    return {'providers':{p:{k:v for k,v in s.items() if not k.startswith('_')} for p,s in summaries.items()},'cross_source':cross}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input-directory',required=True);parser.add_argument('--output-directory',required=True);parser.add_argument('--smoke',action='store_true',help='Structural test only; refuses to call smoke a completed 250-account run');args=parser.parse_args()
    result=summarize(args.input_directory,args.output_directory,args.smoke)
    print(json.dumps({'matched_accounts':result['cross_source']['matched_valid_accounts'],'smoke':args.smoke,'reports':str(Path(args.output_directory))},indent=2))

if __name__=='__main__':main()
