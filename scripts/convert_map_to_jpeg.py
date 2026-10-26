"""One-time script: convert PDF map artifact for competition 14 to JPEG."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from io import BytesIO
import fitz
from app.database import SessionLocal
from app.database.minio_integration import get_minio_client
from app.artifact.artifact_model import Artifact
from app.enums.artifact_kind import ArtifactKind

BUCKET_NAME = 'event-artifacts'
COMPETITION_ID = 14


def convert():
    db = SessionLocal()
    minio = get_minio_client()

    artifact = db.query(Artifact).filter(
        Artifact.competition_id == COMPETITION_ID,
        Artifact.kind == ArtifactKind.MAP,
    ).first()

    if not artifact:
        print(f'No MAP artifact found for competition {COMPETITION_ID}')
        return

    print(f'Found artifact id={artifact.id}  file={artifact.file_name}  mime={artifact.mime_type}')

    if not artifact.mime_type == 'application/pdf':
        print('Already not a PDF — nothing to do.')
        return

    # Download from MinIO
    response = minio.get_object(BUCKET_NAME, artifact.file_path)
    pdf_content = response.read()
    response.close()
    print(f'Downloaded {len(pdf_content)} bytes')

    # Convert page 1 to JPEG at 300 DPI
    doc = fitz.open(stream=pdf_content, filetype='pdf')
    page = doc[0]
    mat = fitz.Matrix(300 / 72, 300 / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    jpeg_content = pix.tobytes('jpeg', jpg_quality=88)
    print(f'Converted to JPEG: {len(jpeg_content)} bytes')

    # Build new path/name
    old_path = artifact.file_path
    new_file_name = artifact.file_name.rsplit('.', 1)[0] + '.jpg'
    new_file_path = artifact.file_path.rsplit('.', 1)[0] + '.jpg'

    # Upload JPEG
    minio.put_object(BUCKET_NAME, new_file_path, BytesIO(jpeg_content), len(jpeg_content))
    print(f'Uploaded to {new_file_path}')

    # Delete old PDF
    minio.remove_object(BUCKET_NAME, old_path)
    print(f'Deleted old PDF {old_path}')

    # Update DB record
    artifact.file_path = new_file_path
    artifact.file_name = new_file_name
    artifact.file_size = len(jpeg_content)
    artifact.mime_type = 'image/jpeg'
    db.commit()
    print(f'DB updated: artifact id={artifact.id} → {new_file_name}')


if __name__ == '__main__':
    convert()
