"""Clean PR analyzer with proper issue consolidation and summary"""

import asyncio
import json
import logging
import re
from typing import List, Dict, Any
from collections import defaultdict
from azure_pr_reviewer.config import Settings
from azure_pr_reviewer.azure_client import AzureDevOpsClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CleanSecurityDetector:
    """Clean security detector focused on password issues only"""
    
    def analyze_file_security(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze file for security issues - consolidated per line"""
        
        if not content:
            return []
        
        # Group issues by line to avoid spam
        issues_by_line = defaultdict(list)
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            line_stripped = line.strip()
            
            # Skip empty lines and comments
            if not line_stripped or self._is_comment_line(line_stripped, file_path):
                continue
            
            # Primary security patterns (consolidated)
            security_issues = []
            
            # RevealPassword or similar password exposure methods
            if any(pattern in line_lower for pattern in [
                'revealpassword', 'showpassword', 'getpassword', 'displaypassword'
            ]):
                security_issues.append("Method exposes password information")
            
            # Password in return statements
            elif 'return' in line_lower and 'password' in line_lower:
                security_issues.append("Returns password value")
            
            # Password in logging
            elif ('log' in line_lower or 'console' in line_lower) and 'password' in line_lower:
                security_issues.append("Logs password information")
            
            # Password in toString methods
            elif 'tostring' in line_lower and 'password' in line_lower:
                security_issues.append("ToString exposes password")
            
            # Consolidate all security issues for this line
            if security_issues:
                consolidated_message = f"CRITICAL SECURITY: {', '.join(security_issues)}. Line: {line_stripped}"
                issues_by_line[line_num] = [{
                    "file_path": file_path,
                    "line_number": line_num,
                    "content": consolidated_message,
                    "severity": "error",
                    "issue_type": "security",
                    "line_content": line_stripped
                }]
        
        # Return consolidated issues (one per line max)
        consolidated_issues = []
        for line_issues in issues_by_line.values():
            consolidated_issues.extend(line_issues)
        
        return consolidated_issues
    
    def _is_comment_line(self, line: str, file_path: str) -> bool:
        """Check if line is a comment"""
        line = line.strip()
        
        if file_path.endswith(('.cs', '.java', '.js', '.ts', '.tsx', '.jsx')):
            return line.startswith('//') or line.startswith('/*') or line.startswith('*')
        elif file_path.endswith('.py'):
            return line.startswith('#')
        elif file_path.endswith('.sql'):
            return line.startswith('--') or line.startswith('/*')
        
        return False

class CleanPRAnalyzer:
    """Clean PR analyzer without try-catch noise and with proper summary"""
    
    def __init__(self):
        self.settings = Settings()
        self.azure_client = AzureDevOpsClient(self.settings)
        self.security_detector = CleanSecurityDetector()
        self.posted_reviews = set()  # Track posted reviews to avoid duplicates
    
    async def analyze_and_post_clean_review(self, repo_id: str, pr_id: int):
        """Analyze PR cleanly and post single consolidated review"""
        
        # Check if we already posted for this PR
        review_key = f"{repo_id}_{pr_id}"
        if review_key in self.posted_reviews:
            print(f"Review already posted for {repo_id} PR #{pr_id}, skipping duplicate")
            return {"success": True, "duplicate": True}
        
        print(f"CLEAN PR ANALYSIS: PR #{pr_id}")
        print("=" * 50)
        print("Clean analysis features:")
        print("- No try-catch block inspection")
        print("- One consolidated comment per line")
        print("- No duplicate posting")
        print("- Comprehensive summary with test suggestions")
        print()
        
        try:
            # Get PR details
            pr_details = await self.azure_client.get_pull_request(
                self.settings.azure_organization,
                self.settings.azure_project,
                repo_id,
                pr_id
            )
            
            print(f"PR: {pr_details.title}")
            is_bug_fix = 'hotfix' in pr_details.description.lower() or 'bug' in pr_details.title.lower()
            print(f"Type: {'Bug Fix' if is_bug_fix else 'Feature/Enhancement'}")
            
            # Get PR changes
            changes = await self.azure_client.get_pull_request_changes(
                self.settings.azure_organization,
                self.settings.azure_project,
                repo_id,
                pr_id
            )
            
            print(f"Files changed: {len(changes)}")
            
            # Analyze files cleanly (no try-catch inspection)
            all_issues = []
            has_tests = False
            changed_files = []
            
            for change in changes:
                file_path = change['path']
                content = change.get('new_content', '')
                is_test_file = change.get('is_test_file', False)
                
                changed_files.append(file_path)
                
                if is_test_file:
                    has_tests = True
                    print(f"  [OK] Test file: {file_path}")
                else:
                    print(f"  - Production file: {file_path}")
                
                # Only analyze security issues (no try-catch)
                if content:
                    security_issues = self.security_detector.analyze_file_security(file_path, content)
                    all_issues.extend(security_issues)
                    
                    if security_issues:
                        print(f"    Security issues: {len(security_issues)}")
            
            # Generate specific test suggestions with actual test names (NO line comments)
            missing_test_suggestions = []
            if is_bug_fix and not has_tests:
                # Generate specific test names based on the actual files changed
                missing_test_suggestions = self._generate_specific_test_names(changed_files, pr_details.title)
                
                # CRITICAL: Do NOT add missing tests to all_issues - they go in summary ONLY
                # No line comments for missing tests!
            
            # Determine review decision - BUG FIXES WITHOUT TESTS ARE NEVER APPROVED
            critical_issues = [i for i in all_issues if i['severity'] == 'error']
            security_issues = [i for i in all_issues if i.get('issue_type') == 'security']
            
            # CRITICAL: Bug fixes MUST have tests - this is non-negotiable
            if is_bug_fix and not has_tests:
                approved = False
                severity = "critical"  # Bug fixes without tests are CRITICAL failures
                print(f"  [X] BUG FIX REJECTED: No tests provided (POLICY VIOLATION)")
            elif critical_issues:
                approved = False
                severity = "critical" if security_issues else "major"
            else:
                approved = True
                severity = "approved"
            
            # Create comprehensive summary
            summary = self._create_comprehensive_summary(
                all_issues, missing_test_suggestions, is_bug_fix, approved, severity, changed_files
            )
            
            # Create clean review (no duplicate comments, no test line comments)
            # Filter out any missing_test issues that might have snuck in
            line_comments = [issue for issue in all_issues if issue.get('issue_type') != 'missing_tests']
            
            review = {
                "approved": approved,
                "severity": severity,
                "summary": summary,
                "comments": line_comments  # Only security issues, NO missing test comments
            }
            
            print(f"\nAnalysis complete:")
            print(f"  Security issues: {len(security_issues)}")
            print(f"  Missing tests: {1 if (is_bug_fix and not has_tests) else 0}")
            print(f"  Total issues: {len(all_issues)}")
            print(f"  Decision: {'APPROVED' if approved else 'REJECTED'}")
            if is_bug_fix and not has_tests:
                print(f"  Reason: Bug fixes require tests - POLICY ENFORCEMENT")
            
            # Post single clean review
            print(f"\nPosting clean review...")
            result = await self.azure_client.post_review_to_azure(
                self.settings.azure_organization,
                self.settings.azure_project,
                repo_id,
                pr_id,
                review
            )
            
            # Mark as posted to prevent duplicates
            self.posted_reviews.add(review_key)
            
            print(f"[SUCCESS] Clean review posted!")
            print(f"  Line comments: {result['comments_posted']}")
            print(f"  Summary: Markdown format with test stubs")
            vote_value = -10 if not approved else 10
            print(f"  Vote: {vote_value} ({'CRITICAL REJECTION' if not approved else 'APPROVED'})")
            
            return {
                "success": True,
                "issues_found": len(all_issues),
                "security_issues": len(security_issues),
                "test_suggestions": len(missing_test_suggestions),
                "approved": approved,
                "severity": severity,
                "duplicate": False
            }
            
        except Exception as e:
            logger.error(f"Clean analysis error: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_comprehensive_summary(self, issues, test_suggestions, is_bug_fix, approved, severity, changed_files):
        """Create comprehensive summary with issues and test suggestions"""
        
        summary_parts = []
        
            # Status header (no emojis)
        if not approved:
            if severity == "critical" and test_suggestions:
                summary_parts.append("## AUTOMATIC REJECTION - BUG FIX WITHOUT REQUIRED TESTS")
            elif severity == "critical":
                summary_parts.append("## AUTOMATIC REJECTION - CRITICAL SECURITY VIOLATIONS")
            else:
                summary_parts.append("## CHANGES REQUIRED - MAJOR ISSUES DETECTED")
        else:
            summary_parts.append("## APPROVED - Code meets quality standards")
        
        summary_parts.append("\n")
        
        # Files changed
        summary_parts.append(f"### FILES CHANGED: {len(changed_files)}")
        for file in changed_files[:3]:  # Show first 3 files
            summary_parts.append(f"- `{file}`")
        if len(changed_files) > 3:
            summary_parts.append(f"- ... and {len(changed_files) - 3} more files")
        summary_parts.append("")
        
        # Issues summary
        security_issues = [i for i in issues if i.get('issue_type') == 'security']
        test_issues = []  # No missing test line comments - only in summary
        
        summary_parts.append("### ISSUES FOUND")
        if security_issues:
            summary_parts.append(f"**Security violations: {len(security_issues)}**")
            for issue in security_issues[:2]:  # Show first 2
                line_info = f"Line {issue['line_number']}" if issue['line_number'] > 1 else "Multiple lines"
                summary_parts.append(f"- {line_info}: {issue.get('content', 'Security issue detected')}")
        
        if is_bug_fix and test_suggestions:
            summary_parts.append(f"**Testing violations: Bug fix lacks required tests**")
            summary_parts.append(f"- {len(test_suggestions)} specific test methods MUST be implemented")
            summary_parts.append(f"- This PR cannot be approved until tests are added")
        
        if not issues and not test_suggestions:
            summary_parts.append("**No critical issues detected**")
        elif not security_issues and test_suggestions:
            summary_parts.append("**Only missing tests detected**")
        
        summary_parts.append("")
        
        # Test suggestions as markdown code stubs
        if test_suggestions:
            summary_parts.append("### REQUIRED TEST CASES")
            summary_parts.append("")
            # Detect language from file extensions
            is_csharp = any(f.endswith('.cs') for f in changed_files)
            is_python = any(f.endswith('.py') for f in changed_files)
            is_javascript = any(f.endswith('.js') or f.endswith('.ts') for f in changed_files)
            
            if is_csharp:
                summary_parts.append("```csharp")
                summary_parts.append("// Add these test methods to your test class")
                summary_parts.append("using NUnit.Framework;  // or xUnit, MSTest")
                summary_parts.append("")
                summary_parts.append("[TestFixture]")
                summary_parts.append("public class QuestionnairesTests")
                summary_parts.append("{")
                for test in test_suggestions:
                    method_name = test.split('.')[-1].replace('()', '')
                    summary_parts.append(f"    [Test]")
                    summary_parts.append(f"    public void {method_name}()")
                    summary_parts.append(f"    {{")
                    summary_parts.append(f"        // TODO: Implement test for {method_name}")
                    summary_parts.append(f"        Assert.Fail(\"Test not implemented\");")
                    summary_parts.append(f"    }}")
                    summary_parts.append("")
                summary_parts.append("}")
                summary_parts.append("```")
            elif is_python:
                summary_parts.append("```python")
                summary_parts.append("# Add these test methods to your test file")
                summary_parts.append("import unittest")
                summary_parts.append("")
                summary_parts.append("class TestQuestionnaires(unittest.TestCase):")
                for test in test_suggestions:
                    method_name = test.split('.')[-1].replace('()', '')
                    summary_parts.append(f"    def test_{method_name.lower()}(self):")
                    summary_parts.append(f"        \"\"\"TODO: Implement test for {method_name}\"\"\"")
                    summary_parts.append(f"        self.fail('Test not implemented')")
                    summary_parts.append("")
                summary_parts.append("```")
            else:
                # Generic list if language not detected
                for i, suggestion in enumerate(test_suggestions, 1):
                    summary_parts.append(f"{i}. `{suggestion}`")
            summary_parts.append("")
        
        # Policy enforcement
        if is_bug_fix and test_suggestions:
            summary_parts.append("### POLICY ENFORCEMENT")
            summary_parts.append("**Bug fixes require tests - NO EXCEPTIONS**")
            summary_parts.append("This PR will be AUTOMATICALLY REJECTED until tests are provided")
        
        if security_issues:
            summary_parts.append("**SECURITY POLICY**: Methods exposing passwords violate security standards")
        
        return "\n".join(summary_parts)
    
    def _generate_specific_test_names(self, changed_files: List[str], pr_title: str) -> List[str]:
        """Generate specific test method names based on actual code changes"""
        
        # Extract class and method names from file paths and PR context
        test_names = []
        
        for file_path in changed_files:
            if file_path.endswith('.cs'):
                # Extract class name from file path
                class_name = file_path.split('/')[-1].replace('.cs', '')
                
                # Infer method name from PR title or common patterns
                title_lower = pr_title.lower()
                
                # Check for specific operations and entities
                if ('delete' in title_lower or 'deletion' in title_lower) and 'invite' in title_lower:
                    method_name = 'DeleteInvite'
                elif 'delete' in title_lower or 'deletion' in title_lower or 'remove' in title_lower:
                    method_name = 'DeleteItem'
                elif 'update' in title_lower and 'invite' in title_lower:
                    method_name = 'UpdateInvite'
                elif 'update' in title_lower or 'modify' in title_lower:
                    method_name = 'UpdateRecord'
                elif 'create' in title_lower and 'invite' in title_lower:
                    method_name = 'CreateInvite'
                elif 'create' in title_lower or 'add' in title_lower:
                    method_name = 'CreateRecord'
                elif 'fix' in title_lower and 'invite' in title_lower:
                    # Handle "Fix invite deletion" pattern
                    method_name = 'DeleteInvite'
                else:
                    method_name = 'ProcessRequest'  # Generic fallback
                
                # Generate specific test method names
                test_class = f"{class_name}Tests"
                test_names.extend([
                    f"{test_class}.{method_name}_ShouldReturnFalse_WhenItemNotFound()",
                    f"{test_class}.{method_name}_ShouldReturnTrue_WhenItemExists()", 
                    f"{test_class}.{method_name}_ShouldHandleNullParameters_Gracefully()",
                    f"{test_class}.{method_name}_ShouldCallSaveChanges_WhenSuccessful()",
                    f"{test_class}.{method_name}_RegressionTest_OriginalBugScenario()"
                ])
                break  # Only process first relevant file
        
        # Fallback if no specific files found
        if not test_names:
            test_names = [
                "ComponentTests.BugFix_ShouldReproduceOriginalIssue()",
                "ComponentTests.BugFix_ShouldValidateFixedBehavior()",
                "ComponentTests.BugFix_ShouldHandleEdgeCases()",
                "IntegrationTests.BugFix_ShouldWorkInFullWorkflow()",
                "RegressionTests.BugFix_ShouldPreventRecurrence()"
            ]
        
        return test_names[:5]  # Limit to 5 specific tests

async def run_clean_analysis():
    """Run clean analysis on PR #1364"""
    
    analyzer = CleanPRAnalyzer()
    result = await analyzer.analyze_and_post_clean_review("Zinnia", 1364)
    
    return result

if __name__ == "__main__":
    print("CLEAN PR ANALYZER")
    print("Fixes:")
    print("- ❌ Removed try-catch block inspection")
    print("- ❌ No duplicate comment posting") 
    print("- ❌ No line assignment spam")
    print("- ✅ Comprehensive summary with issues and test suggestions")
    print()
    
    result = asyncio.run(run_clean_analysis())
    
    if result["success"]:
        if result.get("duplicate"):
            print(f"[INFO] Review already posted, skipped duplicate")
        else:
            print(f"[SUCCESS] Clean analysis complete!")
            print(f"  Security issues: {result['security_issues']} (with correct lines)")
            print(f"  Test suggestions: {result['test_suggestions']}")
            print(f"  Total comments: {result['issues_found']} (no duplicates)")
            print(f"  Decision: {'APPROVED' if result['approved'] else 'REJECTED'}")
            print(f"\nFixed issues:")
            print(f"  ✓ No try-catch noise")
            print(f"  ✓ One comment per issue") 
            print(f"  ✓ No duplicate posting")
            print(f"  ✓ Comprehensive summary included")
    else:
        print(f"[FAILED] {result.get('error', 'Unknown error')}")
    
    print(f"\nClean review posted to Azure DevOps!")