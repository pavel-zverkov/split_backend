from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint)
from geoalchemy2 import Geometry

from ....database import Base


class OrientMap(Base):
    __tablename__ = 'o_maps'

    id = Column(Integer, primary_key=True, index=True)
    artifact = Column(Integer, ForeignKey('artifact.id'))
    map_name = Column(String)
    location_name = Column(String)
    location_point = Column(Geometry('POINT'))

    __table_args__ = (
        UniqueConstraint(
            'map_name',
            'location_name',
            name='o_maps_unique_constraint'
        ),
    )
