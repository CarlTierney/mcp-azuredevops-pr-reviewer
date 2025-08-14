"""
Repository Cloner and Code Access
Provides capabilities to clone repos and access the full codebase for analysis
"""

import os
import sys
import subprocess
import shutil
import tempfile
from typing import Optional, Dict, List, Any
from pathlib import Path
import json


class RepoCloner:
    """Manages repository cloning and code access"""
    
    def __init__(self, base_analyzer, workspace_dir=None):
        self.analyzer = base_analyzer
        
        # Use provided workspace or default to D:\dev\prreview
        if workspace_dir:
            self.workspace_dir = workspace_dir
        else:
            # Default to D:\dev\prreview for PR review workspace
            self.workspace_dir = r"D:\dev\prreview"
        
        self.repo_path = None
        self.current_branch = None
        
        # Ensure workspace directory exists
        try:
            os.makedirs(self.workspace_dir, exist_ok=True)
            print(f"[INFO] Using workspace directory: {self.workspace_dir}")
        except Exception as e:
            # Fallback to temp directory if can't create the preferred one
            self.workspace_dir = os.path.join(tempfile.gettempdir(), "pr_review_workspace")
            os.makedirs(self.workspace_dir, exist_ok=True)
            print(f"[INFO] Using fallback workspace: {self.workspace_dir}")
        
        # Build clone URL with authentication
        self.clone_url = self._build_clone_url()
    
    def _build_clone_url(self) -> str:
        """Build authenticated clone URL for Azure DevOps"""
        # Format: https://PAT@dev.azure.com/org/project/_git/repo
        return f"https://{self.analyzer.pat_token}@dev.azure.com/{self.analyzer.org_name}/{self.analyzer.project_name}/_git/{self.analyzer.repo_name}"
    
    def _clean_workspace(self):
        """Clean the entire workspace directory to ensure no git conflicts"""
        print(f"[CLEAN] Cleaning workspace directory: {self.workspace_dir}")
        
        try:
            # List all items in workspace
            if os.path.exists(self.workspace_dir):
                items = os.listdir(self.workspace_dir)
                
                for item in items:
                    item_path = os.path.join(self.workspace_dir, item)
                    
                    # Skip cache directory if configured to keep it
                    if item == '.cache':
                        continue
                    
                    try:
                        if os.path.isdir(item_path):
                            print(f"  Removing directory: {item}")
                            if sys.platform == 'win32':
                                # Use Windows rmdir for better handling of git repos
                                subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', item_path], 
                                             capture_output=True, timeout=30)
                            else:
                                shutil.rmtree(item_path, ignore_errors=True)
                        else:
                            print(f"  Removing file: {item}")
                            os.remove(item_path)
                    except Exception as e:
                        print(f"  [WARNING] Could not remove {item}: {e}")
                
                print("[OK] Workspace cleaned")
            else:
                print("[INFO] Workspace directory doesn't exist, creating it")
                os.makedirs(self.workspace_dir, exist_ok=True)
                
        except Exception as e:
            print(f"[ERROR] Failed to clean workspace: {e}")
    
    def clone_repository(self, branch: Optional[str] = None, shallow: bool = False, force_clean: bool = True) -> bool:
        """Clone the repository to local workspace
        
        Args:
            branch: Specific branch to clone
            shallow: Whether to do a shallow clone (depth=1)
            force_clean: Always clean workspace before cloning (default: True)
        """
        print(f"\n[CLONE] Cloning repository {self.analyzer.repo_name}...")
        
        # Clean workspace if requested or if switching repos
        if force_clean:
            self._clean_workspace()
        
        # Set repo path
        self.repo_path = os.path.join(self.workspace_dir, self.analyzer.repo_name)
        
        # Remove existing repo if it exists (extra safety)
        if os.path.exists(self.repo_path):
            print(f"[INFO] Removing existing repository at {self.repo_path}")
            try:
                # Use more aggressive removal on Windows
                if sys.platform == 'win32':
                    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', self.repo_path], 
                                 capture_output=True, timeout=30)
                else:
                    shutil.rmtree(self.repo_path, ignore_errors=True)
            except Exception as e:
                print(f"[WARNING] Could not fully remove old repo: {e}")
        
        try:
            # Build clone command
            clone_cmd = ["git", "clone"]
            
            if shallow:
                clone_cmd.extend(["--depth", "1"])
            
            if branch:
                clone_cmd.extend(["--branch", branch])
            
            clone_cmd.extend([self.clone_url, self.repo_path])
            
            # Hide the PAT token in output
            safe_cmd = clone_cmd.copy()
            safe_cmd[-2] = "https://***@dev.azure.com/..."
            print(f"[CMD] {' '.join(safe_cmd)}")
            
            # Execute clone
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                print(f"[ERROR] Clone failed: {result.stderr}")
                return False
            
            print(f"[OK] Repository cloned to {self.repo_path}")
            
            # Get current branch
            self.current_branch = self._get_current_branch()
            print(f"[INFO] Current branch: {self.current_branch}")
            
            return True
            
        except subprocess.TimeoutExpired:
            print("[ERROR] Clone operation timed out")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to clone repository: {e}")
            return False
    
    def checkout_branch(self, branch: str) -> bool:
        """Checkout a specific branch"""
        if not self.repo_path or not os.path.exists(self.repo_path):
            print("[ERROR] Repository not cloned")
            return False
        
        try:
            print(f"[CHECKOUT] Switching to branch {branch}...")
            
            # Fetch the branch if it's remote
            fetch_cmd = ["git", "fetch", "origin", f"{branch}:{branch}"]
            subprocess.run(fetch_cmd, cwd=self.repo_path, capture_output=True)
            
            # Checkout the branch
            checkout_cmd = ["git", "checkout", branch]
            result = subprocess.run(
                checkout_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"[ERROR] Checkout failed: {result.stderr}")
                return False
            
            self.current_branch = branch
            print(f"[OK] Checked out branch {branch}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to checkout branch: {e}")
            return False
    
    def fetch_pr_branches(self, pr_id: int) -> Dict[str, str]:
        """Fetch and checkout PR branches"""
        print(f"\n[FETCH] Fetching branches for PR #{pr_id}...")
        
        # Get PR details to find branches
        from analyzers.pr_fetcher import PRFetcher
        pr_fetcher = PRFetcher(self.analyzer)
        pr_data = pr_fetcher.fetch_pull_request(pr_id)
        
        if not pr_data:
            print(f"[ERROR] Could not fetch PR #{pr_id}")
            return {}
        
        source_branch = pr_data.get('sourceRefName', '').replace('refs/heads/', '')
        target_branch = pr_data.get('targetRefName', '').replace('refs/heads/', '')
        
        branches = {
            'source': source_branch,
            'target': target_branch
        }
        
        print(f"[INFO] PR branches - Source: {source_branch}, Target: {target_branch}")
        
        # Ensure we have both branches locally
        for branch_type, branch_name in branches.items():
            if branch_name:
                try:
                    fetch_cmd = ["git", "fetch", "origin", branch_name]
                    subprocess.run(fetch_cmd, cwd=self.repo_path, capture_output=True)
                    print(f"[OK] Fetched {branch_type} branch: {branch_name}")
                except:
                    print(f"[WARNING] Could not fetch {branch_type} branch: {branch_name}")
        
        return branches
    
    def get_diff(self, base_branch: str, compare_branch: str, file_path: Optional[str] = None) -> str:
        """Get diff between two branches"""
        if not self.repo_path:
            print("[ERROR] Repository not cloned")
            return ""
        
        try:
            print(f"\n[DIFF] Getting diff between {base_branch} and {compare_branch}")
            
            # Build diff command
            diff_cmd = ["git", "diff", f"{base_branch}...{compare_branch}"]
            
            if file_path:
                diff_cmd.append("--")
                diff_cmd.append(file_path)
                print(f"[INFO] Filtering diff to file: {file_path}")
            
            result = subprocess.run(
                diff_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"[ERROR] Diff failed: {result.stderr}")
                return ""
            
            diff_output = result.stdout
            
            # Parse diff statistics
            if diff_output:
                lines = diff_output.split('\n')
                additions = sum(1 for line in lines if line.startswith('+') and not line.startswith('+++'))
                deletions = sum(1 for line in lines if line.startswith('-') and not line.startswith('---'))
                print(f"[STATS] +{additions} additions, -{deletions} deletions")
            
            return diff_output
            
        except Exception as e:
            print(f"[ERROR] Failed to get diff: {e}")
            return ""
    
    def get_pr_diff(self, pr_id: int) -> Dict[str, Any]:
        """Get complete diff for a PR"""
        branches = self.fetch_pr_branches(pr_id)
        
        if not branches.get('source') or not branches.get('target'):
            print("[ERROR] Could not determine PR branches")
            return {}
        
        # Get the full diff
        full_diff = self.get_diff(branches['target'], branches['source'])
        
        # Parse changed files
        changed_files = self._parse_changed_files(full_diff)
        
        return {
            'pr_id': pr_id,
            'source_branch': branches['source'],
            'target_branch': branches['target'],
            'full_diff': full_diff,
            'changed_files': changed_files,
            'statistics': self._calculate_diff_stats(full_diff)
        }
    
    def find_test_files(self, changed_file: str) -> List[str]:
        """Find test files related to a changed file"""
        if not self.repo_path:
            return []
        
        test_files = []
        
        # Extract base name for the changed file
        file_name = os.path.basename(changed_file)
        base_name = os.path.splitext(file_name)[0]
        
        # Common test file patterns
        test_patterns = [
            f"*{base_name}Test*",
            f"*{base_name}Tests*",
            f"*Test{base_name}*",
            f"*{base_name}.test*",
            f"*{base_name}.spec*",
            f"*{base_name}_test*"
        ]
        
        print(f"\n[SEARCH] Looking for test files related to {file_name}...")
        
        # Search for test files
        for pattern in test_patterns:
            try:
                find_cmd = ["git", "ls-files", f"*{pattern}*"]
                result = subprocess.run(
                    find_cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    files = result.stdout.strip().split('\n')
                    test_files.extend([f for f in files if f])
            except:
                pass
        
        # Also search in common test directories
        test_dirs = ['test', 'tests', 'Test', 'Tests', 'spec', '__tests__']
        for test_dir in test_dirs:
            test_path = os.path.join(self.repo_path, test_dir)
            if os.path.exists(test_path):
                for root, dirs, files in os.walk(test_path):
                    for file in files:
                        if base_name.lower() in file.lower():
                            rel_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                            test_files.append(rel_path.replace('\\', '/'))
        
        # Remove duplicates
        test_files = list(set(test_files))
        
        if test_files:
            print(f"[OK] Found {len(test_files)} test file(s):")
            for test_file in test_files[:5]:  # Show first 5
                print(f"  - {test_file}")
        else:
            print(f"[WARNING] No test files found for {file_name}")
        
        return test_files
    
    def read_file(self, file_path: str, branch: Optional[str] = None) -> Optional[str]:
        """Read a file from the repository"""
        if not self.repo_path:
            print("[ERROR] Repository not cloned")
            return None
        
        try:
            if branch and branch != self.current_branch:
                # Read from specific branch using git show
                show_cmd = ["git", "show", f"{branch}:{file_path}"]
                result = subprocess.run(
                    show_cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return result.stdout
            else:
                # Read from working directory
                full_path = os.path.join(self.repo_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Failed to read file {file_path}: {e}")
            return None
    
    def search_codebase(self, pattern: str, file_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search the codebase for a pattern"""
        if not self.repo_path:
            return []
        
        try:
            print(f"\n[SEARCH] Searching for pattern: {pattern}")
            
            # Use git grep for fast searching
            grep_cmd = ["git", "grep", "-n", pattern]
            
            if file_filter:
                grep_cmd.extend(["--", file_filter])
            
            result = subprocess.run(
                grep_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            matches = []
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[:50]:  # Limit to first 50 matches
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        matches.append({
                            'file': parts[0],
                            'line': parts[1],
                            'content': parts[2].strip()
                        })
            
            print(f"[OK] Found {len(matches)} match(es)")
            return matches
            
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            return []
    
    def analyze_test_coverage(self, changed_files: List[str]) -> Dict[str, Any]:
        """Analyze test coverage for changed files"""
        coverage = {
            'files_with_tests': [],
            'files_without_tests': [],
            'test_files_found': [],
            'coverage_percentage': 0
        }
        
        for file in changed_files:
            test_files = self.find_test_files(file)
            
            if test_files:
                coverage['files_with_tests'].append(file)
                coverage['test_files_found'].extend(test_files)
            else:
                coverage['files_without_tests'].append(file)
        
        total_files = len(changed_files)
        if total_files > 0:
            coverage['coverage_percentage'] = (len(coverage['files_with_tests']) / total_files) * 100
        
        # Remove duplicates from test files
        coverage['test_files_found'] = list(set(coverage['test_files_found']))
        
        return coverage
    
    def _get_current_branch(self) -> Optional[str]:
        """Get the current branch name"""
        if not self.repo_path:
            return None
        
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
            return None
            
        except:
            return None
    
    def _parse_changed_files(self, diff: str) -> List[str]:
        """Parse changed files from diff output"""
        changed_files = []
        
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                # Extract file path from diff header
                parts = line.split()
                if len(parts) >= 3:
                    file_path = parts[2][2:] if parts[2].startswith('b/') else parts[2]
                    changed_files.append(file_path)
        
        return list(set(changed_files))
    
    def _calculate_diff_stats(self, diff: str) -> Dict[str, int]:
        """Calculate statistics from diff"""
        lines = diff.split('\n')
        
        stats = {
            'additions': 0,
            'deletions': 0,
            'files_changed': 0
        }
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                stats['additions'] += 1
            elif line.startswith('-') and not line.startswith('---'):
                stats['deletions'] += 1
            elif line.startswith('diff --git'):
                stats['files_changed'] += 1
        
        stats['total_changes'] = stats['additions'] + stats['deletions']
        
        return stats
    
    def cleanup(self):
        """Clean up cloned repository"""
        if self.repo_path and os.path.exists(self.repo_path):
            print(f"\n[CLEANUP] Removing repository at {self.repo_path}")
            try:
                shutil.rmtree(self.repo_path, ignore_errors=True)
                print("[OK] Repository cleaned up")
            except Exception as e:
                print(f"[WARNING] Cleanup failed: {e}")
        
        self.repo_path = None
        self.current_branch = None