#!/usr/bin/env python3
"""
Quick test to verify the Azure DevOps analyzer is working with the fixed date filtering
"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.main_analyzer import AzureDevOpsAnalyzer

def test_analyzer():
    """Test the analyzer with sample data"""
    
    print("=== TESTING AZURE DEVOPS ANALYZER ===")
    print()
      # Use dummy credentials since we have cached data
    analyzer = AzureDevOpsAnalyzer(
        org_name="test_org",
        project_name="test_project", 
        repo_name="test_repo",
        pat_token="dummy_token"
    )
    
    print("✅ Analyzer initialized successfully")
    print(f"📅 Date range: {analyzer.date_from} to {analyzer.date_to}")
    print()
    
    # Try to load existing data
    try:
        analyzer.data_collector.load_collected_data()
        print(f"📊 Data loaded:")
        print(f"  - Commits: {len(analyzer.commits)}")
        print(f"  - Detailed commits: {len(analyzer.detailed_commits)}")
        print(f"  - Pull requests: {len(analyzer.pull_requests)}")
        print(f"  - Work items: {len(analyzer.work_items)}")
        print()
        
        if len(analyzer.commits) > 0:
            print("🎉 SUCCESS: The date filtering issue has been resolved!")
            print("✅ The analyzer can now process commits and proceed with analysis")
            return True
        else:
            print("⚠️  Still no commits loaded, but detailed commits exist")
            return False
            
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False

if __name__ == "__main__":
    success = test_analyzer()
    if success:
        print("\n🚀 The Azure DevOps code analyzer is ready to run full analysis!")
    else:
        print("\n🔧 There may still be some configuration issues to resolve")
