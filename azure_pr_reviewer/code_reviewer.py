"""Code review functionality that prepares data for Claude CLI analysis with file-type specific prompts"""

import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .file_type_detector import FileTypeDetector, FileType

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
    
    def prepare_review_data(
        self,
        pr_details: Any,
        changes: List[Dict[str, Any]]
    ) -> ReviewData:
        """Prepare PR data for Claude CLI to review with file-type awareness"""
        try:
            # Analyze file types in the PR
            file_type_summary = self.file_detector.analyze_pr_files(changes)
            
            # Build the review context
            review_prompt = self._build_review_prompt(pr_details, changes, file_type_summary)
            
            # Prepare structured data
            pr_data = {
                "pull_request_id": pr_details.pull_request_id,
                "title": pr_details.title,
                "description": pr_details.description or "No description provided",
                "source_branch": pr_details.source_ref_name,
                "target_branch": pr_details.target_ref_name,
                "created_by": pr_details.created_by.display_name if pr_details.created_by else "Unknown",
                "status": pr_details.status
            }
            
            # Convert file type summary to JSON-serializable format
            file_type_summary_str = {
                ft.value: files for ft, files in file_type_summary.items()
            }
            
            logger.info(f"Prepared review data for PR #{pr_details.pull_request_id}")
            logger.info(f"File types detected: {list(file_type_summary_str.keys())}")
            
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
            "test_name": "TestClassName.TestMethodName",
            "description": "What this test should verify",
            "test_code": "// Stubbed test code\\n[Test]\\npublic void TestMethodName()\\n{\\n    // Arrange\\n    \\n    // Act\\n    \\n    // Assert\\n    Assert.Fail(\\"Not implemented\\");\\n}"
        }
    ]
}
```

## Severity Guidelines
- **approved**: Code meets standards, follows best practices
- **minor**: Style issues, minor improvements
- **major**: Performance, maintainability, or design issues
- **critical**: Security vulnerabilities, bugs, or data integrity issues

## Test Suggestions
For any bug fixes or new features, provide specific test suggestions with:
- Concrete test method names
- Description of what each test verifies
- Stubbed test code in the appropriate testing framework
- Focus on edge cases, error conditions, and critical paths
- For bug fixes: MUST include tests that verify the fix
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
        file_type_summary: Dict[FileType, List[str]]
    ) -> str:
        """Build the review context for Claude with file type awareness"""
        
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
    
    def parse_review_response(self, review_json: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the review response from Claude CLI"""
        try:
            return {
                "approved": review_json.get("approved", False),
                "severity": review_json.get("severity", "minor"),
                "summary": review_json.get("summary", "Review completed"),
                "comments": review_json.get("comments", []),
                "test_suggestions": review_json.get("test_suggestions", [])
            }
        except Exception as e:
            logger.error(f"Error parsing review response: {e}")
            return {
                "approved": False,
                "severity": "minor",
                "summary": "Could not parse review response",
                "comments": [],
                "test_suggestions": []
            }