#!/usr/bin/env python3
"""
Get the actual code diff for PR 1364
"""

import os
import sys
import requests
import base64 as b64

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_pr_diff():
    """Get the actual diff for PR 1364"""
    
    # Configuration
    org_name = os.getenv('AZDO_ORG', '')
    project_name = os.getenv('AZDO_PROJECT', '')
    repo_name = os.getenv('AZDO_REPO', '')
    pat_token = os.getenv('AZDO_PAT', '')
    
    if not all([org_name, project_name, repo_name, pat_token]):
        print("[ERROR] Missing Azure DevOps configuration!")
        return
    
    print("="*70)
    print("FETCHING CODE DIFF FOR PR #1364")
    print("="*70)
    
    # Setup API access
    base_url = f"https://dev.azure.com/{org_name}/{project_name}/_apis"
    headers = {
        'Authorization': f'Basic {b64.b64encode(f":{pat_token}".encode()).decode()}',
        'Content-Type': 'application/json'
    }
    
    # Get the PR to find commit IDs
    pr_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364?api-version=7.0"
    response = requests.get(pr_url, headers=headers)
    if response.status_code != 200:
        print("[ERROR] Could not fetch PR")
        return
    
    pr_data = response.json()
    
    # Method 1: Get the actual commit that has the change
    print("\n1. FETCHING COMMIT WITH ACTUAL CHANGES:")
    commits_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/commits?api-version=7.0"
    response = requests.get(commits_url, headers=headers)
    if response.status_code == 200:
        commits = response.json().get('value', [])
        
        # Find the non-merge commit
        for commit in commits:
            commit_id = commit.get('commitId')
            comment = commit.get('comment', '')
            
            # Skip merge commits
            if 'merge' not in comment.lower():
                print(f"\nCommit: {commit_id[:8]}")
                print(f"Message: {comment}")
                
                # Get the changes for this commit
                changes_url = f"{base_url}/git/repositories/{repo_name}/commits/{commit_id}/changes?api-version=7.0"
                changes_response = requests.get(changes_url, headers=headers)
                
                if changes_response.status_code == 200:
                    changes_data = changes_response.json()
                    changes = changes_data.get('changes', [])
                    
                    for change in changes:
                        item = change.get('item', {})
                        path = item.get('path', '')
                        
                        if 'Questionnaires.cs' in path:
                            print(f"\nFile: {path}")
                            print(f"Change Type: {change.get('changeType', '')}")
                            
                            # Try to get the actual diff
                            # Get the file content from the commit
                            content_url = f"{base_url}/git/repositories/{repo_name}/items?path={path}&version={commit_id}&api-version=7.0"
                            content_response = requests.get(content_url, headers=headers)
                            
                            if content_response.status_code == 200:
                                print("\nFile exists in commit - changes were made")
                            
                            # Get parent commit to compare
                            parent_url = f"{base_url}/git/repositories/{repo_name}/commits/{commit_id}?api-version=7.0"
                            parent_response = requests.get(parent_url, headers=headers)
                            if parent_response.status_code == 200:
                                parent_data = parent_response.json()
                                parents = parent_data.get('parents', [])
                                if parents:
                                    parent_id = parents[0]
                                    print(f"Parent commit: {parent_id[:8]}")
    
    # Method 2: Use iterations API to get the diff
    print("\n2. FETCHING DIFF FROM ITERATIONS:")
    
    # Get iterations
    iterations_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/iterations?api-version=7.0"
    iterations_response = requests.get(iterations_url, headers=headers)
    
    if iterations_response.status_code == 200:
        iterations = iterations_response.json().get('value', [])
        
        # Check each iteration for changes
        for i, iteration in enumerate(iterations, 1):
            iter_id = iteration.get('id')
            print(f"\nIteration {i} (ID: {iter_id}):")
            
            # Get changes in this iteration
            changes_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/iterations/{iter_id}/changes?api-version=7.0"
            changes_response = requests.get(changes_url, headers=headers)
            
            if changes_response.status_code == 200:
                change_entries = changes_response.json().get('changeEntries', [])
                
                for change in change_entries:
                    item = change.get('item', {})
                    path = item.get('path', '')
                    
                    if 'Questionnaires.cs' in path:
                        print(f"  File: {path}")
                        print(f"  Change Type: {change.get('changeType', '')}")
                        
                        # Try to get diff between iterations
                        if i > 1:
                            prev_iter_id = iterations[i-2].get('id')
                            diff_url = f"{base_url}/git/repositories/{repo_name}/pullrequests/1364/iterations/{iter_id}/changes?$compareTo={prev_iter_id}&api-version=7.0"
                            diff_response = requests.get(diff_url, headers=headers)
                            if diff_response.status_code == 200:
                                print("  Diff available between iterations")
    
    # Method 3: Get PR diff directly
    print("\n3. ATTEMPTING TO GET PR DIFF:")
    
    # Try to get the diff using source and target refs
    source_ref = pr_data.get('sourceRefName', '').replace('refs/heads/', '')
    target_ref = pr_data.get('targetRefName', '').replace('refs/heads/', '')
    
    print(f"Source branch: {source_ref}")
    print(f"Target branch: {target_ref}")
    
    # Get the diff between branches
    if pr_data.get('lastMergeSourceCommit') and pr_data.get('lastMergeTargetCommit'):
        source_commit = pr_data['lastMergeSourceCommit']['commitId']
        target_commit = pr_data['lastMergeTargetCommit']['commitId']
        
        print(f"\nComparing commits:")
        print(f"  Source: {source_commit[:8]}")
        print(f"  Target: {target_commit[:8]}")
        
        # Get specific file diff
        file_path = "/ZinniaInternal.Businesslogic/WWL/Questionnaires.cs"
        
        # Try to get file from source
        source_file_url = f"{base_url}/git/repositories/{repo_name}/items?path={file_path}&version={source_commit}&api-version=7.0&includeContent=true"
        source_response = requests.get(source_file_url, headers=headers)
        
        # Try to get file from target
        target_file_url = f"{base_url}/git/repositories/{repo_name}/items?path={file_path}&version={target_commit}&api-version=7.0&includeContent=true"
        target_response = requests.get(target_file_url, headers=headers)
        
        if source_response.status_code == 200 and target_response.status_code == 200:
            source_content = source_response.json().get('content', '')
            target_content = target_response.json().get('content', '')
            
            # Decode base64 content if needed
            if source_content and target_content:
                try:
                    source_lines = b64.b64decode(source_content).decode('utf-8').split('\n')
                    target_lines = b64.b64decode(target_content).decode('utf-8').split('\n')
                    
                    # Find differences
                    print("\n4. ACTUAL CODE CHANGES FOUND:")
                    print("-" * 50)
                    
                    # Simple diff - show lines that changed
                    import difflib
                    diff = difflib.unified_diff(
                        target_lines, 
                        source_lines, 
                        fromfile='target/Questionnaires.cs',
                        tofile='source/Questionnaires.cs',
                        lineterm='',
                        n=3
                    )
                    
                    diff_lines = list(diff)
                    if diff_lines:
                        for line in diff_lines[:100]:  # Show first 100 lines of diff
                            print(line)
                    else:
                        print("No differences found between source and target")
                        
                except Exception as e:
                    print(f"Error decoding content: {e}")
        else:
            print(f"\nCould not fetch file content:")
            print(f"  Source response: {source_response.status_code}")
            print(f"  Target response: {target_response.status_code}")

if __name__ == "__main__":
    get_pr_diff()