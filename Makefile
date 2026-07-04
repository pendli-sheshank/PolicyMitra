.PHONY: setup migrate ingest reset-db retrieval-eval eval test test-unit test-integration api frontend

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

migrate:
	python3 -m db.migrate

ingest:
	python3 -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield --embedder local
	python3 -m ingestion.cli --insurer-dir corpus/insurers/suraksha_health --embedder local
	python3 -m ingestion.cli --insurer-dir corpus/insurers/nirvana_care --embedder local

reset-db:
	rm -f data/policymitra.db data/policymitra.db-wal data/policymitra.db-shm

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
