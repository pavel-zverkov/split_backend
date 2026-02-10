dev:
	uvicorn app.main:app --reload

test:
	pytest tests/ -v

migrate:
	alembic upgrade head

migrate_create:
	alembic revision --autogenerate -m "$(msg)"

db_up:
	docker-compose up -d

db_down:
	docker-compose down
