"""
Code Review Analyzer
Performs deep code analysis with access to full repository
"""

import re
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


import json

class CodeReviewAnalyzer:
    """Analyzes code changes with full repository context"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        
        # Load configuration if available
        self.config = self._load_config()
        
        # Initialize repo cloner with configured workspace
        from analyzers.repo_cloner import RepoCloner
        workspace_dir = self.config.get('workspace', {}).get('default_directory', r'D:\dev\prreview')
        self.repo_cloner = RepoCloner(base_analyzer, workspace_dir=workspace_dir)
        
        # Code quality patterns
        self.quality_patterns = {
            'security_risks': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'eval\s*\(',
                r'exec\s*\(',
                r'SELECT\s+\*\s+FROM',
                r'DELETE\s+FROM.*WHERE\s+1\s*=\s*1'
            ],
            'code_smells': [
                r'TODO|FIXME|HACK|XXX',
                r'catch\s*\(\s*Exception\s+',
                r'System\.out\.println',
                r'console\.(log|debug)',
                r'throw\s+new\s+Exception\(',
                r'magic\s+number'
            ],
            'performance_issues': [
                r'SELECT.*IN\s*\([^)]{100,}\)',  # Large IN clauses
                r'foreach.*foreach',  # Nested loops
                r'\.ToList\(\).*\.Count\(\)',  # Inefficient counting
                r'Thread\.Sleep\(',
                r'Task\.Delay\('
            ]
        }
    
    def review_pr_with_code(self, pr_id: int, clean_workspace: bool = True) -> Dict[str, Any]:
        """Perform comprehensive code review with full repository access
        
        Args:
            pr_id: Pull request ID to review
            clean_workspace: Whether to clean workspace before review (default: True)
        """
        print(f"\n[REVIEW] Starting comprehensive code review for PR #{pr_id}")
        
        review = {
            'pr_id': pr_id,
            'has_repo_access': False,
            'diff_analysis': {},
            'test_coverage': {},
            'code_quality': {},
            'security_analysis': {},
            'recommendations': []
        }
        
        try:
            # Always clone fresh to avoid git conflicts between different repos/PRs
            print("[CLONE] Cloning repository for analysis...")
            
            # Force clean is True by default in clone_repository
            if not self.repo_cloner.clone_repository(shallow=True, force_clean=clean_workspace):
                print("[WARNING] Could not clone repository, proceeding with limited analysis")
                return review
        
        review['has_repo_access'] = True
        
        # Get PR diff
        print(f"\n[DIFF] Analyzing PR #{pr_id} changes...")
        diff_data = self.repo_cloner.get_pr_diff(pr_id)
        
        if not diff_data:
            print("[ERROR] Could not get PR diff")
            return review
        
        # Analyze the diff
        review['diff_analysis'] = self._analyze_diff(diff_data)
        
        # Analyze test coverage
        print("\n[TESTS] Analyzing test coverage...")
        review['test_coverage'] = self._analyze_test_coverage(diff_data)
        
        # Analyze code quality
        print("\n[QUALITY] Analyzing code quality...")
        review['code_quality'] = self._analyze_code_quality(diff_data)
        
        # Security analysis
        print("\n[SECURITY] Analyzing security implications...")
        review['security_analysis'] = self._analyze_security(diff_data)
        
        # Generate recommendations
        review['recommendations'] = self._generate_code_recommendations(review)
        
        # Print summary
        self._print_code_review_summary(review)
        
        except Exception as e:
            print(f"[ERROR] Code review failed: {e}")
            review['error'] = str(e)
        
        finally:
            # Option to clean up after review (can be configured)
            if clean_workspace and self.config.get('workspace', {}).get('cleanup_after_review', False):
                print("[CLEANUP] Cleaning up workspace after review...")
                self.repo_cloner.cleanup()
        
        return review
    
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'pr_review_config.json')
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Could not load config: {e}")
        
        # Return default config
        return {
            'workspace': {
                'default_directory': r'D:\dev\prreview'
            }
        }
    
    def _analyze_diff(self, diff_data: Dict) -> Dict[str, Any]:
        """Analyze the actual code diff"""
        full_diff = diff_data.get('full_diff', '')
        changed_files = diff_data.get('changed_files', [])
        stats = diff_data.get('statistics', {})
        
        analysis = {
            'files_changed': len(changed_files),
            'lines_added': stats.get('additions', 0),
            'lines_deleted': stats.get('deletions', 0),
            'total_changes': stats.get('total_changes', 0),
            'changed_files': changed_files,
            'file_types': self._categorize_files(changed_files),
            'change_patterns': self._analyze_change_patterns(full_diff)
        }
        
        # Analyze each changed file
        file_analyses = []
        for file in changed_files[:10]:  # Analyze up to 10 files
            file_analysis = self._analyze_file_changes(file, full_diff)
            if file_analysis:
                file_analyses.append(file_analysis)
        
        analysis['file_analyses'] = file_analyses
        
        return analysis
    
    def _analyze_test_coverage(self, diff_data: Dict) -> Dict[str, Any]:
        """Analyze test coverage for changed files"""
        changed_files = diff_data.get('changed_files', [])
        
        # Use repo cloner to find test files
        coverage = self.repo_cloner.analyze_test_coverage(changed_files)
        
        # Analyze test content if test files exist
        if coverage['test_files_found']:
            print(f"[INFO] Found {len(coverage['test_files_found'])} test file(s)")
            
            # Check if tests were modified in this PR
            tests_modified = any(
                test_file in changed_files 
                for test_file in coverage['test_files_found']
            )
            
            coverage['tests_modified_in_pr'] = tests_modified
            
            if not tests_modified:
                coverage['recommendation'] = "No tests were modified - consider adding tests for the changes"
            else:
                coverage['recommendation'] = "Tests were updated with the changes"
        else:
            coverage['recommendation'] = "No test files found - tests should be added"
        
        # Calculate coverage score
        coverage['score'] = self._calculate_coverage_score(coverage)
        
        return coverage
    
    def _analyze_code_quality(self, diff_data: Dict) -> Dict[str, Any]:
        """Analyze code quality issues in the changes"""
        full_diff = diff_data.get('full_diff', '')
        
        quality = {
            'issues_found': [],
            'code_smells': [],
            'performance_concerns': [],
            'best_practices': []
        }
        
        # Check for quality patterns in diff
        diff_lines = full_diff.split('\n')
        
        for i, line in enumerate(diff_lines):
            # Only check added lines
            if not line.startswith('+'):
                continue
            
            # Check for code smells
            for pattern in self.quality_patterns['code_smells']:
                if re.search(pattern, line, re.IGNORECASE):
                    quality['code_smells'].append({
                        'line': i,
                        'pattern': pattern,
                        'content': line[1:].strip()[:100]
                    })
            
            # Check for performance issues
            for pattern in self.quality_patterns['performance_issues']:
                if re.search(pattern, line, re.IGNORECASE):
                    quality['performance_concerns'].append({
                        'line': i,
                        'pattern': pattern,
                        'content': line[1:].strip()[:100]
                    })
            
            # Check for common issues
            if len(line) > 120:  # Long lines
                quality['issues_found'].append({
                    'type': 'long_line',
                    'line': i,
                    'length': len(line)
                })
            
            if '\t' in line and '    ' in line:  # Mixed indentation
                quality['issues_found'].append({
                    'type': 'mixed_indentation',
                    'line': i
                })
        
        # Calculate quality score
        quality['score'] = self._calculate_quality_score(quality)
        
        return quality
    
    def _analyze_security(self, diff_data: Dict) -> Dict[str, Any]:
        """Analyze security implications of changes"""
        full_diff = diff_data.get('full_diff', '')
        
        security = {
            'risks': [],
            'sensitive_patterns': [],
            'recommendations': []
        }
        
        diff_lines = full_diff.split('\n')
        
        for i, line in enumerate(diff_lines):
            # Only check added lines
            if not line.startswith('+'):
                continue
            
            # Check for security risks
            for pattern in self.quality_patterns['security_risks']:
                if re.search(pattern, line, re.IGNORECASE):
                    security['risks'].append({
                        'severity': 'high',
                        'line': i,
                        'pattern': pattern,
                        'content': line[1:].strip()[:100]
                    })
            
            # Check for sensitive data patterns
            sensitive_patterns = [
                r'[a-zA-Z0-9]{32,}',  # Potential API keys
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
                r'\\\\[a-zA-Z0-9_-]+\\[a-zA-Z0-9_-]+',  # Network paths
                r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
            ]
            
            for pattern in sensitive_patterns:
                if re.search(pattern, line):
                    security['sensitive_patterns'].append({
                        'line': i,
                        'type': 'potential_sensitive_data',
                        'content': line[1:].strip()[:100]
                    })
        
        # Generate security recommendations
        if security['risks']:
            security['recommendations'].append("High-risk security patterns detected - review carefully")
        
        if security['sensitive_patterns']:
            security['recommendations'].append("Potential sensitive data in code - ensure it's not hardcoded")
        
        # Calculate security score
        security['score'] = 100 - (len(security['risks']) * 20) - (len(security['sensitive_patterns']) * 10)
        security['score'] = max(0, security['score'])
        
        return security
    
    def _analyze_file_changes(self, file_path: str, full_diff: str) -> Optional[Dict]:
        """Analyze changes in a specific file"""
        # Extract diff for this specific file
        file_diff = self._extract_file_diff(file_path, full_diff)
        
        if not file_diff:
            return None
        
        analysis = {
            'file': file_path,
            'language': self._detect_language(file_path),
            'additions': file_diff.count('\n+'),
            'deletions': file_diff.count('\n-'),
            'complexity_change': self._estimate_complexity_change(file_diff),
            'has_tests': False
        }
        
        # Check if this is a test file
        if any(pattern in file_path.lower() for pattern in ['test', 'spec', '_test']):
            analysis['is_test_file'] = True
        else:
            analysis['is_test_file'] = False
            # Check if corresponding test exists
            test_files = self.repo_cloner.find_test_files(file_path)
            analysis['has_tests'] = len(test_files) > 0
            analysis['test_files'] = test_files
        
        return analysis
    
    def _categorize_files(self, files: List[str]) -> Dict[str, int]:
        """Categorize files by type"""
        categories = {
            'source': 0,
            'test': 0,
            'config': 0,
            'documentation': 0,
            'other': 0
        }
        
        for file in files:
            file_lower = file.lower()
            
            if any(pattern in file_lower for pattern in ['test', 'spec', '_test']):
                categories['test'] += 1
            elif any(ext in file_lower for ext in ['.cs', '.js', '.py', '.java', '.ts', '.cpp']):
                categories['source'] += 1
            elif any(ext in file_lower for ext in ['.json', '.xml', '.yaml', '.yml', '.config']):
                categories['config'] += 1
            elif any(ext in file_lower for ext in ['.md', '.txt', '.doc', '.rst']):
                categories['documentation'] += 1
            else:
                categories['other'] += 1
        
        return categories
    
    def _analyze_change_patterns(self, diff: str) -> Dict[str, Any]:
        """Analyze patterns in the changes"""
        patterns = {
            'refactoring': False,
            'new_feature': False,
            'bug_fix': False,
            'documentation': False
        }
        
        diff_lower = diff.lower()
        
        # Detect refactoring (many changes with similar additions/deletions)
        additions = diff.count('\n+')
        deletions = diff.count('\n-')
        if additions > 10 and deletions > 10 and abs(additions - deletions) < max(additions, deletions) * 0.3:
            patterns['refactoring'] = True
        
        # Detect new feature (mostly additions)
        if additions > deletions * 2:
            patterns['new_feature'] = True
        
        # Detect bug fix (small targeted changes)
        if additions < 50 and deletions < 50:
            patterns['bug_fix'] = True
        
        # Detect documentation
        if '.md' in diff_lower or 'readme' in diff_lower:
            patterns['documentation'] = True
        
        return patterns
    
    def _extract_file_diff(self, file_path: str, full_diff: str) -> str:
        """Extract diff for a specific file"""
        lines = full_diff.split('\n')
        file_diff = []
        in_file = False
        
        for line in lines:
            if line.startswith('diff --git'):
                in_file = file_path in line
            elif in_file:
                if line.startswith('diff --git'):
                    break
                file_diff.append(line)
        
        return '\n'.join(file_diff)
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext_to_lang = {
            '.cs': 'C#',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.py': 'Python',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.rs': 'Rust',
            '.sql': 'SQL'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_to_lang.get(ext, 'Unknown')
    
    def _estimate_complexity_change(self, file_diff: str) -> str:
        """Estimate complexity change from diff"""
        # Count control flow additions
        control_patterns = [
            r'\+.*\bif\b',
            r'\+.*\bfor\b',
            r'\+.*\bwhile\b',
            r'\+.*\bswitch\b',
            r'\+.*\btry\b',
            r'\+.*\bcatch\b'
        ]
        
        control_additions = sum(
            len(re.findall(pattern, file_diff))
            for pattern in control_patterns
        )
        
        if control_additions > 5:
            return "increased"
        elif control_additions > 0:
            return "slightly increased"
        
        # Check for removals
        control_removals = sum(
            len(re.findall(pattern.replace('+', '-'), file_diff))
            for pattern in control_patterns
        )
        
        if control_removals > control_additions:
            return "decreased"
        
        return "unchanged"
    
    def _calculate_coverage_score(self, coverage: Dict) -> float:
        """Calculate test coverage score"""
        score = 0.0
        
        # Base score on coverage percentage
        score = coverage.get('coverage_percentage', 0)
        
        # Bonus for modified tests
        if coverage.get('tests_modified_in_pr'):
            score += 20
        
        # Cap at 100
        return min(100, score)
    
    def _calculate_quality_score(self, quality: Dict) -> float:
        """Calculate code quality score"""
        score = 100.0
        
        # Deduct for issues
        score -= len(quality.get('issues_found', [])) * 5
        score -= len(quality.get('code_smells', [])) * 10
        score -= len(quality.get('performance_concerns', [])) * 15
        
        return max(0, score)
    
    def _generate_code_recommendations(self, review: Dict) -> List[str]:
        """Generate recommendations based on code analysis"""
        recommendations = []
        
        # Test coverage recommendations
        test_coverage = review.get('test_coverage', {})
        if test_coverage.get('coverage_percentage', 0) < 50:
            recommendations.append("Add tests for untested files - current coverage is low")
        
        if not test_coverage.get('tests_modified_in_pr'):
            recommendations.append("No tests were modified - ensure changes are tested")
        
        # Code quality recommendations
        code_quality = review.get('code_quality', {})
        if code_quality.get('code_smells'):
            recommendations.append(f"Address {len(code_quality['code_smells'])} code smell(s) found")
        
        if code_quality.get('performance_concerns'):
            recommendations.append(f"Review {len(code_quality['performance_concerns'])} performance concern(s)")
        
        # Security recommendations
        security = review.get('security_analysis', {})
        if security.get('risks'):
            recommendations.append(f"CRITICAL: Address {len(security['risks'])} security risk(s)")
        
        # Diff analysis recommendations
        diff_analysis = review.get('diff_analysis', {})
        if diff_analysis.get('lines_added', 0) > 500:
            recommendations.append("Large PR - consider breaking into smaller changes")
        
        change_patterns = diff_analysis.get('change_patterns', {})
        if change_patterns.get('refactoring'):
            recommendations.append("Refactoring detected - ensure behavior is preserved")
        
        return recommendations
    
    def _print_code_review_summary(self, review: Dict):
        """Print code review summary"""
        print("\n" + "="*70)
        print("CODE REVIEW SUMMARY")
        print("="*70)
        
        # Diff analysis
        diff = review.get('diff_analysis', {})
        print(f"\nChanges:")
        print(f"  Files: {diff.get('files_changed', 0)}")
        print(f"  Lines: +{diff.get('lines_added', 0)} -{diff.get('lines_deleted', 0)}")
        
        file_types = diff.get('file_types', {})
        if file_types:
            print(f"  Types: {', '.join(f'{k}={v}' for k, v in file_types.items() if v > 0)}")
        
        # Test coverage
        coverage = review.get('test_coverage', {})
        print(f"\nTest Coverage:")
        print(f"  Score: {coverage.get('score', 0):.0f}/100")
        print(f"  Files with tests: {len(coverage.get('files_with_tests', []))}")
        print(f"  Files without tests: {len(coverage.get('files_without_tests', []))}")
        
        # Code quality
        quality = review.get('code_quality', {})
        print(f"\nCode Quality:")
        print(f"  Score: {quality.get('score', 0):.0f}/100")
        print(f"  Code smells: {len(quality.get('code_smells', []))}")
        print(f"  Performance concerns: {len(quality.get('performance_concerns', []))}")
        
        # Security
        security = review.get('security_analysis', {})
        print(f"\nSecurity:")
        print(f"  Score: {security.get('score', 0):.0f}/100")
        print(f"  Risks found: {len(security.get('risks', []))}")
        
        # Recommendations
        recommendations = review.get('recommendations', [])
        if recommendations:
            print(f"\nRecommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*70)