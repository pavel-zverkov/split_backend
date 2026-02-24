from sqlalchemy.orm import Session

from .distance_model import Distance
from .control_point_model import ControlPoint
from .distance_schema import DistanceCreate, DistanceUpdate, ControlPointInput


def create_distance(
    db: Session,
    competition_id: int,
    data: DistanceCreate
) -> Distance:
    distance = Distance(
        competition_id=competition_id,
        name=data.name,
        distance_meters=data.distance_meters,
        climb_meters=data.climb_meters,
        classes=data.classes,
    )
    db.add(distance)
    db.flush()

    if data.control_points:
        for i, cp in enumerate(data.control_points, start=1):
            control_point = ControlPoint(
                distance_id=distance.id,
                code=cp.code,
                sequence=i,
                type=cp.type,
            )
            db.add(control_point)

    db.commit()
    db.refresh(distance)
    return distance


def get_distance(db: Session, distance_id: int) -> Distance | None:
    return db.query(Distance).filter(Distance.id == distance_id).first()


def get_distances_by_competition(
    db: Session,
    competition_id: int
) -> list[Distance]:
    return db.query(Distance).filter(
        Distance.competition_id == competition_id
    ).order_by(Distance.id).all()


def update_distance(db: Session, distance: Distance, data: DistanceUpdate) -> Distance:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(distance, field, value)
    db.commit()
    db.refresh(distance)
    return distance


def delete_distance(db: Session, distance: Distance) -> None:
    db.delete(distance)
    db.commit()


def replace_control_points(
    db: Session,
    distance: Distance,
    control_points: list[ControlPointInput]
) -> list[ControlPoint]:
    # Delete existing CPs
    db.query(ControlPoint).filter(ControlPoint.distance_id == distance.id).delete()

    new_cps = []
    for i, cp in enumerate(control_points, start=1):
        control_point = ControlPoint(
            distance_id=distance.id,
            code=cp.code,
            sequence=i,
            type=cp.type,
        )
        db.add(control_point)
        new_cps.append(control_point)

    db.commit()
    for cp in new_cps:
        db.refresh(cp)
    return new_cps


def get_distance_by_class(
    db: Session,
    competition_id: int,
    class_name: str
) -> Distance | None:
    """Find the distance that contains the given class."""
    distances = get_distances_by_competition(db, competition_id)
    for distance in distances:
        if distance.classes and class_name in distance.classes:
            return distance
    return None


def get_all_classes_for_competition(db: Session, competition_id: int) -> list[str]:
    """Get all classes across all distances for a competition."""
    distances = get_distances_by_competition(db, competition_id)
    classes = []
    for distance in distances:
        if distance.classes:
            classes.extend(distance.classes)
    return classes


def get_distances_count(db: Session, competition_id: int) -> int:
    return db.query(Distance).filter(Distance.competition_id == competition_id).count()
