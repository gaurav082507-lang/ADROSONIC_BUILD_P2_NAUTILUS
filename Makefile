.PHONY: dev test openapi

dev:
	@echo "Starting backend and frontend..."
	@start cmd /c "cd backend && uvicorn app.main:app --reload --port 8000"
	@start cmd /c "cd frontend && npm run dev"

openapi:
	@python backend/scripts/export_openapi.py

test:
	@echo "Tests not implemented yet"
