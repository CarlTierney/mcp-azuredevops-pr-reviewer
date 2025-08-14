"""
Pull Request Fetcher and Analyzer
Fetches and analyzes specific pull requests or all PRs from Azure DevOps
"""

import requests
import json
from datetime import datetime
import base64
from typing import Optional, List, Dict, Any


class PRFetcher:
    """Fetches and processes pull requests from Azure DevOps"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        self.base_url = f"https://dev.azure.com/{base_analyzer.org_name}/{base_analyzer.project_name}/_apis"
        self.headers = {
            'Authorization': f'Basic {base64.b64encode(f":{base_analyzer.pat_token}".encode()).decode()}',
            'Content-Type': 'application/json'
        }
    
    def fetch_pull_request(self, pr_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific pull request by ID"""
        print(f"\n[FETCH] Fetching Pull Request #{pr_id}...")
        
        try:
            # Get PR details
            pr_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}?api-version=7.0"
            response = requests.get(pr_url, headers=self.headers)
            response.raise_for_status()
            pr_data = response.json()
            
            # Get PR threads (comments and discussions)
            threads_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}/threads?api-version=7.0"
            threads_response = requests.get(threads_url, headers=self.headers)
            if threads_response.status_code == 200:
                pr_data['threads'] = threads_response.json().get('value', [])
            
            # Get PR work items
            workitems_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}/workitems?api-version=7.0"
            workitems_response = requests.get(workitems_url, headers=self.headers)
            if workitems_response.status_code == 200:
                pr_data['workItems'] = workitems_response.json().get('value', [])
            
            # Get PR commits
            commits_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}/commits?api-version=7.0"
            commits_response = requests.get(commits_url, headers=self.headers)
            if commits_response.status_code == 200:
                pr_data['commits'] = commits_response.json().get('value', [])
            
            # Get PR iterations (versions)
            iterations_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}/iterations?api-version=7.0"
            iterations_response = requests.get(iterations_url, headers=self.headers)
            if iterations_response.status_code == 200:
                pr_data['iterations'] = iterations_response.json().get('value', [])
            
            print(f"[OK] Successfully fetched PR #{pr_id}: {pr_data.get('title', 'No Title')}")
            return pr_data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"[ERROR] Pull Request #{pr_id} not found")
            else:
                print(f"[ERROR] Failed to fetch PR #{pr_id}: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error fetching PR #{pr_id}: {e}")
            return None
    
    def fetch_pull_requests(self, status: str = "all", top: int = 100, 
                           source_branch: Optional[str] = None,
                           target_branch: Optional[str] = None,
                           author: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch multiple pull requests with filters"""
        print(f"\n[FETCH] Fetching pull requests (status: {status}, limit: {top})...")
        
        try:
            # Build query parameters
            params = {
                "api-version": "7.0",
                "$top": top
            }
            
            # Add status filter
            if status != "all":
                status_map = {
                    "active": "active",
                    "completed": "completed",
                    "abandoned": "abandoned"
                }
                if status in status_map:
                    params["searchCriteria.status"] = status_map[status]
            
            # Add branch filters
            if source_branch:
                params["searchCriteria.sourceRefName"] = f"refs/heads/{source_branch}"
            if target_branch:
                params["searchCriteria.targetRefName"] = f"refs/heads/{target_branch}"
            
            # Add author filter
            if author:
                params["searchCriteria.creatorId"] = author
            
            # Make request
            pr_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests"
            response = requests.get(pr_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            prs = response.json().get('value', [])
            print(f"[OK] Fetched {len(prs)} pull requests")
            
            # Optionally fetch additional details for each PR
            for i, pr in enumerate(prs):
                pr_id = pr.get('pullRequestId')
                if pr_id:
                    print(f"  [{i+1}/{len(prs)}] PR #{pr_id}: {pr.get('title', 'No Title')[:60]}...")
            
            return prs
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch pull requests: {e}")
            return []
    
    def fetch_pr_changes(self, pr_id: int) -> List[Dict[str, Any]]:
        """Fetch file changes for a specific PR"""
        print(f"\n[FETCH] Fetching changes for PR #{pr_id}...")
        
        try:
            # Get PR iterations to find the latest changes
            iterations_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}/iterations?api-version=7.0"
            iterations_response = requests.get(iterations_url, headers=self.headers)
            
            if iterations_response.status_code != 200:
                print(f"[WARNING] Could not fetch iterations for PR #{pr_id}")
                return []
            
            iterations = iterations_response.json().get('value', [])
            if not iterations:
                print(f"[WARNING] No iterations found for PR #{pr_id}")
                return []
            
            # Get the latest iteration
            latest_iteration = iterations[-1]
            iteration_id = latest_iteration.get('id')
            
            # Get changes from the latest iteration
            changes_url = f"{self.base_url}/git/repositories/{self.analyzer.repo_name}/pullrequests/{pr_id}/iterations/{iteration_id}/changes?api-version=7.0&$top=500"
            changes_response = requests.get(changes_url, headers=self.headers)
            
            if changes_response.status_code != 200:
                print(f"[WARNING] Could not fetch changes for PR #{pr_id}")
                return []
            
            change_entries = changes_response.json().get('changeEntries', [])
            
            # Process changes
            file_changes = []
            for change in change_entries:
                item = change.get('item', {})
                if not item:
                    continue
                    
                file_path = item.get('path', '')
                change_type = change.get('changeType', '')
                
                # Skip non-file changes
                if change_type in ['none', 'all'] or not file_path:
                    continue
                
                file_change = {
                    'path': file_path,
                    'changeType': change_type,
                    'additions': 0,
                    'deletions': 0,
                    'isFolder': item.get('isFolder', False)
                }
                
                # Try to get content changes if available
                if 'originalPath' in change:
                    file_change['originalPath'] = change['originalPath']
                
                file_changes.append(file_change)
            
            print(f"[OK] Found {len(file_changes)} files changed in PR #{pr_id}")
            
            return file_changes
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch PR changes: {e}")
            return []
    
    def get_pr_statistics(self, pr_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a PR"""
        pr = self.fetch_pull_request(pr_id)
        if not pr:
            return {}
        
        stats = {
            'pr_id': pr_id,
            'title': pr.get('title', ''),
            'description': pr.get('description', ''),
            'status': pr.get('status', ''),
            'created_by': pr.get('createdBy', {}).get('displayName', 'Unknown'),
            'creation_date': pr.get('creationDate', ''),
            'closed_date': pr.get('closedDate', ''),
            'source_branch': pr.get('sourceRefName', '').replace('refs/heads/', ''),
            'target_branch': pr.get('targetRefName', '').replace('refs/heads/', ''),
            'merge_status': pr.get('mergeStatus', ''),
            'reviewers': [],
            'threads_count': len(pr.get('threads', [])),
            'comments_count': 0,
            'work_items': [],
            'commits_count': len(pr.get('commits', [])),
            'iterations_count': len(pr.get('iterations', [])),
            'files_changed': 0,
            'additions': 0,
            'deletions': 0
        }
        
        # Process reviewers
        for reviewer in pr.get('reviewers', []):
            stats['reviewers'].append({
                'name': reviewer.get('displayName', 'Unknown'),
                'vote': reviewer.get('vote', 0),
                'is_required': reviewer.get('isRequired', False)
            })
        
        # Count comments in threads
        for thread in pr.get('threads', []):
            stats['comments_count'] += len(thread.get('comments', []))
        
        # Process work items
        for work_item in pr.get('workItems', []):
            stats['work_items'].append({
                'id': work_item.get('id', ''),
                'title': work_item.get('title', ''),
                'type': work_item.get('workItemType', '')
            })
        
        # Get file change statistics
        changes = self.fetch_pr_changes(pr_id)
        stats['files_changed'] = len(changes)
        for change in changes:
            stats['additions'] += change.get('additions', 0)
            stats['deletions'] += change.get('deletions', 0)
        
        # Calculate duration
        if stats['creation_date'] and stats['closed_date']:
            created = datetime.fromisoformat(stats['creation_date'].replace('Z', '+00:00'))
            closed = datetime.fromisoformat(stats['closed_date'].replace('Z', '+00:00'))
            duration = closed - created
            stats['duration_hours'] = duration.total_seconds() / 3600
            stats['duration_days'] = duration.days
        else:
            stats['duration_hours'] = None
            stats['duration_days'] = None
        
        return stats
    
    def save_pr_data(self, pr_id: int, output_dir: Optional[str] = None):
        """Save PR data to JSON file"""
        if output_dir is None:
            output_dir = self.analyzer.data_dir
        
        pr_data = self.fetch_pull_request(pr_id)
        if not pr_data:
            return False
        
        # Add changes
        pr_data['file_changes'] = self.fetch_pr_changes(pr_id)
        
        # Add statistics
        pr_data['statistics'] = self.get_pr_statistics(pr_id)
        
        # Save to file
        output_file = f"{output_dir}/pr_{pr_id}_details.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(pr_data, f, indent=2, default=str)
        
        print(f"[OK] PR data saved to: {output_file}")
        return True