restart_dev_server:
	docker-compose down
	rm -rf ./postgres/data
	docker-compose up -d
	uvicorn app.main:app --reload --reload-include="*.html" --reload-include="*.css" --reload-include="*.js"

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
