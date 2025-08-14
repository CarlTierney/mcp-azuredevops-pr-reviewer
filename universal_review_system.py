"""Universal review system that applies security and test prompts to ALL file types"""

import os
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class UniversalReviewSystem:
    """Ensures security and test reviews are applied to ALL file types"""
    
    def __init__(self):
        self.prompts_dir = Path("prompts")
        self.security_prompt = self._load_prompt("security_focused_prompt.txt")
        self.test_prompt = self._load_prompt("test_review_prompt.txt")
        self.thinking_prefix = self._get_thinking_prefix()
        
    def _get_thinking_prefix(self) -> str:
        """Universal thinking instructions for all reviews"""
        return """
## CRITICAL: DEEP THINKING REQUIRED FOR THIS REVIEW

**STOP AND THINK CAREFULLY**: This is not a quick review. Take substantial time to:

1. **READ THE ENTIRE FILE** - Not just the diff, but the complete context
2. **THINK ABOUT SECURITY** - Every single change could introduce vulnerabilities
3. **CONSIDER TEST REQUIREMENTS** - Bug fixes MUST have tests, no exceptions
4. **ANALYZE THOROUGHLY** - Think through all implications and edge cases
5. **LOOK FOR HIDDEN ISSUES** - Security problems are often subtle

**SPECIFIC ATTENTION REQUIRED**:
- Methods named RevealPassword, GetPassword, ShowPassword, ExposeSecret, etc.
- ANY code that returns, logs, or exposes sensitive information
- ToString() methods that might include passwords or secrets
- Database queries that could be vulnerable to injection
- Missing tests for bug fixes (automatic rejection)
- Authentication and authorization logic
- Error messages that might leak information

**TAKE YOUR TIME**: 
- Think step-by-step through each concern
- Consider how an attacker might exploit the code
- Verify that tests actually prevent regression
- Check that security best practices are followed

Quality and thoroughness matter more than speed.
A missed security issue or missing test could have serious consequences.

---
"""
    
    def _load_prompt(self, filename: str) -> str:
        """Load a prompt file"""
        prompt_path = self.prompts_dir / filename
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def get_review_prompt_for_file(self, file_path: str, change_type: str) -> str:
        """Get comprehensive review prompt for ANY file type
        
        This ensures:
        1. Security review is applied to ALL files
        2. Test review is applied to ALL files  
        3. Deep thinking is required for ALL reviews
        """
        
        # Start with universal thinking instructions
        prompt_parts = [self.thinking_prefix]
        
        # Add file-specific context
        prompt_parts.append(f"\n## FILE UNDER REVIEW: {file_path}")
        prompt_parts.append(f"Change Type: {change_type}")
        prompt_parts.append("")
        
        # ALWAYS add security review (for ALL file types)
        prompt_parts.append("## SECURITY REVIEW (MANDATORY FOR ALL FILES)")
        prompt_parts.append(self.security_prompt)
        prompt_parts.append("")
        
        # ALWAYS add test requirements review (for ALL file types)
        prompt_parts.append("## TEST REQUIREMENTS REVIEW (MANDATORY FOR ALL FILES)")
        prompt_parts.append(self.test_prompt)
        prompt_parts.append("")
        
        # Add language-specific review if applicable
        language_prompt = self._get_language_specific_prompt(file_path)
        if language_prompt:
            prompt_parts.append(f"## LANGUAGE-SPECIFIC REVIEW")
            prompt_parts.append(language_prompt)
            prompt_parts.append("")
        
        # Add final thinking reminder
        prompt_parts.append("## FINAL REMINDER")
        prompt_parts.append("Remember to think deeply about:")
        prompt_parts.append("1. Security vulnerabilities (especially password/secret exposure)")
        prompt_parts.append("2. Missing tests for bug fixes")
        prompt_parts.append("3. Code quality and maintainability")
        prompt_parts.append("4. Performance implications")
        prompt_parts.append("5. Integration with existing code")
        prompt_parts.append("")
        prompt_parts.append("Take your time. Be thorough. Quality matters.")
        
        return "\n".join(prompt_parts)
    
    def _get_language_specific_prompt(self, file_path: str) -> str:
        """Get language-specific prompt based on file extension"""
        
        ext_to_prompt = {
            '.cs': 'csharp_review_prompt.txt',
            '.js': 'javascript_review_prompt.txt',
            '.ts': 'typescript_review_prompt.txt',
            '.py': 'python_review_prompt.txt',
            '.java': 'java_review_prompt.txt',
            '.sql': 'sql_review_prompt.txt',
            '.razor': 'razor_view_review_prompt.txt',
            '.cshtml': 'razor_view_review_prompt.txt',
            '.json': 'json_review_prompt.txt',
            '.xml': 'config_review_prompt.txt',
            '.config': 'config_review_prompt.txt',
            '.md': 'markdown_review_prompt.txt'
        }
        
        # Get file extension
        _, ext = os.path.splitext(file_path.lower())
        
        # Load appropriate prompt
        if ext in ext_to_prompt:
            prompt_file = ext_to_prompt[ext]
            return self._load_prompt(prompt_file)
        
        # Default to general review
        return self._load_prompt('default_review_prompt.txt')
    
    def create_comprehensive_review_instructions(self, files: List[str], is_bug_fix: bool) -> str:
        """Create comprehensive review instructions for a PR
        
        Args:
            files: List of file paths being reviewed
            is_bug_fix: Whether this PR is a bug fix
            
        Returns:
            Complete review instructions with all necessary prompts
        """
        
        instructions = []
        
        # Strong emphasis on thinking for bug fixes
        if is_bug_fix:
            instructions.append("## CRITICAL: BUG FIX DETECTED - TESTS ARE MANDATORY")
            instructions.append("")
            instructions.append("**THIS IS A BUG FIX**: Tests are REQUIRED. No exceptions.")
            instructions.append("Think carefully about what tests are needed to:")
            instructions.append("1. Verify the fix works")
            instructions.append("2. Prevent regression")
            instructions.append("3. Cover edge cases")
            instructions.append("")
            instructions.append("If tests are missing, this PR must be REJECTED.")
            instructions.append("")
        
        # Add thinking prefix
        instructions.append(self.thinking_prefix)
        
        # Note about universal application
        instructions.append("## UNIVERSAL REVIEW STANDARDS")
        instructions.append("")
        instructions.append("The following reviews apply to ALL files, regardless of type:")
        instructions.append("1. **Security Review** - Every file could have security implications")
        instructions.append("2. **Test Requirements** - All changes need appropriate test coverage")
        instructions.append("3. **Code Quality** - Maintainability and readability matter everywhere")
        instructions.append("")
        
        # File-specific sections
        instructions.append(f"## FILES TO REVIEW ({len(files)} files)")
        instructions.append("")
        for i, file_path in enumerate(files[:10], 1):  # Show first 10
            instructions.append(f"{i}. `{file_path}`")
        if len(files) > 10:
            instructions.append(f"... and {len(files) - 10} more files")
        instructions.append("")
        
        # Security emphasis
        instructions.append("## SECURITY CHECKLIST (think about each item)")
        instructions.append("")
        instructions.append("- [ ] No methods that expose passwords (RevealPassword, GetPassword, etc.)")
        instructions.append("- [ ] No sensitive data in logs or error messages")
        instructions.append("- [ ] No hardcoded secrets or credentials")
        instructions.append("- [ ] No SQL injection vulnerabilities")
        instructions.append("- [ ] No path traversal risks")
        instructions.append("- [ ] Proper authentication and authorization")
        instructions.append("- [ ] No information disclosure in responses")
        instructions.append("")
        
        # Test checklist
        instructions.append("## TEST CHECKLIST (think about each item)")
        instructions.append("")
        if is_bug_fix:
            instructions.append("- [ ] **BUG FIX HAS TESTS** (MANDATORY)")
            instructions.append("- [ ] Regression test that reproduces the original bug")
            instructions.append("- [ ] Test that verifies the fix works")
        instructions.append("- [ ] Appropriate unit test coverage")
        instructions.append("- [ ] Edge cases are tested")
        instructions.append("- [ ] Error conditions are tested")
        instructions.append("- [ ] Integration tests where appropriate")
        instructions.append("")
        
        # Final thinking reminder
        instructions.append("## THINK BEFORE YOU APPROVE")
        instructions.append("")
        instructions.append("Before completing this review, ask yourself:")
        instructions.append("1. Have I thoroughly analyzed the security implications?")
        instructions.append("2. Are there adequate tests (especially for bug fixes)?")
        instructions.append("3. Would I be comfortable with this code in production?")
        instructions.append("4. Have I considered all edge cases and failure modes?")
        instructions.append("5. Is there any possibility of data exposure or security breach?")
        instructions.append("")
        instructions.append("If you have any doubts, request changes. Better safe than sorry.")
        
        return "\n".join(instructions)


# Example usage
if __name__ == "__main__":
    print("UNIVERSAL REVIEW SYSTEM")
    print("Applies security and test reviews to ALL file types")
    print()
    
    system = UniversalReviewSystem()
    
    # Example: Get review prompt for different file types
    test_files = [
        "/src/Controllers/UserController.cs",
        "/src/utils/helpers.js",
        "/tests/unit/UserTests.cs",
        "/config/app.config",
        "/docs/README.md"
    ]
    
    print("Security and test reviews will be applied to ALL these files:")
    for file_path in test_files:
        print(f"  - {file_path}")
    
    print()
    print("Sample comprehensive review instructions:")
    print("-" * 50)
    
    instructions = system.create_comprehensive_review_instructions(
        files=test_files,
        is_bug_fix=True
    )
    
    # Show first 50 lines
    lines = instructions.split('\n')
    for line in lines[:50]:
        print(line)
    
    if len(lines) > 50:
        print(f"\n... and {len(lines) - 50} more lines")
    
    print()
    print("Key features:")
    print("1. Security review applied to EVERY file")
    print("2. Test requirements checked for EVERY file")
    print("3. Deep thinking required for ALL reviews")
    print("4. Bug fixes MUST have tests (enforced)")
    print("5. Comprehensive checklists for thorough review")