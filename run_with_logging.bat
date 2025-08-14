@echo off
echo Starting Azure DevOps Analyzer with logging...
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Run the analyzer with logging
python run_analyzer_logged.py

echo.
echo Analysis complete. Check the logs folder for the detailed log file.
pause