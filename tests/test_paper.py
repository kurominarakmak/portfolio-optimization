import json
import numpy as np
import pandas as pd
import pytest
from portfolio_engine.cli import demo_inputs
from portfolio_engine.data import read_portfolio
from portfolio_engine.paper import start_paper,update_paper,read_paper


def inputs(tmp_path):
    r,m=demo_inputs(tmp_path/'inputs')
    p=read_portfolio(tmp_path/'inputs'/'holdings.csv','2026-10-24T00:00:00Z')
    return p,r,m


def future(r,m):
    dates=pd.bdate_range('2026-10-26',periods=2)
    values=pd.DataFrame([[.1,0,-.1],[0,.05,0]],index=dates,columns=r.columns)
    frame=pd.concat([r,values]); meta=m|{'coverage_end':str(dates[-1].date()),'retrieved_at':'2026-10-28T00:00:00Z','expected_sessions':[str(d.date()) for d in frame.index]}
    return frame,meta


def test_frozen_paper_snapshot_drift_cost_and_reproducibility(tmp_path):
    p,r,m=inputs(tmp_path)
    root=tmp_path/'paper'
    s=start_paper(root,p,r,m,holdings_provenance={'kind':'synthetic','source':'fixture'},as_of='2026-10-24T00:00:00Z',scenario_count=400)
    assert s['first_decision']['decision']=='NO_TRADE'
    assert s['live_forward_status']=='NOT_STARTED'
    initial=(root/'snapshot.json').read_bytes()
    assert set(s['books'])=={'hold','equal_weight','optimized_exploratory'}
    assert all(b['initial_nav_usd']==10000 for b in s['books'].values())
    f,meta=future(r,m); outcome=update_paper(root,f,meta,synthetic_replay=True)
    assert (root/'snapshot.json').read_bytes()==initial
    assert outcome['first_decision']['decision']=='NO_TRADE'
    assert outcome['live_forward_status']=='NOT_STARTED'
    for name,book in s['books'].items():
        prices=np.array([110,105,90])
        expected=np.array(book['quantity'])@prices+book['cash_usd']
        assert outcome['books'][name]['nav_usd']==pytest.approx(expected)
        assert outcome['books'][name]['quantity']==book['quantity']
    assert outcome['books']['hold']['nav_usd']==pytest.approx(10150)
    ledger=(root/'events.jsonl').read_bytes()
    assert update_paper(root,f,meta,synthetic_replay=True)['books']==outcome['books']
    assert (root/'events.jsonl').read_bytes()==ledger
    assert read_paper(root)['snapshot_id']==s['snapshot_id']
    with pytest.raises(FileExistsError): start_paper(root,p,r,m,holdings_provenance={'kind':'synthetic','source':'fixture'},as_of='2026-10-24T00:00:00Z')


def test_reject_revisions_future_fit_and_snapshot_tampering(tmp_path):
    p,r,m=inputs(tmp_path); root=tmp_path/'paper'
    start_paper(root,p,r,m,holdings_provenance={'kind':'synthetic','source':'fixture'},as_of='2026-10-24T00:00:00Z',scenario_count=400)
    f,meta=future(r,m); f.iloc[1,0]+=.001
    with pytest.raises(ValueError,match='revis'): update_paper(root,f,meta,synthetic_replay=True)
    f,meta=future(r,m)
    with pytest.raises(ValueError,match='future'): start_paper(tmp_path/'future',p,f,meta,holdings_provenance={'kind':'synthetic','source':'fixture'},as_of='2026-10-24T00:00:00Z')
    snapshot=json.loads((root/'snapshot.json').read_text()); snapshot['payload']['initial_nav_usd']=1
    (root/'snapshot.json').write_text(json.dumps(snapshot))
    with pytest.raises(ValueError,match='fingerprint'): read_paper(root)


def test_failed_benchmark_is_recorded_without_relaxation(tmp_path):
    from portfolio_engine.optimize import Constraints
    p,r,m=inputs(tmp_path)
    result=start_paper(tmp_path/'failed',p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',constraints=Constraints(max_weight=.2,max_cash=.1),scenario_count=400)
    assert result['books']['equal_weight']['failure']
    assert result['books']['optimized_exploratory']['failure']
    assert result['books']['equal_weight']['quantity']==[30.,30.,30.]
    assert result['first_decision']['decision']=='NO_TRADE'


def test_paper_ledger_detects_tamper_and_rejects_invalid_batch(tmp_path):
    p,r,m=inputs(tmp_path); root=tmp_path/'paper'
    start_paper(root,p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',scenario_count=400)
    original=(root/'events.jsonl').read_bytes()
    f,meta=future(r,m); f.iloc[-1]=[-1,-1,-1]
    with pytest.raises(ValueError): update_paper(root,f,meta,synthetic_replay=True)
    assert (root/'events.jsonl').read_bytes()==original
    event=json.loads(original); event['books']['hold']['cash_usd']+=1
    (root/'events.jsonl').write_text(json.dumps(event)+'\n')
    with pytest.raises(ValueError,match='fingerprint'): read_paper(root)


def test_initial_cost_charged_once_and_updates_preserve_quantities(tmp_path):
    from portfolio_engine.optimize import Constraints
    p,r,m=inputs(tmp_path)
    # A looser cash bound permits a separately feasible rounded initial target.
    p['positions'].loc['AAA','quantity']=50
    p['positions'].loc['BBB','quantity']=10
    p['weights']=np.array([.5,.1,.3,.1])
    root=tmp_path/'paper'
    s=start_paper(root,p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',constraints=Constraints(max_cash=.2),scenario_count=400)
    b=s['books']['equal_weight']
    assert b['initial_cost_usd']>0
    assert b['nav_usd']+b['initial_cost_usd']==pytest.approx(10000)
    f,meta=future(r,m); out=update_paper(root,f,meta,synthetic_replay=True)
    new=out['books']['equal_weight']
    assert new['total_transaction_cost_usd']==b['initial_cost_usd']
    assert new['quantity']==b['quantity']
    events=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    assert all(e['books']['equal_weight']['transaction_cost_usd']==0 for e in events[1:])
    assert new['forecast_var_exceedance_frequency'] is not None


def test_cli_paper_status(tmp_path,monkeypatch,capsys):
    from portfolio_engine.cli import main
    p,r,m=inputs(tmp_path); root=tmp_path/'paper'
    start_paper(root,p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',scenario_count=400)
    monkeypatch.setattr('sys.argv',['portfolio-engine','paper-status','--directory',str(root)])
    main()
    assert json.loads(capsys.readouterr().out)['no_execution'] is True


def test_observed_future_batch_rejected_without_ledger_change(tmp_path,monkeypatch):
    import portfolio_engine.paper as paper
    p,r,m=inputs(tmp_path)
    m=m|{'kind':'observed','investable':True,'session_coverage_verified':True,'calendar_source':'independently attributed test fixture grid'}
    root=tmp_path/'paper'
    start_paper(root,p,r,m,{'kind':'observed','source':'TEST holdings attestation','genuine_holdings_verified':True},'2026-10-24T00:00:00Z',scenario_count=400)
    monkeypatch.setattr(paper,'_utc_now',lambda:pd.Timestamp('2026-10-26T12:00:00Z'))
    before=(root/'events.jsonl').read_bytes(); head=(root/'committed_head.json').read_bytes()
    frame=pd.concat([r,pd.DataFrame([[.1,0,0]],index=pd.to_datetime(['2099-01-05']),columns=r.columns)])
    meta=m|{'coverage_end':'2099-01-05','retrieved_at':'2099-01-06T00:00:00Z','expected_sessions':[str(d.date()) for d in frame.index]}
    with pytest.raises(ValueError,match='actual UTC'): update_paper(root,frame,meta)
    assert (root/'events.jsonl').read_bytes()==before
    with pytest.raises(ValueError,match='actual UTC'): update_paper(root,frame,meta|{'retrieved_at':'2026-10-26T12:00:00Z'})
    with pytest.raises(ValueError,match='Synthetic replay'): update_paper(root,frame,meta,synthetic_replay=True)
    assert (root/'committed_head.json').read_bytes()==head
    with pytest.raises(ValueError,match='actual UTC'): update_paper(root,r,m|{'retrieved_at':'2099-01-06T00:00:00Z'})
    assert (root/'events.jsonl').read_bytes()==before


def test_complete_record_truncation_rejected_by_committed_head(tmp_path):
    p,r,m=inputs(tmp_path);root=tmp_path/'paper'
    start_paper(root,p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',scenario_count=400)
    f,meta=future(r,m);update_paper(root,f,meta,synthetic_replay=True)
    lines=(root/'events.jsonl').read_text().splitlines(keepends=True)
    (root/'events.jsonl').write_text(''.join(lines[:-1]))
    with pytest.raises(ValueError,match='committed head'): read_paper(root)
    with pytest.raises(ValueError,match='committed head'): update_paper(root,f,meta,synthetic_replay=True)


def test_synthetic_future_replay_is_explicit_and_records_actual_update_time(tmp_path,monkeypatch):
    import portfolio_engine.paper as paper
    p,r,m=inputs(tmp_path);root=tmp_path/'paper'
    start_paper(root,p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',scenario_count=400)
    now=pd.Timestamp('2026-10-26T12:00:00Z');monkeypatch.setattr(paper,'_utc_now',lambda:now)
    f,meta=future(r,m)
    with pytest.raises(ValueError,match='actual UTC'): update_paper(root,f,meta)
    result=update_paper(root,f,meta,synthetic_replay=True)
    assert result['last_update_at']==now.isoformat()
    assert result['live_forward_status']=='NOT_STARTED'
    events=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    assert all(e['updated_at']==now.isoformat() and e['synthetic_replay'] and not e['observation_verified'] for e in events[1:])


def test_interrupted_head_commit_fails_closed(tmp_path,monkeypatch):
    import portfolio_engine.paper as paper
    p,r,m=inputs(tmp_path);root=tmp_path/'paper'
    start_paper(root,p,r,m,{'kind':'synthetic','source':'fixture'},'2026-10-24T00:00:00Z',scenario_count=400)
    original_head=(root/'committed_head.json').read_bytes()
    def interrupted(*args): raise OSError('simulated interruption after journal fsync')
    monkeypatch.setattr(paper,'_commit_head',interrupted)
    f,meta=future(r,m)
    with pytest.raises(OSError,match='interruption'): update_paper(root,f,meta,synthetic_replay=True)
    assert (root/'committed_head.json').read_bytes()==original_head
    with pytest.raises(ValueError,match='committed head'): read_paper(root)
