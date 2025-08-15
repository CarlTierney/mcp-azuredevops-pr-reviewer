#!/usr/bin/env python
"""
Robust wrapper script to start the Azure PR Reviewer MCP server
This ensures environment variables are properly loaded regardless of how it's called
"""

import os
import sys
import json
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
os.chdir(SCRIPT_DIR)

# Add the project directory to Python path
sys.path.insert(0, str(SCRIPT_DIR))

print(f"Starting Azure PR Reviewer from: {SCRIPT_DIR}", file=sys.stderr)

# Try to load .env file with multiple strategies
def load_env_file():
    """Load .env file with multiple fallback strategies"""
    env_file = SCRIPT_DIR / '.env'
    
    if not env_file.exists():
        print(f"ERROR: .env file not found at {env_file}", file=sys.stderr)
        print("Please create a .env file with your Azure DevOps credentials", file=sys.stderr)
        return False
    
    try:
        from dotenv import load_dotenv
        
        # Try to load with override to ensure variables are set
        print(f"Loading environment from: {env_file}", file=sys.stderr)
        load_dotenv(env_file, override=True)
        
        # Double-check by reading the file manually if needed
        pat = os.getenv("AZURE_DEVOPS_PAT")
        org = os.getenv("AZURE_DEVOPS_ORG")
        
        if not pat or not org:
            print("Environment variables not loaded via dotenv, trying manual parse...", file=sys.stderr)
            
            # Manually parse the .env file as a fallback
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        # Remove inline comments
                        if '#' in value:
                            value = value.split('#')[0]
                        value = value.strip().strip('"').strip("'")
                        if key in ['AZURE_DEVOPS_PAT', 'AZURE_DEVOPS_ORG', 'AZURE_DEVOPS_PROJECT', 'WORKING_DIRECTORY']:
                            os.environ[key] = value
                            if key == 'AZURE_DEVOPS_PAT':
                                print(f"Manually set {key}=***{value[-4:] if len(value) >= 4 else '***'}", file=sys.stderr)
                            else:
                                print(f"Manually set {key}={value}", file=sys.stderr)
        
        # Final verification
        pat = os.getenv("AZURE_DEVOPS_PAT")
        org = os.getenv("AZURE_DEVOPS_ORG")
        
        if not pat:
            print("ERROR: AZURE_DEVOPS_PAT not found in environment", file=sys.stderr)
            return False
        if not org:
            print("ERROR: AZURE_DEVOPS_ORG not found in environment", file=sys.stderr)
            return False
            
        print(f"Environment loaded successfully: Organization={org}, PAT=***{pat[-4:]}", file=sys.stderr)
        return True
        
    except ImportError:
        print("ERROR: python-dotenv not installed. Run: pip install python-dotenv", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR loading .env file: {e}", file=sys.stderr)
        return False

# Load environment
if not load_env_file():
    sys.exit(1)

# Import and start the server
try:
    # Set the working directory environment variable if not set
    if not os.getenv("WORKING_DIRECTORY"):
        os.environ["WORKING_DIRECTORY"] = str(SCRIPT_DIR / "temp_pr_analysis")
    
    # Import the server module
    from azure_pr_reviewer import server
    
    # Start the server
    server.main()
    
except ImportError as e:
    print(f"ERROR: Failed to import server module: {e}", file=sys.stderr)
    print("Make sure all dependencies are installed: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Server failed to start: {e}", file=sys.stderr)
    sys.exit(1)