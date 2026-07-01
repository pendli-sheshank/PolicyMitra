.PHONY: setup db-up migrate ingest retrieval-eval eval test test-unit test-integration api frontend

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

db-up:
	service postgresql start
	sudo -u postgres psql -c "CREATE DATABASE policymitra;" || true

migrate:
	python3 -m db.migrate

ingest:
	python3 -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield --embedder local
	python3 -m ingestion.cli --insurer-dir corpus/insurers/suraksha_health --embedder local
	python3 -m ingestion.cli --insurer-dir corpus/insurers/nirvana_care --embedder local

retrieval-eval:
	python3 -m eval.harness.run_retrieval_eval

eval:
	python3 -m eval.run_all

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

test: test-unit test-integration

api:
	uvicorn api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev
