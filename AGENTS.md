# HH Control — Agent Instructions

## Project
Self-hosted application for managing personal
HeadHunter resumes through the official HH API.

## Tech Stack
- Python 3.12+, FastAPI, SQLAlchemy 2
- Vue 3, TypeScript, Vite
- SQLite, APScheduler
- Docker Compose

## Development Rules
- Follow KISS and YAGNI.
- Use type hints and asynchronous HTTP requests.
- Keep business logic separate from API endpoints.
- Never hardcode credentials or tokens.
- Use only the official HeadHunter API.
- Respect API rate limits and publishing restrictions.
- Write tests for new business logic.
- Keep the architecture modular and extensible.

## Documentation
- docs/requirements.md — functional requirements.
- docs/architecture.md — architectural decisions.

## Workflow
- Read docs/requirements.md before implementing features.
- Implement changes incrementally.
- Run relevant tests after changes.
- Update documentation when behavior changes.
- Do not introduce unnecessary infrastructure.
