@echo off
REM Batch script to start server with environment variables
REM This reads from .env and sets them before starting Python

setlocal enabledelayedexpansion

REM Read .env file and set environment variables
for /f "tokens=1,2 delims==" %%a in (.env) do (
    REM Skip comments and empty lines
    echo %%a | findstr /r "^#" >nul
    if errorlevel 1 (
        if not "%%a"=="" (
            set "%%a=%%b"
            echo Setting %%a
        )
    )
)

REM Start the Python server
python -m azure_pr_reviewer.server %*