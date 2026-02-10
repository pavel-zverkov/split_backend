from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2 import WKTElement

from .orient_map_model import OrientMap as ORMomap
from .orient_map_schema import OrientMap, OrientMapCreate, OrientMapUpdate
from ....logger import logger


def get_map(db: Session, omap_id: int) -> ORMomap | None:
    return db.query(ORMomap).filter(ORMomap.id == omap_id).first()


def get_map_by_location(
    db: Session,
    latitude: float,
    longitude: float,
    radius_meters: float = 1000
) -> list[ORMomap]:
    """Find maps near a given location within radius (meters)."""
    point = WKTElement(f'POINT({longitude} {latitude})', srid=4326)
    return db.query(ORMomap).filter(
        func.ST_DWithin(
            func.ST_Transform(ORMomap.location_point, 3857),
            func.ST_Transform(point, 3857),
            radius_meters
        )
    ).all()


def get_maps_by_name(db: Session, name: str) -> list[ORMomap]:
    """Search maps by name."""
    search_pattern = f'%{name}%'
    return db.query(ORMomap).filter(
        ORMomap.map_name.ilike(search_pattern)
    ).all()


def create_omap(
    db: Session,
    omap: OrientMapCreate
) -> ORMomap:
    db_omap = ORMomap(**omap.model_dump())
    db.add(db_omap)
    db.commit()
    db.refresh(db_omap)

    logger.success(f'Create o_map {omap.model_dump()}')
    return db_omap


def update_omap(
    db: Session,
    omap: ORMomap,
    update_data: OrientMapUpdate
) -> ORMomap:
    """Update an orient map."""
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(omap, field, value)
    db.commit()
    db.refresh(omap)
    logger.info(f'Updated o_map {omap.id}')
    return omap


def delete_omap(db: Session, omap: ORMomap) -> None:
    """Delete an orient map."""
    db.delete(omap)
    db.commit()
    logger.info(f'Deleted o_map {omap.id}')
