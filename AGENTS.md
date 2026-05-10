# Project Instructions

This file provides context for AI assistants working on this project.

## Project Type: Node.js and Python Backend

### Commands
- Install: `pnpm i`
- Build: `pnpm run build`
- Start: `pnpm dev`
- backend start: `cd backend-python && uvicorn main:app --reload`

### Framework: Vite

### Documentation
See README.md for project overview.

### Version Control
This project uses Git. See .gitignore for excluded files.


## Guidelines

- Follow existing code style and patterns
- Write tests for new functionality
- Keep changes focused and atomic
- Document public APIs

## Important Notes

- Using uv to manage Python dependencies and virtual environments is recommended for the backend.
- backend-python is a separate service that the Vite frontend communicates with via API calls. Ensure it is running when developing the frontend.
- backend-python already have .venv, please using this virtual environment to run the backend service. 
