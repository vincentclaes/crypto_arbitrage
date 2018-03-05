import json
import os
import unittest
import mock

from engines.triangular_arbitrage import CryptoEngineTriArbitrage

TEST_ROOT = os.path.dirname(os.path.realpath(__file__))


class BaseArbitragePossibilitiesForExchange(unittest.TestCase):
    @classmethod
    def run_for_coin_on_exchange(cls, coin, exchange):
        configs = BaseArbitragePossibilitiesForExchange.read_config(os.path.join(TEST_ROOT, 'configs'), exchange)
        config_for_coin = configs.get(coin)
        engine = CryptoEngineTriArbitrage(config_for_coin, True)
        engine.hasOpenOrder = False
        with mock.patch.object(CryptoEngineTriArbitrage, 'check_balance') as m_balance:
            with mock.patch.object(CryptoEngineTriArbitrage, 'place_order') as m_place_order:
                m_balance.return_value = {coin: 1000, u'ETH': 1, u'BTC': 1}
                engine.run()

    @staticmethod
    def read_config(dir_path, file_name):
        config_file = os.path.join(dir_path, file_name + ".json")
        with open(config_file) as f:
            config = json.load(f)
        return config


class ArbitragePossibilitiesForBitfinexTest(BaseArbitragePossibilitiesForExchange):
    @classmethod
    def setUpClass(cls):

        cls.exception = None

        try:
            BaseArbitragePossibilitiesForExchange.run_for_coin_on_exchange("AVT", "bitfinex")
        except Exception as e:
            cls.exception = e

    def test_did_not_throw_exception(self):
        self.assertIsNone(self.exception)


class ArbitragePossibilitiesForBittrexTest(BaseArbitragePossibilitiesForExchange):
    @classmethod
    def setUpClass(cls):

        cls.exception = None

        try:
            BaseArbitragePossibilitiesForExchange.run_for_coin_on_exchange("AVT", "bittrex")
        except Exception as e:
            cls.exception = e

    def test_did_not_throw_exception(self):
        self.assertIsNone(self.exception)
