from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from ....database import Base


class OrientMap(Base):
    __tablename__ = 'orient_maps'

    id = Column(Integer, primary_key=True, index=True)
    artifact_id = Column(Integer, ForeignKey('artifacts.id'), nullable=False)
    map_name = Column(String, nullable=False)
    location_name = Column(String, nullable=True)
    location_point = Column(Geometry('POINT'), nullable=True)
    scale = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'map_name',
            'location_name',
            name='orient_maps_unique_constraint'
        ),
    )

    # Relationships
    artifact = relationship('Artifact')
