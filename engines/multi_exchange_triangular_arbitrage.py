import json
import time
from collections import defaultdict
from time import strftime

import grequests

from exchanges.loader import EngineLoader


class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.exchange_names = self.exchange.get('exchange_name', [])
        self.exchange_codes = self.exchange.get('exchange_code', [])
        self.mock = mock
        self.minProfitUSDT = 0.3
        self.hasOpenOrder = True  # always assume there are open orders first
        self.openOrderCheckCount = 0

        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

    def start_engine(self):
        print strftime('%Y%m%d%H%M%S') + ' starting Triangular Arbitrage Engine...'
        if self.mock:
            print '---------------------------- MOCK MODE ----------------------------'
        while True:
            try:
                if not self.exchange_names:
                    self.exchange_names = self.engine.get_accounts(self.exchange_names)
                for exchange_code in self.exchange_codes:
                    triangular_combinations = self.get_triangular_combinations(exchange_code)
                    for currency, conversion_currencies in triangular_combinations.iteritems():
                        conversion_currencies = sorted(conversion_currencies)
                        if len(conversion_currencies) == 2:
                            print 'checking {}, {}, {}'.format(currency, conversion_currencies[0],
                                                               conversion_currencies[1])
                            self.exchange["tickerPairA"] = '{}/{}'.format(conversion_currencies[1],
                                                                          conversion_currencies[0])
                            self.exchange["tickerPairB"] = '{}/{}'.format(currency, conversion_currencies[0])
                            self.exchange["tickerPairC"] = '{}/{}'.format(currency, conversion_currencies[1])
                            self.exchange["tickerA"] = conversion_currencies[0]
                            self.exchange["tickerB"] = conversion_currencies[1]
                            self.exchange["tickerC"] = currency
                            self.check_account_combination(exchange_code)
            except Exception as e:
                print e
            time.sleep(self.engine.sleepTime)

    def check_account_combination(self, exchange_code):
        # TODO -> do something with the combination
        if not self.mock and self.hasOpenOrder:
            self.check_openOrder()
        elif self.check_balance(self.exchange.get('auth_id')):
            bookStatus = self.check_orderBook(exchange_code)
            if bookStatus['status']:
                self.place_order(bookStatus['orderInfo'])

    def get_triangular_combinations(self, account):
        req = self.engine.get_markets_for_account(account)
        markets = self.send_request([req])
        combinatons = []
        for account_combi in json.loads(markets[0].content).get('data'):
            if account_combi.get('exch_code') == account:
                combinatons.append(account_combi.get('mkt_name'))
        combinations_object = defaultdict(list)
        for combination in combinatons:
            x, y = combination.split('/')
            if not y == 'USD' or y == 'EUR':
                combinations_object[x].append(y)
        return combinations_object

    def get_accounts(self):
        return 'return the accounts for our user'

    def check_openOrder(self):
        if self.openOrderCheckCount >= 5:
            self.cancel_allOrders()
        else:
            print 'checking open orders...'
            rs = [self.engine.get_open_order()]
            responses = self.send_request(rs)

            if not responses[0]:
                print responses
                return False

            if responses[0].parsed:
                self.engine.openOrders = responses[0].parsed
                print self.engine.openOrders
                self.openOrderCheckCount += 1
            else:
                self.hasOpenOrder = False
                print 'no open orders'
                print 'starting to check order book...'

    def cancel_allOrders(self):
        print 'cancelling all open orders...'
        rs = []
        print self.exchange['exchange']
        for order in self.engine.openOrders:
            print order
            rs.append(self.engine.cancel_order(order['orderId']))

        responses = self.send_request(rs)

        self.engine.openOrders = []
        self.hasOpenOrder = False

    # Check and set current balance
    def check_balance(self, auth_id):
        rs = [self.engine.get_balance(auth_id, [
            self.exchange['tickerA'],
            self.exchange['tickerB'],
            self.exchange['tickerC']
        ])]

        responses = self.send_request(rs)

        self.engine.balance = responses[0].parsed

        ''' Not needed? '''
        # if not self.mock:
        #     for res in responses:
        #         for ticker in res.parsed:
        #             if res.parsed[ticker] < 0.05:
        #                 print ticker, res.parsed[ticker], '- Not Enough'
        #                 return False
        return True

    def check_orderBook(self, exchange_code):
        rs = [self.engine.get_ticker_lastPrice(exchange_code, self.exchange['tickerPairA'], self.exchange['tickerA']),
              self.engine.get_ticker_lastPrice(exchange_code, self.exchange['tickerPairB'], self.exchange['tickerB']),
              self.engine.get_ticker_lastPrice(exchange_code, self.exchange['tickerPairC'], self.exchange['tickerC']),
              ]
        lastPrices = []
        for res in self.send_request(rs):
            lastPrices.append(float(next(res.parsed.itervalues())))

        rs = [self.engine.get_ticker_orderBook_innermost(exchange_code, self.exchange['tickerPairA']),
              self.engine.get_ticker_orderBook_innermost(exchange_code, self.exchange['tickerPairB']),
              self.engine.get_ticker_orderBook_innermost(exchange_code, self.exchange['tickerPairC']),
              ]

        responses = self.send_request(rs)

        print '{} : {}'.format(self.exchange['tickerPairA'], lastPrices[0])
        print '{} : {}'.format(self.exchange['tickerPairB'], lastPrices[1])
        print '{} : {}'.format(self.exchange['tickerPairC'], lastPrices[2])

        # bid route BTC->ETH->LTC->BTC
        bidRoute_result = (1 / responses[0].parsed['ask']['price']) \
                          / responses[1].parsed['ask']['price'] \
                          * responses[2].parsed['bid']['price']

        # ask route ETH->BTC->LTC->ETH
        askRoute_result = (1 * responses[0].parsed['bid']['price']) \
                          / responses[2].parsed['ask']['price'] \
                          * responses[1].parsed['bid']['price']

        # Max amount for bid route & ask routes can be different and so less profit
        if bidRoute_result > 1 or \
                (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (
                            askRoute_result - 1) * lastPrices[1]):
            status = 1  # bid route
        elif askRoute_result > 1:
            status = 2  # ask route
        else:
            status = 0  # do nothing

        if status > 0:
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
            fee = 0
            for index, amount in enumerate(maxAmounts):
                fee += amount * lastPrices[index]
            fee *= self.engine.feeRatio

            bidRoute_profit = (bidRoute_result - 1) * lastPrices[0] * maxAmounts[0]
            askRoute_profit = (askRoute_result - 1) * lastPrices[1] * maxAmounts[1]
            # print 'bidRoute_profit - {0} askRoute_profit - {1} fee - {2}'.format(
            #     bidRoute_profit, askRoute_profit, fee
            # )
            if status == 1 and bidRoute_profit - fee > self.minProfitUSDT:
                print strftime('%Y%m%d%H%M%S') + ' Bid Route: Result - {0} Fee - {1}'.format(
                    bidRoute_result, fee)
                print '****************'
                print strftime('%Y%m%d%H%M%S') + ' Profit - {0} '.format(
                    bidRoute_profit)
                print '****************'

                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "bid",
                        "price": responses[0].parsed['ask']['price'],
                        "amount": maxAmounts[0]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "bid",
                        "price": responses[1].parsed['ask']['price'],
                        "amount": maxAmounts[1]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "ask",
                        "price": responses[2].parsed['bid']['price'],
                        "amount": maxAmounts[2]
                    }
                ]
                return {'status': 1, "orderInfo": orderInfo}
            elif status == 2 and askRoute_profit - fee > self.minProfitUSDT:
                print strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(
                    askRoute_result, askRoute_profit, fee)
                print '****************'
                print strftime('%Y%m%d%H%M%S') + ' Profit - {0} '.format(
                    askRoute_profit)
                print '****************'
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": responses[0].parsed['bid']['price'],
                        "amount": maxAmounts[0]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": responses[1].parsed['bid']['price'],
                        "amount": maxAmounts[1]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": responses[2].parsed['ask']['price'],
                        "amount": maxAmounts[2]
                    }
                ]
                return {'status': 2, 'orderInfo': orderInfo}
        return {'status': 0}

    # Using USDT may not be accurate
    def getMaxAmount(self, lastPrices, orderBookRes, status):
        maxUSDT = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # 1: 'bid', -1: 'ask'
            if index == 0:
                bid_ask = -1
            elif index == 1:
                bid_ask = -1
            else:
                bid_ask = 1
            # switch for ask route
            if status == 2: bid_ask *= -1
            bid_ask = 'bid' if bid_ask == 1 else 'ask'

            maxBalance = min(orderBookRes[index].parsed[bid_ask]['amount'],
                             self.engine.balance[self.exchange[tickerIndex]])
            # print '{0} orderBookAmount - {1} ownAmount - {2}'.format(
            #     self.exchange[tickerIndex], 
            #     orderBookRes[index].parsed[bid_ask]['amount'], 
            #     self.engine.balance[self.exchange[tickerIndex]]
            # )
            USDT = maxBalance * lastPrices[index] * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT:
                maxUSDT = USDT

        maxAmounts = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # May need to handle scientific notation
            maxAmounts.append(maxUSDT / lastPrices[index])

        return maxAmounts

    def place_order(self, orderInfo):
        print orderInfo
        rs = []
        for order in orderInfo:
            rs.append(self.engine.place_order(
                order['tickerPair'],
                order['action'],
                order['amount'],
                order['price'])
            )

        if not self.mock:
            responses = self.send_request(rs)

        self.hasOpenOrder = True
        self.openOrderCheckCount = 0

    def send_request(self, rs):
        responses = grequests.map(rs)
        for res in responses:
            if not res:
                print responses
                raise Exception
        return responses

    def run(self):
        self.start_engine()
