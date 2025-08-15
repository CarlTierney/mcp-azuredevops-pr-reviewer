"""Code review functionality that prepares data for Claude CLI analysis with file-type specific prompts"""

import logging
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .file_type_detector import FileTypeDetector, FileType
from .security_detector import SecurityDetector

logger = logging.getLogger(__name__)


@dataclass
class ReviewData:
    """Data prepared for code review"""
    pr_details: Dict[str, Any]
    changes: List[Dict[str, Any]]
    review_prompt: str
    file_type_summary: Dict[str, List[str]]


class CodeReviewer:
    def __init__(self, settings):
        self.settings = settings
        self.file_detector = FileTypeDetector()
        self.security_detector = SecurityDetector()
        self.package_analysis = None  # Will store package analysis results
        self.security_issues = []  # Will store security issues found
    
    def prepare_review_data(
        self,
        pr_details: Any,
        changes: List[Dict[str, Any]]
    ) -> ReviewData:
        """Prepare PR data for Claude CLI to review with file-type awareness, package analysis, and security scanning"""
        try:
            # Analyze file types in the PR
            file_type_summary = self.file_detector.analyze_pr_files(changes)
            
            # Analyze packages for vulnerabilities
            package_summary, package_issues = self.analyze_packages_in_pr(changes)
            
            # Run security analysis on all changed files
            security_issues = self.analyze_security_in_pr(changes)
            
            # Build the review context with all analyses
            review_prompt = self._build_review_prompt(pr_details, changes, file_type_summary, package_summary, security_issues)
            
            # Prepare structured data
            pr_data = {
                "pull_request_id": pr_details.pull_request_id,
                "title": pr_details.title,
                "description": pr_details.description or "No description provided",
                "source_branch": pr_details.source_ref_name,
                "target_branch": pr_details.target_ref_name,
                "created_by": pr_details.created_by.display_name if pr_details.created_by else "Unknown",
                "status": pr_details.status,
                "package_analysis": package_summary
            }
            
            # Convert file type summary to JSON-serializable format
            file_type_summary_str = {
                ft.value: files for ft, files in file_type_summary.items()
            }
            
            logger.info(f"Prepared review data for PR #{pr_details.pull_request_id}")
            logger.info(f"File types detected: {list(file_type_summary_str.keys())}")
            logger.info(f"Packages examined: {package_summary['total_packages_examined']}")
            if package_summary['has_issues']:
                logger.warning(f"Package vulnerabilities found: {package_summary['vulnerable_packages']}")
            
            return ReviewData(
                pr_details=pr_data,
                changes=changes,
                review_prompt=review_prompt,
                file_type_summary=file_type_summary_str
            )
            
        except Exception as e:
            logger.error(f"Error preparing review data: {e}")
            raise
    
    def get_review_instructions(self, file_types: Optional[Dict[FileType, List[str]]] = None) -> str:
        """Get the review instructions/prompt for Claude based on file types"""
        
        # If no file types provided, use default
        if not file_types:
            return self._get_prompt_for_type(FileType.DEFAULT)
        
        # If mixed review needed, combine prompts
        if self.file_detector.should_use_mixed_review(
            [{"path": path} for paths in file_types.values() for path in paths]
        ):
            return self._get_combined_prompt(file_types)
        
        # Use dominant file type prompt
        dominant_type = max(file_types.keys(), key=lambda k: len(file_types[k]))
        return self._get_prompt_for_type(dominant_type)
    
    def _get_prompt_for_type(self, file_type: FileType) -> str:
        """Get the review prompt for a specific file type"""
        
        # Check if custom prompt file is specified
        if self.settings.custom_review_prompt_file:
            try:
                with open(self.settings.custom_review_prompt_file, 'r') as f:
                    custom_prompt = f.read()
                    logger.info(f"Using custom review prompt from {self.settings.custom_review_prompt_file}")
                    return custom_prompt
            except Exception as e:
                logger.warning(f"Failed to load custom prompt file: {e}, using file-type specific prompt")
        
        # Get file-type specific prompt
        prompt_file = self.file_detector.get_prompt_file_for_type(file_type)
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'prompts', 
            prompt_file
        )
        
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, 'r') as f:
                    logger.info(f"Using {file_type.value} specific prompt from {prompt_file}")
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load prompt file {prompt_file}: {e}")
        
        # Fallback to default prompt
        return self._get_default_prompt()
    
    def _get_combined_prompt(self, file_types: Dict[FileType, List[str]]) -> str:
        """Create a combined prompt for PRs with multiple file types"""
        
        prompt_parts = [
            "# Multi-Type Code Review\n",
            "This PR contains multiple file types. Review each according to its specific requirements.\n\n"
        ]
        
        # Add file type summary
        prompt_parts.append("## Files by Type:\n")
        for file_type, files in file_types.items():
            if files:
                prompt_parts.append(f"- **{file_type.value}**: {len(files)} file(s)\n")
        
        prompt_parts.append("\n## Review Guidelines:\n\n")
        
        # Priority file types to include specific guidance for
        priority_types = [
            FileType.CSHARP,
            FileType.RAZOR_VIEW,
            FileType.JAVASCRIPT,
            FileType.TYPESCRIPT,
            FileType.SQL,
            FileType.TEST_CSHARP
        ]
        
        # Add condensed guidelines for each present file type
        for file_type in priority_types:
            if file_type in file_types and file_types[file_type]:
                prompt_parts.append(f"### {file_type.value.replace('_', ' ').title()} Files:\n")
                prompt_parts.append(self._get_condensed_guidelines(file_type))
                prompt_parts.append("\n")
        
        # Add standard response format
        prompt_parts.append(self._get_response_format())
        
        return "".join(prompt_parts)
    
    def _get_condensed_guidelines(self, file_type: FileType) -> str:
        """Get condensed review guidelines for a file type"""
        
        guidelines = {
            FileType.CSHARP: """- SOLID principles, dependency injection, async/await patterns
- Security: input validation, SQL injection prevention
- Performance: LINQ efficiency, memory management
- Null safety, error handling, proper disposal\n""",
            
            FileType.RAZOR_VIEW: """- XSS prevention: proper encoding, avoid @Html.Raw with user input
- CSRF protection: @Html.AntiForgeryToken in forms
- Performance: minimize view logic, avoid database calls
- Model binding, partial views, JavaScript integration\n""",
            
            FileType.JAVASCRIPT: """- Use const/let (never var), strict equality (===)
- Async patterns: Promises, async/await, error handling
- DOM efficiency, event delegation, memory leaks
- Security: XSS prevention, no eval(), input validation\n""",
            
            FileType.TYPESCRIPT: """- Type safety: avoid 'any', use unknown when needed
- Interfaces, generics, discriminated unions
- Strict mode compliance, null checks
- Proper import/export patterns\n""",
            
            FileType.SQL: """- SQL injection prevention: parameterized queries
- Performance: indexes, execution plans, set-based logic
- Transactions, error handling, constraints
- Proper NULL handling, data types\n""",
            
            FileType.TEST_CSHARP: """- Test coverage: edge cases, error conditions
- AAA pattern, single assertion per test
- Proper mocking, test independence
- Descriptive test names, fast execution\n"""
        }
        
        return guidelines.get(file_type, "- Follow language best practices\n- Ensure security and performance\n")
    
    def _get_response_format(self) -> str:
        """Get the standard JSON response format"""
        return """
## Response Format

Format your response as JSON:
```json
{
    "approved": true/false,
    "severity": "approved/minor/major/critical",
    "summary": "Overall assessment of the changes",
    "comments": [
        {
            "file_path": "path/to/file",
            "line_number": 123,
            "content": "Specific feedback",
            "severity": "info/warning/error"
        }
    ],
    "test_suggestions": [
        {
            "file_path": "path/to/file.cs",
            "test_name": "ShouldValidateUserInput",
            "description": "Verify that user input is properly validated before processing",
            "test_code": "[Test]\\npublic void ShouldValidateUserInput()\\n{\\n    // Arrange\\n    \\n    // Act\\n    \\n    // Assert\\n    Assert.Fail(\\"Not implemented\\");\\n}"
        }
    ],
    "files_with_tests": {
        "path/to/file1.cs": [
            {
                "test_name": "ShouldHandleNullInput",
                "description": "Verify the method handles null input gracefully",
                "test_code": "[Test]\\npublic void ShouldHandleNullInput()\\n{\\n    // Arrange\\n    \\n    // Act\\n    \\n    // Assert\\n    Assert.Fail(\\"Not implemented\\");\\n}"
            }
        ],
        "path/to/file2.cs": [
            {
                "test_name": "ShouldThrowOnInvalidState",
                "description": "Verify exception is thrown when object is in invalid state",
                "test_code": "[Test]\\npublic void ShouldThrowOnInvalidState()\\n{\\n    // Arrange\\n    \\n    // Act\\n    \\n    // Assert\\n    Assert.Fail(\\"Not implemented\\");\\n}"
            }
        ]
    }
}
```

## CRITICAL: Security Analysis Required

**ALWAYS check for security issues in EVERY line of EVERY changed file:**
- RevealPassword methods or any method that exposes password information
- Password values being returned, logged, or displayed
- ToString methods that expose sensitive data
- Hardcoded passwords, API keys, or connection strings
- Any method that reveals sensitive information

**If security issues are found:**
- Set severity to "critical" 
- Add comments with exact line numbers for each security violation
- Include "SECURITY" in the comment content
- Set approved to false

**Security issues take priority over all other concerns.**

## Severity Guidelines
- **approved**: Code meets standards, follows best practices
- **minor**: Style issues, minor improvements
- **major**: Performance, maintainability, or design issues
- **critical**: Security vulnerabilities, bugs, or data integrity issues

## Test Suggestions - REQUIRED FOR ALL CHANGED FILES

**MANDATORY: For EVERY file with code changes (add/edit), provide test method stubs:**
- Include file_path to indicate which file the test is for
- Create concrete test method names only (e.g., ShouldThrowWhenUserNotFound, VerifyPasswordIsNotExposed)
- Method names should describe what is being tested
- Description should explain the test scenario
- test_code should be ONLY the method stub, not the full test class
- For C#: Just the method with [Test] attribute
- For JavaScript/TypeScript: Just the it() or test() block
- For Python: Just the def test_* method
- MUST include tests for:
  - Bug fixes (regression tests)
  - New features (happy path and edge cases)
  - Error handling
  - Boundary conditions

Example test_code format:
For C#: 
"[Test]\npublic void ShouldValidateUserInput()\n{\n    // Arrange\n    \n    // Act\n    \n    // Assert\n    Assert.Fail(\"Not implemented\");\n}"

For JavaScript:
"it('should validate user input', () => {\n    // Arrange\n    \n    // Act\n    \n    // Assert\n    expect(false).toBe(true); // Not implemented\n});"
"""
    
    def _get_default_prompt(self) -> str:
        """Get the default review prompt"""
        default_prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'prompts', 
            'default_review_prompt.txt'
        )
        
        if os.path.exists(default_prompt_path):
            try:
                with open(default_prompt_path, 'r') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to load default prompt file: {e}")
        
        # Fallback prompt
        return """Review the pull request for code quality, security, performance, and best practices.
        
Provide your review in JSON format:
{
    "approved": true/false,
    "severity": "approved/minor/major/critical",
    "summary": "Overall review summary",
    "comments": [
        {
            "file_path": "path/to/file",
            "line_number": 123,
            "content": "Your comment",
            "severity": "info/warning/error"
        }
    ]
}"""
    
    def _build_review_prompt(
        self,
        pr_details: Any,
        changes: List[Dict[str, Any]],
        file_type_summary: Dict[FileType, List[str]],
        package_summary: Optional[Dict[str, Any]] = None,
        security_issues: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Build the review context for Claude with file type awareness, package analysis, and security issues"""
        
        prompt_parts = [
            f"Pull Request #{pr_details.pull_request_id}: {pr_details.title}",
            f"Description: {pr_details.description or 'No description provided'}",
            f"Source Branch: {pr_details.source_ref_name}",
            f"Target Branch: {pr_details.target_ref_name}",
            "\n### File Type Summary:\n"
        ]
        
        # Add file type breakdown
        for file_type, files in file_type_summary.items():
            if files:
                prompt_parts.append(f"- {file_type.value}: {len(files)} file(s)")
        
        # Add package analysis summary
        if package_summary:
            prompt_parts.append("\n### Package Analysis:\n")
            prompt_parts.append(f"- Total packages examined: {package_summary['total_packages_examined']}")
            
            if package_summary['packages_by_type']:
                prompt_parts.append("- Package types found:")
                for pkg_type, count in package_summary['packages_by_type'].items():
                    prompt_parts.append(f"  - {pkg_type}: {count} packages")
            
            if package_summary['has_issues']:
                prompt_parts.append(f"- **CRITICAL**: {package_summary['vulnerable_packages']} vulnerable package(s) found:")
                for vuln in package_summary['vulnerable_list'][:5]:  # Show first 5
                    prompt_parts.append(f"  - {vuln}")
                if len(package_summary['vulnerable_list']) > 5:
                    prompt_parts.append(f"  - ... and {len(package_summary['vulnerable_list']) - 5} more")
            else:
                prompt_parts.append("- **No package vulnerabilities detected**")
        
        # Add security issues summary
        if security_issues:
            prompt_parts.append("\n### CRITICAL SECURITY ISSUES DETECTED:\n")
            prompt_parts.append(f"**Found {len(security_issues)} security issue(s) that MUST be addressed:**\n")
            
            # Group by file
            issues_by_file = {}
            for issue in security_issues:
                file_path = issue.get("file_path", "Unknown")
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []
                issues_by_file[file_path].append(issue)
            
            for file_path, file_issues in issues_by_file.items():
                prompt_parts.append(f"\n**{file_path}:**")
                for issue in file_issues[:10]:  # Show first 10 per file
                    prompt_parts.append(f"  - Line {issue['line_number']}: {issue['content']}")
                if len(file_issues) > 10:
                    prompt_parts.append(f"  - ... and {len(file_issues) - 10} more issues")
            
            prompt_parts.append("\n**IMPORTANT**: These security issues MUST be added as comments in your review JSON.")
            prompt_parts.append("Each security issue should have a comment with the exact file_path and line_number.")
        
        prompt_parts.append("\n### File Changes:\n")
        
        # Group changes by file type for better organization
        for file_type, files in file_type_summary.items():
            if not files:
                continue
                
            prompt_parts.append(f"\n#### {file_type.value.replace('_', ' ').title()} Files:\n")
            
            for change in changes:
                if change.get('path') in files:
                    self._add_change_to_prompt(change, prompt_parts)
        
        # Add the appropriate review instructions
        prompt_parts.append("\n### Review Instructions:\n")
        prompt_parts.append(self.get_review_instructions(file_type_summary))
        
        return "\n".join(prompt_parts)
    
    def _add_change_to_prompt(self, change: Dict[str, Any], prompt_parts: List[str]):
        """Add a single file change to the prompt"""
        if change["change_type"] == "delete":
            prompt_parts.append(f"\n**Deleted**: {change['path']}")
        elif change["change_type"] == "add":
            prompt_parts.append(f"\n**Added**: {change['path']}")
            if change.get("new_content"):
                # Limit content size
                content = change["new_content"][:10000]
                prompt_parts.append(f"```\n{content}\n```")
        elif change["change_type"] == "edit":
            prompt_parts.append(f"\n**Modified**: {change['path']}")
            if change.get("old_content") and change.get("new_content"):
                prompt_parts.append("\nChanges:")
                prompt_parts.append(f"```diff\n{self._create_simple_diff(change['old_content'], change['new_content'])}\n```")
    
    def _create_simple_diff(self, old_content: str, new_content: str) -> str:
        """Create a simple diff representation"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff_lines = []
        max_lines = max(len(old_lines), len(new_lines))
        
        for i in range(min(max_lines, 500)):  # Limit to 500 lines
            if i < len(old_lines) and i < len(new_lines):
                if old_lines[i] != new_lines[i]:
                    diff_lines.append(f"- {old_lines[i]}")
                    diff_lines.append(f"+ {new_lines[i]}")
                else:
                    diff_lines.append(f"  {old_lines[i]}")
            elif i < len(old_lines):
                diff_lines.append(f"- {old_lines[i]}")
            elif i < len(new_lines):
                diff_lines.append(f"+ {new_lines[i]}")
        
        if max_lines > 500:
            diff_lines.append("... (diff truncated)")
        
        return "\n".join(diff_lines)
    
    def analyze_packages_in_pr(self, changes: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
        """Analyze packages in PR changes for vulnerabilities and outdated versions
        
        Returns:
            Tuple of (package_summary, issues_found)
        """
        packages_found = {
            "npm": {},
            "nuget": {},
            "pip": {},
            "maven": {},
            "composer": {}
        }
        
        issues = []
        total_packages = 0
        vulnerable_packages = []
        outdated_packages = []
        
        # Known vulnerable packages (simplified for demonstration)
        vulnerable_db = {
            "npm": {
                "lodash": ["< 4.17.21", "CVE-2021-23337"],
                "minimist": ["< 1.2.6", "CVE-2021-44906"],
                "axios": ["< 0.21.2", "CVE-2021-3749"]
            },
            "nuget": {
                "Newtonsoft.Json": ["< 13.0.1", "CVE-2021-42219"],
                "System.Text.Encodings.Web": ["< 4.7.2", "CVE-2021-26701"]
            },
            "pip": {
                "django": ["< 3.2.13", "CVE-2022-28346"],
                "pillow": ["< 9.0.1", "CVE-2022-24303"]
            }
        }
        
        # Process each changed file
        for change in changes:
            file_path = change.get("path", "")
            content = change.get("new_content", "") or change.get("full_content", "")
            
            if not content:
                continue
            
            # Check for package files
            if file_path.endswith("package.json") or file_path.endswith("package-lock.json"):
                # Parse npm packages
                try:
                    data = json.loads(content)
                    deps = {}
                    if "dependencies" in data:
                        deps.update(data["dependencies"])
                    if "devDependencies" in data:
                        deps.update(data["devDependencies"])
                    
                    for name, version in deps.items():
                        packages_found["npm"][name] = self._clean_version(version)
                        total_packages += 1
                        
                        # Check if vulnerable
                        if name in vulnerable_db.get("npm", {}):
                            vuln_info = vulnerable_db["npm"][name]
                            vulnerable_packages.append(f"{name}@{version} ({vuln_info[1]})")
                            issues.append(f"CRITICAL: Vulnerable package {name}@{version} - {vuln_info[1]}")
                except:
                    pass
            
            elif file_path.endswith(".csproj") or file_path.endswith("packages.config"):
                # Parse NuGet packages
                try:
                    tree = ET.fromstring(content)
                    
                    # Handle .csproj files
                    if file_path.endswith(".csproj"):
                        for item in tree.findall(".//PackageReference"):
                            name = item.get("Include")
                            version = item.get("Version", "unknown")
                            if name:
                                packages_found["nuget"][name] = version
                                total_packages += 1
                                
                                # Check if vulnerable
                                if name in vulnerable_db.get("nuget", {}):
                                    vuln_info = vulnerable_db["nuget"][name]
                                    vulnerable_packages.append(f"{name}@{version} ({vuln_info[1]})")
                                    issues.append(f"CRITICAL: Vulnerable package {name}@{version} - {vuln_info[1]}")
                    
                    # Handle packages.config
                    elif file_path.endswith("packages.config"):
                        for package_elem in tree.findall(".//package"):
                            name = package_elem.get("id")
                            version = package_elem.get("version", "unknown")
                            if name:
                                packages_found["nuget"][name] = version
                                total_packages += 1
                                
                                # Check if vulnerable
                                if name in vulnerable_db.get("nuget", {}):
                                    vuln_info = vulnerable_db["nuget"][name]
                                    vulnerable_packages.append(f"{name}@{version} ({vuln_info[1]})")
                                    issues.append(f"CRITICAL: Vulnerable package {name}@{version} - {vuln_info[1]}")
                except:
                    pass
            
            elif "requirements" in file_path and file_path.endswith(".txt"):
                # Parse pip packages
                try:
                    lines = content.splitlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Parse package and version
                            parts = line.split("==")
                            if len(parts) == 2:
                                name = parts[0].strip()
                                version = parts[1].strip()
                                packages_found["pip"][name] = version
                                total_packages += 1
                                
                                # Check if vulnerable
                                if name in vulnerable_db.get("pip", {}):
                                    vuln_info = vulnerable_db["pip"][name]
                                    vulnerable_packages.append(f"{name}@{version} ({vuln_info[1]})")
                                    issues.append(f"CRITICAL: Vulnerable package {name}@{version} - {vuln_info[1]}")
                except:
                    pass
        
        # Create summary
        package_summary = {
            "total_packages_examined": total_packages,
            "packages_by_type": {
                k: len(v) for k, v in packages_found.items() if v
            },
            "vulnerable_packages": len(vulnerable_packages),
            "vulnerable_list": vulnerable_packages,
            "has_issues": len(issues) > 0
        }
        
        # Store for later use
        self.package_analysis = package_summary
        
        return package_summary, issues
    
    def _clean_version(self, version: str) -> str:
        """Clean version string"""
        # Remove common prefixes
        version = version.lstrip("^~>=<!")
        # Remove any ranges
        version = version.split(",")[0]
        version = version.split("||")[0]
        return version.strip()
    
    def analyze_security_in_pr(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze all changed files for security issues
        
        Returns:
            List of security issues found with file path and line numbers
        """
        all_security_issues = []
        
        for change in changes:
            file_path = change.get("path", "")
            content = change.get("new_content", "") or change.get("full_content", "")
            
            if not content:
                continue
            
            # Run security analysis on the file
            file_issues = self.security_detector.analyze_file_security(file_path, content)
            
            # Add all issues to the list
            all_security_issues.extend(file_issues)
            
            # Log if we found critical issues
            if file_issues:
                logger.warning(f"Found {len(file_issues)} security issues in {file_path}")
                for issue in file_issues:
                    logger.warning(f"  Line {issue['line_number']}: {issue['content']}")
        
        # Store for later use
        self.security_issues = all_security_issues
        
        return all_security_issues
    
    def parse_review_response(self, review_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the review response from Claude CLI"""
        try:
            # Collect all test suggestions from both formats
            all_test_suggestions = []
            
            # Get test suggestions from the main array
            test_suggestions = review_json.get("test_suggestions", [])
            all_test_suggestions.extend(test_suggestions)
            
            # Get test suggestions from files_with_tests
            files_with_tests = review_json.get("files_with_tests", {})
            for file_path, tests in files_with_tests.items():
                for test in tests:
                    # Ensure each test has the file_path
                    test_with_path = dict(test)
                    if "file_path" not in test_with_path:
                        test_with_path["file_path"] = file_path
                    all_test_suggestions.append(test_with_path)
            
            return {
                "approved": review_json.get("approved", False),
                "severity": review_json.get("severity", "minor"),
                "summary": review_json.get("summary", "Review completed"),
                "comments": review_json.get("comments", []),
                "test_suggestions": all_test_suggestions,
                "files_with_tests": files_with_tests  # Keep original structure too
            }
        except Exception as e:
            logger.error(f"Error parsing review response: {e}")
            return {
                "approved": False,
                "severity": "minor",
                "summary": "Could not parse review response",
                "comments": [],
                "test_suggestions": [],
                "files_with_tests": {}
            }