from sqlalchemy import Index

from . import db


class Itinerary(db.Model):
    __tablename__ = 'itinerary'
    __table_args__ = (
        db.UniqueConstraint('search_id', 'itinerary_id'),
        db.Index('ix_itinerary_search_itinerary_id', 'search_id', 'itinerary_id')
    )

    rowid = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.Integer,db.ForeignKey('search.rowid'), nullable=False)
    itinerary_id = db.Column(db.String(255), nullable=False, index=True)
    flyFrom = db.Column(db.String(3), nullable=False)
    flyTo = db.Column(db.String(3), nullable=False)
    cityFrom = db.Column(db.String(50), nullable=False)
    cityCodeFrom = db.Column(db.String(3), nullable=False)
    cityTo = db.Column(db.String(50), nullable=False)
    cityCodeTo = db.Column(db.String(3), nullable=False)
    countryFromCode = db.Column(db.String(2), nullable=False)
    countryFromName = db.Column(db.String(50), nullable=False)
    countryToCode = db.Column(db.String(2), nullable=False)
    countryToName = db.Column(db.String(50), nullable=False)
    local_departure = db.Column(db.DateTime, nullable=False)
    local_arrival = db.Column(db.DateTime, nullable=False)
    nightsInDest = db.Column(db.Integer, nullable=False)
    quality = db.Column(db.Float, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    durationDeparture = db.Column(db.Integer, nullable=False)
    durationReturn = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False, index=True)
    conversionEUR = db.Column(db.Float, nullable=False)
    availabilitySeats = db.Column(db.Integer)
    airlines = db.Column(db.String(30), nullable=False)
    booking_token = db.Column(db.String(2048), nullable=False)
    deep_link = db.Column(db.String(2048), nullable=False)
    facilitated_booking_available = db.Column(db.Boolean, nullable=False)
    pnr_count = db.Column(db.Integer, nullable=False)
    has_airport_change = db.Column(db.Boolean, nullable=False)
    technical_stops = db.Column(db.Integer, nullable=False)
    throw_away_ticketing = db.Column(db.Boolean, nullable=False)
    hidden_city_ticketing = db.Column(db.Boolean, nullable=False)
    virtual_interlining = db.Column(db.Boolean, nullable=False)
    rlocal_departure = db.Column(db.DateTime)
    rlocal_arrival = db.Column(db.DateTime)

    search = db.relationship('Search', back_populates='itineraries')
    routes = db.relationship('Route', secondary='itinerary2route', back_populates='itineraries')



t_itinerary2route = db.Table(
    'itinerary2route',
    db.Column('itinerary_id', db.ForeignKey('itinerary.rowid'), primary_key=True, nullable=False),
    db.Column('route_id', db.ForeignKey('route.rowid'), primary_key=True, nullable=False),
    Index('route_idx', 'route_id')
)



class Route(db.Model):
    __tablename__ = 'route'

    rowid = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.String(26), nullable=False, unique=True)
    combination_id = db.Column(db.String(24), nullable=False)
    flyFrom = db.Column(db.String(3), nullable=False)
    flyTo = db.Column(db.String(3), nullable=False)
    cityFrom = db.Column(db.String(50), nullable=False)
    cityCodeFrom = db.Column(db.String(3), nullable=False)
    cityTo = db.Column(db.String(50), nullable=False)
    cityCodeTo = db.Column(db.String(3), nullable=False)
    local_departure = db.Column(db.DateTime, nullable=False)
    local_arrival = db.Column(db.DateTime, nullable=False)
    airline = db.Column(db.String(2), nullable=False)
    flight_no = db.Column(db.Integer, nullable=False)
    operating_carrier = db.Column(db.String(2), nullable=False)
    operating_flight_no = db.Column(db.String(4), nullable=False)
    fare_basis = db.Column(db.String(10), nullable=False)
    fare_category = db.Column(db.String(1), nullable=False)
    fare_classes = db.Column(db.String(1), nullable=False)
    _return = db.Column(db.Integer, nullable=False)
    bags_recheck_required = db.Column(db.Boolean, nullable=False)
    vi_connection = db.Column(db.Boolean, nullable=False)
    guarantee = db.Column(db.Boolean, nullable=False)
    equipment = db.Column(db.String(4))
    vehicle_type = db.Column(db.String(8), nullable=False)

    itineraries = db.relationship('Itinerary', secondary='itinerary2route', back_populates='routes')

    def compare(self, new_route: 'Route') -> dict[str, tuple[str, str]]:
        """ Compares the attributes of the current instance with those of a new instance."""
        return {
            item: (
                str(self.__getattribute__(item)),
                str(new_route.__getattribute__(item)),
            )
            for item in self.__dict__
            if item not in ("_sa_instance_state", "rowid", "itineraries")
               and self.__getattribute__(item) != new_route.__getattribute__(item)
        }


class Search(db.Model):
    __tablename__ = 'search'

    rowid = db.Column(db.Integer, primary_key=True)
    search_id = db.Column(db.String(36), nullable=False, unique=True)
    url = db.Column(db.String(2048), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    range_start = db.Column(db.Date, nullable=False)
    range_end = db.Column(db.Date, nullable=False)
    results = db.Column(db.Integer, nullable=False)
    actual = db.Column(db.Boolean, nullable=False, index=True)

    itineraries = db.relationship('Itinerary', back_populates='search')
