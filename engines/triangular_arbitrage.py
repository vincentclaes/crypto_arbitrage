import json
import time
from time import strftime

import grequests

from exchanges.loader import EngineLoader


class CryptoEngineTriArbitrage(object):
    def __init__(self, exchange, mock=False):
        self.exchange = exchange
        self.mock = mock
        self.minProfitUSDT = 0.3
        self.hasOpenOrder = True  # always assume there are open orders first
        self.openOrderCheckCount = 0

        self.engine = EngineLoader.getEngine(self.exchange['exchange'], self.exchange['keyFile'])

    def start_engine(self):
        print strftime('%Y%m%d%H%M%S') + ' starting Triangular Arbitrage Engine...'
        if self.mock:
            print '---------------------------- MOCK MODE ----------------------------'
        # Send the request asynchronously
        while True:
            try:
                if not self.mock and self.hasOpenOrder:
                    self.check_openOrder()
                elif self.check_balance():
                    bookStatus = self.check_orderBook()
                    if bookStatus['status']:
                        self.place_order(bookStatus['orderInfo'])
                        print 'order placed'
            except Exception, e:
                # raise
                print e

            time.sleep(self.engine.sleepTime)

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
    def check_balance(self):
        rs = [self.engine.get_balance([
            self.exchange['tickerA'],
            self.exchange['tickerB'],
            self.exchange['tickerC']
        ])]

        responses = self.send_request(rs)

        self.engine.balance = responses[0].parsed

        return True

    def check_orderBook(self):
        rs = [self.engine.get_ticker_lastPrice(self.exchange['tickerA']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerB']),
              self.engine.get_ticker_lastPrice(self.exchange['tickerC']),
              ]
        lastPrices = []
        for res in self.send_request(rs):
            lastPrices.append(float(next(res.parsed.itervalues())))

        rs = [self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairA']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairB']),
              self.engine.get_ticker_orderBook_innermost(self.exchange['tickerPairC']),
              ]

        responses = self.send_request(rs)

        print '{} : {}'.format(self.exchange['tickerPairA'], lastPrices[0])
        print '{} : {}'.format(self.exchange['tickerPairB'], lastPrices[1])
        print '{} : {}'.format(self.exchange['tickerPairC'], lastPrices[2])

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
        # "tickerPairA": "ETH-BTC",
        # "tickerPairB": "NEO-ETH",
        # "tickerPairC": "NEO-BTC",

        print 'response 0 : {}'.format(responses[0].url.rsplit('/')[-1])
        print 'response 1 : {}'.format(responses[1].url.rsplit('/')[-1])
        print 'response 2 : {}'.format(responses[2].url.rsplit('/')[-1])


        # bid route BTC > ETH > NEO > BTC

        print 'bid_route'
        print 'BTC > ETH > NEO > BTC'
        print '(1 / {}) / {} * {}'.format(responses[0].parsed['ask']['price'], responses[1].parsed['ask']['price'],
                                          responses[2].parsed['bid']['price'])

        # bidRoute_result = (1 / responses[0].parsed['ask']['price']) \
        #                   / responses[1].parsed['ask']['price'] \
        #                   * responses[2].parsed['bid']['price']

        bidRoute_result = self.bid_route(responses)

        # ask route BTC > NEO > ETH > BTC
        print 'ask route'
        print 'BTC > NEO > ETH > BTC'
        print '(1 * {}) / {} * {}'.format(responses[0].parsed['ask']['price'], responses[2].parsed['bid']['price'],
                                          responses[1].parsed['ask']['price'])

        # askRoute_result = (1 / responses[2].parsed['ask']['price']) \
        #                   / responses[1].parsed['bid']['price'] \
        #                   * responses[0].parsed['bid']['price']

        askRoute_result = self.ask_route(responses)

        # # Max amount for bid route & ask routes can be different and so less profit
        # if bidRoute_result > 1 or \
        #         (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (
        #                     askRoute_result - 1) * lastPrices[1]):
        #     status = 1  # bid route
        # elif askRoute_result > 1:
        #     status = 2  # ask route
        # else:
        #     status = 0  # do nothing

        status = self.pick_route(bidRoute_result, askRoute_result, lastPrices)

        if status > 0:
            maxAmounts = self.getMaxAmount(lastPrices, responses, status)
            fee = 0
            for index, amount in enumerate(maxAmounts):
                fee += amount * lastPrices[index]
            fee *= self.engine.feeRatio

            bidRoute_profit = (bidRoute_result - 1) * lastPrices[0] * maxAmounts[0]
            print 'bidroute profit : {}'.format(bidRoute_profit)
            askRoute_profit = (askRoute_result - 1) * lastPrices[1] * maxAmounts[1]
            print 'askroute profit : {}'.format(askRoute_profit)

            if status == 1 and bidRoute_profit - fee > self.minProfitUSDT:
                print strftime('%Y%m%d%H%M%S') + ' Bid Route: Result - {0} Profit - {1} Fee - {2}'.format(
                    bidRoute_result, bidRoute_profit, fee)
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
                orderInfo = [
                    {
                        "tickerPair": self.exchange['tickerPairC'],
                        "action": "bid",
                        "price": responses[2].parsed['ask']['price'],
                        "amount": maxAmounts[2]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairB'],
                        "action": "ask",
                        "price": responses[1].parsed['bid']['price'],
                        "amount": maxAmounts[1]
                    },
                    {
                        "tickerPair": self.exchange['tickerPairA'],
                        "action": "ask",
                        "price": responses[0].parsed['bid']['price'],
                        "amount": maxAmounts[0]
                    }
                ]
                return {'status': 2, 'orderInfo': orderInfo}
        print strftime('%Y%m%d%H%M%S') + ' no arbitrage possibilities ...'
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

            USDT = maxBalance * lastPrices[index] * (1 - self.engine.feeRatio)
            if not maxUSDT or USDT < maxUSDT:
                maxUSDT = USDT

        maxAmounts = []
        for index, tickerIndex in enumerate(['tickerA', 'tickerB', 'tickerC']):
            # May need to handle scientific notation
            maxAmounts.append(maxUSDT / lastPrices[index])

        return maxAmounts

    def place_order(self, orderInfo):
        print json.dumps(orderInfo, indent=4, sort_keys=True)
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


    @staticmethod
    def pick_route(bidRoute_result, askRoute_result, lastPrices):
        # Max amount for bid route & ask routes can be different and so less profit
        if bidRoute_result > 1 or \
                (bidRoute_result > 1 and askRoute_result > 1 and (bidRoute_result - 1) * lastPrices[0] > (
                            askRoute_result - 1) * lastPrices[1]):
            status = 1  # bid route
        elif askRoute_result > 1:
            status = 2  # ask route
        else:
            status = 0  # do nothing
        return status

    def run(self):
        self.start_engine()
