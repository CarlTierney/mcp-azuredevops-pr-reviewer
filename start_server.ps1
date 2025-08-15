# PowerShell script to start server with environment variables from .env

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Loading environment from .env file..." -ForegroundColor Green

# Read .env file
$envFile = Join-Path $scriptPath ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        # Skip comments and empty lines
        if ($_ -match '^([^#][^=]+)=([^#]+)') {
            $key = $matches[1].Trim()
            # Remove inline comments and quotes
            $value = $matches[2].Trim()
            # Remove trailing comments
            if ($value -match '^([^#]+)#') {
                $value = $matches[1].Trim()
            }
            # Remove quotes
            $value = $value.Trim('"').Trim("'")
            
            [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
            if ($key -eq "AZURE_DEVOPS_PAT") {
                if ($value.Length -ge 4) {
                    Write-Host "Set $key=***$($value.Substring($value.Length - 4))" -ForegroundColor Yellow
                } else {
                    Write-Host "Set $key=***" -ForegroundColor Yellow
                }
            } else {
                Write-Host "Set $key=$value" -ForegroundColor Yellow
            }
        }
    }
} else {
    Write-Host "ERROR: .env file not found at $envFile" -ForegroundColor Red
    exit 1
}

# Verify critical variables
$pat = [System.Environment]::GetEnvironmentVariable("AZURE_DEVOPS_PAT", [System.EnvironmentVariableTarget]::Process)
$org = [System.Environment]::GetEnvironmentVariable("AZURE_DEVOPS_ORG", [System.EnvironmentVariableTarget]::Process)

if (-not $pat) {
    Write-Host "ERROR: AZURE_DEVOPS_PAT not set" -ForegroundColor Red
    exit 1
}
if (-not $org) {
    Write-Host "ERROR: AZURE_DEVOPS_ORG not set" -ForegroundColor Red
    exit 1
}

Write-Host "Starting Azure PR Reviewer Server..." -ForegroundColor Green
Write-Host "Organization: $org" -ForegroundColor Cyan

# Start the Python server
python -m azure_pr_reviewer.server $args