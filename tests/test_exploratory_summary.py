import copy
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from portfolio_engine.exploratory import make_portfolios,replay_account

spec=importlib.util.spec_from_file_location('exploratory_summary',Path(__file__).parents[1]/'scripts/summarize_exploratory.py')
summary=importlib.util.module_from_spec(spec);spec.loader.exec_module(summary)

@pytest.fixture(scope='module')
def payload():
    r=pd.DataFrame(np.random.default_rng(9).normal(0,.01,(567,23)),index=pd.bdate_range('2020-01-01',periods=567),columns=[f'A{i}' for i in range(23)])
    definitions=make_portfolios(r.iloc[:504]);accounts=[replay_account(r,d,definitions['scenario_seed'],max_folds=1) for d in definitions['portfolios'][:2]]
    config={'smoke':True,'requested_portfolios_per_provider':250,'evaluated_portfolios_per_provider':2,'definitions_sha256':definitions['definitions_sha256'],'lane':'EXPLORATORY_REAL_MARKET','status':'HISTORICAL_RETURN_REPLAY','decision':'NO_TRADE','validated':False,'train':504,'step':63,'scenario_count':1000,'alpha':.95,'risk_aversion':1,'cost_rate':.001,'max_risky_weight':.6,'max_cash':.1,'cost_budget':.01,'seed':42}
    folds=[{k:v for k,v in accounts[0]['folds'][0].items() if k!='test_tail_warning'}]
    return {'configuration':config,'provider':'alpaca','return_definition':'SYNTHETIC summary test only','accounts':accounts},definitions,accounts[0]['dates'],folds


def test_summary_distributions_and_exact_alignment(payload):
    p,d,dates,folds=payload
    result=summary.condense_provider(p,d,dates,folds,smoke=True)
    assert result['valid_accounts']==2
    assert result['distributions']['bl_cvar']['net_total_return']['n']==2
    assert result['paired']['min_cvar']['fraction_return_ties']==1
    assert len(result['calendar_year_slices'])==len(set(pd.DatetimeIndex(dates).year))
    report=summary.provider_markdown(result)
    assert 'lower-decile' in report and 'Complete failure ledger' in report
    broken=copy.deepcopy(p);broken['accounts'][0]['dates'][1]='2099-01-01'
    with pytest.raises(ValueError,match='alignment'):summary.condense_provider(broken,d,dates,folds,smoke=True)
    with pytest.raises(ValueError,match='count'):summary.condense_provider(p,d,dates,folds,smoke=False)


def test_summary_rejects_hash_or_nav_changes(payload):
    p,d,dates,folds=payload
    bad=copy.deepcopy(d);bad['portfolios'][0]['weights'][0]+=.01
    with pytest.raises(ValueError,match='hash'):summary.verify_definitions(bad)
    bad=copy.deepcopy(p);bad['accounts'][0]['strategies']['bl_cvar']['daily']['nav_usd'][1]+=1
    with pytest.raises(ValueError,match='reconciliation'):summary.condense_provider(bad,d,dates,folds,smoke=True)


def test_account_and_fold_failures_remain_in_report(payload):
    p,d,dates,folds=payload;bad=copy.deepcopy(p)
    bad['accounts'][0]={'portfolio_id':bad['accounts'][0]['portfolio_id'],'definition':bad['accounts'][0]['definition'],'status':'ACCOUNT_FAILED','reason':'visible failure'}
    s=bad['accounts'][1]['strategies']['bl_cvar'];failure={'fold':0,'reason':'visible solver failure','fallback':'held state'}
    s['failures']=[failure];s['folds'][0]['failure']=failure;s['metrics']['failed_folds']=1
    result=summary.condense_provider(bad,d,dates,folds,smoke=True)
    assert result['valid_accounts']==1 and len(result['failed_accounts'])==1
    assert len(result['failure_ledger'])==1
    assert 'visible failure' in summary.provider_markdown(result)
    assert 'visible solver failure' in summary.provider_markdown(result)


def test_paired_date_blocks_do_not_create_independent_account_precision():
    series=np.array([.01,-.02,.03,-.01,.02]*15)
    a=summary.paired_date_block_ci(series)
    b=summary.paired_date_block_ci(np.tile(series,(250,1)).mean(axis=0))
    assert a['conditional_95_interval']==pytest.approx(b['conditional_95_interval'])
    assert a['draws']==500 and a['block_length']==10
    assert summary.distribution([1,2,3,None])['missing']==1


def test_cross_source_exact_matched_risk_allocations_and_rank(payload):
    p,d,dates,folds=payload;a=summary.condense_provider(p,d,dates,folds,smoke=True)
    t=copy.deepcopy(a);t['provider']='tiingo'
    cross=summary.cross_source(a,t)
    assert cross['matched_valid_accounts']==2
    for s in cross['strategies'].values():
        assert s['net_return_tiingo_minus_alpaca']['mean']==0
        assert s['mean_fold_allocation_l1_difference']['maximum']==0
        assert s['mean_absolute_forecast_es_difference']['mean']==0
    assert 'Spearman' in summary.cross_markdown(cross)


def test_markdown_table_rows_are_contiguous(payload):
    import re
    p,d,dates,folds=payload;s=summary.condense_provider(p,d,dates,folds,smoke=True)
    for text in (summary.provider_markdown(s),summary.cross_markdown(summary.cross_source(s,s))):
        assert not re.search(r'(?m)^\|[^\n]*\|\n\n+(?=\|)',text)
    overview=summary._join_markdown(['Overview\n','| A | B |\n|---|---|\n','| x | y |\n','| z | w |\n','\nAfter\n'])
    assert '|---|---|\n| x | y |\n| z | w |' in overview
    assert '\n\nAfter' in overview
