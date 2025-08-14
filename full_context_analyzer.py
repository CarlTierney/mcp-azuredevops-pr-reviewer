"""Full context analyzer that clones repository for complete analysis"""

import os
import shutil
import tempfile
import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path
import subprocess

from azure_pr_reviewer.config import Settings
from azure_pr_reviewer.azure_client import AzureDevOpsClient
from azure_pr_reviewer.security_detector import SecurityDetector
from package_vulnerability_analyzer import PackageVulnerabilityAnalyzer, VulnerabilityReport

logger = logging.getLogger(__name__)


class FullContextAnalyzer:
    """Analyzer that clones full repository for complete context analysis"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.azure_client = AzureDevOpsClient(settings)
        self.security_detector = SecurityDetector()
        self.working_dir = Path(settings.working_directory)
        self.auto_cleanup = settings.auto_cleanup
        self.package_analyzer = None  # Will be initialized when needed
        
    def _ensure_working_directory(self):
        """Ensure working directory exists and is clean - ALWAYS clean before starting"""
        # ALWAYS clean before starting a new analysis
        if self.working_dir.exists():
            print(f"Cleaning existing working directory: {self.working_dir}")
            shutil.rmtree(self.working_dir, ignore_errors=True)
        
        self.working_dir.mkdir(parents=True, exist_ok=True)
        print(f"Working directory ready: {self.working_dir}")
        
    def _cleanup_working_directory(self):
        """Clean up working directory after analysis"""
        if self.auto_cleanup and self.working_dir.exists():
            print(f"Cleaning up working directory: {self.working_dir}")
            shutil.rmtree(self.working_dir, ignore_errors=True)
            
    async def clone_repository(
        self,
        organization: str,
        project: str,
        repository: str,
        branch: str = "main"
    ) -> Path:
        """Clone repository to working directory"""
        
        # Clean/create working directory
        self._ensure_working_directory()
        
        # Build clone URL
        clone_url = f"https://{self.settings.azure_pat}@dev.azure.com/{organization}/{project}/_git/{repository}"
        repo_path = self.working_dir / repository
        
        try:
            print(f"Cloning repository: {repository}")
            print(f"  Branch: {branch}")
            print(f"  Target: {repo_path}")
            
            # Clone the repository
            result = subprocess.run(
                ["git", "clone", "-b", branch, "--depth", "1", clone_url, str(repo_path)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Clone failed: {result.stderr}")
                raise Exception(f"Failed to clone repository: {result.stderr}")
                
            print(f"Repository cloned successfully to {repo_path}")
            return repo_path
            
        except subprocess.TimeoutExpired:
            logger.error("Clone operation timed out")
            raise Exception("Repository clone timed out")
        except Exception as e:
            logger.error(f"Clone error: {e}")
            raise
    
    async def analyze_packages(self, repo_path: Path) -> VulnerabilityReport:
        """Analyze all packages in the repository for vulnerabilities"""
        
        print(f"\n{'='*50}")
        print("PACKAGE VULNERABILITY ANALYSIS")
        print(f"{'='*50}")
        
        # Initialize package analyzer if not already done
        if self.package_analyzer is None:
            self.package_analyzer = PackageVulnerabilityAnalyzer(self.working_dir)
        
        # Run comprehensive package analysis
        vulnerability_report = await self.package_analyzer.analyze_repository(repo_path)
        
        return vulnerability_report
            
    async def checkout_pr_branch(
        self,
        repo_path: Path,
        pr_branch: str
    ):
        """Checkout PR branch for analysis"""
        try:
            print(f"Checking out PR branch: {pr_branch}")
            
            # Fetch the PR branch
            result = subprocess.run(
                ["git", "fetch", "origin", pr_branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"Fetch warning: {result.stderr}")
                
            # Checkout the branch
            result = subprocess.run(
                ["git", "checkout", pr_branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Try to checkout as detached HEAD
                result = subprocess.run(
                    ["git", "checkout", f"origin/{pr_branch}"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
            print(f"Checked out branch: {pr_branch}")
            
        except Exception as e:
            logger.error(f"Checkout error: {e}")
            raise
            
    async def analyze_full_repository(
        self,
        repo_path: Path,
        changed_files: List[str]
    ) -> Dict[str, Any]:
        """Analyze full repository context for changed files"""
        
        all_issues = []
        analyzed_files = 0
        
        print(f"\nAnalyzing {len(changed_files)} changed files with full context...")
        
        for file_path in changed_files:
            # Get full file path
            full_path = repo_path / file_path.lstrip('/')
            
            if not full_path.exists():
                print(f"  File not found: {file_path}")
                continue
                
            try:
                # Read entire file content
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                print(f"  Analyzing: {file_path} ({len(content)} chars)")
                
                # Analyze entire file for security issues
                security_issues = self.security_detector.analyze_file_security(
                    file_path,
                    content
                )
                
                if security_issues:
                    print(f"    Found {len(security_issues)} security issues:")
                    for issue in security_issues[:3]:  # Show first 3
                        print(f"      - Line {issue['line_number']}: {issue['content'][:60]}...")
                    all_issues.extend(security_issues)
                    
                analyzed_files += 1
                
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                print(f"    Error: {e}")
                
        print(f"\nAnalysis complete:")
        print(f"  Files analyzed: {analyzed_files}")
        print(f"  Total issues found: {len(all_issues)}")
        
        return {
            "issues": all_issues,
            "files_analyzed": analyzed_files,
            "total_issues": len(all_issues)
        }
        
    async def analyze_pr_with_full_context(
        self,
        organization: str,
        project: str,
        repository: str,
        pr_id: int
    ) -> Dict[str, Any]:
        """Analyze PR with full repository context"""
        
        try:
            print(f"\n{'='*50}")
            print(f"FULL CONTEXT ANALYSIS FOR PR #{pr_id}")
            print(f"{'='*50}")
            
            # Get PR details
            pr = await self.azure_client.get_pull_request(
                organization, project, repository, pr_id
            )
            
            print(f"PR Title: {pr.title}")
            print(f"Source: {pr.source_ref_name}")
            print(f"Target: {pr.target_ref_name}")
            
            # Get changed files
            changes = await self.azure_client.get_pull_request_changes(
                organization, project, repository, pr_id
            )
            
            changed_files = [change['path'] for change in changes]
            print(f"Changed files: {len(changed_files)}")
            
            # Clone repository
            target_branch = pr.target_ref_name.replace('refs/heads/', '')
            repo_path = await self.clone_repository(
                organization, project, repository, target_branch
            )
            
            # Checkout PR branch
            source_branch = pr.source_ref_name.replace('refs/heads/', '')
            await self.checkout_pr_branch(repo_path, source_branch)
            
            # Analyze with full context
            analysis_result = await self.analyze_full_repository(
                repo_path, changed_files
            )
            
            # Analyze packages for vulnerabilities
            print("\nAnalyzing packages for vulnerabilities...")
            vulnerability_report = await self.analyze_packages(repo_path)
            
            # Add package vulnerabilities to the result
            package_issues = []
            if vulnerability_report.vulnerable_packages > 0:
                for pkg in vulnerability_report.packages:
                    if pkg.is_vulnerable:
                        for vuln in pkg.vulnerabilities:
                            package_issues.append({
                                'file_path': pkg.file_path,
                                'line_number': 0,  # Package level issue
                                'content': f"VULNERABLE PACKAGE: {pkg.name}@{pkg.version} - {vuln['cve']}: {vuln['description']} (Severity: {vuln['severity'].upper()})",
                                'severity': vuln['severity'],
                                'issue_type': 'package_vulnerability'
                            })
            
            # Check for critical issues
            critical_issues = [
                issue for issue in analysis_result['issues']
                if 'revealpassword' in issue.get('content', '').lower()
                or 'password' in issue.get('content', '').lower()
            ]
            
            if critical_issues:
                print(f"\n**CRITICAL SECURITY ISSUES FOUND:**")
                for issue in critical_issues:
                    print(f"  - {issue['file_path']}:{issue['line_number']}")
                    print(f"    {issue['content']}")
                    
            # Clean up
            if self.auto_cleanup:
                self._cleanup_working_directory()
                
            return {
                "success": True,
                "pr_id": pr_id,
                "issues": analysis_result['issues'] + package_issues,
                "critical_issues": critical_issues,
                "files_analyzed": analysis_result['files_analyzed'],
                "vulnerability_report": {
                    "total_packages": vulnerability_report.total_packages,
                    "vulnerable_packages": vulnerability_report.vulnerable_packages,
                    "critical_vulnerabilities": vulnerability_report.critical_vulnerabilities,
                    "high_vulnerabilities": vulnerability_report.high_vulnerabilities,
                    "recommendations": vulnerability_report.recommendations
                }
            }
            
        except Exception as e:
            logger.error(f"Full context analysis failed: {e}")
            # Clean up on error
            if self.auto_cleanup:
                self._cleanup_working_directory()
            return {
                "success": False,
                "error": str(e)
            }
            
            
async def test_full_context_analysis():
    """Test full context analysis on PR 1364"""
    
    settings = Settings()
    analyzer = FullContextAnalyzer(settings)
    
    result = await analyzer.analyze_pr_with_full_context(
        settings.azure_organization,
        settings.azure_project,
        "Zinnia",
        1364
    )
    
    if result['success']:
        print(f"\n{'='*50}")
        print("FULL CONTEXT ANALYSIS RESULTS")
        print(f"{'='*50}")
        print(f"PR #{result['pr_id']} analyzed successfully")
        print(f"Files analyzed: {result['files_analyzed']}")
        print(f"Total issues: {len(result['issues'])}")
        print(f"Critical issues: {len(result['critical_issues'])}")
        
        if 'vulnerability_report' in result:
            vr = result['vulnerability_report']
            print(f"\nPACKAGE VULNERABILITIES:")
            print(f"  Total packages: {vr['total_packages']}")
            print(f"  Vulnerable packages: {vr['vulnerable_packages']}")
            print(f"  Critical vulnerabilities: {vr['critical_vulnerabilities']}")
            print(f"  High vulnerabilities: {vr['high_vulnerabilities']}")
        
        if result['critical_issues']:
            print(f"\n**CRITICAL: RevealPassword method detected!**")
            print("This would have been caught with full context analysis.")
    else:
        print(f"Analysis failed: {result['error']}")
        
        
if __name__ == "__main__":
    print("FULL CONTEXT ANALYZER")
    print("Clones repository for complete file analysis")
    print("Includes comprehensive package vulnerability analysis")
    print()
    
    asyncio.run(test_full_context_analysis())