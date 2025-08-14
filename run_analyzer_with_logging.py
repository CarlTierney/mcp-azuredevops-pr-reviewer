#!/usr/bin/env python3
"""
Runner script for Azure DevOps Repository Analytics Analyzer with dual logging
Logs output to both console and a file
"""

import os
import sys
import logging
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# Set up dual logging (console + file)
def setup_logging():
    """Configure logging to output to both console and file"""
    
    # Create logs directory if it doesn't exist
    log_dir = "./logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Generate log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"analyzer_run_{timestamp}.log")
    
    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Create formatters
    console_formatter = logging.Formatter('%(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger, log_filename

# Custom print function that uses logging
class DualOutput:
    """Class to redirect print statements to both console and file"""
    def __init__(self, logger):
        self.logger = logger
        self.terminal = sys.stdout
        
    def write(self, message):
        # Write to console
        self.terminal.write(message)
        # Write to log file (strip trailing newline for logging)
        if message.strip():
            self.logger.info(message.strip())
            
    def flush(self):
        self.terminal.flush()

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded configuration from .env file")
except ImportError:
    # dotenv not installed, will use environment variables or hardcoded values
    pass

from analyzer import AzureDevOpsAnalyzer

def main():
    """Main function to run the Azure DevOps analyzer with logging"""
    
    # Set up logging
    logger, log_filename = setup_logging()
    
    # Redirect stdout to dual output
    sys.stdout = DualOutput(logger)
    
    print(f"[LOG] Logging to file: {log_filename}")
    print("=" * 60)
    
    # Configuration - Update these values with your Azure DevOps details
    ORG_NAME=""           # Set your Azure DevOps organization name
    PROJECT_NAME=""       # Set your project name
    REPO_NAME=""          # Set your repository name
    PAT_TOKEN=""   # Set your Azure DevOps Personal Access Token
    
    # Optional: Read from environment variables for security
    ORG_NAME = os.getenv('AZDO_ORG', ORG_NAME)
    PROJECT_NAME = os.getenv('AZDO_PROJECT', PROJECT_NAME)
    REPO_NAME = os.getenv('AZDO_REPO', REPO_NAME)
    PAT_TOKEN = os.getenv('AZDO_PAT', PAT_TOKEN)
    
    # Validate required parameters
    if not all([ORG_NAME, PROJECT_NAME, REPO_NAME, PAT_TOKEN]):
        print("❌ Error: Missing required configuration!")
        print("\nPlease update the configuration in this script or set environment variables:")
        print("  - AZDO_ORG: Your Azure DevOps organization name")
        print("  - AZDO_PROJECT: Your project name")
        print("  - AZDO_REPO: Your repository name")
        print("  - AZDO_PAT: Your Personal Access Token")
        print("\nExample:")
        print("  export AZDO_ORG='mycompany'")
        print("  export AZDO_PROJECT='MyProject'")
        print("  export AZDO_REPO='MyRepository'")
        print("  export AZDO_PAT='your-pat-token-here'")
        print("\nTo create a PAT token:")
        print("  1. Go to https://dev.azure.com/{your-org}/_usersSettings/tokens")
        print("  2. Click 'New Token'")
        print("  3. Give it a name and select these scopes:")
        print("     - Code (read)")
        print("     - Work Items (read)")
        print("     - Pull Request (read)")
        sys.exit(1)
    
    print("[START] Starting Azure DevOps Repository Analysis...")
    print(f"   Organization: {ORG_NAME}")
    print(f"   Project: {PROJECT_NAME}")
    print(f"   Repository: {REPO_NAME}")
    print(f"   PAT Token: {'*' * (len(PAT_TOKEN) - 4) + PAT_TOKEN[-4:] if len(PAT_TOKEN) > 4 else '****'}")
    
    try:
        # Initialize the analyzer
        analyzer = AzureDevOpsAnalyzer(
            org_name=ORG_NAME,
            project_name=PROJECT_NAME,
            repo_name=REPO_NAME,
            pat_token=PAT_TOKEN,
            data_dir="./azdo_analytics"  # Data will be stored here
        )
        
        # Run the complete analysis
        results = analyzer.run_complete_analysis()
        
        print("\n🎉 Analysis completed successfully!")
        print("\n📋 Generated Reports:")
        print("   • azdo_productivity_metrics.csv - Developer productivity analysis")
        print("   • azdo_csharp_sql_quality_metrics.csv - Code quality metrics")
        print("   • azdo_commit_timing_metrics.csv - Commit timing patterns")
        print("   • azdo_enhanced_quality_metrics.csv - Advanced quality analysis")
        print("   • azdo_advanced_developer_contributions.csv - Comprehensive developer analysis")
        print("   • azdo_repository_health_trends.csv - Repository health over time")
        print("   • azdo_team_collaboration_patterns.csv - Team collaboration analysis")
        print("   • azdo_file_hotspots_analysis.csv - File hotspot and risk analysis")
        print("   • azdo_bus_factor_analysis.csv - Bus factor risk assessment")
        print("   • azdo_enhanced_summary_report.csv - Consolidated summary")
        
        print(f"\n📁 All reports saved to: ./results/")
        print(f"📝 Complete log saved to: {log_filename}")
        print("\n💡 Next Steps:")
        print("   1. Review the summary report for key insights")
        print("   2. Check individual CSV files for detailed metrics")
        print("   3. Use the collaboration analysis to identify knowledge silos")
        print("   4. Review bus factor analysis for risk mitigation")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify your PAT token has the required permissions")
        print("   2. Check that organization, project, and repository names are correct")
        print("   3. Ensure you have network access to Azure DevOps")
        print("   4. Check the Azure DevOps service status")
        sys.exit(1)
    finally:
        # Restore stdout
        sys.stdout = sys.stdout.terminal
        print(f"\n[LOG] Full analysis log saved to: {log_filename}")

if __name__ == "__main__":
    main()