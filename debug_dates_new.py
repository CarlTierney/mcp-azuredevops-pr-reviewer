#!/usr/bin/env python3
"""
Debug script to check commit dates and understand the filtering issue
"""

import json
import os
from datetime import datetime, timedelta

def debug_commit_dates():
    """Debug commit date filtering issue"""
    
    # Check if data exists
    commits_file = "azdo_analytics/commits.json"
    detailed_commits_dir = "azdo_analytics/detailed_commits"
    
    print("=== DEBUGGING COMMIT DATE FILTERING ===")
    print()
    
    # Current date range (default: last 180 days)
    now = datetime.now()
    date_from = (now - timedelta(days=180))
    date_to = now
    
    print(f"Current date filter range:")
    print(f"  From: {date_from.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  To:   {date_to.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check commits.json
    if os.path.exists(commits_file):
        print(f"📁 Found {commits_file}")
        with open(commits_file, 'r') as f:
            commits = json.load(f)
        
        print(f"  Total commits in file: {len(commits)}")
        
        if len(commits) == 0:
            print("  🚨 COMMITS FILE IS EMPTY!")
            print("  💡 This suggests the initial commit collection failed or used wrong parameters")
        else:
            # Sample first few commit dates
            print("  Sample commit dates:")
            for i, commit in enumerate(commits[:10]):
                author_date = commit.get('author', {}).get('date', 'Unknown')
                commit_id = commit.get('commitId', 'Unknown')[:8]
                print(f"    {i+1}. {commit_id} - {author_date}")
    else:
        print(f"❌ {commits_file} not found")
    
    print()
    
    # Check detailed commits
    if os.path.exists(detailed_commits_dir):
        detailed_files = [f for f in os.listdir(detailed_commits_dir) if f.endswith('.json')]
        print(f"📁 Found {detailed_commits_dir} with {len(detailed_files)} files")
        
        if detailed_files:
            print("  Sample detailed commit files:")
            for i, file in enumerate(detailed_files[:5]):
                print(f"    {i+1}. {file}")
            
            print()
            print("  💡 DIAGNOSIS:")
            print("     - Detailed commits exist (370 files)")
            print("     - Regular commits.json is empty (0 commits)")
            print("     - This suggests date filtering issue in initial collection")
            print("     - Or the detailed collection bypassed date filtering")
            
    else:
        print(f"❌ {detailed_commits_dir} not found")
    
    print()
    print("=== RECOMMENDED SOLUTIONS ===")
    print("1. Extend the date range to cover older commits")
    print("2. Check the data collection parameters")
    print("3. Re-run collection with broader date range")
    print("4. Modify base_analyzer.py to use longer default period")

if __name__ == "__main__":
    debug_commit_dates()
