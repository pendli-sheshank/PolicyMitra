#!/bin/bash
set -e

echo "🚀 PolicyMitra Development Container Setup"
echo "=========================================="

# Create and activate virtual environment
echo "📦 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env.devcontainer with postgres credentials (git-ignored)
echo "⚙️  Setting up database credentials..."
# Generate a random dev-only password
DEVPASS=$(head -c 16 /dev/urandom | base64 | tr -d '=' | tr '+/' '-_')
cat > .devcontainer/.env.devcontainer <<EOF
POSTGRES_DB=policymitra
POSTGRES_USER=policymitra
POSTGRES_PASSWORD=${DEVPASS}
DATABASE_URL=postgresql://policymitra:${DEVPASS}@postgres:5432/policymitra
EOF

# Setup main .env file
if [ ! -f .env ]; then
  echo "⚙️  Creating .env file from template..."
  cp .env.example .env
  # Set DATABASE_URL to use the docker-compose postgres service
  sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql://policymitra:${DEVPASS}@postgres:5432/policymitra|" .env
else
  echo "✓ .env already exists"
fi

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
DB_URL="postgresql://policymitra:${DEVPASS}@postgres:5432/policymitra"
for i in {1..30}; do
  if python3 -c "import psycopg; psycopg.connect('${DB_URL}')" 2>/dev/null; then
    echo "✓ PostgreSQL is ready"
    break
  fi
  echo "  Attempt $i/30..."
  sleep 1
done

# Run migrations
echo "🔄 Running database migrations..."
python3 -m db.migrate

# Run ingestion
echo "📥 Ingesting corpus data..."
python3 -m ingestion.cli --insurer-dir corpus/insurers/arogya_shield --embedder local
python3 -m ingestion.cli --insurer-dir corpus/insurers/suraksha_health --embedder local
python3 -m ingestion.cli --insurer-dir corpus/insurers/nirvana_care --embedder local

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. In one terminal: make api"
echo "  2. In another terminal: cd frontend && npm install && npm run dev"
echo "  3. Open http://localhost:3000 in your browser"
echo ""
echo "You can also run:"
echo "  make test-unit          # Run unit tests"
echo "  make test-integration   # Run integration tests"
echo "  make eval               # Run evaluation suite"
