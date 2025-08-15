"""
Debug script to check what environment variables are available
when running through Claude Desktop
"""

import os
import sys
import json

print("=" * 60)
print("ENVIRONMENT DEBUG")
print("=" * 60)
print()

# Check current working directory
print(f"Current Directory: {os.getcwd()}")
print(f"Script Location: {os.path.abspath(__file__)}")
print()

# Check for .env file
env_file = os.path.join(os.path.dirname(__file__), '.env')
print(f".env file exists: {os.path.exists(env_file)}")
print(f".env path: {env_file}")
print()

# Check environment variables
print("Azure DevOps Environment Variables:")
print("-" * 40)
env_vars = {
    "AZURE_DEVOPS_ORG": os.getenv("AZURE_DEVOPS_ORG"),
    "AZURE_DEVOPS_PROJECT": os.getenv("AZURE_DEVOPS_PROJECT"),
    "AZURE_DEVOPS_PAT": os.getenv("AZURE_DEVOPS_PAT"),
    "WORKING_DIRECTORY": os.getenv("WORKING_DIRECTORY"),
    "PYTHONPATH": os.getenv("PYTHONPATH")
}

for key, value in env_vars.items():
    if key == "AZURE_DEVOPS_PAT" and value:
        # Don't print the full PAT
        print(f"{key}: ***{value[-4:]} ({len(value)} chars)")
    else:
        print(f"{key}: {value if value else '[NOT SET]'}")

print()
print("Attempting to load .env file manually...")
print("-" * 40)

try:
    from dotenv import load_dotenv
    
    # Try multiple loading strategies
    strategies = [
        ("load_dotenv()", lambda: load_dotenv()),
        ("load_dotenv(override=True)", lambda: load_dotenv(override=True)),
        (f"load_dotenv('{env_file}')", lambda: load_dotenv(env_file)),
        (f"load_dotenv('{env_file}', override=True)", lambda: load_dotenv(env_file, override=True))
    ]
    
    for strategy_name, strategy_func in strategies:
        print(f"\nTrying: {strategy_name}")
        result = strategy_func()
        print(f"Result: {result}")
        
        # Check if it worked
        pat = os.getenv("AZURE_DEVOPS_PAT")
        if pat:
            print(f"SUCCESS! PAT loaded: ***{pat[-4:]} ({len(pat)} chars)")
            break
        else:
            print("PAT still not loaded")
            
except ImportError:
    print("ERROR: python-dotenv not installed")
    
print()
print("=" * 60)
print("END DEBUG")
print("=" * 60)