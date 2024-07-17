from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        Text,
                        UniqueConstraint)

from ..database import Base
from ..enums.enum_artifact_kind import ArtifactKind


class Artifact(Base):
    __tablename__ = 'artifact'

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(Enum(ArtifactKind), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    tags = Column(Text)
    competition = Column(
        Integer,
        ForeignKey('competitions.id'),
        nullable=True
    )
    uploader = Column(Integer, ForeignKey('users.id'), nullable=True)
    upload_ts = Column(DateTime)

    __table_args__ = (
        UniqueConstraint(
            'file_name',
            'competition',
            name='artifact_unique_constraint'
        ),
    )
