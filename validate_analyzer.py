#!/usr/bin/env python3
"""
Validation script to check analyzer configuration and data integrity
"""

import os
import json
import sys
import requests
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

def check_configuration():
    """Check if configuration is set up correctly"""
    print("🔍 Checking Configuration...")
    
    issues = []
    
    # Check environment variables
    env_vars = {
        'AZDO_ORG': os.environ.get('AZDO_ORG'),
        'AZDO_PROJECT': os.environ.get('AZDO_PROJECT'),
        'AZDO_REPO': os.environ.get('AZDO_REPO'),
        'AZDO_PAT': os.environ.get('AZDO_PAT')
    }
    
    # Check run_analyzer.py for hardcoded values
    config_file = "run_analyzer.py"
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Check if values are empty
            if 'ORG_NAME=""' in content or 'PROJECT_NAME=""' in content:
                if not all(env_vars.values()):
                    issues.append("Configuration values are empty and no environment variables set")
    
    # Display configuration status
    print("\n📋 Configuration Status:")
    for var, value in env_vars.items():
        if value:
            masked_value = value[:3] + "***" if var == 'AZDO_PAT' else value
            print(f"  ✅ {var}: {masked_value}")
        else:
            print(f"  ❌ {var}: Not set")
            if var != 'AZDO_PAT':
                issues.append(f"{var} not configured")
    
    return issues

def check_data_files():
    """Check if data files exist and are valid"""
    print("\n🔍 Checking Data Files...")
    
    data_dir = "./azdo_analytics"
    files_to_check = [
        "commits.json",
        "pull_requests.json",
        "work_items.json"
    ]
    
    data_status = {}
    
    for file in files_to_check:
        file_path = os.path.join(data_dir, file)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else 1
                    size_kb = os.path.getsize(file_path) / 1024
                    data_status[file] = {
                        'exists': True,
                        'valid': True,
                        'count': count,
                        'size_kb': size_kb
                    }
                    print(f"  ✅ {file}: {count} items ({size_kb:.1f} KB)")
            except json.JSONDecodeError:
                data_status[file] = {'exists': True, 'valid': False}
                print(f"  ⚠️ {file}: Invalid JSON")
        else:
            data_status[file] = {'exists': False}
            print(f"  ❌ {file}: Not found")
    
    # Check detailed commits directory
    detailed_dir = os.path.join(data_dir, "detailed_commits")
    if os.path.exists(detailed_dir):
        detailed_count = len([f for f in os.listdir(detailed_dir) if f.endswith('.json')])
        print(f"  ✅ detailed_commits/: {detailed_count} files")
    else:
        print(f"  ❌ detailed_commits/: Directory not found")
    
    return data_status

def check_api_connectivity():
    """Test Azure DevOps API connectivity"""
    print("\n🔍 Testing API Connectivity...")
    
    org = os.environ.get('AZDO_ORG')
    pat = os.environ.get('AZDO_PAT')
    
    if not org or not pat:
        print("  ⚠️ Cannot test API - missing configuration")
        return False
    
    # Test API endpoint
    url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.0"
    headers = {
        'Authorization': f'Basic {pat}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            projects = response.json().get('value', [])
            print(f"  ✅ API connection successful")
            print(f"  📁 Found {len(projects)} projects")
            return True
        elif response.status_code == 401:
            print(f"  ❌ Authentication failed (401)")
            print("     Check your PAT token")
            return False
        else:
            print(f"  ❌ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

def check_results_files():
    """Check if analysis results exist"""
    print("\n🔍 Checking Analysis Results...")
    
    results_dir = "./results"
    if os.path.exists(results_dir):
        csv_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
        if csv_files:
            print(f"  ✅ Found {len(csv_files)} result files:")
            for file in csv_files[:5]:
                size_kb = os.path.getsize(os.path.join(results_dir, file)) / 1024
                print(f"    • {file} ({size_kb:.1f} KB)")
            if len(csv_files) > 5:
                print(f"    ... and {len(csv_files) - 5} more")
        else:
            print("  ⚠️ No CSV result files found")
    else:
        print("  ❌ Results directory not found")
    
    # Check azdo_analytics directory for results
    azdo_dir = "./azdo_analytics"
    if os.path.exists(azdo_dir):
        csv_files = [f for f in os.listdir(azdo_dir) if f.endswith('.csv')]
        if csv_files:
            print(f"\n  ✅ Found {len(csv_files)} CSV files in azdo_analytics/:")
            for file in csv_files[:5]:
                size_kb = os.path.getsize(os.path.join(azdo_dir, file)) / 1024
                print(f"    • {file} ({size_kb:.1f} KB)")

def diagnose_common_issues(issues):
    """Provide diagnostics for common issues"""
    if issues:
        print("\n⚠️ Detected Issues:")
        for issue in issues:
            print(f"  • {issue}")
        
        print("\n💡 Troubleshooting Tips:")
        print("  1. Set configuration in run_analyzer.py or use environment variables")
        print("  2. Ensure PAT token has 'Code (read)' permission")
        print("  3. Verify organization, project, and repository names")
        print("  4. Run the analyzer with: python run_analyzer.py")

def main():
    """Main validation routine"""
    print("=" * 60)
    print("Azure DevOps Analyzer Validation")
    print("=" * 60)
    
    # Run checks
    config_issues = check_configuration()
    data_status = check_data_files()
    api_ok = check_api_connectivity()
    check_results_files()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Validation Summary")
    print("=" * 60)
    
    all_good = True
    
    # Configuration
    if not config_issues:
        print("✅ Configuration: OK")
    else:
        print("❌ Configuration: Issues found")
        all_good = False
    
    # Data files
    commits_ok = data_status.get('commits.json', {}).get('exists', False)
    if commits_ok:
        print("✅ Data Files: Present")
    else:
        print("⚠️ Data Files: Missing or incomplete")
        all_good = False
    
    # API
    if api_ok:
        print("✅ API Connection: OK")
    else:
        print("❌ API Connection: Failed")
        all_good = False
    
    # Provide recommendations
    if not all_good:
        diagnose_common_issues(config_issues)
    else:
        print("\n✅ All checks passed! The analyzer is ready to use.")
        print("\nRun analysis with: python run_analyzer.py")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())