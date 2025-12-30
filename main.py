import os
import json
from pathlib import Path
from vnpy.trader.setting import SETTINGS
from alerts.alerts_runner import AlertsRunner
prj_path = Path(__file__).parent

if __name__ == "__main__":
    # with open(str(prj_path.absolute()) + "/.vntrader/vt_setting.json", 'r', encoding='utf-8') as f:
    #     SETTINGS = json.load(f)
    SETTINGS["datafeed.username"] = "c:/zd_zyb"
    SETTINGS["datafeed.name"] = "tdx"
    print(SETTINGS)
    AlertsRunner.set_conf_path(str(prj_path.absolute()) + "/.vntrader")
    AlertsRunner.run_alerts(str(prj_path.absolute()) + "/alerts")