"""One-day models. Annualized moments use 252 days; ES is never scaled."""
import numpy as np
from sklearn.covariance import LedoitWolf


def psd(matrix):
    a=np.asarray(matrix,dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.isfinite(a).all() or not np.allclose(a,a.T,atol=1e-12):
        raise ValueError('Covariance must be finite and symmetric')
    if np.linalg.eigvalsh(a).min() < -1e-10:
        raise ValueError('Covariance is not PSD')
    return (a+a.T)/2


def covariance(returns,method='shrinkage',decay=.94):
    r=np.asarray(returns,dtype=float)
    if r.ndim!=2 or len(r)<max(60,5*r.shape[1]) or not np.isfinite(r).all():
        raise ValueError('Insufficient or invalid covariance data')
    if method=='shrinkage': s=LedoitWolf().fit(r).covariance_
    elif method=='sample': s=np.atleast_2d(np.cov(r,rowvar=False))
    elif method=='ewma':
        if not 0<decay<1: raise ValueError('Invalid decay')
        w=decay**np.arange(len(r)-1,-1,-1); w/=w.sum()
        z=r-w@r
        s=(z*w[:,None]).T@z/(1-w@w)
    else: raise ValueError('Unknown covariance estimator')
    return psd(s)


def empirical_es(losses,alpha=.95):
    a=np.asarray(losses,dtype=float).ravel()
    if not 0<alpha<1 or not len(a) or not np.isfinite(a).all(): raise ValueError('Invalid ES inputs')
    a=np.sort(a)[::-1]; mass=len(a)*(1-alpha); full=int(np.floor(mass))
    return float((a[:full].sum()+(mass-full)*a[min(full,len(a)-1)])/mass)


def max_drawdown(returns):
    wealth=np.r_[1.,np.cumprod(1+np.asarray(returns))]
    return float(np.min(wealth/np.maximum.accumulate(wealth)-1))


def _dated_evidence(evidence,as_of):
    import pandas as pd
    if not isinstance(evidence,dict) or not evidence.get('source') or not evidence.get('as_of') or as_of is None:
        return False
    try:
        date=pd.to_datetime(evidence['as_of'],utc=True); decision=pd.to_datetime(as_of,utc=True)
        return bool(not pd.isna(date) and not pd.isna(decision) and date<=decision)
    except (ValueError,TypeError):
        return False


def black_litterman(sigma,prior,tau=.05,P=None,Q=None,omega=None,evidence=None,as_of=None):
    import pandas as pd
    s=psd(sigma); pi=np.asarray(prior,float)
    if pi.shape!=(len(s),) or not np.isfinite(pi).all() or not np.isfinite(tau) or tau<=0: raise ValueError('Invalid BL prior/tau')
    t=tau*s
    if P is None:
        if Q is not None or omega is not None: raise ValueError('Views require P/Q/Omega')
        return {'mean':pi.copy(),'mean_uncertainty':t,'innovation_covariance':s,'prior':pi,'tau':tau,'views':None}
    if not _dated_evidence(evidence,as_of): raise ValueError('Views need dated predecision evidence')
    p=np.asarray(P,float); q=np.asarray(Q,float); o=psd(omega)
    if p.ndim!=2 or p.shape[1]!=len(s) or q.shape!=(len(p),) or o.shape!=(len(p),len(p)) or not np.isfinite(p).all() or not np.isfinite(q).all() or np.linalg.eigvalsh(o).min()<=0: raise ValueError('Invalid views')
    a=p@t@p.T+o
    mu=pi+t@p.T@np.linalg.solve(a,q-p@pi)
    m=psd(t-t@p.T@np.linalg.solve(a,p@t))
    return {'mean':mu,'mean_uncertainty':m,'innovation_covariance':s,'prior':pi,'tau':tau,'views':{'P':p,'Q':q,'omega':o,'evidence':evidence}}


def market_prior(sigma,weights,risk_aversion,evidence,as_of):
    import pandas as pd
    w=np.asarray(weights,float)
    if w.shape!=(len(sigma),) or not np.isfinite(w).all() or (w<0).any() or not np.isclose(w.sum(),1) or not np.isfinite(risk_aversion) or risk_aversion<=0 or not _dated_evidence(evidence,as_of) or evidence.get('basis')!='market_capitalization': raise ValueError('Genuine dated market capitalization evidence required')
    return risk_aversion*psd(sigma)@w


def stationary_indices(length,size,rng,block_length=10):
    if length<1 or size<1 or block_length<1: raise ValueError('Invalid bootstrap size')
    idx=np.empty(size,dtype=int); idx[0]=rng.integers(length)
    for i in range(1,size): idx[i]=rng.integers(length) if rng.random()<1/block_length else (idx[i-1]+1)%length
    return idx


def scenarios(returns,mean,sigma,size=2000,seed=42,family='bootstrap',mean_uncertainty=None,block_length=10):
    r=np.asarray(returns,float); mu=np.asarray(mean,float); rng=np.random.default_rng(seed)
    if size<1 or mu.shape!=(r.shape[1],): raise ValueError('Invalid scenarios')
    if family=='gaussian':
        s=psd(sigma)+(0 if mean_uncertainty is None else psd(mean_uncertainty))
        out=rng.multivariate_normal(mu,s,size=size)
    elif family=='bootstrap':
        if mean_uncertainty is not None: raise ValueError('Bootstrap is conditional; predictive uncertainty unsupported')
        out=(r-r.mean(axis=0))[stationary_indices(len(r),size,rng,block_length)]+mu
    else: raise ValueError('Unknown scenario family')
    if not np.isfinite(out).all() or (out < -1).any(): raise ValueError('Impossible generated simple returns')
    return out


def risk_metrics(returns,weights,alpha=.95,factors=None):
    if factors is not None and hasattr(returns,'index') and hasattr(factors,'index') and not returns.index.equals(factors.index): raise ValueError('Factor dates must exactly align')
    r=np.asarray(returns,float); w=np.asarray(weights,float); p=r@w
    vol=float(p.std(ddof=1))
    out={'horizon':'one trading day','daily_mean':float(p.mean()),'daily_volatility':vol,'annualized_arithmetic_mean':float(p.mean()*252),'annualized_volatility':vol*np.sqrt(252),'daily_var':float(np.quantile(-p,alpha,method='higher')),'daily_es':empirical_es(-p,alpha),'historical_drawdown':max_drawdown(p),'concentration_hhi':float(w@w),'effective_positions':float(1/(w@w)),'historical_tail_count':len(p)*(1-alpha)}
    if factors is not None:
        f=np.asarray(factors,float)
        if f.ndim!=2 or len(f)!=len(r) or not np.isfinite(f).all(): raise ValueError('Factors must be aligned')
        x=np.c_[np.ones(len(f)),f]
        if np.linalg.matrix_rank(x)<x.shape[1]: raise ValueError('Rank deficient factors')
        out['factor_ols_intercept_and_betas']=np.linalg.lstsq(x,p,rcond=None)[0]
    return out
