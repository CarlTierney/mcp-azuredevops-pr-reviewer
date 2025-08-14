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
        
        if commits:
            # Sample first few commit dates
            print("  Sample commit dates:")
            for i, commit in enumerate(commits[:10]):
                author_date = commit.get('author', {}).get('date', 'Unknown')
                commit_id = commit.get('commitId', 'Unknown')[:8]
                print(f"    {i+1}. {commit_id} - {author_date}")
            
            # Find date range of all commits
            commit_dates = []
            for commit in commits:
                date_str = commit.get('author', {}).get('date', '')
                if date_str:
                    try:
                        commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        commit_dates.append(commit_date)
                    except:
                        pass
            
            if commit_dates:
                commit_dates.sort()
                print(f"  Commit date range in data:")
                print(f"    Oldest: {commit_dates[0].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Newest: {commit_dates[-1].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Check how many would pass current filter
                filtered_count = 0
                for date in commit_dates:
                    if date_from <= date <= date_to:
                        filtered_count += 1
                
                print(f"  Commits in current date range: {filtered_count} / {len(commit_dates)}")
                
                if filtered_count == 0:
                    print("  🚨 NO COMMITS IN CURRENT DATE RANGE!")
                    print(f"  💡 Try extending date range to include {commit_dates[0].strftime('%Y-%m-%d')}")
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
    else:
        print(f"❌ {detailed_commits_dir} not found")

if __name__ == "__main__":
    debug_commit_dates()
