import unittest
import os
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from vnpy.trader.setting import SETTINGS
from alerts.alerts_runner import AlertBase
from alerts.turnover_alert import TurnoverAlert


class TestAlertsRunner(unittest.TestCase):
    def setUp(self):
        SETTINGS["datafeed.username"] = "c:/zd_zyb"
        SETTINGS["datafeed.name"] = "tdx"
    def test_run(self):
        alert = TurnoverAlert()
        alert.load_config(".vntrader/turnover_alert.json")
        alert.configure_logging(enabled=True, level=logging.WARNING)

        alert.pre_run()

        alert.run()

if __name__ == "__main__":
    unittest.main()