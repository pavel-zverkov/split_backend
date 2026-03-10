# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI backend for an orienteering competition analysis platform. Core features include split time comparison between athletes, workout tracking with GPS/FIT/TCX data, competition management, and artifact storage (maps, GPS files).

## Development Commands

All commands run from project root `/`:

```bash
# Start infrastructure (PostgreSQL)
docker-compose up -d

# Run dev server with hot reload
uvicorn app.main:app --reload

# Full restart (destroys PostgreSQL data)
make restart_dev_server

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Install dependencies
poetry install

# Run tests
pytest tests/ -v
pytest tests/test_module.py::test_function -v

# Linting/type checking
pylint app/
mypy app/
isort app/
```

## Project Structure

```
split_backend/
├── app/                      # Application code
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration
│   ├── logger.py            # Logging setup
│   ├── database/            # SQLAlchemy setup, MinIO integration
│   ├── auth/                # Authentication
│   ├── user/                # User management
│   ├── workout/             # Training sessions with splits
│   ├── competition/         # Competition metadata
│   ├── event/               # Event organization
│   ├── result/              # Competition results
│   ├── artifact/            # File storage, O-Maps
│   ├── club/                # Club management
│   ├── split_comparer/      # Core feature: split time comparison
│   └── enums/               # Enumeration types
├── tests/                   # Test files
├── migrations/              # Alembic migrations
├── init-scripts/            # PostgreSQL init scripts
├── docker-compose.yaml      # Docker configuration
├── Dockerfile               # Container build
├── pyproject.toml           # Poetry dependencies
├── alembic.ini              # Alembic configuration
├── makefile                 # Development shortcuts
└── .env                     # Environment variables
```

## Architecture

### Module Structure

Each domain module follows this pattern:
```
domain/
  ├── domain_controller.py    # FastAPI router
  ├── domain_crud.py          # Database operations
  ├── domain_model.py         # SQLAlchemy model
  ├── domain_schema.py        # Pydantic schemas
  └── domain_entity.py        # Business logic (optional)
```

### Data Flow

```
FastAPI Router (controller)
    → CRUD functions (crud.py)
    → SQLAlchemy ORM (model.py)
    → PostgreSQL/MinIO
```

### Infrastructure

- **PostgreSQL 16 + PostGIS** (port 5432) - Relational data with geospatial support
- **MinIO** (ports 9000/9001) - Object storage for maps and GPS files (optional)
- Configured via `docker-compose.yaml`

### Key Patterns

- Dependency injection: `db: Session = Depends(get_db)`
- Config singleton: `from app.config import Config`
- Logging: `from app.logger import logger`
- Artifacts stored as: `{event_name}/{date}/{competition_name}/{file_name}`

## Environment

Configuration in `.env`:
- PostgreSQL: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- MinIO: `MINIO_HOST`, `MINIO_PORT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
- `LOG_LEVEL` controls loguru output
