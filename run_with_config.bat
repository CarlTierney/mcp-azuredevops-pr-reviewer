@echo off
REM Set your Azure DevOps configuration here
set AZDO_ORG=your_organization_name
set AZDO_PROJECT=your_project_name
set AZDO_REPO=your_repository_name
set AZDO_PAT=your_personal_access_token

echo Running Azure DevOps Analyzer...
python run_analyzer.py
pause