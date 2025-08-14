#!/usr/bin/env python3
"""
Debug script to investigate PR 1364 data discrepancy
"""

import os
import sys
import json
import requests
import base64

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def debug_pr_1364():
    """Debug PR 1364 to understand the discrepancy"""
    
    # Configuration
    org_name = os.getenv('AZDO_ORG', '')
    project_name = os.getenv('AZDO_PROJECT', '')
    repo_name = os.getenv('AZDO_REPO', '')
    pat_token = os.getenv('AZDO_PAT', '')
    
    if not all([org_name, project_name, repo_name, pat_token]):
        print("[ERROR] Missing Azure DevOps configuration!")
        return
    
    print("="*70)
    print("DEBUGGING PR #1364")
    print("="*70)
    
    # Setup API access
    base_url = f"https://dev.azure.com/{org_name}/{project_name}/_apis"
    headers = {
        'Authorization': f'Basic {base64.b64encode(f":{pat_token}".encode()).decode()}',
        'Content-Type': 'application/json'
    }
    
    # 1. Get basic PR info
    print("\n1. BASIC PR INFO:")
    pr_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364?api-version=7.0"
    response = requests.get(pr_url, headers=headers)
    if response.status_code == 200:
        pr_data = response.json()
        print(f"   Title: {pr_data.get('title')}")
        print(f"   Status: {pr_data.get('status')}")
        print(f"   Created: {pr_data.get('creationDate')}")
        print(f"   Source: {pr_data.get('sourceRefName')}")
        print(f"   Target: {pr_data.get('targetRefName')}")
        print(f"   Last merge commit: {pr_data.get('lastMergeCommit', {}).get('commitId', 'N/A')[:8]}")
        print(f"   Last merge source: {pr_data.get('lastMergeSourceCommit', {}).get('commitId', 'N/A')[:8]}")
        print(f"   Last merge target: {pr_data.get('lastMergeTargetCommit', {}).get('commitId', 'N/A')[:8]}")
    
    # 2. Get PR commits
    print("\n2. PR COMMITS:")
    commits_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/commits?api-version=7.0"
    response = requests.get(commits_url, headers=headers)
    if response.status_code == 200:
        commits = response.json().get('value', [])
        print(f"   Total commits: {len(commits)}")
        for i, commit in enumerate(commits[:10], 1):  # Show first 10
            print(f"   {i}. {commit.get('commitId', '')[:8]} - {commit.get('comment', '')[:60]}")
    
    # 3. Get PR iterations (versions)
    print("\n3. PR ITERATIONS:")
    iterations_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/iterations?api-version=7.0"
    response = requests.get(iterations_url, headers=headers)
    if response.status_code == 200:
        iterations = response.json().get('value', [])
        print(f"   Total iterations: {len(iterations)}")
        for i, iteration in enumerate(iterations, 1):
            print(f"   Iteration {i}: {iteration.get('createdDate', '')} - ID: {iteration.get('id')}")
            
            # Get changes for each iteration
            if i == len(iterations):  # Check latest iteration
                iter_id = iteration.get('id')
                changes_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/iterations/{iter_id}/changes?api-version=7.0"
                changes_resp = requests.get(changes_url, headers=headers)
                if changes_resp.status_code == 200:
                    changes_data = changes_resp.json()
                    change_entries = changes_data.get('changeEntries', [])
                    print(f"      Changes in latest iteration: {len(change_entries)}")
                    
                    # Show first few changes
                    for j, change in enumerate(change_entries[:5], 1):
                        item = change.get('item', {})
                        change_type = change.get('changeType', '')
                        path = item.get('path', '')
                        print(f"      {j}. {change_type}: {path}")
                    
                    if len(change_entries) > 5:
                        print(f"      ... and {len(change_entries) - 5} more")
    
    # 4. Get diff between source and target
    print("\n4. ACTUAL DIFF (Source vs Target):")
    
    # Get source and target commit IDs
    if pr_data:
        source_branch = pr_data.get('sourceRefName', '')
        target_branch = pr_data.get('targetRefName', '')
        
        # Get the diff
        diff_url = f"{base_url}/git/repositories/{repo_name}/diffs/commits?api-version=7.0"
        diff_params = {
            'baseVersion': target_branch.replace('refs/heads/', ''),
            'targetVersion': source_branch.replace('refs/heads/', ''),
            '$top': 100
        }
        
        # Alternative: Use commit comparison
        if pr_data.get('lastMergeSourceCommit'):
            source_commit = pr_data['lastMergeSourceCommit']['commitId']
            target_commit = pr_data.get('lastMergeTargetCommit', {}).get('commitId')
            
            if target_commit:
                diff_url = f"{base_url}/git/repositories/{repo_name}/diffs/commits?baseVersion={target_commit}&targetVersion={source_commit}&api-version=7.0"
                response = requests.get(diff_url, headers=headers)
                if response.status_code == 200:
                    diff_data = response.json()
                    changes = diff_data.get('changes', [])
                    print(f"   Real changes count: {len(changes)}")
                    
                    # Group by change type
                    change_types = {}
                    for change in changes:
                        ct = change.get('changeType', 'unknown')
                        change_types[ct] = change_types.get(ct, 0) + 1
                    
                    print(f"   Change types: {change_types}")
                    
                    # Show actual file changes
                    print("\n   Actual files changed:")
                    for i, change in enumerate(changes[:10], 1):
                        item = change.get('item', {})
                        path = item.get('path', '')
                        change_type = change.get('changeType', '')
                        print(f"   {i}. [{change_type}] {path}")
                    
                    if len(changes) > 10:
                        print(f"   ... and {len(changes) - 10} more files")
    
    # 5. Use the correct API endpoint for PR changes
    print("\n5. PR FILE CHANGES (Correct API):")
    # This endpoint should give us the actual changes
    pr_files_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/iterations/1/changes?api-version=7.0&$top=500"
    response = requests.get(pr_files_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        change_entries = data.get('changeEntries', [])
        print(f"   Change entries found: {len(change_entries)}")
        
        if change_entries:
            # Count actual file modifications
            real_changes = [c for c in change_entries if c.get('changeType') not in ['none', 'all']]
            print(f"   Real file changes: {len(real_changes)}")
            
            print("\n   Actual modified files:")
            for i, change in enumerate(real_changes[:10], 1):
                item = change.get('item', {})
                path = item.get('path', '')
                change_type = change.get('changeType', '')
                print(f"   {i}. [{change_type}] {path}")

if __name__ == "__main__":
    debug_pr_1364()