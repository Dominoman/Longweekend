import json
import os
from datetime import datetime, date
from typing import Optional

import click
from dateutil.relativedelta import relativedelta
from flask import current_app
from flask.cli import with_appcontext
from tqdm import tqdm

from app import db
from app.models import Search, Itinerary, Route
from common.kiwi import Tequila, KIWI_DATETIME_FORMAT

class RouteCache:
    def __init__(self)->None:
        self.route_cache={}

    def get_route(self,route_id:str)->Optional[Route]:
        if route_id in self.route_cache:
            return self.route_cache[route_id]
        route=Route.query.filter_by(route_id=route_id).first()
        if route is None:
            return None
        self.route_cache[route_id]=route
        return route

    def add_route(self,route:Route)->None:
        self.route_cache[route.route_id]=route


def save_json(json_data:dict, range_start:datetime, save_dir:str)->None:
    if not save_dir:
        return
    os.makedirs(save_dir,exist_ok=True)
    file_name = os.path.join(save_dir,f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{range_start.strftime('%Y%m')}.json")
    with open(file_name, "w", encoding="utf-8") as fo:
        json.dump(json_data, fo, indent=4, ensure_ascii=False)


def add_itinerary(itinerary:dict)->Itinerary:
    local_departure = datetime.strptime(itinerary["local_departure"], KIWI_DATETIME_FORMAT)
    local_arrival = datetime.strptime(itinerary["local_arrival"], KIWI_DATETIME_FORMAT)
    airlines = ','.join(itinerary["airlines"])
    return Itinerary(itinerary_id=itinerary["id"],
                              flyFrom=itinerary["flyFrom"],
                              flyTo=itinerary["flyTo"], cityFrom=itinerary["cityFrom"],
                              cityCodeFrom=itinerary["cityCodeFrom"], cityTo=itinerary["cityTo"],
                              cityCodeTo=itinerary["cityCodeTo"],
                              countryFromCode=itinerary["countryFrom"]["code"],
                              countryFromName=itinerary["countryFrom"]["name"],
                              countryToCode=itinerary["countryTo"]["code"],
                              countryToName=itinerary["countryTo"]["name"], local_departure=local_departure,
                              local_arrival=local_arrival, nightsInDest=itinerary["nightsInDest"],
                              quality=itinerary["quality"], distance=itinerary["distance"],
                              durationDeparture=itinerary["duration"]["departure"],
                              durationReturn=itinerary["duration"]["return"], price=itinerary["price"],
                              conversionEUR=itinerary["conversion"]["EUR"],
                              availabilitySeats=itinerary["availability"]["seats"], airlines=airlines,
                              booking_token=itinerary["booking_token"], deep_link=itinerary["deep_link"],
                              facilitated_booking_available=itinerary["facilitated_booking_available"],
                              pnr_count=itinerary["pnr_count"],
                              has_airport_change=itinerary["has_airport_change"],
                              technical_stops=itinerary["technical_stops"],
                              throw_away_ticketing=itinerary["throw_away_ticketing"],
                              hidden_city_ticketing=itinerary["hidden_city_ticketing"],
                              virtual_interlining=itinerary["virtual_interlining"])

route_cache = RouteCache()


def update_route(old_route: Route, diff: dict[str, tuple[str, str]])->None:
    for k, v in diff.items():
        if k not in ["local_departure", "local_arrival"]:
            old_route.__setattr__(k, v[1])

def add_route(parent_itinerary:Itinerary, route:dict)->bool:
    local_departure = datetime.strptime(route["local_departure"], KIWI_DATETIME_FORMAT)
    local_arrival = datetime.strptime(route["local_arrival"], KIWI_DATETIME_FORMAT)
    new_route = Route(route_id=route["id"], combination_id=route["combination_id"], flyFrom=route["flyFrom"],
                      flyTo=route["flyTo"], cityFrom=route["cityFrom"], cityCodeFrom=route["cityCodeFrom"],
                      cityTo=route["cityTo"], cityCodeTo=route["cityCodeTo"], local_departure=local_departure,
                      local_arrival=local_arrival, airline=route["airline"], flight_no=route["flight_no"],
                      operating_carrier=route["operating_carrier"],
                      operating_flight_no=route["operating_flight_no"],
                      fare_basis=route["fare_basis"], fare_category=route["fare_category"],
                      fare_classes=route["fare_classes"], _return=route["return"],
                      bags_recheck_required=route["bags_recheck_required"],
                      vi_connection=route["vi_connection"],
                      guarantee=route["guarantee"], equipment=route["equipment"],
                      vehicle_type=route["vehicle_type"])
    if route["return"] == 1:
        if parent_itinerary.rlocal_departure is None:
            parent_itinerary.rlocal_departure = local_departure
        parent_itinerary.rlocal_arrival = local_arrival
    old_route=route_cache.get_route(new_route.route_id)
    if old_route is None:
        parent_itinerary.routes.append(new_route)
        route_cache.add_route(new_route)
        return True
    diff = old_route.compare(new_route)
    if len(diff)>0:
        update_route(old_route, diff)
    parent_itinerary.routes.append(old_route)
    return False


def insert_json(json_data: dict, url: str = "", timestamp: datetime = None, range_start: date = None,
                    range_end: date = None,actual:bool=True)->bool:
    old_search=Search.query.filter_by(search_id=json_data["search_id"]).first()
    if old_search is not None:
        return False
    if timestamp is None:
        timestamp=datetime.now()
    new_search = Search(search_id=json_data["search_id"], url=url, timestamp=timestamp,
                            results=json_data["_results"], range_start=range_start, range_end=range_end, actual=actual)
    db.session.add(new_search)

    for itinerary in json_data['data']:
        new_itinerary=add_itinerary(itinerary)
        new_search.itineraries.append(new_itinerary)
        for route in itinerary['route']:
            add_route(new_itinerary, route)
    db.session.commit()
    return True


@click.command('scan',short_help='Scanning flights for next 12 months')
@with_appcontext
def scan():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    current_app.logger.info("Start")
    kiwi = Tequila(current_app.config["APIKEY"])
    range_start = datetime.now().date()
    for _ in range(13):
        range_end = range_start + relativedelta(months=1, day=1, days=-1)
        max_trying = 10
        while max_trying>0:
            max_trying -= 1
            current_app.logger.info("Search")
            try:
                result=kiwi.search("BUD",range_start,range_end,nights_in_dst_from=2,nights_in_dst_to=3,limit=1000)
            except Exception as ex:
                current_app.logger.exception("Kiwi Error:")
                current_app.logger.debug(f"Kiwi response: {kiwi.status_code}")
            else:
                save_json(result, range_start,current_app.config['SAVEDIR'])
                if kiwi.status_code==200:
                    insert_json(result, kiwi.search_url, datetime.now(),range_start=range_start, range_end=range_end)
                    break
        range_start=range_start+relativedelta(months=1,day=1)

@click.command('import_jsons',short_help='Reimport all json from tmo folder')
@with_appcontext
def import_jsons():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    current_app.logger.info("Start")
    all_jsons = [f for f in os.listdir(current_app.config['SAVEDIR']) if f.endswith(".json")]
    pbar = tqdm(all_jsons, desc="Processing json files", unit="file", ncols=100, mininterval=1.0)
    for file in pbar:
        with open(os.path.join(current_app.config['SAVEDIR'],file),'r') as fo:
            data = json.load(fo)
            timestamp = datetime.strptime(file[:14], "%Y%m%d%H%M%S")
            range_start = datetime.strptime(file[15:21] + "01", "%Y%m%d").date()
            range_end = range_start + relativedelta(months=1, days=-1)
            insert_json(data, timestamp=timestamp, range_start=range_start, range_end=range_end, actual=False)


def register(app):
    app.cli.add_command(scan)
    app.cli.add_command(import_jsons)
