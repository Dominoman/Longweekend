from flask import render_template
from sqlalchemy import text, func

from common.apininja import Ninja
from config import Config
from . import main
from .. import db
from ..models import Search


@main.route('/')
def index():
    return 'Sabai sabai'

@main.route('/longweekend')
def longweekend():
    logos = {}
    img_resources={}
    apininja=Ninja(Config.APININJASKEY)
    with open("sql/monthly_5_cheapest.sql") as f:
        sql = text(f.read())
    result=db.session.execute(sql).mappings().all()
    for row in result:
        l=apininja.get_airline_logos(row['firstairline'])
        logos[row['firstairline']]=l['logo_url']
        l=apininja.get_flag(row['countryFromCode'])
        img_resources[row['countryFromCode']]=l
        l=apininja.get_flag(row['countryToCode'])
        img_resources[row['countryToCode']] = l

    latest_ts = db.session.query(
        func.max(Search.timestamp)
    ).scalar()
    return render_template('index.html',itineraries=result,logos=logos, latest_ts=latest_ts,img_resources=img_resources)
