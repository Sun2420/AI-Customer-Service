.PHONY: dev backend frontend test lint seed docker-up docker-down

dev:
	docker compose up --build

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest -q

lint:
	cd backend && python -m compileall -q app tests

seed:
	cd backend && python -m app.seed

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

