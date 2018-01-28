from mod_imports import *
import jsonpath_rw_ext
import json
class ExchangeEngine(ExchangeEngineBase):
    def __init__(self):
        self.API_URL = 'https://api.coinigy.com/api'
        self.apiVersion = 'v1'
        self.sleepTime = 5
        self.feeRatio = 0.002
        self.async = True

    def _send_request(self, command, httpMethod, params={}, hook=None):
        command = '/{0}/{1}'.format(self.apiVersion, command)

        url = self.API_URL + command
        headers = {}
        if httpMethod == "GET":
            R = grequests.get
        elif httpMethod == "POST":
            R = grequests.post

            # secret = self.key['private']
            # params['request'] = command
            # params['nonce'] = str(long(1000000 * time.time()))
            #
            # j = json.dumps(params)
            # message = base64.standard_b64encode(j.encode('utf8'))
            #
            # signature = hmac.new(secret.encode('utf8'), message, hashlib.sha384)
            # signature = signature.hexdigest()

            headers = {
                'Content-Type': 'application/json',
                'X-API-KEY': self.key['public'],
                'X-API-SECRET': self.key['private']
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

    def get_accounts(self, exchange_code):
        return self._send_request('exchanges', 'POST', {}, self.hook_get_account)

    def hook_get_account(self, r, *args, **kwargs):
        pass

    def get_markets_for_account(self, exchange_code):
        return self._send_request('markets', 'POST', {"exchange_code": exchange_code}, self.hook_get_markets_for_account)

    def hook_get_markets_for_account(self, r, *args, **kwargs):
        r_data = json.loads(r.content).get('data')

    '''
        return in r.parsed, showing all and required tickers
        {
            'ETH': 0.005,
            'OMG': 0
        }
    '''

    def get_balance(self, auth_id, tickers=[]):
        return self._send_request('balances', 'POST', {'auth_id':auth_id}, [self.hook_getBalance(tickers=tickers)])

    def hook_getBalance(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            json = r.json()
            r.parsed = {ticker:0.0 for ticker in factory_kwargs.get('tickers') }

            if factory_kwargs['tickers']:
                json = filter(lambda ticker: ticker['balance_curr_code'].upper() in factory_kwargs['tickers'], json.get('data'))

            for ticker in json:
                r.parsed[ticker['balance_curr_code'].upper()] = float(ticker.get('balance_amount_avail', 0))

        return res_hook

    '''
        return in r.parsed
        {
            'bid': {
                'price': 0.02202,
                'amount': 1103.5148
            },
            'ask': {
                'price': 0.02400,
                'amount': 103.2
            },           
        }
    '''

    def get_ticker_orderBook_innermost(self, exchange_code, ticker):
        payload = {
            "exchange_code": exchange_code,
            "exchange_market": ticker,
            "type": "orders"
        }
        return self._send_request('data', 'POST', json.dumps(payload), self.hook_orderBook)

    def hook_orderBook(self, r, *r_args, **r_kwargs):
        data = json.loads(r.content).get('data')
        if data['asks'] and data['bids']:
            r.parsed = {
                'bid': {
                    'price': float(data['bids'][0]['price']),
                    'amount': float(data['bids'][0]['quantity'])
                },
                'ask': {
                    'price': float(data['asks'][0]['price']),
                    'amount': float(data['asks'][0]['quantity'])
                }
            }
        else:
            r.parsed = {}

    '''
        return in r.parsed
        [
            {
                'orderId': 1242424
            }
        ]
    '''

    def get_open_order(self):
        return self._send_request('orders', 'POST', {}, self.hook_openOrder)

    def hook_openOrder(self, r, *r_args, **r_kwargs):
        json = r.json()
        r.parsed = []
        for order in json:
            r.parsed.append({'orderId': order['id'], 'created': order['timestamp']})

    '''
        ticker: 'OMGETH'
        action: 'bid' or 'ask'
        amount: 700
        price: 0.2
    '''

    def place_order(self, ticker, action, amount, price):
        action = 'buy' if action == 'bid' else 'sell'
        data = {'symbol': ticker, 'side': action, 'amount': str(amount), 'price': str(price), 'exchange': 'bitfinex',
                'type': 'exchange limit'}
        return self._send_request('order/new', 'POST', data)

    def cancel_order(self, orderID):
        return self._send_request('order/cancel', 'POST', {'order_id': long(orderID)})

    '''
        return USDT in r.parsed
        {
            'BTC': 18000    
        }
    '''

    def get_ticker_lastPrice(self,exchange_code, exchange_markets, ticker):
        return self._send_request('ticker', 'POST', json.dumps({'exchange_code': str(exchange_code), 'exchange_market': '{}/USD'.format(ticker)}),
                                  [self.hook_lastPrice(ticker=ticker)])

    def hook_lastPrice(self, *factory_args, **factory_kwargs):
        def res_hook(r, *r_args, **r_kwargs):
            r.parsed = {}
            if r.content:
                data = json.loads(r.content).get('data')[0]
                r.parsed[factory_kwargs['ticker']] = data['last_trade']

        return res_hook