import unittest

import mock

from bitfinex_configurations import configs
from engines.triangular_arbitrage import CryptoEngineTriArbitrage


class ArbitragePossibilitiesForCoinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):

        cls.exception = None
        coin = "FUN"
        config = configs.get(coin)
        try:
            engine = CryptoEngineTriArbitrage(config, True)
            engine.hasOpenOrder = False
            with mock.patch.object(CryptoEngineTriArbitrage, 'check_balance') as m_balance:
                with mock.patch.object(CryptoEngineTriArbitrage, 'place_order') as m_place_order:
                    m_balance.return_value = {coin: 1000, u'ETH': 1, u'BTC': 1}
                    engine.run()
        except Exception as e:
            cls.exception = e

    def test_did_not_throw_exception(self):
        self.assertIsNone(self.exception)
