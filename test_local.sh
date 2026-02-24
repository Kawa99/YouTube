#!/bin/bash
echo "Running Black..."
docker-compose run --rm web black --check . || exit 1

echo "Running Ruff..."
docker-compose run --rm web ruff check . || exit 1

echo "Running Bandit..."
docker-compose run --rm web bandit -c bandit.yaml -r . || exit 1

echo "Running Pytest..."
docker-compose run --rm web pytest tests/ -v || exit 1

echo "✅ All checks passed! You are ready to git push."