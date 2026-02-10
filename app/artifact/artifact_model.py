from sqlalchemy import (ARRAY,
                        Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        CheckConstraint,
                        func)

from ..database import Base
from ..enums.artifact_kind import ArtifactKind


class Artifact(Base):
    __tablename__ = 'artifacts'

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey('competitions.id'), nullable=True)
    workout_id = Column(Integer, ForeignKey('workouts.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    kind = Column(Enum(ArtifactKind), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    tags = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            '(competition_id IS NOT NULL AND workout_id IS NULL) OR '
            '(competition_id IS NULL AND workout_id IS NOT NULL)',
            name='artifact_owner_check'
        ),
    )
