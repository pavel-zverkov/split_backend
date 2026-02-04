# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI backend for an orienteering competition analysis platform. Core features include split time comparison between athletes, workout tracking with GPS/FIT/TCX data, competition management, and artifact storage (maps, GPS files).

## Development Commands

All commands run from `/packages/backend/`:

```bash
# Start infrastructure (PostgreSQL + MinIO)
docker-compose -f ../../docker/docker-compose.yaml up -d

# Run dev server with hot reload
uvicorn src.app:app --reload --reload-include="*.html" --reload-include="*.css" --reload-include="*.js"

# Full restart (destroys PostgreSQL data)
make restart_dev_server

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Install dependencies
poetry install

# Run tests
pytest
pytest tests/test_module.py::test_function -v

# Linting/type checking
pylint src/
mypy src/
isort src/
```

## Architecture

### Module Structure

Each domain module follows this pattern:
```
domain/
  ├── domain_controller.py      # FastAPI router
  ├── domain_crud.py            # Database operations
  ├── domain_orm_model.py       # SQLAlchemy model
  ├── domain_pydantic_model.py  # Pydantic schemas
  └── domain_entity.py          # Business logic (optional)
```

### Core Modules (packages/backend/src/)

- **split_comparer/** - Core feature: compares runner split times on same course
- **user/** - User management
- **workout/** - Training sessions with split data
- **competition/** - Competition metadata
- **event/** - Event organization
- **artifact/** - File storage, O-Maps via MinIO
- **relations/** - User-Competition/Event many-to-many relationships
- **database/** - SQLAlchemy setup, MinIO integration

### Data Flow

```
FastAPI Router (controller)
    → CRUD functions (crud.py)
    → SQLAlchemy ORM (orm_model.py)
    → PostgreSQL/MinIO
```

### Infrastructure

- **PostgreSQL 15 + PostGIS** (port 5432) - Relational data with geospatial support
- **MinIO** (ports 9000/9001) - Object storage for maps and GPS files
- Both configured via `docker/docker-compose.yaml`

### Key Patterns

- Dependency injection: `db: Session = Depends(get_db)`
- Config singleton: `from src.config import Config`
- Logging: `from src.logger import logger`
- Artifacts stored as: `{event_name}/{date}/{competition_name}/{file_name}`

## Environment

Configuration in `/packages/backend/.env`:
- PostgreSQL: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- MinIO: `MINIO_HOST`, `MINIO_PORT`, `ACCESS_KEY`, `SECRET_KEY`
- `LOG_LEVEL` controls loguru output
