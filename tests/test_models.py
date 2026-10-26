import numpy as np
import pytest
from portfolio_engine.models import empirical_es, black_litterman, covariance, scenarios, max_drawdown

def test_fractional_es_and_sign():
    assert empirical_es([1,2,3,4],.625)==pytest.approx((4+.5*3)/1.5)
    assert empirical_es([-2,-1],.5)==-1
    with pytest.raises(ValueError): empirical_es([1],1)

def test_bl_reference():
    from pypfopt.black_litterman import BlackLittermanModel
    s=np.array([[.02,.003],[.003,.01]])
    p=np.array([[1.,-1.]])
    q=np.array([.01]); omega=np.array([[.005]]); prior=np.array([.002,.003])
    got=black_litterman(s,prior,P=p,Q=q,omega=omega,evidence={'as_of':'2020-01-01','source':'supplied'},as_of='2020-01-02')
    ref=BlackLittermanModel(s,pi=prior,P=p,Q=q,omega=omega,tau=.05)
    assert np.allclose(got['mean'],ref.bl_returns())
    assert np.allclose(s+got['mean_uncertainty'],ref.bl_cov())
    assert np.array_equal(black_litterman(s,prior)['mean'],prior)

def test_psd_and_seed():
    r=np.random.default_rng(4).normal(0,.01,(500,2)); s=covariance(r)
    assert np.linalg.eigvalsh(s).min()>=0
    for family in ['gaussian','bootstrap']:
        a=scenarios(r,np.zeros(2),s,1000,42,family)
        assert np.array_equal(a,scenarios(r,np.zeros(2),s,1000,42,family))
    assert max_drawdown([-.2,.1])==pytest.approx(-.2)

def test_scenario_moments_and_synchronized_dependence():
    rng=np.random.default_rng(14); r=rng.normal(0,.01,(1000,2)); s=covariance(r); mu=np.array([.001,.002])
    g=scenarios(r,mu,s,30000,8,'gaussian')
    assert np.allclose(g.mean(axis=0),mu,atol=.0002)
    assert np.allclose(np.cov(g,rowvar=False),s,rtol=.06,atol=3e-6)
    dependent=np.c_[r[:,0],2*r[:,0]]
    b=scenarios(dependent,[.001,.002],covariance(dependent),2000,4,'bootstrap')
    assert np.allclose(b[:,1],2*b[:,0])


def test_factor_dates_must_align():
    import pandas as pd
    from portfolio_engine.models import risk_metrics
    r=pd.DataFrame({'A':[.01,.02,.03]},index=pd.date_range('2020-01-01',periods=3))
    f=pd.DataFrame({'F':[.01,.03,.04]},index=pd.date_range('2020-01-02',periods=3))
    with pytest.raises(ValueError): risk_metrics(r,[1],factors=f)
