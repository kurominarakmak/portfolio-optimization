"""Offline CLI: attributed inputs, transparent JSON, escaped static HTML."""
import argparse
from dataclasses import asdict
import html
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import read_portfolio, read_returns, validate_returns, utc
from .models import covariance, black_litterman, scenarios, risk_metrics, empirical_es
from .optimize import Constraints, optimize, residuals, preview_shares, decide
from .evaluation import evaluate


def json_value(x):
    if isinstance(x,np.ndarray): return x.tolist()
    if isinstance(x,np.generic): return x.item()
    raise TypeError(type(x).__name__)


def _summary_html(report):
    esc=lambda value: html.escape(str(value),quote=True)
    out='<p><strong>'+esc(report.get('decision','Exploratory comparison'))+'</strong>: '+esc(report.get('reason',report.get('claims','')))+'</p>'
    out+='<h2>Provenance</h2><p>'+esc(report.get('provenance',{}).get('provider','Unavailable'))+' | '+esc(report.get('data_kind','unknown'))+' | One trading day</p>'
    if 'nav_usd' in report:
        out+='<p>NAV USD '+esc(f"{report['nav_usd']:,.2f}")+' | Cash USD '+esc(f"{report['nav_usd']*report['current_weights'][-1]:,.2f}")+'</p>'
    if 'symbols' in report:
        proposed=report.get('candidate',{}).get('weights')
        rounded=report.get('whole_share_preview',{}).get('weights')
        out+='<h2>Composition</h2><table><thead><tr><th>Symbol</th><th>Current</th><th>Continuous</th><th>Rounded</th></tr></thead><tbody>'
        for i,symbol in enumerate(report['symbols']):
            cells=[report['current_weights'][i],None if proposed is None else proposed[i],None if rounded is None else rounded[i]]
            out+='<tr><th>'+esc(symbol)+'</th>'+''.join('<td>'+('Unavailable' if value is None else f'{value:.2%}')+'</td>' for value in cells)+'</tr>'
        out+='</tbody></table><h2>One-day net scenario risk</h2><table><thead><tr><th>Allocation</th><th>Volatility</th><th>ES</th><th>Cost / pre-trade NAV</th></tr></thead><tbody>'
        for label,key in [('Current','current_scenario'),('Continuous','continuous_scenario'),('Rounded','implemented')]:
            risk=report.get(key)
            out+='<tr><th>'+label+'</th>'+(''.join('<td>'+f"{risk[field]:.4%}"+'</td>' for field in ['daily_volatility','daily_es_net','cost']) if risk else '<td colspan="3">Unavailable</td>')+'</tr>'
        out+='</tbody></table>'
    hist=report.get('scenario_net_loss_histogram')
    if hist:
        series=[('current_counts','#1769aa'),('continuous_counts','#d96813'),('implemented_counts','#218354')]
        maximum=max(1,max(max(hist.get(key) or [0]) for key,color in series)); count=len(hist['bin_edges'])-1; width=600/count
        out+='<h2>One-day net loss scenarios</h2><p>Current: blue; Continuous: orange; Rounded: green. Shared bins; frequency counts.</p><svg viewBox="0 0 640 240" role="img" aria-label="Shared-bin one-day net loss frequencies"><title>Current, continuous and rounded net loss distribution</title>'
        for j,(key,color) in enumerate(series):
            for i,value in enumerate(hist.get(key) or []):
                height=180*value/maximum
                out+=f'<rect x="{20+i*width+j*width/3:.2f}" y="{200-height:.2f}" width="{width/3:.2f}" height="{height:.2f}" fill="{color}"/>'
        out+=f'<text x="20" y="225">{hist["bin_edges"][0]:.2%} loss</text><text x="500" y="225">{hist["bin_edges"][-1]:.2%} loss</text></svg>'
    out+='<h2>Warnings</h2><ul>'+''.join('<li>'+esc(warning)+'</li>' for warning in report.get('warnings',report.get('limitations',[])))+'</ul>'
    return out


def write_report(report,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(report,default=json_value,indent=2,allow_nan=False)
    path.with_suffix('.json').write_text(payload)
    path.with_suffix('.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Portfolio research</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f7;padding:1rem}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{text-align:left;padding:.5rem;border-bottom:1px solid #ccc}svg{max-width:100%}h1{color:#123}strong{color:#943}</style><h1>Portfolio research decision support</h1><p><strong>Research only. No trade execution. Mathematical tests do not establish investment performance.</strong></p><p>All losses and scenarios use one trading day; annualized moments use 252 days.</p>'+_summary_html(report)+'<details><summary>Full reproducible JSON details</summary><pre>'+html.escape(payload)+'</pre></details></html>')


def _scenario_statistics(R,x,cost,mean,risk_aversion,alpha):
    net=R@x-cost
    es=empirical_es(-net,alpha)
    return {'pre_nav_fractions':x,'cost':cost,'daily_volatility':float(np.std(net,ddof=1)),'daily_es_net':es,'daily_expected_net_return':float(mean@x-cost),'utility':float(mean@x-cost-risk_aversion*es)}


def analyze(portfolio,returns,metadata,constraints=None,seed=42,scenario_count=2000,alpha=.95,risk_aversion=1.,prior=None,views=None,evidence=None,cash_rate=0.,as_of=None):
    c=constraints or Constraints(); symbols=portfolio['symbols'][:-1]
    r=validate_returns(returns,metadata,symbols); current=portfolio['weights']; rr=np.c_[r.to_numpy(),np.full(len(r),cash_rate)]
    stamp=utc(as_of or portfolio['timestamp']); end=pd.Timestamp(r.index[-1]).tz_localize('UTC')
    if not pd.Timedelta(0)<=stamp-utc(portfolio['timestamp'])<=pd.Timedelta(days=4): raise ValueError('Portfolio snapshot stale or future relative to analysis')
    if not pd.Timedelta(0)<=stamp-end<=pd.Timedelta(days=4): raise ValueError('Return history is stale or future relative to analysis')
    if not np.isfinite(cash_rate) or cash_rate < -1: raise ValueError('Invalid daily cash return')
    sigma=covariance(r); full=np.pad(sigma,((0,1),(0,1)))
    user_prior=np.zeros(len(symbols)) if prior is None else np.asarray(prior,float)
    bl=black_litterman(sigma,user_prior,as_of=stamp,**(views or {})); mu=np.r_[bl['mean']+cash_rate,cash_rate]
    S=scenarios(r,mu[:-1],sigma,scenario_count,seed); R=np.c_[S,np.full(scenario_count,cash_rate)]
    report={'data_kind':metadata['kind'],'provenance':metadata,'valuation_timestamp':portfolio['timestamp'],'as_of':stamp.isoformat(),'nav_usd':portfolio['nav'],'symbols':portfolio['symbols'],'current_weights':current,'constraints':asdict(c),'risk_horizon':'one trading day','scenario_model':'synchronized stationary-bootstrap residuals centered and shifted to BL mean; conditional, no parameter uncertainty','cash_daily_return':cash_rate,'alpha':alpha,'risk_aversion':risk_aversion,'prior_label':'explicit user daily excess prior' if prior is not None else 'user-labelled zero daily excess prior; no market capitalization supplied','bl':bl,'current_historical_risk':risk_metrics(rr,current,alpha),'warnings':['Current fixed-weight historical risk is descriptive; not reconstructed historical holdings.','No empirical superiority claim; Monte Carlo creates no additional historical tail information.','Independent uncertainty evidence is required for actionable recommendation.']}
    try:
        candidate=optimize(R,mu,current,full,c,alpha,risk_aversion)
        current_stats=_scenario_statistics(R,current,0.,mu,risk_aversion,alpha)
        continuous_stats=_scenario_statistics(R,candidate['pre_nav_fractions'],candidate['cost'],mu,risk_aversion,alpha)
        continuous_improvement=candidate['utility']-current_stats['utility']
        preview_valid=True; implemented=None; proposal_id=None
        try:
            preview=preview_shares(candidate,portfolio,c)
            implemented=_scenario_statistics(R,preview['pre_nav_fractions'],preview['cost_usd']/portfolio['nav'],mu,risk_aversion,alpha)
            implemented['turnover']=float(np.abs(preview['pre_nav_fractions'][:-1]-current[:-1]).sum())
            implemented['utility_improvement']=implemented['utility']-current_stats['utility']
            input_digest=hashlib.sha256(r.to_csv(float_format='%.17g').encode()).hexdigest()
            identity={'symbols':portfolio['symbols'],'current_weights':current,'rounded_fractions':preview['pre_nav_fractions'],'constraints':asdict(c),'alpha':alpha,'risk_aversion':risk_aversion,'cash_rate':cash_rate,'seed':seed,'scenario_count':scenario_count,'as_of':stamp.isoformat(),'return_input_digest':input_digest,'provenance':metadata,'nav_usd':portfolio['nav'],'rounded_quantities':preview['quantity'],'prior':user_prior,'posterior_mean':bl['mean'],'views':bl['views']}
            proposal_id=hashlib.sha256(json.dumps(identity,default=json_value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        except ValueError as exc: preview={'error':str(exc)}; preview_valid=False
        sensitivities=[]
        # These fits diagnose instability; they are not independent superiority evidence.
        for family in ['gaussian','bootstrap']:
            for lam in [.5,2.]:
                try:
                    alt=scenarios(r,mu[:-1],sigma,scenario_count,seed+1,family)
                    fit=optimize(np.c_[alt,np.full(scenario_count,cash_rate)],mu,current,full,c,alpha,lam)
                    span=float(np.abs(fit['weights']-candidate['weights']).sum())
                    sensitivities.append({'family':family,'risk_aversion':lam,'weights':fit['weights'],'turnover':fit['turnover'],'l1_difference_from_continuous':span})
                except ValueError as exc: sensitivities.append({'family':family,'risk_aversion':lam,'failure':str(exc)})
        failures=[item for item in sensitivities if 'failure' in item]
        maximum=max((item['l1_difference_from_continuous'] for item in sensitivities if 'failure' not in item),default=None)
        stable=not failures and maximum is not None and maximum<=.25
        sensitivity={'stable':stable,'max_l1_difference':maximum,'threshold':.25,'rule':'Uncalibrated engineering screen: no failed sensitivity and maximum L1 normalized-weight difference <= 0.25','failures':failures}
        feasible=residuals(current,current,c)[0]<=1e-6
        improvement=implemented['utility_improvement'] if implemented else None
        reason=None
        if metadata['kind']!='observed' or metadata.get('investable') is not True: reason='Observed investable instrument data required; synthetic/proxy inputs are descriptive only'
        elif not metadata.get('expected_sessions') or not metadata.get('calendar_source') or metadata.get('session_coverage_verified') is not True: reason='Independently attributed and verified expected-session coverage required'
        elif not stable: reason='Computed model sensitivity failed or exceeds the uncalibrated stability threshold'
        elif not preview_valid: reason='Whole-share preview failed'
        elif not evidence or evidence.get('proposal_id')!=proposal_id: reason='Independent evidence must identify the exact rounded proposal_id'
        policy={'decision':'NO_TRADE','reason':reason} if reason else decide(improvement,feasible,len(r),scenario_count,evidence,alpha,preview_valid=preview_valid)
        if implemented and implemented['turnover']==0 and policy['decision']=='REBALANCE': policy={'decision':'HOLD' if feasible else 'NO_TRADE','reason':'Rounded proposal leaves quantities unchanged'}
        losses={'current':-R@current,'continuous':candidate['cost']-R@candidate['pre_nav_fractions']}
        if implemented: losses['implemented']=implemented['cost']-R@implemented['pre_nav_fractions']
        edges=np.histogram_bin_edges(np.concatenate(list(losses.values())),bins=24)
        histogram={'horizon':'one trading day net loss including transition costs','sample_count':scenario_count,'bin_edges':edges.tolist()}
        for name,values in losses.items(): histogram[name+'_counts']=np.histogram(values,bins=edges)[0].tolist()
        report['warnings'].append('External uncertainty evidence is an unauthenticated supplied attestation, not statistical proof. Synthetic/proxy data, unverified sessions, and computed sensitivity failures cannot be overridden.')
        report.update(candidate=candidate,candidate_historical_risk=risk_metrics(rr,candidate['weights'],alpha),current_scenario=current_stats,continuous_scenario=continuous_stats,implemented=implemented,current_scenario_daily_es=current_stats['daily_es_net'],continuous_estimated_net_utility_improvement=continuous_improvement,estimated_net_utility_improvement=improvement,whole_share_preview=preview,proposal_id=proposal_id,sensitivity=sensitivities,sensitivity_assessment=sensitivity,scenario_net_loss_histogram=histogram,uncertainty_evidence=evidence,**policy)
    except ValueError as exc: report.update(decision='NO_TRADE',reason=str(exc))
    return report


def demo_inputs(directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(42); common=rng.normal(0,.008,(756,1)); values=common+rng.normal(.0001,.009,(756,3))
    frame=pd.DataFrame(values,index=pd.bdate_range(end='2026-10-23',periods=756),columns=['AAA','BBB','CCC']); frame.index.name='date'; frame.to_csv(directory/'returns.csv')
    metadata={'provider':'NumPy seeded SYNTHETIC fixture','permitted_usage':'engineering demonstration only','adjustment':'total_return','currency':'USD','frequency':'daily','units':'decimal','retrieved_at':'2026-10-24T00:00:00Z','kind':'synthetic','coverage_start':str(frame.index[0].date()),'coverage_end':str(frame.index[-1].date())}
    metadata.update(investable=False,expected_sessions=[str(d.date()) for d in frame.index],calendar_source='SYNTHETIC weekday fixture; not an observed exchange calendar',session_coverage_verified=False)
    (directory/'returns.json').write_text(json.dumps(metadata,indent=2))
    (directory/'holdings.csv').write_text('symbol,quantity,price,currency,valuation_timestamp,nav\nAAA,30,100,USD,2026-10-23T20:00:00Z,10000\nBBB,30,100,USD,2026-10-23T20:00:00Z,10000\nCCC,30,100,USD,2026-10-23T20:00:00Z,10000\nCASH,1000,1,USD,2026-10-23T20:00:00Z,10000\n')
    return frame,metadata


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    for name in ['analyze','evaluate','demo']:
        cmd=sub.add_parser(name); cmd.add_argument('--output',default='reports/'+name); cmd.add_argument('--seed',type=int,default=42)
        if name!='demo': cmd.add_argument('--returns',required=True); cmd.add_argument('--metadata',required=True)
        if name=='analyze': cmd.add_argument('--holdings',required=True); cmd.add_argument('--as-of',required=True)
        if name=='evaluate':
            cmd.add_argument('--train',type=int,default=504); cmd.add_argument('--step',type=int,default=63); cmd.add_argument('--max-cash',type=float,default=1.); cmd.add_argument('--expanding',action='store_true')
    for name in ['paper-start','paper-update','paper-status']:
        cmd=sub.add_parser(name); cmd.add_argument('--directory',required=True)
        if name!='paper-status': cmd.add_argument('--returns',required=True); cmd.add_argument('--metadata',required=True)
        if name=='paper-update': cmd.add_argument('--synthetic-replay',action='store_true',help='Explicit fixture-only replay; never grants live status')
        if name=='paper-start':
            cmd.add_argument('--holdings',required=True); cmd.add_argument('--holdings-metadata',required=True); cmd.add_argument('--as-of',required=True)
    cmd=sub.add_parser('sample'); cmd.add_argument('--universe',required=True); cmd.add_argument('--start-at',required=True); cmd.add_argument('--output',required=True); cmd.add_argument('--seed',type=int,default=42)
    args=p.parse_args()
    try:
        if args.command=='sample':
            from .sampling import sample_portfolios,save_definitions
            result=sample_portfolios(json.loads(Path(args.universe).read_text()),args.start_at,args.seed)
            save_definitions(result,args.output); print(result['status']); return
        if args.command.startswith('paper-'):
            from .paper import start_paper,update_paper,read_paper
            if args.command=='paper-status': result=read_paper(args.directory)
            else:
                metadata=json.loads(Path(args.metadata).read_text()); frame=read_returns(args.returns,args.metadata)
                if args.command=='paper-update': result=update_paper(args.directory,frame,metadata,synthetic_replay=args.synthetic_replay)
                else:
                    portfolio=read_portfolio(args.holdings,args.as_of)
                    result=start_paper(args.directory,portfolio,frame,metadata,json.loads(Path(args.holdings_metadata).read_text()),args.as_of)
            print(json.dumps(result,default=json_value,indent=2,allow_nan=False)); return
        if args.command=='demo':
            frame,metadata=demo_inputs('examples/synthetic'); portfolio=read_portfolio('examples/synthetic/holdings.csv','2026-10-24T00:00:00Z')
            report=analyze(portfolio,frame,metadata,seed=args.seed,as_of='2026-10-24T00:00:00Z')
        else:
            metadata=json.loads(Path(args.metadata).read_text()); frame=read_returns(args.returns,args.metadata)
            if args.command=='evaluate': report=evaluate(frame,metadata,train=args.train,step=args.step,seed=args.seed,expanding=args.expanding,constraints=Constraints(max_cash=args.max_cash,cost_budget=.01))
            else:
                portfolio=read_portfolio(args.holdings,args.as_of)
                report=analyze(portfolio,frame,metadata,seed=args.seed,as_of=args.as_of)
        write_report(report,args.output)
        print(str(Path(args.output).with_suffix('.json')))
    except (ValueError,KeyError,OSError) as exc:
        if args.command.startswith('paper-') or args.command=='sample': p.exit(2,'Input rejected: '+str(exc)+'\n')
        write_report({'decision':'NO_TRADE','reason':str(exc),'status':'input rejected; no execution'},args.output)
        p.exit(2,'Input rejected; see sanitized local report.\n')

if __name__=='__main__': main()
