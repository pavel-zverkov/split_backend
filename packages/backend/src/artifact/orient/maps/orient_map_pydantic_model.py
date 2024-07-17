from datetime import datetime

from pydantic import BaseModel
from geoalchemy2.types import WKBElement
from typing_extensions import Annotated

DEFAULT_LOCATION_NAME = 'Без_локации'


class LocationPoint:
    latitude: float
    longitude: float


class OrientMapCreate(BaseModel):
    artifact: int | None = None
    map_name: str | None = None
    location_name: str = DEFAULT_LOCATION_NAME
    location_point: Annotated[str, WKBElement] | None = None


class OrientMap(OrientMapCreate):
    id: int
