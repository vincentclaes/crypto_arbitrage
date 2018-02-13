import unittest

from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class TestGetMaxAmountOfCoinsForArbitrageAskRouteTest(unittest.TestCase):
    """
    maxUSDT = 80.8387861146

    ask route -> bid, bid, ask

    ETH-BTC  (bid)
    --------

    amount of eth times the price expressed in btc/eth = amount of btc
    P(btc/eth) * Q(eth) = Q(btc)

    <=>

    we multiply both sides with the price of usd/btc
    P(btc/eth) * Q(eth) * P(usd/btc) = Q(btc) * P(usd/btc)

    <=>

    Q(btc) * P(usd/btc) is equal to the amount of usd
    P(btc/eth) * Q(eth) * P(usd/btc) = Q(usd)

    <=>

    we know the prices and the maximum amount of usdt we can spend (Q(usd) = maxUSDT)

    Q(eth) = Q(usd) / (P(btc/eth) * P(usd/btc))


    Q(eth) = 80.8387861146 / (0.10048 * 8571) = 0.09386607580150107

    NEO-ETH (bid)
    -------

    Q(neo) = Q(usd)/(P(eth/neo) * P(usd/eth))

    Q(neo) = 80.8387861146 / (0.13131 * 861.68) = 0.714456792064095


    NEO-BTC (ask)
    -------

    Q(neo) = Q(usd)/(P(btc/neo) * P(usd/btc))

    Q(neo) = 80.8387861146 / (0.013194 * 8571) = 0.7148448761963639


    """

    @classmethod
    def setUpClass(cls):
        config = {
            "exchange": "bitfinex",
            "keyFile": "../keys/bitfinex.key_sample",
            "tickerPairA": "ETH-BTC",
            "tickerPairB": "NEO-ETH",
            "tickerPairC": "NEO-BTC",
            "tickerA": "BTC",
            "tickerB": "ETH",
            "tickerC": "NEO",
            "minimum_amount": {"ETH-BTC": 0.02, "NEO-ETH": 0.2, "NEO-BTC": 0.2},

        }
        orderbooks = [

            # bid --> max USD / (Pbtcusd * P
            {'ask': {'price': 0.10053, 'amount': 0.24}, 'bid': {'price': 0.10048, 'amount': 2.82743343},
             'ticker_pair': u'ETH-BTC'},
            {'ask': {'price': 0.13154, 'amount': 45.52996456}, 'bid': {'price': 0.13131, 'amount': 2.72},
             'ticker_pair': u'NEO-ETH'},
            {'ask': {'price': 0.013194, 'amount': 1.44583981}, 'bid': {'price': 0.013172, 'amount': 1.258},
             'ticker_pair': u'NEO-BTC'}
        ]
        order_book_list = []
        for i, obj_ in enumerate(orderbooks):
            class orderbook_object: pass

            setattr(orderbook_object, 'parsed', obj_)
            order_book_list.append(orderbook_object)

        current_balance = {u'NEO': 0.71682113, u'ETH': 0.20341264, u'BTC': 0.04819959}
        last_prices = {u'NEO': 113.0, u'ETH': 861.68, u'BTC': 8571.0}
        engine = CryptoEngineTriArbitrage(config, True)
        engine.engine.last_prices = last_prices
        engine.engine.balance = current_balance
        engine.engine.exchange = config
        cls.max_amounts_result = engine.calculate_max_amount(last_prices, order_book_list, 2)

    def test_verify_max_amounts(self):
        self.assertListEqual(self.max_amounts_result,
                             [0.0938660758015243, 0.7144567920642717, 0.7148448761965409])


class TestGetMaxAmountOfCoinsForArbitrageBidRouteTest(unittest.TestCase):
    """
    bid route --> ask / ask / bid

    maxusdt = 269.070686753

    ETH-BTC (ask)
    -------
    Q(eth) = Q(usd) / (P(btc/eth) * P(usd/btc))


    Q(eth) = 269.070686753 / (0.10575 * 9333.2) = 0.27261857211232704


    NEO-ETH (ask)
    -------
    Q(neo) = Q(usd)/(P(eth/neo) * P(usd/eth))

    Q(neo) = 269.070686753 / (0.13072 * 986.66) = 2.0862042513795602


    NEO-BTC (bid)
    -------
    Q(neo) = Q(usd)/(P(btc/neo) * P(usd/btc))

    Q(neo) = 269.070686753 / (0.013824 * 9333.2) = 2.085461082239481



    """

    @classmethod
    def setUpClass(cls):
        config = {
            "exchange": "bitfinex",
            "keyFile": "../keys/bitfinex.key_sample",
            "tickerPairA": "ETH-BTC",
            "tickerPairB": "NEO-ETH",
            "tickerPairC": "NEO-BTC",
            "tickerA": "BTC",
            "tickerB": "ETH",
            "tickerC": "NEO",
            "minimum_amount": {"ETH-BTC": 0.02, "NEO-ETH": 0.2, "NEO-BTC": 0.2},

        }

        orderbooks = [
            {'ask': {'price': 0.10575, 'amount': 3.5}, 'bid': {'price': 0.10566, 'amount': 6.6259513}},
            {'ask': {'price': 0.13072, 'amount': 0.27325513}, 'bid': {'price': 0.1303, 'amount': 1.6159}},
            {'ask': {'price': 0.013831, 'amount': 35.98939827}, 'bid': {'price': 0.013824, 'amount': 40.29722331}}
        ]
        order_book_list = []
        for i, obj_ in enumerate(orderbooks):
            class orderbook_object: pass

            setattr(orderbook_object, 'parsed', obj_)
            order_book_list.append(orderbook_object)

        current_balance = {u'NEO': 2.20618882, u'ETH': 0.27563599, u'BTC': 0.05124354}
        last_prices = {'BTC': 9333.2, 'ETH': 986.66, 'NEO': 129.3}
        engine = CryptoEngineTriArbitrage(config, True)
        engine.engine.last_prices = last_prices
        engine.engine.balance = current_balance
        engine.engine.exchange = config
        cls.max_amounts_result = engine.calculate_max_amount(last_prices, order_book_list, 1)

    def test_verify_max_amounts(self):
        self.assertListEqual(self.max_amounts_result,[0.2726185721119911, 2.0862042513769894, 2.085461082236911])
