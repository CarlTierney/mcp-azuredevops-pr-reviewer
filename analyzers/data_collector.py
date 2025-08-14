"""
Data collection from Azure DevOps APIs
"""

import os
import json
import requests
import re
import sys
from datetime import datetime

# Ensure we can import from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class DataCollector:
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer

    def collect_all_data(self):
        """Collect all data from Azure DevOps APIs without any limits"""
        print("Starting comprehensive data collection from Azure DevOps...")
        
        repo_id = self.analyzer.get_repository_id()
        print(f"Repository ID: {repo_id}")
        print(f"Collecting data from {self.analyzer.date_from} to {self.analyzer.date_to}")
        
        # Create data directory
        os.makedirs(self.analyzer.data_dir, exist_ok=True)
        
        # Collect ALL commits
        all_commits = self._collect_commits(repo_id)
        
        # Collect ALL pull requests
        all_prs = self._collect_pull_requests(repo_id)
        
        # Collect detailed commit data
        self._collect_detailed_commits(repo_id, all_commits)
        
        # Collect work items
        self._collect_work_items()
        
        print("[OK] Comprehensive data collection complete!")
        print(f"[STATS] Final Summary:")
        print(f"  - Commits: {len(all_commits)}")
        print(f"  - Pull Requests: {len(all_prs)}")
        
        return repo_id

    def _collect_commits(self, repo_id):
        """Collect all commits with retry logic and better error handling"""
        print("Collecting ALL commits from all branches...")
        all_commits = []
        commit_ids_seen = set()  # Track unique commits across branches
        
        # Collect from multiple branches - adjust this list based on your needs
        branches_to_check = ['main', 'master', 'develop', 'development']
        
        for branch in branches_to_check:
            print(f"  Checking branch: {branch}")
            skip = 0
            batch_size = 1000
            max_retries = 3
            branch_commits = []
            
            while True:
                commits_url = f"{self.analyzer.api_base}/git/repositories/{repo_id}/commits"
                commits_params = {
                    'searchCriteria.fromDate': self.analyzer.date_from,
                    'searchCriteria.toDate': self.analyzer.date_to,
                    'searchCriteria.itemVersion.version': branch,
                    'searchCriteria.itemVersion.versionType': 'branch',
                    '$top': batch_size,
                    '$skip': skip,
                    'api-version': '7.0'
                }
                
                # Retry logic for API calls
                for retry in range(max_retries):
                    try:
                        commits_response = requests.get(commits_url, headers=self.analyzer.headers, params=commits_params, timeout=30)
                        if commits_response.status_code == 200:
                            break
                        elif commits_response.status_code == 404:
                            # Branch doesn't exist, skip it
                            print(f"    Branch '{branch}' not found, skipping...")
                            break
                        elif commits_response.status_code == 429:  # Rate limited
                            wait_time = min(2 ** retry * 5, 30)
                            print(f"    Rate limited. Waiting {wait_time} seconds...")
                            import time
                            time.sleep(wait_time)
                        else:
                            if retry < max_retries - 1:
                                print(f"    Retrying ({retry + 1}/{max_retries})...")
                                import time
                                time.sleep(2)
                    except requests.exceptions.RequestException as e:
                        if retry < max_retries - 1:
                            print(f"    Retrying ({retry + 1}/{max_retries})...")
                            import time
                            time.sleep(5)
                        else:
                            print(f"    Failed after {max_retries} attempts")
                            break
                
                if commits_response.status_code == 404:
                    break  # Branch doesn't exist, move to next branch
                    
                if commits_response.status_code != 200:
                    print(f"    [WARNING] Could not fetch commits from branch {branch}")
                    break
                    
                try:
                    batch_commits = commits_response.json().get('value', [])
                except json.JSONDecodeError:
                    print(f"    [WARNING] Invalid JSON response")
                    break
                    
                if not batch_commits:
                    break
                
                # Add only unique commits
                for commit in batch_commits:
                    commit_id = commit.get('commitId')
                    if commit_id and commit_id not in commit_ids_seen:
                        commit_ids_seen.add(commit_id)
                        all_commits.append(commit)
                        branch_commits.append(commit)
                
                skip += batch_size
                print(f"    Found {len(branch_commits)} commits in {branch} (total unique: {len(all_commits)})")
                
                if len(batch_commits) < batch_size:
                    break
            
            print(f"  Branch {branch}: {len(branch_commits)} commits")
        
        # Ensure data directory exists
        os.makedirs(self.analyzer.data_dir, exist_ok=True)
        
        # Save with validation
        if all_commits:
            try:
                with open(f"{self.analyzer.data_dir}/commits.json", 'w') as f:
                    json.dump(all_commits, f, indent=2)
                print(f"  [OK] Total commits collected and saved: {len(all_commits)}")
            except Exception as e:
                print(f"  [ERROR] Error saving commits: {e}")
        else:
            print("  [WARNING] No commits collected")
        
        return all_commits

    def _collect_pull_requests(self, repo_id):
        """Collect all pull requests with retry logic and better error handling"""
        print("Collecting ALL pull requests...")
        all_prs = []
        skip = 0
        batch_size = 1000
        max_retries = 3
        
        while True:
            prs_url = f"{self.analyzer.api_base}/git/repositories/{repo_id}/pullrequests"
            prs_params = {
                'searchCriteria.status': 'all',
                'searchCriteria.includeLinks': 'true',  # Include branch information
                '$top': batch_size,
                '$skip': skip,
                'api-version': '7.0'
            }
            
            # Retry logic for API calls
            for retry in range(max_retries):
                try:
                    prs_response = requests.get(prs_url, headers=self.analyzer.headers, params=prs_params, timeout=30)
                    if prs_response.status_code == 200:
                        break
                    elif prs_response.status_code == 429:  # Rate limited
                        wait_time = min(2 ** retry * 5, 30)
                        print(f"  Rate limited. Waiting {wait_time} seconds...")
                        import time
                        time.sleep(wait_time)
                    else:
                        print(f"  Error fetching pull requests: {prs_response.status_code}")
                        if retry < max_retries - 1:
                            print(f"  Retrying ({retry + 1}/{max_retries})...")
                            import time
                            time.sleep(2)
                except requests.exceptions.RequestException as e:
                    print(f"  Network error: {e}")
                    if retry < max_retries - 1:
                        print(f"  Retrying ({retry + 1}/{max_retries})...")
                        import time
                        time.sleep(5)
                    else:
                        print(f"  Failed after {max_retries} attempts")
                        break
            
            if prs_response.status_code != 200:
                print(f"  [WARNING] Could not fetch PRs batch at offset {skip}")
                break
                
            try:
                batch_prs = prs_response.json().get('value', [])
            except json.JSONDecodeError:
                print(f"  [WARNING] Invalid JSON response at offset {skip}")
                break
                
            if not batch_prs:
                break
                
            all_prs.extend(batch_prs)
            skip += batch_size
            print(f"  Collected {len(all_prs)} pull requests so far...")
            
            if len(batch_prs) < batch_size:
                break
        
        # Ensure data directory exists
        os.makedirs(self.analyzer.data_dir, exist_ok=True)
        
        # Save with validation
        try:
            with open(f"{self.analyzer.data_dir}/pull_requests.json", 'w') as f:
                json.dump(all_prs, f, indent=2)
            print(f"  [OK] Total pull requests collected and saved: {len(all_prs)}")
        except Exception as e:
            print(f"  [ERROR] Error saving pull requests: {e}")
        
        return all_prs

    def _collect_detailed_commits(self, repo_id, commits):
        """Collect detailed commit information including file changes"""
        if not commits:
            print("  No commits to process for detailed information")
            return
            
        print(f"[FILES] Collecting detailed changes for {len(commits)} commits...")
        
        # Ensure detailed_commits directory exists
        detailed_dir = f"{self.analyzer.data_dir}/detailed_commits"
        os.makedirs(detailed_dir, exist_ok=True)
        
        # Check for existing detailed commits to avoid re-fetching
        existing_commits = set()
        if os.path.exists(detailed_dir):
            existing_commits = {f[:-5] for f in os.listdir(detailed_dir) if f.endswith('.json')}
            if existing_commits:
                print(f"  Found {len(existing_commits)} existing detailed commits")
        
        # Add time tracking
        import time
        start_time = time.time()
        last_progress_time = start_time
        elapsed = 0  # Initialize elapsed variable
        max_retries = 3
        failed_commits = []
        
        for i, commit in enumerate(commits):
            current_time = time.time()
            elapsed = current_time - start_time  # Update elapsed time
            
            if i % 50 == 0 or (current_time - last_progress_time) > 30:
                progress_pct = (i / len(commits)) * 100
                commits_per_sec = i / max(elapsed, 1)
                eta_seconds = (len(commits) - i) / max(commits_per_sec, 0.1)
                
                print(f"    Detailed commits: {i:,}/{len(commits):,} ({progress_pct:.1f}%)")
                print(f"      Speed: {commits_per_sec:.1f} commits/sec | ETA: {eta_seconds/60:.1f} minutes")
                last_progress_time = current_time
            
            # Log current processing status for visibility
            if i % 100 == 0:
                current_commit_short = commit['commitId'][:8] if commit.get('commitId') else "unknown"
                print(f"    [LOCATION] Currently processing detailed commit: {current_commit_short} ({i}/{len(commits)})")

            commit_id = commit.get('commitId')
            if not commit_id:
                print(f"  [WARNING] Skipping commit with no ID at index {i}")
                continue
                
            # Skip if we already have this commit's details
            if commit_id in existing_commits:
                continue
                
            changes_url = f"{self.analyzer.api_base}/git/repositories/{repo_id}/commits/{commit_id}/changes"
            changes_params = {'api-version': '7.0'}
            
            # Retry logic for each commit
            success = False
            for retry in range(max_retries):
                try:
                    changes_response = requests.get(changes_url, headers=self.analyzer.headers, params=changes_params, timeout=30)
                    if changes_response.status_code == 200:
                        changes_data = changes_response.json()
                        
                        # Validate data before saving
                        if changes_data and 'changes' in changes_data:
                            output_file = f"{detailed_dir}/{commit_id}.json"
                            with open(output_file, 'w') as f:
                                json.dump(changes_data, f, indent=2)
                            success = True
                            break
                        else:
                            print(f"  [WARNING] Empty or invalid data for commit {commit_id[:8]}")
                    elif changes_response.status_code == 429:  # Rate limited
                        wait_time = min(2 ** retry * 5, 30)
                        print(f"  Rate limited on commit {commit_id[:8]}. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    elif changes_response.status_code == 404:
                        print(f"  [WARNING] Commit {commit_id[:8]} not found (404)")
                        break  # No point retrying a 404
                    else:
                        if retry < max_retries - 1:
                            time.sleep(2)
                        
                except requests.exceptions.RequestException as e:
                    if retry < max_retries - 1:
                        print(f"  Network error on commit {commit_id[:8]}, retrying...")
                        time.sleep(5)
                    else:
                        print(f"  [ERROR] Failed to fetch commit {commit_id[:8]} after {max_retries} attempts: {e}")
                except Exception as e:
                    print(f"  [ERROR] Unexpected error processing commit {commit_id[:8]}: {e}")
                    break
            
            if not success:
                failed_commits.append(commit_id)

        # Summary
        successful_count = len([f for f in os.listdir(detailed_dir) if f.endswith('.json')])
        print(f"  [OK] Detailed commit processing complete.")
        print(f"    Successfully processed: {successful_count}/{len(commits)}")
        if failed_commits:
            print(f"    Failed commits: {len(failed_commits)}")
            # Save failed commits list for potential retry
            with open(f"{self.analyzer.data_dir}/failed_commits.json", 'w') as f:
                json.dump(failed_commits, f, indent=2)

    def _collect_work_items(self):
        """Collect work items referenced in commits"""
        try:
            work_item_ids = set()
            with open(f"{self.analyzer.data_dir}/commits.json", 'r') as f:
                commits = json.load(f)
            
            work_item_pattern = r'#(\d+)'
            for commit in commits:
                comment = commit.get('comment', '')
                matches = re.findall(work_item_pattern, comment)
                work_item_ids.update(matches)
            
            if not work_item_ids:
                return []
            
            work_items = []
            work_item_ids = list(work_item_ids)  # Process all work items without artificial limits
            
            if work_item_ids:
                work_items_url = f"https://dev.azure.com/{self.analyzer.org_name}/_apis/wit/workitems"
                params = {'ids': ','.join(work_item_ids), 'api-version': '7.0'}
                
                response = requests.get(work_items_url, headers=self.analyzer.headers, params=params)
                if response.status_code == 200:
                    work_items = response.json().get('value', [])
                    
                    with open(f"{self.analyzer.data_dir}/work_items.json", 'w') as f:
                        json.dump(work_items, f, indent=2)
            
            return work_items
            
        except Exception as e:
            print(f"Error collecting work items: {e}")
            return []

    def load_collected_data(self):
        """Load all collected data from files"""
        print("Loading collected data...")
        
        os.makedirs(self.analyzer.data_dir, exist_ok=True)
        
        # Load commits
        commits_file = f"{self.analyzer.data_dir}/commits.json"
        if os.path.exists(commits_file):
            with open(commits_file, 'r') as f:
                self.analyzer.commits = json.load(f)
            self.analyzer.commits = self._filter_commits_by_date(self.analyzer.commits)
            print(f"  [OK] Loaded {len(self.analyzer.commits)} commits (filtered by date)")
        else:
            self.analyzer.commits = []
            print("  [WARNING]  No commits data found")
        
        # Load pull requests
        prs_file = f"{self.analyzer.data_dir}/pull_requests.json"
        if os.path.exists(prs_file):
            with open(prs_file, 'r') as f:
                self.analyzer.pull_requests = json.load(f)
            print(f"  [OK] Loaded {len(self.analyzer.pull_requests)} pull requests")
        else:
            self.analyzer.pull_requests = []
        
        # Load detailed commits
        detailed_commits_dir = f"{self.analyzer.data_dir}/detailed_commits"
        self.analyzer.detailed_commits = {}
        if os.path.exists(detailed_commits_dir):
            for file in os.listdir(detailed_commits_dir):
                if file.endswith('.json'):
                    commit_id = file[:-5]
                    try:
                        with open(os.path.join(detailed_commits_dir, file), 'r') as f:
                            self.analyzer.detailed_commits[commit_id] = json.load(f)
                    except Exception as e:
                        print(f"    Warning: Could not load {file}: {e}")
            print(f"  [OK] Loaded {len(self.analyzer.detailed_commits)} detailed commits")
        
        # Load work items
        work_items_file = f"{self.analyzer.data_dir}/work_items.json"
        if os.path.exists(work_items_file):
            with open(work_items_file, 'r') as f:
                self.analyzer.work_items = json.load(f)
            print(f"  [OK] Loaded {len(self.analyzer.work_items)} work items")
        else:
            self.analyzer.work_items = []

    def _filter_commits_by_date(self, commits):
        """Filter commits by the global date range"""
        filtered_commits = []
        
        for commit in commits:
            try:
                commit_date_str = commit.get('author', {}).get('date', '')
                if not commit_date_str:
                    continue
                    
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                
                if self.analyzer.date_from_dt <= commit_date <= self.analyzer.date_to_dt:
                    filtered_commits.append(commit)
                    
            except (ValueError, AttributeError, TypeError):
                continue
        
        return filtered_commits
