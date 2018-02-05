import json
import time
from time import strftime

import grequests

from exchanges.loader import EngineLoader


class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitBTC = 0.0005
        self.hasOpenOrder = True  # always assume there are open orders first
        self.openOrderCheckCount = 0

        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

    def start_engine(self):
        print strftime('%Y%m%d%H%M%S') + ' starting Triangular Arbitrage Engine...'
        if self.mock:
            print '---------------------------- MOCK MODE ----------------------------'
        # Send the request asynchronously
        while True:
            self._run()

    def _run(self):
        print '-------------------------------'
        print strftime('%Y%m%d%H%M%S going for the next run ..')
        try:
            if not self.mock and self.hasOpenOrder:
                self.check_openOrder()
            elif self.handle_balance():
                bookStatus = self.check_orderBook()
                if bookStatus['status']:
                    self.place_order(bookStatus['orderInfo'])
                    print 'order placed'
                    self.calculate_wallet_difference()
                else:
                    print ''
                    print 'no arbitrage possibilities'

        except Exception, e:
            # raise
            print e

        time.sleep(self.engine.sleepTime)

    def calculate_wallet_difference(self):
        wallet_pre_arbitrage = self.calculate_wallet_value()
        pre_arbitrage_balance = self.engine.balance
        self.get_last_prices()
        self.handle_balance()
        wallet_post_arbitrage_old_prices = self.calculate_wallet_value(pre_arbitrage_balance)
        wallet_post_arbitrage_new_prices = self.calculate_wallet_value()
        print ''
        print ''
        print '*********************************'
        print '*********************************'
        print '**   BALANCE PRE: {}'.format(wallet_pre_arbitrage)
        print '**   BALANCE POST: {}'.format(wallet_post_arbitrage_new_prices)
        print '**   PRICES: {}'.format(json.dumps(self.engine.last_prices))
        print '**   GROSS PROFIT {}'.format(wallet_post_arbitrage_new_prices - wallet_pre_arbitrage)
        print '**   NETT PROFIT {}'.format(wallet_post_arbitrage_new_prices - wallet_post_arbitrage_old_prices)
        print '*********************************'
        print '*********************************'


    def calculate_wallet_value(self, balances=None):
        wallet_value = []
        _balances = balances if balances is not None else self.engine.balance
        for currency, last_price in self.engine.last_prices.iteritems():
            value = _balances.get(currency) * last_price
            wallet_value.append(value)
        return sum(wallet_value)

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


    def check_balance(self):
        rs = [self.engine.get_balance([
            self.exchange['tickerA'],
            self.exchange['tickerB'],
            self.exchange['tickerC']
        ])]

        responses = self.send_request(rs)
        return responses[0].parsed

    # Check and set current balance
    def handle_balance(self):
        balance = self.check_balance()
        self.engine.balance = balance

        return True

    def get_last_prices(self):
        rs = [self.engine.get_ticker_lastPrice(self.exchange['tickerA']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerB']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerC']),
              ]
        last_prices = []
        self.engine.last_prices = {}
        for res in self.send_request(rs):
            price = float(next(res.parsed.itervalues()))
            last_prices.append(price)
            self.engine.last_prices[next(res.parsed.iterkeys())] = price
        return last_prices

    def get_orderbook(self):
        print 'ORDERBOOK'
        rs = [self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairA']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairB']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairC']),
              ]

        orderbook = self.send_request(rs)
        return orderbook

    def check_orderBook(self):
        """

        bid route BTC->ETH->LTC->BTC

        if ticker pairs are defined as followed:

        "tickerPairA": "BTC-ETH",
        "tickerPairB": "ETH-LTC",
        "tickerPairC": "BTC-LTC",

        we should take

        "tickerPairA":  --> ask (sell btc for eth)
        "tickerPairB":  --> ask (sell eth for ltc)
        "tickerPairC":  --> bid (buy btc for ltc)

        depending on the pairs (BTC-ETH  <-> ETH-BTC) we create a bid or an ask order



        bidRoute_result = (1 / responses[0].parsed['ask']['price']) \
                            / responses[1].parsed['ask']['price']   \
                            * responses[2].parsed['bid']['price']


        # ask route ETH->BTC->LTC->ETH
        askRoute_result = (1 * responses[0].parsed['bid']['price']) \
                            / responses[2].parsed['ask']['price']   \
                            * responses[1].parsed['bid']['price']



        TRIANGULAR ARBITRAGE EXPLAINED

        ask price is the lowest price which a seller wants to sell
        bid price is the highest price which a buyer wants to buy

           pair     expressed in        bid         ask
        ---------------------------------------------------
        "ETH-BTC"      bitcoin        0,099018    0,099075
        "NEO-ETH"      ethereum       0,10434     0,104482
        "NEO-BTC"      bitcoin        0,010301    0,010307

        we start with 1 BTC

        route BTC > ETH > NEO > BTC

        BTC > ETH we have btc and we want to buy ethereum on the pair ETH-BTC (expressed in bitcoin per ethereum)
        1)  1 btc -> buy ethereum (bid); take ask price to buy it directly
            1 btc * 1/(0,099075 btc/eth) = 10,099 eth
            we have to take 1/ask price so that btc can cancel each other out

        ETH > NEO we have eth and we want to buy neo
        2)  10,099 eth -> buy neo (bid); take ask price to buy directly
            10,099 eth * 1/(0,104482 eth/neo) = 96.6577 neo

        NEO > BTC we have neo and want to buy btc
        3)  96.6577 neo -> sell neo (ask); we want to sell our neo and take the bid price.
            96.6577 neo * 0.010301 btc/neo = 0.9957 btc

        ===> we make a los of 1 - 0.9957


        route BTC > NEO > ETH > BTC

        buy neo, sell btc; take ask price to buy neo directly
        1)  1 btc * 1/(0.010307 btc/neo) = 97.02 neo
        buy ethereum, sell neo; take bid price to sell directly
        2)  97.02 neo * 1/(0,10434 eth/neo) = 10.12 eth
        buy btc and sell eth; take bid price to sell directly
        3)  10.12 eth * 0.099018 btc/eth = 1.002 btc

        ===> we make a profit of 1 - 1.002

        """

        last_prices = self.get_last_prices()
        orderbook = self.get_orderbook()

        # bid route BTC > ETH > NEO > BTC
        print ''
        print 'BID ROUTE'
        print 'BTC > ETH > NEO > BTC'
        print '(1 / {}) / {} * {}'.format(orderbook[0].parsed['ask']['price'], orderbook[1].parsed['ask']['price'],
                                          orderbook[2].parsed['bid']['price'])

        print '(1 * {}) / {} * {}'.format('ask', 'ask', 'bid')

        bidRoute_result = self.bid_route(orderbook)

        print 'bid route result : {}'.format(bidRoute_result)

        # ask route BTC > NEO > ETH > BTC
        print ''
        print 'ASK ROUTE'
        print 'BTC > NEO > ETH > BTC'
        print '(1 * {}) / {} * {}'.format(orderbook[0].parsed['ask']['price'], orderbook[2].parsed['bid']['price'],
                                          orderbook[1].parsed['ask']['price'])
        print '(1 * {}) / {} * {}'.format('ask', 'bid', 'ask')

        askRoute_result = self.ask_route(orderbook)

        print 'ask route result : {}'.format(askRoute_result)

        status = self.pick_route(bidRoute_result, askRoute_result)

        if status > 0:
            maxAmounts = self.getMaxAmount(last_prices, orderbook, status)
            if maxAmounts < self.exchange.get('minimum_amount'):
                # we need to have the minimum amount to place an order
                return {'status': 0}
            fee = 0
            for index, amount in enumerate(maxAmounts):
                # calculate total fee in USD
                fee += amount * last_prices[index]
            fee *= self.engine.feeRatio
            # express fee in btc because the profits are also expressed in btc
            # fixme - this is very hardcded. ideally we need 1 unit to compare everything,
            # maybe good to use usd for everything
            fee = fee/last_prices[0]
            print ''
            print 'PROFIT'
            bidRoute_profit = (bidRoute_result - 1) * last_prices[0] * maxAmounts[0]
            print 'bidroute profit : {}'.format(bidRoute_profit)
            askRoute_profit = (askRoute_result - 1) * last_prices[1] * maxAmounts[1]
            print 'askroute profit : {}'.format(askRoute_profit)

            if status == 1 and bidRoute_profit - fee > self.minProfitBTC:
                print strftime('%Y%m%d%H%M%S') + ' Bid Route: Result - {0} Profit - {1} Fee - {2}'.format(
                    bidRoute_result, bidRoute_profit, fee)
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "bid",
                        "price": orderbook[0].parsed['ask']['price'],
                        "amount": '{:.20f}'.format(maxAmounts[0])
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "bid",
                        "price": orderbook[1].parsed['ask']['price'],
                        "amount": '{:.20f}'.format(maxAmounts[1])
                    },
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "ask",
                        "price": orderbook[2].parsed['bid']['price'],
                        "amount": '{:.20f}'.format(maxAmounts[2])
                    }
                ]

                return {'status': 1, "orderInfo": orderInfo}
            elif status == 2 and askRoute_profit - fee > self.minProfitBTC:
                print strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(
                    askRoute_result, askRoute_profit, fee)
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": orderbook[2].parsed['ask']['price'],
                        "amount": '{:.20f}'.format(maxAmounts[2])
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": orderbook[1].parsed['bid']['price'],
                        "amount": '{:.20f}'.format(maxAmounts[1])
                    },
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": orderbook[0].parsed['bid']['price'],
                        "amount": '{:.20f}'.format(maxAmounts[0])
                    }
                ]
                return {'status': 2, 'orderInfo': orderInfo}
        return {'status': 0}

    # Using USDT may not be accurate
    def getMaxAmount(self, lastPrices, orderBookRes, status):
        """
        get the maximum amount of tokens we can purchase for each token.
        1) for each coin we look for the minimum amount of tokens we can buy. We take minimum of balance and latest order in the orderbook.
        2)
        :param lastPrices:
        :param orderBookRes:
        :param status:
        :return:
        """


        ticker_pairs = ['tickerPairA','tickerPairB','tickerPairC']
        affected_balance_list = []
        maxUSDT = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # 1: 'bid', -1: 'ask'
            if status == 1:
                # status == 1 --> check bid route
                # ask / ask / bid --> -1 / -1 / 1
                if index == 0:
                    bid_ask = -1
                elif index == 1:
                    bid_ask = -1
                else:
                    bid_ask = 1
            elif status == 2:
                # status == 2 --> check ask route
                # ask / ask / bid --> -1 / 1 / -1
                if index == 0:
                    bid_ask = -1
                elif index == 1:
                    bid_ask = 1
                else:
                    bid_ask = -1
            bid_ask = 'bid' if bid_ask == 1 else 'ask'
            ticker_pair = ticker_pairs[index]
            ticker_pair_amount, ticker_pair_price = self._split_cross_pair(ticker_pair)

            # depending on bid or ask the balance that gets charged is different
            affected_balance = ticker_pair_price if bid_ask == 'ask' else ticker_pair_amount
            affected_balance_list.append(affected_balance)
            maxBalance = self._get_max_balance(orderBookRes[index], bid_ask, affected_balance)
            # # take the minimum of the amount in order book with the amount in your balance
            # orderbook_amount = orderBookRes[index].parsed[bid_ask]['amount']
            # balance_amount = self.engine.balance[self.exchange[tickerIndex]]
            # maxBalance = min(orderbook_amount, balance_amount)

            # we find the maximum amount of USD we can spend on the orders.
            # this means we take the minimum USD of all the maxbalances across our currencies.
            # fixme - the fee ratio can be removed here because it is taken into account futrher down the line
            USDT = maxBalance * self.engine.last_prices[affected_balance] * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT:
                maxUSDT = USDT

        # # FIXME - we should refactor how prices are handled
        # # BTC-ETH is expressed in BTC
        # # NEO-ETH is expressed in ETH
        # # NEO-BTC is expressed in BTC
        # lastPrices = [lastPrices[0], lastPrices[1], lastPrices[0]]
        # calculate the amount of coins needed for each coin in the list
        maxAmounts = []
        #for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
        for index, balance in enumerate(affected_balance_list):
            maxAmounts.append(maxUSDT / self.engine.last_prices[balance])

        return maxAmounts

    def _split_cross_pair(self, cross_pair):
        ticker_pair_amount, ticker_pair_price = self.exchange[cross_pair].split('-')
        return ticker_pair_amount, ticker_pair_price


    def _get_max_balance(self, order_book, bid_ask, affected_balance):
        # take the minimum of the amount in order book with the amount in your balance
        orderbook_amount = order_book.parsed[bid_ask]['amount']

        # depending on bid or ask the balance that gets charged is different
        balance_amount = self.engine.balance[affected_balance]

        # get minimum of both amounts
        maxBalance = min(orderbook_amount, balance_amount)
        return maxBalance


    def place_order(self, orderInfo):
        print ''
        print 'ORDER INFO'
        print json.dumps(orderInfo)
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

    @staticmethod
    def bid_route(responses):
        """
        route BTC > ETH > NEO > BTC

        BTC > ETH we have btc and we want to buy ethereum on the pair ETH-BTC (expressed in bitcoin per ethereum)
        1)  1 btc -> buy ethereum (bid); take ask price to buy it directly
            1 btc * 1/(0,099075 btc/eth) = 10,099 eth
            we have to take 1/ask price so that btc can cancel each other out

        ETH > NEO we have eth and we want to buy neo
        2)  10,099 eth -> buy neo (bid); take ask price to buy directly
            10,099 eth * 1/(0,104482 eth/neo) = 96.6577 neo

        NEO > BTC we have neo and want to buy btc
        3)  96.6577 neo -> sell neo (ask); we want to sell our neo and take the bid price.
            96.6577 neo * 0.010301 btc/neo = 0.9957 btc
        :param responses:
        :return:
        """
        result = (1 / responses[0].parsed['ask']['price']) \
                 / responses[1].parsed['ask']['price'] \
                 * responses[2].parsed['bid']['price']
        return result

    @staticmethod
    def ask_route(responses):
        """
        route BTC > NEO > ETH > BTC

        buy neo, sell btc; take ask price to buy neo directly
        1)  1 btc * 1/(0.010307 btc/neo) = 97.02 neo
        buy ethereum, sell neo; take bid price to sell directly
        2)  97.02 neo * 0,10434 eth/neo = 10.12 eth
        buy btc and sell eth; take bid price to sell directly
        3)  10.12 eth * 0.099018 btc/eth = 1.002 btc


        :param responses:
        :return:
        """
        result = (1 / responses[2].parsed['ask']['price']) \
                 * responses[1].parsed['bid']['price'] \
                 * responses[0].parsed['bid']['price']
        return result

    def pick_route(self, bidRoute_result, askRoute_result):
        # todo - verify calculations
        # Max amount for bid route & ask routes can be different and so less profit

        # final currency price (always BTC i guess) is the price of the coin that we start and end with while performing
        # arbitrage
        final_currency_price = self.engine[self.exchange['tickerA']]

        if bidRoute_result > 1 or \
                (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * final_currency_price > (
                            askRoute_result - 1) * final_currency_price):
            status = 1  # bid route
        elif askRoute_result > 1:
            status = 2  # ask route
        else:
            status = 0  # do nothing
        return status

    def run(self):
        self.start_engine()
