import numpy as np
import pandas as pd
from portfolio_engine.evaluation import evaluate

def test_walk_forward_past_only_and_costs():
    r=pd.DataFrame(np.random.default_rng(7).normal(.0002,.01,(460,2)),index=pd.bdate_range('2020-01-01',periods=460),columns=['A','B'])
    m={'provider':'fixture','permitted_usage':'test','adjustment':'total_return','currency':'USD','frequency':'daily','units':'decimal','retrieved_at':'2026-10-26T00:00:00Z','kind':'synthetic','coverage_start':str(r.index[0].date()),'coverage_end':str(r.index[-1].date())}
    report=evaluate(r,m,train=400,step=30,scenario_count=400,ci_samples=20)
    assert len(report['folds'])==2
    assert all(f['train_end']<f['test_start'] for f in report['folds'])
    assert report['strategies']['equal_weight']['total_cost_fraction']>0
    assert len(report['strategies'])==12
    assert report['claims']=='Exploratory comparison only; no demonstrated investment superiority.'
