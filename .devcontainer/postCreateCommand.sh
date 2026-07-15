#!/bin/bash
# One-shot Codespaces/devcontainer setup. The backend is Postgres+pgvector
# (a Supabase project by default) — DATABASE_URL must be supplied as a
# Codespaces secret (or .env) before migrate/ingest can run, so those steps
# are skipped when it's missing and re-runnable via `make migrate`/`make ingest`.
set -e

echo "=== PolicyMitra setup ==="

echo "--- Python venv + dependencies"
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

echo "--- Database migrate + corpus ingest (Postgres via DATABASE_URL)"
if [ -n "${DATABASE_URL:-}" ]; then
  python3 -m db.migrate
  python3 -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield
  python3 -m ingestion.cli --insurer-dir corpus/insurers/suraksha_health
  python3 -m ingestion.cli --insurer-dir corpus/insurers/nirvana_care
else
  echo "DATABASE_URL is not set — skipping migrate/ingest."
  echo "Add it as a Codespaces secret, then run: make migrate && make ingest"
fi

echo "--- Frontend API URL"
if [ -n "${CODESPACE_NAME:-}" ] && [ -n "${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-}" ]; then
  echo "NEXT_PUBLIC_API_BASE_URL=https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}" > frontend/.env.local
  # The browser (on the forwarded 3000 origin) must be able to reach port
  # 8000; make it public best-effort. See README "GitHub Codespaces".
  gh codespace ports visibility 8000:public -c "$CODESPACE_NAME" 2>/dev/null || true
else
  echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > frontend/.env.local
fi

echo "--- Frontend dependencies"
(cd frontend && npm install --no-audit --no-fund)

echo ""
echo "=== Setup complete ==="
echo "Run the app:"
echo "  Terminal 1: make api                  # FastAPI on :8000"
echo "  Terminal 2: cd frontend && npm run dev  # Next.js on :3000"
echo ""
echo "Secrets (Codespaces secrets or .env): DATABASE_URL (required),"
echo "GEMINI_API_KEY (LLM answers), OPENAI_API_KEY (semantic embeddings)."
