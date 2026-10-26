"""Run the frozen matched local close-return replay. No downloads or live decisions."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import time
from portfolio_engine.exploratory import load_matched_data,make_portfolios,replay_account,file_hash


def _write(path,value):
    with path.open('x') as stream: json.dump(value,stream,indent=2,allow_nan=False)


def run(data_root,output_directory,smoke=False):
    out=Path(output_directory);out.mkdir(parents=True,exist_ok=False)
    began=time.perf_counter();frames,manifest=load_matched_data(data_root)
    _write(out/'data_manifest.json',manifest)
    definitions=make_portfolios(frames['alpaca'].iloc[:504]);_write(out/'portfolio_definitions.json',definitions)
    selected=definitions['portfolios'][:2] if smoke else definitions['portfolios'];timings={};folds=1 if smoke else 14
    configuration={'lane':'EXPLORATORY_REAL_MARKET','status':'HISTORICAL_RETURN_REPLAY','decision':'NO_TRADE','validated':False,'smoke':smoke,'requested_portfolios_per_provider':250,'evaluated_portfolios_per_provider':len(selected),'seed':42,'scenario_seed':definitions['scenario_seed'],'train':504,'step':63,'scenario_count':1000,'alpha':.95,'risk_aversion':1,'cost_rate':.001,'max_risky_weight':.6,'max_cash':.1,'cost_budget':.01,'execution':'Continuous historical close-return replay; not executable fills','source_manifest':'data_manifest.json','definitions_sha256':definitions['definitions_sha256'],'code_hashes':{str(p):file_hash(p) for p in [Path(__file__),*sorted(Path('src/portfolio_engine').glob('*.py'))]},'uv_lock_sha256':file_hash('uv.lock'),'environment':{name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn','cvxpy']},'limitations':manifest['limitations']+['Both feeds reuse identical full-window-selected survivors and initial definitions; selection is not historical PIT admission.','Raw IEX price returns and vendor adjusted returns remain different definitions.','No historical market prior or views supplied: zero-prior/no-view BL incremental value is not demonstrated.','250 accounts share market dates; independent per-account inferential bootstraps are deliberately absent.','Smoke results are software/timing checks, not the completed 250-account experiment.']}
    _write(out/'run_configuration.json',configuration)
    for provider,frame in frames.items():
        started=time.perf_counter(); cache={}; filename=provider+('_smoke.json' if smoke else '_randomized_250.json')
        with (out/filename).open('x') as stream:
            stream.write('{"configuration":'+json.dumps(configuration,allow_nan=False)+',"provider":'+json.dumps(provider)+',"return_definition":'+json.dumps(manifest['return_definitions'][provider])+',"accounts":[')
            failed=[]
            for index,definition in enumerate(selected):
                try: result=replay_account(frame,definition,definitions['scenario_seed'],cache,max_folds=1 if smoke else None)
                except (ValueError,ArithmeticError) as exc:
                    result={'portfolio_id':definition['portfolio_id'],'definition':definition,'status':'ACCOUNT_FAILED','decision':'NO_TRADE','reason':str(exc)};failed.append(result['portfolio_id'])
                if index: stream.write(',')
                json.dump(result,stream,separators=(',',':'),allow_nan=False);stream.flush()
                if smoke or (index+1)%10==0: print(f'{provider}: {index+1}/{len(selected)} accounts, {time.perf_counter()-started:.2f}s',flush=True)
            elapsed=time.perf_counter()-started;timings[provider]={'seconds':elapsed,'attempted_accounts':len(selected),'failed_accounts':failed,'cached_fit_inputs':len(cache),'estimated_full_seconds_linear':elapsed/len(selected)/folds*250*14 if smoke else elapsed}
            stream.write('],"timing":'+json.dumps(timings[provider],allow_nan=False)+'}')
    timing={'smoke':smoke,'elapsed_seconds':time.perf_counter()-began,'providers':timings,'linear_full_run_estimate_seconds':sum(x['estimated_full_seconds_linear'] for x in timings.values()),'estimate_limit':'Linear extrapolation of account-fold work; cache hits, asset counts, solver conditioning and disk volume can change runtime.'}
    _write(out/'timing.json',timing);print(json.dumps(timing,indent=2),flush=True)
    return timing


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-root',default='/Users/manpao/Downloads/ai-us-equity-portfolio-consultant');parser.add_argument('--output-directory',required=True);parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    run(args.data_root,args.output_directory,args.smoke)

if __name__=='__main__':main()
