#!/usr/bin/env -S uv run
import datetime
import json
import logging
import os

import requests

from common.kiwi import Tequila
from config import config
from dateutil.relativedelta import relativedelta

def savefile(json_data: dict, range_start: datetime.date)->None:
    if not os.path.exists(config.SAVEDIR):
        os.makedirs(config.SAVEDIR)
    fname = f"{config.SAVEDIR}/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{range_start.strftime('%Y%m')}.json"
    with open(fname, "w") as fo:
        json.dump(json_data,fo,indent=4)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    logging.basicConfig(filename="app.log", level=logging.DEBUG, format="{asctime} - {levelname} - {message}",
                        style="{", datefmt="%Y-%m-%d %H:%M")
    logging.info("Start")
    kiwi = Tequila(config.APIKEY)
    range_start = datetime.datetime.now().date()
    for _ in range(13):
        range_end = range_start + relativedelta(months=1, day=1, days=-1)
        max_trying = 10
        while max_trying > 0:
            max_trying -= 1
            logging.info("Search")
            try:
                result = kiwi.search("BUD", range_start, range_end,  nights_in_dst_from=1, nights_in_dst_to=3, max_fly_duration=17,
                                     max_stopovers=1,
                                     limit=1000, hidden_city_ticketing="true")
            except requests.RequestException:
                logging.exception("Kiwi Error:")
                logging.debug(f"Kiwi response: {kiwi.status_code}")
            else:
                savefile(result, range_start)

