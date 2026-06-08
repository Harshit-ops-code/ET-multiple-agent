# Scripts Folder

This directory contains utility scripts for the project.

## Legacy Scripts
- `run.bat`: Legacy script to launch the application on Windows.
- `start.ps1`: Legacy PowerShell script to run both backend and frontend locally.

> [!NOTE]
> These scripts are legacy and kept only for local development/backward compatibility.
> We highly recommend using **Docker** to run the application, as the frontend is now served by FastAPI at `/app` (port 8000).
