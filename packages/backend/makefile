def restart_dev_server:
	docker-compose -f ../../docker/docker-compose.yaml down
	rm -rf ../postgres/data
	docker-compose -f ../../docker/docker-compose.yaml up -d
	uvicorn src.app:app --reload --reload-include="*.html" --reload-include="*.css" --reload-include="*.js"
