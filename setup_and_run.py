#!/usr/bin/env python3
"""
Setup and run script for Azure DevOps Repository Analytics Analyzer
This script will install dependencies and guide you through the setup process
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing required dependencies...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_configuration():
    """Interactive setup for Azure DevOps configuration"""
    print("\n🔧 Azure DevOps Configuration Setup")
    print("=" * 50)
    
    config = {}
    
    print("\n1. Azure DevOps Organization Name")
    print("   (This is the name in your Azure DevOps URL: https://dev.azure.com/YOUR-ORG/)")
    config['org'] = input("   Enter organization name: ").strip()
    
    print("\n2. Project Name")
    print("   (The name of your project within the organization)")
    config['project'] = input("   Enter project name: ").strip()
    
    print("\n3. Repository Name")
    print("   (The name of the repository you want to analyze)")
    config['repo'] = input("   Enter repository name: ").strip()
    
    print("\n4. Personal Access Token (PAT)")
    print("   To create a PAT:")
    print("   • Go to https://dev.azure.com/{}/{{_usersSettings/tokens".format(config['org']))
    print("   • Click 'New Token'")
    print("   • Select these scopes: Code (read), Work Items (read), Pull Request (read)")
    print("   • Copy the generated token")
    config['pat'] = input("   Enter PAT token: ").strip()
    
    # Validate inputs
    if not all([config['org'], config['project'], config['repo'], config['pat']]):
        print("\n❌ All fields are required!")
        return None
    
    return config

def create_env_file(config):
    """Create a .env file with the configuration"""
    env_content = f"""# Azure DevOps Configuration
AZDO_ORG={config['org']}
AZDO_PROJECT={config['project']}
AZDO_REPO={config['repo']}
AZDO_PAT={config['pat']}
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Configuration saved to .env file")
        return True
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")
        return False

def load_env_file():
    """Load configuration from .env file"""
    if not os.path.exists('.env'):
        return None
    
    config = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key.startswith('AZDO_'):
                        config[key] = value
        return config
    except Exception:
        return None

def run_analyzer(config=None):
    """Run the analyzer with configuration"""
    print("\n🚀 Starting Azure DevOps Repository Analysis...")
    
    # Set environment variables if config provided
    if config:
        os.environ['AZDO_ORG'] = config.get('AZDO_ORG', config.get('org', ''))
        os.environ['AZDO_PROJECT'] = config.get('AZDO_PROJECT', config.get('project', ''))
        os.environ['AZDO_REPO'] = config.get('AZDO_REPO', config.get('repo', ''))
        os.environ['AZDO_PAT'] = config.get('AZDO_PAT', config.get('pat', ''))
    
    try:
        # Import and run the analyzer
        from analyzer import AzureDevOpsAnalyzer
        
        org_name = os.environ.get('AZDO_ORG')
        project_name = os.environ.get('AZDO_PROJECT')
        repo_name = os.environ.get('AZDO_REPO')
        pat_token = os.environ.get('AZDO_PAT')
        
        analyzer = AzureDevOpsAnalyzer(
            org_name=org_name,
            project_name=project_name,
            repo_name=repo_name,
            pat_token=pat_token,
            data_dir="./azdo_analytics"
        )
        
        # Run the analysis
        analyzer.run_complete_analysis()
        
        print("\n🎉 Analysis completed successfully!")
        print("📁 Check the './results/' directory for all generated reports")
        
    except Exception as e:
        print(f"\n❌ Error running analysis: {str(e)}")
        return False
    
    return True

def main():
    """Main setup and run function"""
    print("🔍 Azure DevOps Repository Analytics Analyzer")
    print("=" * 50)
    
    # Step 1: Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Step 2: Check for existing configuration
    existing_config = load_env_file()
    
    if existing_config:
        print(f"\n✅ Found existing configuration:")
        print(f"   Organization: {existing_config.get('AZDO_ORG', 'Not set')}")
        print(f"   Project: {existing_config.get('AZDO_PROJECT', 'Not set')}")
        print(f"   Repository: {existing_config.get('AZDO_REPO', 'Not set')}")
        
        use_existing = input("\nUse existing configuration? (y/n): ").lower().strip()
        if use_existing == 'y':
            if run_analyzer(existing_config):
                return
            else:
                sys.exit(1)
    
    # Step 3: Setup new configuration
    config = setup_configuration()
    if not config:
        sys.exit(1)
    
    # Step 4: Save configuration
    if not create_env_file(config):
        sys.exit(1)
    
    # Step 5: Run analyzer
    if not run_analyzer(config):
        sys.exit(1)

if __name__ == "__main__":
    main()
