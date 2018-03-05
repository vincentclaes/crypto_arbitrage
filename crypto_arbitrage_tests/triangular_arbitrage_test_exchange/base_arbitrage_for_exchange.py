import json
import os
import unittest

import mock

import util
from crypto_arbitrage_tests import TEST_ROOT
from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class BaseArbitragePossibilitiesForExchange(unittest.TestCase):
    @classmethod
    def run_for_coin_on_exchange(cls, coin, exchange):
        config = util.read_config(os.path.join(TEST_ROOT, 'configs'), exchange)
        engine = CryptoEngineTriArbitrage(config, True)
        engine.hasOpenOrder = False
        with mock.patch.object(CryptoEngineTriArbitrage, 'check_balance') as m_balance:
            with mock.patch.object(CryptoEngineTriArbitrage, 'place_order') as m_place_order:
                m_balance.return_value = {coin: 1000, u'ETH': 1, u'BTC': 1}
                engine.run()

    @staticmethod
    def read_config(dir_path, file_name):
        config_file = os.path.join(dir_path, file_name)
        with open(config_file) as f:
            config = json.load(f)
        return config
