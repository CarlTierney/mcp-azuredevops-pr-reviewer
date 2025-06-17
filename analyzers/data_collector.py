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
        
        print("✅ Comprehensive data collection complete!")
        print(f"📊 Final Summary:")
        print(f"  - Commits: {len(all_commits)}")
        print(f"  - Pull Requests: {len(all_prs)}")
        
        return repo_id

    def _collect_commits(self, repo_id):
        """Collect all commits"""
        print("Collecting ALL commits...")
        all_commits = []
        skip = 0
        batch_size = 1000
        
        while True:
            commits_url = f"{self.analyzer.api_base}/git/repositories/{repo_id}/commits"
            commits_params = {
                'searchCriteria.fromDate': self.analyzer.date_from,
                'searchCriteria.toDate': self.analyzer.date_to,
                '$top': batch_size,
                '$skip': skip,
                'api-version': '7.0'
            }
            
            commits_response = requests.get(commits_url, headers=self.analyzer.headers, params=commits_params)
            if commits_response.status_code != 200:
                print(f"Error fetching commits: {commits_response.status_code}")
                break
                
            batch_commits = commits_response.json().get('value', [])
            if not batch_commits:
                break
                
            all_commits.extend(batch_commits)
            skip += batch_size
            print(f"  Collected {len(all_commits)} commits so far...")
            
            if len(batch_commits) < batch_size:
                break
        
        with open(f"{self.analyzer.data_dir}/commits.json", 'w') as f:
            json.dump(all_commits, f, indent=2)
        print(f"  ✓ Total commits collected: {len(all_commits)}")
        
        return all_commits

    def _collect_pull_requests(self, repo_id):
        """Collect all pull requests"""
        print("Collecting ALL pull requests...")
        all_prs = []
        skip = 0
        batch_size = 1000
        
        while True:
            prs_url = f"{self.analyzer.api_base}/git/repositories/{repo_id}/pullrequests"
            prs_params = {
                'searchCriteria.status': 'all',
                '$top': batch_size,
                '$skip': skip,
                'api-version': '7.0'
            }
            
            prs_response = requests.get(prs_url, headers=self.analyzer.headers, params=prs_params)
            if prs_response.status_code != 200:
                print(f"Error fetching pull requests: {prs_response.status_code}")
                break
                
            batch_prs = prs_response.json().get('value', [])
            if not batch_prs:
                break
                
            all_prs.extend(batch_prs)
            skip += batch_size
            print(f"  Collected {len(all_prs)} pull requests so far...")
            
            if len(batch_prs) < batch_size:
                break
        
        with open(f"{self.analyzer.data_dir}/pull_requests.json", 'w') as f:
            json.dump(all_prs, f, indent=2)
        print(f"  ✓ Total pull requests collected: {len(all_prs)}")
        
        return all_prs

    def _collect_detailed_commits(self, repo_id, all_commits):
        """Collect detailed commit data"""
        print("Collecting detailed commit changes for ALL commits...")
        os.makedirs(f"{self.analyzer.data_dir}/detailed_commits", exist_ok=True)
        
        total_commits = len(all_commits)
        successful_commits = 0
        failed_commits = 0
        
        for i, commit in enumerate(all_commits):
            commit_id = commit['commitId']
            changes_url = f"{self.analyzer.api_base}/git/repositories/{repo_id}/commits/{commit_id}/changes"
            changes_params = {'api-version': '7.0'}
            
            try:
                changes_response = requests.get(changes_url, headers=self.analyzer.headers, params=changes_params)
                if changes_response.status_code == 200:
                    changes_data = changes_response.json()
                    
                    with open(f"{self.analyzer.data_dir}/detailed_commits/{commit_id}.json", 'w') as f:
                        json.dump(changes_data, f, indent=2)
                    successful_commits += 1
                else:
                    failed_commits += 1
                
                if (i + 1) % 50 == 0 or (i + 1) == total_commits:
                    progress_pct = ((i + 1) / total_commits) * 100
                    print(f"    Progress: {i + 1}/{total_commits} ({progress_pct:.1f}%) - Success: {successful_commits}, Failed: {failed_commits}")
                    
            except Exception as e:
                failed_commits += 1
        
        print(f"  ✓ Detailed commit processing complete:")
        print(f"    - Successfully processed: {successful_commits} commits")
        print(f"    - Failed to process: {failed_commits} commits")

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
            work_item_ids = list(work_item_ids)[:100]
            
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
            print(f"  ✓ Loaded {len(self.analyzer.commits)} commits (filtered by date)")
        else:
            self.analyzer.commits = []
            print("  ⚠️  No commits data found")
        
        # Load pull requests
        prs_file = f"{self.analyzer.data_dir}/pull_requests.json"
        if os.path.exists(prs_file):
            with open(prs_file, 'r') as f:
                self.analyzer.pull_requests = json.load(f)
            print(f"  ✓ Loaded {len(self.analyzer.pull_requests)} pull requests")
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
            print(f"  ✓ Loaded {len(self.analyzer.detailed_commits)} detailed commits")
        
        # Load work items
        work_items_file = f"{self.analyzer.data_dir}/work_items.json"
        if os.path.exists(work_items_file):
            with open(work_items_file, 'r') as f:
                self.analyzer.work_items = json.load(f)
            print(f"  ✓ Loaded {len(self.analyzer.work_items)} work items")
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
