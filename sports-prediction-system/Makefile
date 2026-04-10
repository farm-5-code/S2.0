.PHONY: install install-dev run test coverage smoke docker-up docker-down
install:
	pip install -r requirements.txt
install-dev:
	pip install -r requirements-dev.txt
run:
	python run.py
test:
	pytest -q
coverage:
	pytest --cov=app --cov-report=term-missing
smoke:
	python scripts/smoke_test.py
docker-up:
	docker compose up --build
docker-down:
	docker compose down
