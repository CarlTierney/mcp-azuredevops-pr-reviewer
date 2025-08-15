"""
Wrapper script to start the Azure PR Reviewer MCP server
This ensures the .env file is loaded before starting the server
"""

import os
import sys
from pathlib import Path

# Ensure we're in the right directory
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Load .env file explicitly
from dotenv import load_dotenv
env_path = script_dir / ".env"

if env_path.exists():
    print(f"Loading environment from: {env_path}")
    load_dotenv(env_path, override=True)
    
    # Verify critical variables are loaded
    pat = os.getenv("AZURE_DEVOPS_PAT")
    org = os.getenv("AZURE_DEVOPS_ORG")
    
    if not pat:
        print("ERROR: AZURE_DEVOPS_PAT not found in .env file")
        sys.exit(1)
    if not org:
        print("ERROR: AZURE_DEVOPS_ORG not found in .env file")
        sys.exit(1)
        
    print(f"Environment loaded: Organization={org}, PAT=***{pat[-4:]}")
else:
    print(f"ERROR: .env file not found at {env_path}")
    print("Please create a .env file with your Azure DevOps credentials")
    sys.exit(1)

# Now start the actual server
from azure_pr_reviewer.server import main

if __name__ == "__main__":
    main()