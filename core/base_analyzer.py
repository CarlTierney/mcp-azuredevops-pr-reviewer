#!/usr/bin/env python3
"""
Base analyzer class with common functionality
"""

import os
import json
import base64
import requests
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict
import radon.complexity as radon_cc
import radon.raw as radon_raw

class BaseAnalyzer:
    def __init__(self, org_name, project_name, repo_name, pat_token, data_dir="./azdo_analytics", 
                 date_from=None, date_to=None):
        self.org_name = org_name
        self.project_name = project_name
        self.repo_name = repo_name
        self.pat_token = pat_token
        self.data_dir = data_dir
        self.api_base = f"https://dev.azure.com/{org_name}/{project_name}/_apis"
          # Global date filters - Use 3 months by default for faster analysis
        if date_from is None:
            self.date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00Z")
        else:
            if isinstance(date_from, str):
                self.date_from = date_from if date_from.endswith('Z') else f"{date_from}T00:00:00Z"
            else:
                self.date_from = date_from.strftime("%Y-%m-%dT00:00:00Z")
        
        if date_to is None:
            self.date_to = datetime.now().strftime("%Y-%m-%dT23:59:59Z")
        else:
            if isinstance(date_to, str):
                self.date_to = date_to if date_to.endswith('Z') else f"{date_to}T23:59:59Z"
            else:
                self.date_to = date_to.strftime("%Y-%m-%dT23:59:59Z")
        
        # Convert to datetime objects for filtering
        self.date_from_dt = datetime.fromisoformat(self.date_from.replace('Z', '+00:00'))
        self.date_to_dt = datetime.fromisoformat(self.date_to.replace('Z', '+00:00'))
        
        # Enhanced file type classifications
        self.code_extensions = {
            'csharp': ['.cs', '.vb', '.fs'],
            'csharp_project': ['.csproj', '.vbproj', '.fsproj', '.sln'],
            'dotnet_config': ['.config', '.settings', '.resx', '.xaml'],
            'sql': ['.sql', '.tsql'],
            'sql_server': ['.dacpac', '.bacpac', '.sqlproj'],
            'database': ['.mdf', '.ldf', '.bak'],
            'web_dotnet': ['.aspx', '.ascx', '.master', '.cshtml', '.vbhtml', '.razor'],
            'web_client': ['.html', '.css', '.scss', '.sass', '.less', '.js', '.ts', '.jsx', '.tsx'],
            'api_specs': ['.json', '.yaml', '.yml', '.xml', '.wsdl'],
            'test_csharp': ['.cs'],
            'config': ['.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.appsettings.json'],
            'docs': ['.md', '.rst', '.txt', '.doc', '.docx'],
            'scripts': ['.ps1', '.bat', '.cmd', '.sh'],
            'other': []
        }
        
        # Cache management
        self.cache_dir = os.path.join(data_dir, "cache")
        self.cache_info_file = os.path.join(self.cache_dir, "cache_info.json")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize data attributes
        self.commits = []
        self.pull_requests = []
        self.detailed_commits = {}
        self.work_items = []

    @property
    def headers(self):
        """HTTP headers for Azure DevOps API requests"""
        if not hasattr(self, '_headers'):
            token = base64.b64encode(f":{self.pat_token}".encode()).decode()
            self._headers = {
                'Authorization': f'Basic {token}',
                'Content-Type': 'application/json'
            }
        return self._headers

    def classify_file_type(self, filename):
        """Enhanced file classification for C#/SQL environments"""
        if not filename:
            return 'other'
            
        filename_lower = filename.lower()
        ext = os.path.splitext(filename_lower)[1]
        
        # Special handling for test files
        if any(test_indicator in filename_lower for test_indicator in ['test', 'tests', 'spec', 'specs', 'unittest']):
            if ext == '.cs':
                return 'test_csharp'
            elif ext == '.sql':
                return 'test_sql'
        
        # Special handling for appsettings files
        if 'appsettings' in filename_lower and ext == '.json':
            return 'dotnet_config'
            
        # Migration files
        if 'migration' in filename_lower and ext in ['.cs', '.sql']:
            return 'database_migration'
            
        # Check standard extensions
        for lang, extensions in self.code_extensions.items():
            if ext in extensions:
                return lang
                
        return 'other'

    def analyze_file_contents(self, content):
        """Analyze file contents for metrics like LOC and complexity"""
        if not content or not isinstance(content, str):
            return {
                'loc': 0, 'sloc': 0, 'lloc': 0, 'comments': 0, 'multi': 0, 'blank': 0
            }
        
        # Skip binary content or files that are too large
        if len(content) > 1_000_000:  # Skip files larger than 1MB
            return self._fallback_analysis(content)
        
        # Check for binary content (contains null bytes or too many non-printable characters)
        if '\x00' in content or self._is_likely_binary(content):
            return self._fallback_analysis(content)
        
        # Check if content looks like valid text/code
        if not self._is_valid_text_content(content):
            return self._fallback_analysis(content)
        
        try:
            # Timeout protection - use radon with error handling
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("File analysis timed out")
            
            # Set a 5-second timeout for analysis
            if hasattr(signal, 'SIGALRM'):  # Unix/Linux only
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)
            
            try:
                raw_metrics = radon_raw.analyze(content)
                return {
                    'loc': raw_metrics.loc,
                    'sloc': raw_metrics.sloc,
                    'lloc': raw_metrics.lloc,
                    'comments': raw_metrics.comments,
                    'multi': raw_metrics.multi,
                    'blank': raw_metrics.blank
                }
            finally:
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)  # Cancel the alarm
                    
        except (Exception, TimeoutError) as e:            # If radon fails or times out, fall back to simple line counting
            error_type = type(e).__name__
            if error_type not in ['SyntaxError', 'TimeoutError', 'TokenError', 'IndentationError']:
                print(f"    Warning: Radon analysis failed with {error_type}, using fallback method")
            return self._fallback_analysis(content)
    
    def _is_valid_text_content(self, content):
        """Check if content appears to be valid text that can be analyzed"""
        if not content or len(content.strip()) == 0:
            return False
        
        # Check for binary content first
        if self._is_likely_binary(content):
            return False
        
        # Sample first 1KB for performance
        sample = content[:1024]
        
        # Check for common patterns that indicate non-analyzable content
        problematic_patterns = [
            # Base64 encoded content
            lambda s: len(s) > 100 and s.replace('\n', '').replace('\r', '').replace(' ', '').isalnum() and '=' in s[-10:],
            # Hexadecimal dumps
            lambda s: len([c for c in s[:200] if c in '0123456789abcdefABCDEF \n\r']) / len(s[:200]) > 0.8,
            # Long lines without breaks (minified files)
            lambda s: any(len(line) > 1000 for line in s.split('\n')[:5]),
            # Too many special characters
            lambda s: len([c for c in s[:200] if not c.isalnum() and c not in ' \n\r\t.,;:!?()[]{}"\'-_=+/*']) / len(s[:200]) > 0.5        ]
        
        return not any(pattern(sample) for pattern in problematic_patterns)
    
    def _is_likely_binary(self, content):
        """Check if content is likely binary by examining character distribution"""
        if not content:
            return False
        
        # Sample first 8KB for performance
        sample = content[:8192]
        
        # Check for null bytes (strong indicator of binary content)
        if '\x00' in sample:
            return True
        
        # Count non-printable characters (excluding common whitespace)
        non_printable = sum(1 for c in sample if ord(c) < 32 and c not in '\t\n\r\f\v')
        
        # If more than 30% non-printable, likely binary
        return (non_printable / len(sample)) > 0.3

    def _fallback_analysis(self, content):
        """Fallback analysis method using simple line counting"""
        try:
            lines = content.splitlines()
            total_lines = len(lines)
            
            # Count non-blank lines
            non_blank_lines = 0
            comment_lines = 0
            
            # Common comment patterns for different languages
            comment_patterns = [
                ('#',),  # Python, Shell, Ruby
                ('//', '/*', '*/', '*'),  # C/C++, Java, JavaScript, C#
                ('--',),  # SQL, Haskell
                ("'", 'REM'),  # VB, Batch
                ('<!--', '-->'),  # HTML, XML
                (';',),  # Assembly, Lisp
                ('%',),  # MATLAB, LaTeX
            ]
            
            for line in lines:
                stripped = line.strip()
                if stripped:
                    non_blank_lines += 1
                    
                    # Check if line appears to be a comment
                    for patterns in comment_patterns:
                        if any(stripped.startswith(pattern) for pattern in patterns):
                            comment_lines += 1
                            break
            
            blank_lines = total_lines - non_blank_lines
            
            return {
                'loc': total_lines,
                'sloc': non_blank_lines,
                'lloc': max(non_blank_lines - comment_lines, 0),  # Logical lines (non-comment, non-blank)
                'comments': comment_lines,
                'multi': 0,  # Can't detect multi-line in fallback
                'blank': blank_lines
            }
        except Exception:
            # Ultimate fallback - return zeros
            return {
                'loc': 0, 'sloc': 0, 'lloc': 0, 'comments': 0, 'multi': 0, 'blank': 0
            }

    def calculate_cyclomatic_complexity(self, code, filename):
        """Calculate cyclomatic complexity for code snippet with timeout protection"""
        if not code or not isinstance(code, str):
            return 1
            
        ext = os.path.splitext(filename.lower())[1] if filename else ''
        
        # Only analyze files with known code extensions
        code_extensions = ['.cs', '.vb', '.fs', '.py', '.js', '.ts', '.jsx', '.tsx', 
                          '.java', '.cpp', '.c', '.h', '.hpp', '.cc', '.cxx']
        if ext not in code_extensions:
            return 1
        
        # Skip binary or very large files
        if len(code) > 500_000 or self._is_likely_binary(code) or not self._is_valid_text_content(code):
            return 1
            
        try:
            # Timeout protection
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Complexity analysis timed out")
            
            if hasattr(signal, 'SIGALRM'):  # Unix/Linux only
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(3)  # 3-second timeout for complexity analysis
            
            try:
                results = radon_cc.cc_visit(code)
                if results:
                    complexities = [item.complexity for item in results]
                    return sum(complexities) / len(complexities)
                else:
                    return 1
            finally:
                if hasattr(signal, 'SIGALRM'):
                    signal.alarm(0)
                    
        except (Exception, TimeoutError) as e:
            # Don't log syntax errors for non-Python files being analyzed by radon
            error_type = type(e).__name__
            if error_type not in ['SyntaxError', 'TimeoutError', 'TokenError', 'IndentationError']:
                print(f"    Warning: Complexity analysis failed with {error_type}")
            return 1

    def get_author_info(self, author_data):
        """Extract standardized author information"""
        if not author_data:
            return {'display_name': 'Unknown', 'unique_name': 'unknown@unknown.com', 'email': 'unknown@unknown.com'}
        
        display_name = author_data.get('name', 'Unknown')
        email = author_data.get('email', 'unknown@unknown.com')
        unique_name = email
        
        return {
            'display_name': display_name,
            'unique_name': unique_name,
            'email': email
        }

    def fetch_file_content(self, repo_id, commit_id, file_path):
        """Fetch file content from a specific commit with validation"""
        if not file_path:
            return None
        
        # Skip certain file types that are likely to be binary or problematic
        problematic_extensions = [
            '.exe', '.dll', '.bin', '.so', '.dylib', '.a', '.lib',  # Binaries
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',  # Images
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Documents
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',  # Archives
            '.mp3', '.mp4', '.wav', '.avi', '.mov', '.wmv',  # Media
            '.ttf', '.otf', '.woff', '.woff2',  # Fonts
            '.min.js', '.min.css',  # Minified files
            '.lock', '.log', '.tmp', '.temp',  # Lock/log files
            '.cache', '.bak', '.swp', '.swo'  # Cache/backup files
        ]
        
        file_ext = os.path.splitext(file_path.lower())[1]
        if file_ext in problematic_extensions:
            return None
        
        # Skip files with problematic name patterns
        filename = os.path.basename(file_path).lower()
        problematic_patterns = [
            'vendor/', 'node_modules/', 'packages/', 'libs/', 'third-party/',
            'generated', 'auto-generated', 'autogenerated',
            '.designer.', '.generated.',
            'migration', 'migrations'  # Database migrations often have syntax issues
        ]
        
        if any(pattern in file_path.lower() for pattern in problematic_patterns):
            return None
            
        url = f"{self.api_base}/git/repositories/{repo_id}/items"
        params = {
            'path': file_path,
            'versionType': 'commit',
            'version': commit_id,
            'includeContent': True,
            'api-version': '7.0'
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                content = response.text
                
                # Validate content before returning
                if len(content) > 2_000_000:  # Skip files larger than 2MB
                    return None
                
                # Quick validation - if content looks like it might cause issues, skip it
                if not self._is_valid_text_content(content):
                    return None
                
                return content
            else:
                return None
        except Exception as e:
            # Only log unexpected errors, not common ones
            error_type = type(e).__name__
            if error_type not in ['Timeout', 'ConnectionError', 'HTTPError']:
                print(f"    Warning: Failed to fetch {file_path}: {error_type}")
            return None

    def get_repository_id(self):
        """Get the repository ID from the repository name with better error handling"""
        url = f"{self.api_base}/git/repositories?api-version=7.0"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"\n[ERROR] Network error while fetching repository list: {e}")
            print("\nTroubleshooting:")
            print("  1. Check your internet connection")
            print("  2. Verify Azure DevOps is accessible")
            print(f"  3. Try accessing: https://dev.azure.com/{self.org_name}")
            return None
        
        if response.status_code == 401:
            print(f"\n[ERROR] Authentication failed (401)")
            print("\nTroubleshooting:")
            print("  1. Verify your PAT token is valid and not expired")
            print("  2. Ensure PAT has 'Code (read)' permission")
            print("  3. Regenerate PAT token if needed at:")
            print(f"     https://dev.azure.com/{self.org_name}/_usersSettings/tokens")
            return None
        elif response.status_code == 404:
            print(f"\n[ERROR] Project not found (404)")
            print(f"  Organization: {self.org_name}")
            print(f"  Project: {self.project_name}")
            print("\nPlease verify the organization and project names are correct.")
            return None
        elif response.status_code != 200:
            print(f"\n[ERROR] Failed to get repositories: HTTP {response.status_code}")
            print(f"  Response: {response.text[:500] if response.text else 'No response body'}")
            return None
        
        try:
            repos = response.json().get('value', [])
        except json.JSONDecodeError:
            print(f"\n[ERROR] Invalid JSON response from Azure DevOps")
            return None
        
        if not repos:
            print(f"\n[WARNING] No repositories found in project '{self.project_name}'")
            print("  This project may not have any repositories.")
            return None
        
        # Look for exact match first
        for repo in repos:
            if repo.get('name') == self.repo_name:
                print(f"[OK] Found repository: {self.repo_name} (ID: {repo['id']})")
                return repo['id']
        
        # If no exact match, show available repositories
        print(f"\n[ERROR] Repository '{self.repo_name}' not found in project '{self.project_name}'")
        print("\nAvailable repositories:")
        for repo in repos[:10]:  # Show first 10
            print(f"  • {repo.get('name', 'Unknown')}")
        if len(repos) > 10:
            print(f"  ... and {len(repos) - 10} more")
        print("\nPlease check the repository name and try again.")
        return None

    def calculate_data_hash(self):
        """Calculate a hash of the current data to detect changes"""
        try:
            # Create a hash based on key data characteristics
            hash_data = {
                'commits_count': len(self.commits),
                'detailed_commits_count': len(self.detailed_commits),
                'pull_requests_count': len(self.pull_requests),
                'date_from': self.date_from,
                'date_to': self.date_to,
                'org_name': self.org_name,
                'project_name': self.project_name,
                'repo_name': self.repo_name
            }
            
            # Add commit IDs hash for detailed change detection
            if self.commits:
                commit_ids = sorted([c.get('commitId', '') for c in self.commits])
                hash_data['commit_ids_hash'] = hashlib.md5(''.join(commit_ids).encode()).hexdigest()
            
            # Add detailed commits hash
            if self.detailed_commits:
                detailed_keys = sorted(self.detailed_commits.keys())
                hash_data['detailed_commits_hash'] = hashlib.md5(''.join(detailed_keys).encode()).hexdigest()
            
            # Create final hash
            hash_string = json.dumps(hash_data, sort_keys=True)
            return hashlib.md5(hash_string.encode()).hexdigest()
        
        except Exception as e:
            print(f"Warning: Could not calculate data hash: {e}")
            return None

    def load_cache_info(self):
        """Load cache information from previous runs"""
        try:
            if os.path.exists(self.cache_info_file):
                with open(self.cache_info_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load cache info: {e}")
        return {}

    def save_cache_info(self, cache_info):
        """Save cache information for future runs"""
        try:
            with open(self.cache_info_file, 'w') as f:
                json.dump(cache_info, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache info: {e}")

    def is_analysis_cached(self, analysis_name):
        """Check if analysis results are cached and still valid"""
        cache_info = self.load_cache_info()
        current_hash = self.calculate_data_hash()
        
        if not current_hash:
            return False
        
        analysis_info = cache_info.get(analysis_name, {})
        cached_hash = analysis_info.get('data_hash')
        cached_file = analysis_info.get('output_file')
        
        # Check if hash matches and output file exists
        if cached_hash == current_hash and cached_file and os.path.exists(cached_file):
            cached_time = analysis_info.get('timestamp', '')
            print(f"  [OK] Using cached results for {analysis_name} (generated: {cached_time})")
            return True
        
        return False

    def mark_analysis_cached(self, analysis_name, output_file):
        """Mark an analysis as cached with current data hash"""
        cache_info = self.load_cache_info()
        current_hash = self.calculate_data_hash()
        
        if current_hash:
            cache_info[analysis_name] = {
                'data_hash': current_hash,
                'output_file': output_file,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.save_cache_info(cache_info)

    def get_cached_dataframe(self, analysis_name):
        """Load cached DataFrame if available"""
        cache_info = self.load_cache_info()
        analysis_info = cache_info.get(analysis_name, {})
        cached_file = analysis_info.get('output_file')
        
        if cached_file and os.path.exists(cached_file):
            try:
                return pd.read_csv(cached_file)
            except Exception as e:
                print(f"Warning: Could not load cached file {cached_file}: {e}")
        
        return None
