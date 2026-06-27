#!/bin/bash
set -e
echo "=== Running Backend Tests ==="
docker compose run --rm backend pytest -v --tb=short
echo "=== All tests passed ==="
