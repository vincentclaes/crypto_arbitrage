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
        self.minProfitUSDT = 1
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

        except Exception as e:
            # raise
            print e

        time.sleep(self.engine.sleepTime)

    def calculate_wallet_difference(self):
        wallet_pre_arbitrage = self.calculate_wallet_value()
        pre_arbitrage_balance = self.engine.balance
        self.get_last_prices()
        self.handle_balance()
        balance_amount_diff = self._calculate_balance_diff(pre_arbitrage_balance, self.engine.balance)
        wallet_post_arbitrage_old_prices = self.calculate_wallet_value(pre_arbitrage_balance)
        wallet_post_arbitrage_new_prices = self.calculate_wallet_value()
        print ''
        print ''
        print '*********************************'
        print '*********************************'
        print '**   BALANCE AMOUNT DIFF: {}'.format(balance_amount_diff)
        print '**   BALANCE PRE: {}'.format(wallet_pre_arbitrage)
        print '**   BALANCE POST: {}'.format(wallet_post_arbitrage_new_prices)
        print '**   PRICES: {}'.format(json.dumps(self.engine.last_prices))
        print '**   GROSS PROFIT {}'.format(wallet_post_arbitrage_new_prices - wallet_pre_arbitrage)
        print '**   NETT PROFIT {}'.format(wallet_post_arbitrage_new_prices - wallet_post_arbitrage_old_prices)
        print '*********************************'
        print '*********************************'

    def _calculate_balance_diff(self, wallet_pre_arbitrage, current_balance):
        diff = {}
        for currency, amount in current_balance.iteritems():
            diff[currency] = amount - wallet_pre_arbitrage[currency]
        return diff

    def calculate_wallet_value(self, balances=None):
        wallet_value = []
        _balances = balances if balances is not None else self.engine.balance
        for currency, last_price in self.engine.last_prices.iteritems():
            value = _balances.get(currency) * last_price
            wallet_value.append(value)
        return sum(wallet_value)

    def check_openOrder(self):
        # if self.openOrderCheckCount >= 5:
        #     self.cancel_allOrders()
        # else:
        # print 'checking open orders...'
        # rs = [self.engine.get_open_order()]
        # responses = self.send_request(rs)
        #
        # if not responses[0]:
        #     print responses
        #     return False
        #
        # if responses[0].parsed:
        #     self.engine.openOrders = responses[0].parsed
        #     print self.engine.openOrders
        #     self.openOrderCheckCount += 1
        # else:
        #     self.hasOpenOrder = False
        #     print 'no open orders'
        #     print 'starting to check order book...'
        self.hasOpenOrder = False
        return True

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
        self.engine.last_prices = {}
        for res in self.send_request(rs):
            price = float(next(res.parsed.itervalues()))
            self.engine.last_prices[next(res.parsed.iterkeys())] = price
        print 'last prices {}'.format(self.engine.last_prices)
        return self.engine.last_prices

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
        2)  97.02 neo * (0,10434 eth/neo) = 10.12 eth
        buy btc and sell eth; take bid price to sell directly
        3)  10.12 eth * 0.099018 btc/eth = 1.002 btc

        ===> we make a profit of 1 - 1.002

        """

        last_prices = self.get_last_prices()
        orderbook = self.get_orderbook()

        bid_prices = [orderbook[0].parsed['ask']['price'], orderbook[1].parsed['ask']['price'],
                      orderbook[2].parsed['bid']['price']]
        # bid route BTC > ETH > NEO > BTC
        print ''
        print 'BID ROUTE'
        print 'BTC > ETH > NEO > BTC'
        print '(1 / {}) / {} * {}'.format(bid_prices[0], bid_prices[1], bid_prices[2])

        print '(1 / {}) / {} * {}'.format('ask', 'ask', 'bid')

        bidRoute_result = self.bid_route(orderbook)

        print 'bid route result : {}'.format(bidRoute_result)

        ask_prices = [orderbook[0].parsed['bid']['price'], orderbook[1].parsed['bid']['price'],
                      orderbook[2].parsed['ask']['price']]
        # ask route BTC > NEO > ETH > BTC
        print ''
        print 'ASK ROUTE'
        print 'BTC > NEO > ETH > BTC'
        print '(1 / {}) * {} * {}'.format(ask_prices[2], ask_prices[1], ask_prices[0])
        print '(1 / {}) * {} * {}'.format('ask', 'bid', 'bid')

        askRoute_result = self.ask_route(orderbook)

        print 'ask route result : {}'.format(askRoute_result)

        main_currency_price = self._get_main_currency_price()
        status = self.pick_route(bidRoute_result, askRoute_result, main_currency_price)

        if status > 0:
            maxAmounts, maxUSDT = self.calculate_max_amount(last_prices, orderbook, status)
            if maxAmounts is False:
                # we need to have the minimum amount to place an order
                return {'status': 0}

            print ''
            print 'PROFIT'

            bid_route_profit = self._calculate_profit(bidRoute_result, self.engine.feeRatio)
            print 'bidroute profit : {}'.format(bid_route_profit)

            ask_route_profit = self._calculate_profit(askRoute_result, self.engine.feeRatio)
            print 'askroute profit : {}'.format(ask_route_profit)

            if status == 1 and bid_route_profit > self.minProfitBTC:
                print strftime('%Y%m%d%H%M%S') + ' Bid Route: Result - {0} Profit - {1} Fee - {2}'.format(
                    bidRoute_result, bid_route_profit, self._calculate_fee(bidRoute_result, self.engine.feeRatio))
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
            elif status == 2 and ask_route_profit > self.minProfitBTC:
                print strftime('%Y%m%d%H%M%S') + ' Ask Route: Result - {0} Profit - {1} Fee - {2}'.format(
                    askRoute_result, ask_route_profit, self._calculate_fee(ask_route_profit, self.engine.feeRatio))
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

    def _calculate_profit(self, result, exchange_fee):
        result_minus_fees = self._calculate_fee(result, exchange_fee)
        profit = result_minus_fees - 1
        return profit

    def _calculate_fee(self, result, exchange_fee):
        return result * (1-exchange_fee)**3

    def _get_main_currency(self, ticker_name='tickerA'):
        return self.exchange[ticker_name]

    def _get_main_currency_price(self, ticker_name='tickerA'):
        return self.engine.last_prices[self._get_main_currency(ticker_name)]

    # Using USDT may not be accurate
    def calculate_max_amount(self, last_prices, orderBookRes, status):
        """
        get the maximum amount of tokens we can purchase for each token.
        1) for each coin we look for the minimum amount of tokens we can buy. We take minimum
        of balance_name and latest order in the orderbook.
        2)
        :param lastPrices:
        :param orderBookRes:
        :param status:
        :return:
        """

        ticker_pairs = ['tickerPairA', 'tickerPairB', 'tickerPairC']
        affected_balance_list = []
        maxUSDT = None
        minimum_allowed_amount = []
        order_per_ticker_pair = []
        for index, tickerIndex in enumerate(ticker_pairs):
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
                # 'bid', 'bid', 'ask' --> 1 / 1 / -1
                if index == 0:
                    bid_ask = 1
                elif index == 1:
                    bid_ask = 1
                else:
                    bid_ask = -1
            bid_ask = 'bid' if bid_ask == 1 else 'ask'
            ticker_pair = ticker_pairs[index]
            ticker_pair_amount, ticker_pair_price = self._split_cross_pair(ticker_pair)

            # for each tickerpair we need to keep track of the correct order
            order_per_ticker_pair.append(orderBookRes[index].parsed[bid_ask])

            # depending on bid or ask the balance_name that gets charged is different
            affected_balance = ticker_pair_price if bid_ask == 'ask' else ticker_pair_amount
            affected_balance_list.append(affected_balance)
            maxBalance = self._get_max_balance(orderBookRes[index], bid_ask, affected_balance)

            # we find the maximum amount of USD we can spend on the orders.
            # this means we take the minimum USD of all the maxbalances across our currencies.
            # fixme - the fee ratio can be removed here because it is taken into account futrher down the line
            USDT = maxBalance * last_prices[affected_balance] * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT:
                maxUSDT = USDT

        maxAmounts = []
        for index, ticker_pair in enumerate(ticker_pairs):
            _max_amount = self._get_max_amounts_for_tickerpair(maxUSDT, ticker_pair, last_prices, order_per_ticker_pair[index])
            maxAmounts.append(_max_amount)
            minimum_allowed_amount.append(self.exchange.get('minimum_amount').get(self.exchange[ticker_pair]))
            # _, ticker_pair_price = self._split_cross_pair(ticker_pair)
            #maxAmounts.append(maxUSDT / last_prices[ticker_pair_price])
        if all([item1 > item2 for item1, item2 in zip(maxAmounts, minimum_allowed_amount)]):
            return maxAmounts, maxUSDT
        print 'tradable amounts are too small ...'
        return False, maxUSDT

    def _get_max_amounts_for_tickerpair(self, max_usdt, ticker_pair, last_prices, order):
        """
        for more info see crypto-arbitrage_tests/triangular_arbitrage_test/calculate_max_amounts_test.py:86

        :param max_usdt:
        :param ticker_pair:
        :param last_prices:
        :param order:
        :return:
        """
        _, ticker_pair_price = self._split_cross_pair(ticker_pair)
        return max_usdt / (order.get('price') * last_prices.get(ticker_pair_price))

    def _split_cross_pair(self, cross_pair):
        return self.engine.split_cross_pair(self.exchange[cross_pair])

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
        if not self.mock:
            for order in orderInfo:
                rs.append(self.engine.place_order(
                    order['tickerPair'],
                    order['action'],
                    order['amount'],
                    order['price'])
                )

        # if not self.mock:
        #     responses = self.send_request(rs)

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

    def pick_route(self, bidRoute_result, askRoute_result, main_currency_price):
        # todo - verify calculations
        # Max amount for bid route & ask routes can be different and so less profit

        # final currency price (always BTC i guess) is the price of the coin that we start and end with while performing
        # arbitrage

        if bidRoute_result > 1 and askRoute_result > 1:
            if (bidRoute_result > askRoute_result):
                status = 1
            else:
                status = 2
        elif bidRoute_result > 1:
            status = 1  # bid route
        elif askRoute_result > 1:
            status = 2  # ask route
        else:
            status = 0  # do nothing
        return status

    def run(self):
        self.start_engine()
