import io
import json
import numpy as np
import pandas as pd
import pytest
from portfolio_engine.cli import analyze,demo_inputs,write_report
from portfolio_engine.data import read_portfolio,read_returns,validate_returns
from portfolio_engine.optimize import Constraints
from portfolio_engine.evaluation import evaluate


def fixture(tmp_path):
    r,m=demo_inputs(tmp_path)
    p=read_portfolio(tmp_path/'holdings.csv','2026-10-24T00:00:00Z')
    return p,r,m


def test_sector_mapping_rejects_misspelled_caps():
    with pytest.raises(ValueError): Constraints(sector_caps={'typo':.4},sectors=('tech','health')).validate(3)
    with pytest.raises(ValueError): Constraints(sector_caps={'tech':.4},sectors=('tech','')).validate(3)


def test_raw_duplicate_header_and_daily_calendar(tmp_path):
    p,r,m=fixture(tmp_path)
    path=tmp_path/'duplicate.csv'; path.write_text('date,A,A\n2020-01-01,.01,.02\n')
    with pytest.raises(ValueError,match='duplicate'): read_returns(path,tmp_path/'returns.json')
    m=m|{'expected_sessions':[str(d.date()) for d in r.index],'calendar_source':'synthetic weekday fixture'}
    with pytest.raises(ValueError,match='sessions'): validate_returns(r.drop(r.index[100:110]),m)
    weekly=r.iloc[::5]; wm=m|{'coverage_end':str(weekly.index[-1].date())}; wm.pop('expected_sessions')
    with pytest.raises(ValueError,match='Sparse'): validate_returns(weekly,wm)


def test_synthetic_proxy_and_missing_calendar_never_actionable(tmp_path):
    p,r,m=fixture(tmp_path); e={'independent':True,'source':'forged','lower_bound':1,'sensitivity_stable':True}
    a=analyze(p,r,m,evidence=e,scenario_count=400,as_of='2026-10-24T00:00:00Z')
    e['proposal_id']=a['proposal_id']
    assert analyze(p,r,m,evidence=e,scenario_count=400,as_of='2026-10-24T00:00:00Z')['decision']=='NO_TRADE'
    for meta in (m|{'kind':'observed','investable':False},m|{'kind':'observed','investable':True,'calendar_source':None}):
        assert analyze(p,r,meta,evidence=e,scenario_count=400,as_of='2026-10-24T00:00:00Z')['decision']=='NO_TRADE'


def test_rounded_noop_and_proposal_binding(tmp_path):
    p,r,m=fixture(tmp_path); r=r[['AAA','BBB']]
    text='symbol,quantity,price,currency,valuation_timestamp,nav\nAAA,1,4500,USD,2026-10-23T20:00:00Z,10000\nBBB,1,4500,USD,2026-10-23T20:00:00Z,10000\nCASH,1000,1,USD,2026-10-23T20:00:00Z,10000\n'
    p=read_portfolio(io.StringIO(text),'2026-10-24T00:00:00Z')
    m=m|{'kind':'observed','investable':True,'expected_sessions':[str(d.date()) for d in r.index],'calendar_source':'independently supplied test date grid','session_coverage_verified':True}
    e={'independent':True,'source':'test attestation','lower_bound':1,'sensitivity_stable':True}
    a=analyze(p,r,m,prior=[.015,.015],scenario_count=400,evidence=e,as_of='2026-10-24T00:00:00Z')
    assert a['decision']!='REBALANCE'
    assert a['implemented']['turnover']==0
    assert a['implemented']['utility_improvement']==pytest.approx(0)
    assert np.array_equal(a['whole_share_preview']['quantity'],[1,1])
    b=analyze(p,r,m,prior=[.015,.015],scenario_count=400,evidence=e|{'proposal_id':a['proposal_id']},as_of='2026-10-24T00:00:00Z')
    assert a['proposal_id']==b['proposal_id']
    assert b['decision'] in {'HOLD','NO_TRADE'}


def test_known_sensitivity_failure_cannot_be_overridden(tmp_path,monkeypatch):
    import portfolio_engine.cli as cli
    p,r,m=fixture(tmp_path)
    m=m|{'kind':'observed','investable':True,'expected_sessions':[str(d.date()) for d in r.index],'calendar_source':'independent test grid','session_coverage_verified':True}
    original=cli.scenarios
    def broken(*args,**kwargs):
        if len(args)>5 and args[5]=='gaussian': raise ValueError('sensitivity failed')
        return original(*args,**kwargs)
    monkeypatch.setattr(cli,'scenarios',broken)
    a=cli.analyze(p,r,m,prior=[.01]*3,scenario_count=400,as_of='2026-10-24T00:00:00Z')
    e={'independent':True,'source':'forged','lower_bound':1,'sensitivity_stable':True,'proposal_id':a['proposal_id']}
    b=cli.analyze(p,r,m,prior=[.01]*3,scenario_count=400,evidence=e,as_of='2026-10-24T00:00:00Z')
    assert b['decision']=='NO_TRADE'
    assert not b['sensitivity_assessment']['stable']


def test_histogram_and_html_summary_escaping(tmp_path):
    p,r,m=fixture(tmp_path); m=m|{'provider':'<script>provider</script>'}
    a=analyze(p,r,m,scenario_count=400,as_of='2026-10-24T00:00:00Z')
    h=a['scenario_net_loss_histogram']
    assert sum(h['current_counts'])==400
    assert sum(h['continuous_counts'])==400
    assert sum(h['implemented_counts'])==400
    a['symbols'][0]='<img onerror="oops">'; a['reason']='<script>reason</script>'
    write_report(a,tmp_path/'summary'); page=(tmp_path/'summary.html').read_text()
    for label in ('Current','Continuous','Rounded','Provenance','Cash','NAV','<table','<svg','<details'): assert label in page
    assert '<script>provider</script>' not in page
    assert '<script>reason</script>' not in page
    assert '<img onerror=' not in page


def test_evaluation_forecasts_drift_and_costs_and_cash_units(tmp_path,monkeypatch):
    import portfolio_engine.evaluation as ev
    p,r,m=fixture(tmp_path); r=r.iloc[:410]
    m=m|{'coverage_end':str(r.index[-1].date())}; m.pop('expected_sessions',None)
    means=[]; sampled=[]; objectives=[]; original=ev.scenarios; original_optimize=ev.optimize
    def capture(returns,mean,*args,**kwargs):
        means.append(np.asarray(mean)); values=original(returns,mean,*args,**kwargs); sampled.append(values); return values
    monkeypatch.setattr(ev,'scenarios',capture)
    def capture_objective(R,mean,*args,**kwargs):
        objectives.append(np.asarray(mean)); return original_optimize(R,mean,*args,**kwargs)
    monkeypatch.setattr(ev,'optimize',capture_objective)
    out=evaluate(r,m,train=400,step=10,scenario_count=400,ci_samples=5,cash_rate=.001)
    assert np.allclose(means[0],.001)
    assert any(np.allclose(x,r.iloc[:400].mean()) for x in means)
    assert any(np.allclose(x[:-1],r.iloc[:400].mean()) for x in objectives)
    d=out['strategies']['equal_weight']['daily']
    assert d[0]['forecast_daily_var']!=d[1]['forecast_daily_var']
    assert d[0]['forecast_includes_transition_cost']
    assert not d[1]['forecast_includes_transition_cost']
    assert d[0]['var_exceedance']==(-d[0]['net_return']>d[0]['forecast_daily_var'])
    assert not np.allclose(d[0]['start_weights'],d[1]['start_weights'])
    from portfolio_engine.models import empirical_es
    R=np.c_[sampled[0],np.full(400,.001)]
    for day in [0,1]:
        losses=d[day]['cost']-R@np.array(d[day]['start_weights'])
        assert d[day]['forecast_daily_var']==pytest.approx(np.quantile(losses,.95,method='higher'))
        assert d[day]['forecast_daily_es']==pytest.approx(empirical_es(losses))
        assert d[day]['tail_loss']==pytest.approx(max(0,-d[day]['net_return']-d[day]['forecast_daily_var']))

@pytest.mark.parametrize('date',[None,pd.NaT,'NaT','invalid'])
def test_bl_and_market_prior_reject_missing_dates(date):
    from portfolio_engine.models import black_litterman,market_prior
    e={'source':'test','as_of':date,'basis':'market_capitalization'}
    with pytest.raises(ValueError): black_litterman(np.eye(2),[0,0],P=[[1,0]],Q=[.01],omega=[[.1]],evidence=e,as_of='2026-01-01')
    with pytest.raises(ValueError): market_prior(np.eye(2),[.5,.5],1,e,'2026-01-01')


def test_market_prior_rejects_nonfinite_risk_aversion():
    from portfolio_engine.models import market_prior
    with pytest.raises(ValueError): market_prior(np.eye(2),[.5,.5],np.nan,{'source':'test','as_of':'2020-01-01','basis':'market_capitalization'},'2020-01-02')


def test_exact_proposal_attestation_and_calendar_gate(tmp_path):
    p,r,m=fixture(tmp_path)
    m=m|{'kind':'observed','investable':True,'session_coverage_verified':True,'calendar_source':'independent test grid'}
    config={'prior':[.03,0,0],'scenario_count':400,'as_of':'2026-10-24T00:00:00Z'}
    a=analyze(p,r,m,**config)
    assert a['sensitivity_assessment']['stable']
    assert a['implemented']['utility_improvement']>.0001
    assert 'proposal_id' in a['reason']
    e={'source':'test attestation only','independent':True,'lower_bound':.1,'sensitivity_stable':True,'proposal_id':'wrong'}
    assert analyze(p,r,m,evidence=e,**config)['decision']=='NO_TRADE'
    e['proposal_id']=a['proposal_id']
    assert analyze(p,r,m,evidence=e,**config)['decision']=='REBALANCE'
    changed=analyze(p,r,m,evidence=e,seed=43,**config)
    assert changed['proposal_id']!=a['proposal_id']
    assert changed['decision']=='NO_TRADE'
    missing=m.copy(); missing.pop('expected_sessions')
    result=analyze(p,r,missing,evidence=e,**config)
    assert result['decision']=='NO_TRADE'
    assert 'session' in result['reason']
    unstable=analyze(p,r,m,prior=[.015]*3,scenario_count=400,as_of=config['as_of'])
    assert unstable['sensitivity_assessment']['max_l1_difference']>.25
    assert unstable['decision']=='NO_TRADE'
