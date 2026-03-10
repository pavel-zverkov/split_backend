from sqlalchemy.orm import Session

from .total_config_model import EventTotalConfig
from .total_result_model import EventTotalResult


def create_config(
    db: Session,
    event_id: int,
    name: str,
    rules: dict,
    auto_calculate: bool = True,
) -> EventTotalConfig:
    config = EventTotalConfig(
        event_id=event_id,
        name=name,
        rules=rules,
        auto_calculate=auto_calculate,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def get_config(db: Session, config_id: int) -> EventTotalConfig | None:
    return db.query(EventTotalConfig).filter(EventTotalConfig.id == config_id).first()


def get_configs_by_event(db: Session, event_id: int) -> list[EventTotalConfig]:
    return db.query(EventTotalConfig).filter(
        EventTotalConfig.event_id == event_id
    ).order_by(EventTotalConfig.id).all()


def update_config(
    db: Session,
    config: EventTotalConfig,
    name: str | None = None,
    rules: dict | None = None,
    auto_calculate: bool | None = None,
) -> EventTotalConfig:
    if name is not None:
        config.name = name
    if rules is not None:
        config.rules = rules
    if auto_calculate is not None:
        config.auto_calculate = auto_calculate
    db.commit()
    db.refresh(config)
    return config


def delete_config(db: Session, config: EventTotalConfig) -> None:
    db.delete(config)
    db.commit()


def get_results_count(db: Session, config_id: int) -> int:
    return db.query(EventTotalResult).filter(
        EventTotalResult.config_id == config_id
    ).count()


def get_total_results(
    db: Session,
    config_id: int,
    class_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[EventTotalResult], int]:
    q = db.query(EventTotalResult).filter(EventTotalResult.config_id == config_id)

    if class_filter:
        q = q.filter(EventTotalResult.class_ == class_filter)

    total = q.count()
    results = q.order_by(
        EventTotalResult.position.asc().nullslast()
    ).offset(offset).limit(limit).all()

    return results, total


def get_total_result(db: Session, result_id: int) -> EventTotalResult | None:
    return db.query(EventTotalResult).filter(EventTotalResult.id == result_id).first()


def get_my_total_result(
    db: Session,
    config_id: int,
    user_id: int,
) -> EventTotalResult | None:
    return db.query(EventTotalResult).filter(
        EventTotalResult.config_id == config_id,
        EventTotalResult.user_id == user_id,
    ).first()
