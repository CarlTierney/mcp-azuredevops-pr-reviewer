"""Test security detection integration with the code reviewer"""

import unittest
from unittest.mock import Mock, patch
from azure_pr_reviewer.code_reviewer import CodeReviewer
from azure_pr_reviewer.security_detector import SecurityDetector
from azure_pr_reviewer.config import Settings


class TestSecurityIntegration(unittest.TestCase):
    """Test suite for security detection integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Mock(spec=Settings)
        self.settings.custom_review_prompt_file = None
        self.reviewer = CodeReviewer(self.settings)
        self.security_detector = SecurityDetector()
    
    def test_revealpassword_detection(self):
        """Test that RevealPassword method is detected"""
        test_content = """
public class UserService {
    private string password;
    
    public string RevealPassword() {
        return this.password;
    }
    
    public void SetPassword(string pwd) {
        this.password = pwd;
    }
}
"""
        issues = self.security_detector.analyze_file_security("UserService.cs", test_content)
        
        # Should find the RevealPassword issue
        self.assertTrue(len(issues) > 0, "Should detect RevealPassword security issue")
        
        # Check that we found the specific line
        reveal_issues = [i for i in issues if "RevealPassword" in i["content"]]
        self.assertTrue(len(reveal_issues) > 0, "Should specifically detect RevealPassword method")
        
        # Verify line number
        for issue in reveal_issues:
            self.assertEqual(issue["line_number"], 5)  # RevealPassword method is on line 5
            self.assertEqual(issue["severity"], "error")
            self.assertEqual(issue["issue_type"], "security")
    
    def test_password_return_detection(self):
        """Test that returning password values is detected"""
        test_content = """
public class Account {
    private string userPassword;
    
    public string GetCredentials() {
        return userPassword;  // Security issue: returning password
    }
}
"""
        issues = self.security_detector.analyze_file_security("Account.cs", test_content)
        
        self.assertTrue(len(issues) > 0, "Should detect password return issue")
        
        # Find the specific issue
        return_issues = [i for i in issues if i["line_number"] == 6]
        self.assertTrue(len(return_issues) > 0, "Should detect return password on line 6")
        self.assertIn("password", return_issues[0]["content"].lower())
    
    def test_security_issues_in_review_data(self):
        """Test that security issues are included in review data"""
        # Create mock PR with security issues
        pr_details = Mock()
        pr_details.pull_request_id = 123
        pr_details.title = "Test PR"
        pr_details.description = "Test description"
        pr_details.source_ref_name = "refs/heads/feature"
        pr_details.target_ref_name = "refs/heads/main"
        pr_details.created_by = Mock(display_name="Test User")
        
        changes = [{
            "path": "/src/UserService.cs",
            "change_type": "edit",
            "new_content": """
public class UserService {
    private string password;
    
    public string RevealPassword() {
        return this.password;
    }
    
    public override string ToString() {
        return $"User: password={password}";  // Security issue
    }
}
"""
        }]
        
        # Prepare review data
        review_data = self.reviewer.prepare_review_data(pr_details, changes)
        
        # Check that security issues were found
        self.assertTrue(len(self.reviewer.security_issues) > 0, "Should find security issues")
        
        # Check that review prompt contains security warnings
        self.assertIn("CRITICAL SECURITY ISSUES DETECTED", review_data.review_prompt)
        self.assertIn("RevealPassword", review_data.review_prompt)
    
    def test_multiple_security_issues_same_line(self):
        """Test consolidation of multiple security issues on the same line"""
        test_content = """
public class BadCode {
    public string RevealPassword() { return password; }  // Multiple issues on same line
}
"""
        issues = self.security_detector.analyze_file_security("BadCode.cs", test_content)
        
        # Should consolidate issues on line 3
        line_3_issues = [i for i in issues if i["line_number"] == 3]
        self.assertEqual(len(line_3_issues), 1, "Should consolidate multiple issues on same line")
        
        # Check that both issues are mentioned
        issue_content = line_3_issues[0]["content"]
        self.assertIn("RevealPassword", issue_content)
        self.assertIn("password", issue_content.lower())
    
    def test_security_issues_in_json_format(self):
        """Test that parse_review_response handles security issues in JSON"""
        review_json = {
            "approved": False,
            "severity": "critical",
            "summary": "Security issues found",
            "comments": [
                {
                    "file_path": "/src/UserService.cs",
                    "line_number": 5,
                    "content": "RevealPassword method exposes sensitive information",
                    "severity": "error",
                    "issue_type": "security"
                },
                {
                    "file_path": "/src/UserService.cs",
                    "line_number": 10,
                    "content": "Password logged in ToString method",
                    "severity": "error",
                    "issue_type": "security"
                }
            ],
            "test_suggestions": [
                {
                    "file_path": "/src/UserService.cs",
                    "test_name": "UserServiceTests.ShouldNotExposePassword",
                    "description": "Verify password is not exposed through public methods",
                    "test_code": "[Test]\\npublic void ShouldNotExposePassword()\\n{\\n    Assert.Fail(\"Not implemented\");\\n}"
                }
            ]
        }
        
        parsed = self.reviewer.parse_review_response(review_json)
        
        # Check that security comments are preserved
        self.assertEqual(len(parsed["comments"]), 2)
        security_comments = [c for c in parsed["comments"] if c.get("issue_type") == "security"]
        self.assertEqual(len(security_comments), 2)
        
        # Check line numbers are correct
        line_numbers = [c["line_number"] for c in security_comments]
        self.assertIn(5, line_numbers)
        self.assertIn(10, line_numbers)
        
        # Check test suggestions are included
        self.assertEqual(len(parsed["test_suggestions"]), 1)
        self.assertEqual(parsed["test_suggestions"][0]["file_path"], "/src/UserService.cs")
    
    def test_password_logging_detection(self):
        """Test detection of password logging"""
        test_content = """
public void ProcessLogin(string username, string password) {
    Console.WriteLine($"Login attempt: {username} with password {password}");
    logger.Info($"User {username} logging in with password: {password}");
}
"""
        issues = self.security_detector.analyze_file_security("LoginService.cs", test_content)
        
        # Should detect password logging
        self.assertTrue(len(issues) > 0, "Should detect password logging")
        
        # Check specific lines
        line_3_issues = [i for i in issues if i["line_number"] == 3]
        line_4_issues = [i for i in issues if i["line_number"] == 4]
        
        self.assertTrue(len(line_3_issues) > 0, "Should detect Console.WriteLine with password")
        self.assertTrue(len(line_4_issues) > 0, "Should detect logger with password")
    
    def test_no_false_positives_in_comments(self):
        """Test that commented code doesn't trigger false positives"""
        test_content = """
public class SafeCode {
    // This method used to RevealPassword but was removed
    // public string RevealPassword() { return password; }
    
    public string GetUsername() {
        return username;  // Safe method
    }
}
"""
        issues = self.security_detector.analyze_file_security("SafeCode.cs", test_content)
        
        # Should not detect issues in comments
        reveal_issues = [i for i in issues if "RevealPassword" in i.get("content", "")]
        self.assertEqual(len(reveal_issues), 0, "Should not detect issues in commented code")


if __name__ == '__main__':
    unittest.main()