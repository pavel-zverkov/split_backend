from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement

from .workout_split_model import WorkoutSplit
from .workout_split_schema import SplitCreate, SplitUpdate


def get_workout_splits(db: Session, workout_id: int) -> list[WorkoutSplit]:
    """Get all splits for a workout, ordered by sequence."""
    return db.query(WorkoutSplit).filter(
        WorkoutSplit.workout_id == workout_id
    ).order_by(WorkoutSplit.sequence).all()


def get_split(db: Session, split_id: int) -> WorkoutSplit | None:
    """Get a single split by ID."""
    return db.query(WorkoutSplit).filter(WorkoutSplit.id == split_id).first()


def create_splits(
    db: Session,
    workout_id: int,
    splits_data: list[SplitCreate]
) -> list[WorkoutSplit]:
    """Create multiple splits for a workout (replaces existing)."""
    # Delete existing splits
    db.query(WorkoutSplit).filter(WorkoutSplit.workout_id == workout_id).delete()

    # Create new splits
    splits = []
    for split_data in splits_data:
        position = None
        if split_data.position:
            position = WKTElement(
                f'POINT({split_data.position.lng} {split_data.position.lat})',
                srid=4326
            )

        split = WorkoutSplit(
            workout_id=workout_id,
            sequence=split_data.sequence,
            control_point=split_data.control_point,
            distance_meters=split_data.distance_meters,
            cumulative_time=split_data.cumulative_time,
            split_time=split_data.split_time,
            position=position,
        )
        db.add(split)
        splits.append(split)

    db.commit()
    for split in splits:
        db.refresh(split)

    return splits


def update_split(db: Session, split: WorkoutSplit, data: SplitUpdate) -> WorkoutSplit:
    """Update a single split."""
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == 'position' and value is not None:
            position = WKTElement(
                f'POINT({value["lng"]} {value["lat"]})',
                srid=4326
            )
            setattr(split, 'position', position)
        elif value is not None:
            setattr(split, field, value)

    db.commit()
    db.refresh(split)
    return split


def delete_all_splits(db: Session, workout_id: int) -> int:
    """Delete all splits for a workout. Returns count of deleted splits."""
    count = db.query(WorkoutSplit).filter(
        WorkoutSplit.workout_id == workout_id
    ).delete()
    db.commit()
    return count
