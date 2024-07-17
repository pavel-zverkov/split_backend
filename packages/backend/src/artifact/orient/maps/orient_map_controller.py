from sqlalchemy.orm import Session

from ..maps import orient_map_crud
from ..maps.orient_map_pydantic_model import OrientMap, OrientMapCreate


async def read_omap(omap_id: int, db: Session):
    omap = orient_map_crud.get_map(db=db, omap_id=omap_id)
    return omap


async def create_omap(db: Session, omap: OrientMapCreate) -> OrientMap:
    return orient_map_crud.create_omap(db=db, omap=omap)
