"""Official Webull account_v2 reads only. Unsupported response shapes fail closed."""
import io
import os
import pandas as pd
from .data import read_portfolio, utc

class BrokerError(ValueError): pass


def _response(call,*args):
    try: response=call(*args)
    except Exception: raise BrokerError('Broker connectivity or SDK failure; no credentials logged') from None
    if response.status_code in (401,403): raise BrokerError('Broker authentication/eligibility denied')
    if response.status_code==429: raise BrokerError('Broker rate limited; retry later')
    if response.status_code!=200: raise BrokerError('Broker read failed')
    if any(k.lower() in {'link','x-next-page','pagination-key','x-pagination-key'} for k in getattr(response,'headers',{})):
        raise BrokerError('Unexpected broker pagination')
    try: return response.json()
    except Exception: raise BrokerError('Invalid broker response') from None


def read_webull(account_id,as_of,valuation_timestamp,eligible=False,account_v2=None):
    """Timestamp must be independently verified; retrieval time is not quote freshness.

    Official account positions omit quote timestamps. Without independently supplied
    valuation evidence the caller must not invoke this adapter for an actionable report.
    """
    if not eligible: raise BrokerError('TH account eligibility must be independently confirmed')
    utc(valuation_timestamp)
    if account_v2 is None:
        key=os.environ.get('WEBULL_APP_KEY'); secret=os.environ.get('WEBULL_APP_SECRET')
        if not key or not secret: raise BrokerError('Missing broker environment credentials')
        try:
            from webull.core.client import ApiClient
            from webull.trade.trade.v2.account_info_v2 import AccountV2
            api=ApiClient(key,secret,'th'); api.add_endpoint('th','api.webull.co.th')
            account_v2=AccountV2(api)
        except Exception: raise BrokerError('Official broker SDK unavailable or initialization failed') from None
    accounts=_response(account_v2.get_account_list)
    if not isinstance(accounts,list) or not any(isinstance(a,dict) and a.get('account_id')==account_id and a.get('account_type')=='CASH' for a in accounts):
        raise BrokerError('Unsupported account list, pagination, or account type; CASH account required')
    balance=_response(account_v2.get_account_balance,account_id)
    positions=_response(account_v2.get_account_position,account_id)
    try:
        if not isinstance(balance,dict) or not isinstance(positions,list) or any(k in balance for k in ('pagination_key','has_more','next','data')): raise ValueError()
        if balance['total_asset_currency']!='USD' or any(float(balance.get(k,0))!=0 for k in ('used_margin','used_margin_for_open_order','interests_unpaid')): raise ValueError()
        assets=balance['account_currency_assets']
        if len(assets)!=1 or assets[0]['currency']!='USD' or float(assets[0].get('frozen_amount',0))!=0 or float(assets[0].get('held_amount',0))!=0: raise ValueError()
        cash=float(balance['total_cash_balance']); nav=float(balance['total_net_liquidation_value'])
        rows=[]
        for p in positions:
            if p['instrument_type']!='EQUITY' or p['currency']!='USD' or p.get('legs') or any(k in p for k in ('pagination_key','has_more','next')): raise ValueError()
            rows.append({'symbol':p['symbol'],'quantity':p['quantity'],'price':p['last_price'],'currency':'USD','valuation_timestamp':valuation_timestamp,'nav':nav,'cost_basis':p['cost_price']})
        rows.append({'symbol':'CASH','quantity':cash,'price':1,'currency':'USD','valuation_timestamp':valuation_timestamp,'nav':nav,'cost_basis':0})
        if abs(sum(float(p['quantity'])*float(p['last_price']) for p in positions)-float(balance['total_market_value']))>.01: raise ValueError()
        # Reuse exactly the CSV trust boundary and accounting checks.
        normalized=read_portfolio(io.StringIO(pd.DataFrame(rows).to_csv(index=False)),as_of)
    except (ValueError,KeyError,TypeError,OverflowError): raise BrokerError('Unsupported or unreconciled broker schema; snapshot rejected') from None
    normalized['provenance']={'provider':'Webull official account_v2','region':'TH','host':'api.webull.co.th','valuation_evidence':'caller supplied independently verified timestamp','live_validation':'not established by mocks'}
    return normalized
