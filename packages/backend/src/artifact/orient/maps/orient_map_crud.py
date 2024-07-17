from datetime import date

from sqlalchemy.orm import Session

from .orient_map_orm_model import OrientMap as ORMomap
from .orient_map_pydantic_model import OrientMap, OrientMapCreate
from ....logger import logger

# def get_user(db: Session, mobile_number: str) -> None:
#     return db.query(User).filter(User.mobile_number == mobile_number).first()


def get_map(db: Session, omap_id: int) -> OrientMap | None:
    return db.query(ORMomap).filter(ORMomap.id == omap_id).first()

# TODO: need to fix
# def get_map_by_location(
#     db: Session,
#     location_point: LocationPoint
# ) -> ORMomap | None:
#     return db.query(ORMomap)\
#              .filter(
#                  ORMomap.location_point ==
#         f'POINT {location_point.latitude} {location_point.longitude}'
#     )\
#         .first()


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

# TODO: update_omap, delete_omap
