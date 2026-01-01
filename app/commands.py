import json
import os
import time
from datetime import datetime, date
from logging import Logger
from typing import Optional

import click
from dateutil.relativedelta import relativedelta
from flask import current_app
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select, delete, exists
from tqdm import tqdm

from app import db
from app.models import Search, Itinerary, Route, t_itinerary2route
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


class DbUtils:
    def __init__(self,db_session:SQLAlchemy,logger:Logger)->None:
        self.db=db_session
        self.logger=logger

    def clear_active(self)->int:
        updated = Search.query.filter_by(actual=True).update({'actual':False})
        self.db.session.commit()
        self.logger.info(f"Cleared {updated} active searches")
        return updated

    def delete_search(self,search:Search)->tuple[int,int,int,int]:
        """
        Deletes the given search and all related itineraries and unused routes from the database.
        """
        itineraries = list(search.itineraries)
        itinerary_rowids = [it.rowid for it in itineraries]

        stmt = delete(t_itinerary2route).where(t_itinerary2route.c.itinerary_id.in_(itinerary_rowids))
        itinerary2route_result = self.db.session.execute(stmt)

        stmt = delete(Itinerary).where(Itinerary.rowid.in_(itinerary_rowids))
        itinerary_result = self.db.session.execute(stmt)

        stmt = delete(Route).where(
            ~exists(
                select(1).where(
                    t_itinerary2route.c.route_id == Route.rowid
                )
            )
        )
        route_result = self.db.session.execute(stmt)

        self.db.session.delete(search)
        self.db.session.commit()
        return 1, itinerary_result.rowcount(), route_result.rowcount(), itinerary2route_result.rowcount()


    def delete_notactual_searches(self):
        searches=Search.query.filter_by(actual=0).all()
        for search in searches:
            self.delete_search(search)

class SearchImporter:
    def __init__(self):
        self.route_cache = RouteCache()

    @staticmethod
    def save_json(json_data:dict, range_start:datetime, save_dir:str)->None:
        if not save_dir:
            return
        os.makedirs(save_dir,exist_ok=True)
        file_name = os.path.join(save_dir,f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{range_start.strftime('%Y%m')}.json")
        with open(file_name, "w", encoding="utf-8") as fo:
            json.dump(json_data, fo, indent=4, ensure_ascii=False)

    @staticmethod
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


    def add_route(self,parent_itinerary:Itinerary, route:dict)->bool:
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
        old_route=self.route_cache.get_route(new_route.route_id)
        if old_route is None:
            parent_itinerary.routes.append(new_route)
            self.route_cache.add_route(new_route)
            return True
        diff = old_route.compare(new_route)
        if len(diff)>0:
            self.update_route(old_route, diff)
        parent_itinerary.routes.append(old_route)
        return False

    @staticmethod
    def update_route(old_route: Route, diff: dict[str, tuple[str, str]])->None:
        for k, v in diff.items():
            if k not in ["local_departure", "local_arrival"]:
                old_route.__setattr__(k, v[1])


    def insert_json(self,json_data: dict, url: str = "", timestamp: datetime = None, range_start: date = None,
                        range_end: date = None,actual:bool=True)->bool:
        if json_data['_results'] == 0:
            return False
        old_search=Search.query.filter_by(search_id=json_data["search_id"]).first()
        if old_search is not None:
            return False
        if timestamp is None:
            timestamp=datetime.now()
        new_search = Search(search_id=json_data["search_id"], url=url, timestamp=timestamp,
                                results=json_data["_results"], range_start=range_start, range_end=range_end, actual=actual)
        db.session.add(new_search)

        for itinerary in json_data['data']:
            new_itinerary=self.add_itinerary(itinerary)
            new_search.itineraries.append(new_itinerary)
            for route in itinerary['route']:
                self.add_route(new_itinerary, route)
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
    db_utils=DbUtils(db,current_app.logger)
    db_utils.clear_active()
    importer=SearchImporter()
    for _ in range(13):
        range_end = range_start + relativedelta(months=1, day=1, days=-1)
        max_trying = 10
        attempt = 0
        while max_trying>0:
            max_trying -= 1
            attempt += 1
            current_app.logger.info("Search attempt %d for %s", attempt, range_start)
            try:
                result=kiwi.search("BUD",range_start,range_end,nights_in_dst_from=2,nights_in_dst_to=3,limit=1000)
            except Exception as ex:
                current_app.logger.exception("Kiwi Error:")
                current_app.logger.debug("Kiwi response status: %s", getattr(kiwi, "status_code", None))
                time.sleep(min(5 * attempt, 30))
            else:
                importer.save_json(result, range_start,current_app.config['SAVEDIR'])
                if kiwi.status_code==200:
                    importer.insert_json(result, kiwi.search_url, datetime.now(),range_start=range_start, range_end=range_end)
                    break
        range_start=range_start+relativedelta(months=1,day=1)
    # db_utils.delete_notactual_searches()

@click.command('import_jsons',short_help='Reimport all json from tmo folder')
@with_appcontext
def import_jsons():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    current_app.logger.info("Start")
    all_jsons = [f for f in os.listdir(current_app.config['SAVEDIR']) if f.endswith(".json")]
    pbar = tqdm(all_jsons, desc="Processing json files", unit="file", ncols=100, mininterval=1.0)
    importer=SearchImporter()
    for file in pbar:
        with open(os.path.join(current_app.config['SAVEDIR'],file),'r') as fo:
            data = json.load(fo)
            timestamp = datetime.strptime(file[:14], "%Y%m%d%H%M%S")
            range_start = datetime.strptime(file[15:21] + "01", "%Y%m%d").date()
            range_end = range_start + relativedelta(months=1, days=-1)
            importer.insert_json(data, timestamp=timestamp, range_start=range_start, range_end=range_end, actual=False)

@click.command('cleanup', short_help='Delete all not actual searches and related records')
@with_appcontext
def cleanup():
    db_utils=DbUtils(db,current_app.logger)
    searches = Search.query.filter_by(actual=0).all()
    pbar = tqdm(searches,desc="Delete unused searches", unit="search")
    for search in pbar:
        db_utils.delete_search(search)

    db_utils.delete_notactual_searches()

def register(app):
    app.cli.add_command(scan)
    app.cli.add_command(import_jsons)
    app.cli.add_command(cleanup)
