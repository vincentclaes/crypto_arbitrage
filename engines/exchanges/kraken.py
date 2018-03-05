'''
    Maker    Taker    Volume
    0.16%    0.26%    < 50,000
    0.14%    0.24%    < 100,000
    0.12%    0.22%    < 250,000
    0.10%    0.20%    < 500,000
    0.08%    0.18%    < 1,000,000
    0.06%    0.16%    < 2,500,000
    0.04%    0.14%    < 5,000,000
    0.02%    0.12%    < 10,000,000
    0.00%    0.10%    > 10,000,000
'''

import calendar
from datetime import datetime, timedelta

from mod_imports import *


class ExchangeEngine(ExchangeEngineBase):
    def __init__(self):
        self.API_URL = 'https://api.kraken.com'
        self.apiVersion = '0'
        self.feeRatio = 0.0026
        self.sleepTime = 5
        self.async = True

    def _send_request(self, command, httpMethod, params={}, hook=None):
        command = '/{0}/{1}'.format(self.apiVersion, command)

        url = self.API_URL + command

        if httpMethod == "GET":
            R = grequests.get
        elif httpMethod == "POST":
            R = grequests.post

        headers = {}
        if not any(x in command for x in ['Public', 'public']):
            secret = self.key['private']

            params['nonce'] = int(1000 * time.time())

            message = command + hashlib.sha256(str(params['nonce']) + urllib.urlencode(params)).digest()
            signature = hmac.new(base64.b64decode(secret), message, hashlib.sha512)

            headers = {
                'API-Key': self.key['public'],
                'API-Sign': base64.b64encode(signature.digest())
            }

        args = {'data': params, 'headers': headers}
        if hook:
            args['hooks'] = dict(response=hook)

        req = R(url, **args)
        if self.async:
            return req
        else:
            response = grequests.map([req])[0].json()

        if 'error' in response:
            print response
        return response

    def get_balance(self, tickers=[]):
        return self._send_request('private/Balance', 'POST', {}, [self.hook_getBalance(tickers=tickers)])

    def hook_getBalance(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            json = r.json()
            r.parsed = {}

            if factory_kwargs['tickers']:
                filtered = filter(lambda ticker: ticker.upper() in factory_kwargs['tickers'], json['result'])
            else:
                filtered = json['result']

            for ticker in filtered:
                r.parsed[ticker.upper()] = float(json['result'][ticker])

        return res_hook

    def get_ticker_orderBook_innermost(self, ticker):
        return self._send_request('public/Depth?pair={0}&count=1'.format(ticker), 'GET', {}, self.hook_orderBook)

    def hook_orderBook(self, r, *r_args, **r_kwargs):
        json_ = r.json()
        ticker = next(iter(json_['result']))
        result = json_['result'][ticker]
        r.parsed = {
            'bid': {
                'price': float(result['bids'][0][0]),
                'amount': float(result['bids'][0][1])
            },
            'ask': {
                'price': float(result['asks'][0][0]),
                'amount': float(result['asks'][0][1])
            }
        }

    def get_open_order(self):
        return self._send_request('private/OpenOrders', 'POST', {}, self.hook_openOrder)

    def hook_openOrder(self, r, *r_args, **r_kwargs):
        json = r.json()
        print json
        # r.parsed = []
        # for order in json['result']:
        #     r.parsed.append({'orderId': str(order['OrderUuid']), 'created': order['Opened']})

    def cancel_order(self, orderID):
        return self._send_request('private/CancelOrder', 'POST', {'txid': orderID})

    def withdraw(self, ticker, withdrawalKey, amount):
        return self._send_request('private/Withdraw', 'POST',
                                  {'asset ': ticker, 'key': withdrawalKey, 'amount': amount})

    '''
        ticker: 'XRPUSD'
        action: 'bid' or 'ask'
        amount: 700
        price: 0.2
    '''

    def place_order(self, ticker, action, amount, price):
        action = 'buy' if action == 'bid' else 'sell'
        data = {'pair': ticker, 'type': action, 'volume': str(amount), 'price': str(price), 'ordertype': 'limit'}
        return self._send_request('private/AddOrder', 'POST', data)

    '''
    <time>, <open>, <high>, <low>, <close>, <vwap>, <volume>, <count>
    '''

    def get_ticker_history(self, ticker, timeframe='1'):
        # 1 hour ago
        since = calendar.timegm((datetime.utcnow() - timedelta(hours=1)).timetuple())
        return self._send_request('public/OHLC?pair={0}&interval={1}&since={2}'.format(ticker, timeframe, since), 'GET')

    def parseTickerData(self, ticker, tickerData):
        vwapIndex = 5
        for key in tickerData['result'].keys():
            if isinstance(tickerData['result'][key], list):
                return {'exchange': self.key['exchange'], 'ticker': ticker,
                        'data': list(map(lambda x: {'price': x[vwapIndex]}, tickerData['result'][key]))}

    def get_ticker_lastPrice(self, ticker):

         return self._send_request('public/Ticker?pair={}USD'.format(ticker), 'GET', {}, [self.hook_lastPrice(ticker=ticker)])

    def hook_lastPrice(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            if r.status_code >= 300:
                print 'status code: {} : {}'.format(r.status_code, r.content)
            json_ = r.json()
            key = iter(json_.get('result')).next()
            last_trade = json_.get('result').get(key).get('c')
            last_tradeprice = float(last_trade[0])
            r.parsed = {}
            r.parsed[factory_kwargs['ticker']] = last_tradeprice
        return res_hook
