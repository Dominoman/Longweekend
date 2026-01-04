from os import getcwd

from flask import render_template
from sqlalchemy import text

from . import main
from .. import db


@main.route('/')
def index():
    return 'Sabai sabai'

@main.route('/flights')
def test():
    with open("sql/monthly_5_cheapest.sql") as f:
        sql = text(f.read())
    result=db.session.execute(sql)
    return render_template('index.html',itineraries=result)