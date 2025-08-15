"""Test that MCP server properly exposes security analysis results"""

import unittest
import json
from unittest.mock import Mock, patch, AsyncMock
from azure_pr_reviewer.server import AzurePRReviewerServer
from azure_pr_reviewer.code_reviewer import CodeReviewer
from azure_pr_reviewer.security_detector import SecurityDetector


class TestMCPSecurityIntegration(unittest.TestCase):
    """Test security analysis integration in MCP server"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('azure_pr_reviewer.server.Settings') as mock_settings:
            mock_settings.return_value.validate_settings.return_value = None
            mock_settings.return_value.azure_organization = "test_org"
            mock_settings.return_value.azure_project = "test_project"
            mock_settings.return_value.azure_pat = "test_pat"
            
            with patch('azure_pr_reviewer.server.AzureDevOpsClient'):
                self.server = AzurePRReviewerServer()
    
    @patch('azure_pr_reviewer.server.AzureDevOpsClient')
    async def test_get_pr_for_review_includes_security_analysis(self, mock_client_class):
        """Test that get_pr_for_review includes security analysis in response"""
        
        # Setup mock PR with security issue
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.description = "Test description"
        mock_pr.source_ref_name = "refs/heads/feature"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.created_by = Mock(display_name="Test User")
        mock_pr.status = "active"
        
        # Mock changes with security issue
        mock_changes = [{
            "path": "/src/UserService.cs",
            "change_type": "edit",
            "new_content": '''
public class UserService {
    private string password;
    
    public string RevealPassword() {
        return this.password;
    }
}''',
            "full_content": '''
public class UserService {
    private string password;
    
    public string RevealPassword() {
        return this.password;
    }
}'''
        }]
        
        # Setup mocks
        mock_client = mock_client_class.return_value
        mock_client.get_pull_request = AsyncMock(return_value=mock_pr)
        mock_client.get_pull_request_changes = AsyncMock(return_value=mock_changes)
        
        # Call the method
        result_json = await self.server._setup_tools.__wrapped__(self.server).get_pr_for_review(
            repository_id="test_repo",
            pull_request_id=123,
            project="test_project",
            organization="test_org"
        )
        
        # Parse the result
        result = json.loads(result_json)
        
        # Verify security analysis is included
        self.assertIn("security_analysis", result)
        security_analysis = result["security_analysis"]
        
        # Should have detected the RevealPassword issue
        self.assertGreater(security_analysis["issues_found"], 0)
        self.assertTrue(security_analysis["has_critical_issues"])
        self.assertGreater(len(security_analysis["issues"]), 0)
        
        # Verify the specific security issue
        security_issue = security_analysis["issues"][0]
        self.assertEqual(security_issue["file_path"], "/src/UserService.cs")
        self.assertEqual(security_issue["line_number"], 5)  # RevealPassword method line
        self.assertIn("RevealPassword", security_issue["content"])
        self.assertEqual(security_issue["severity"], "error")
        self.assertEqual(security_issue["issue_type"], "security")
    
    async def test_review_and_confirm_shows_security_issues(self):
        """Test that review_and_confirm shows security issues in the response"""
        
        # Setup mock PR with security issue
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR with Security Issue"
        mock_pr.created_by = Mock(display_name="Test User")
        mock_pr.source_ref_name = "refs/heads/feature"
        mock_pr.target_ref_name = "refs/heads/main"
        
        mock_changes = [{
            "path": "/src/LoginService.cs",
            "change_type": "edit",
            "new_content": '''
public void ProcessLogin(string username, string password) {
    Console.WriteLine($"Login attempt: {username} with password {password}");
}''',
            "full_content": '''
public void ProcessLogin(string username, string password) {
    Console.WriteLine($"Login attempt: {username} with password {password}");
}'''
        }]
        
        # Setup mocks
        with patch.object(self.server.azure_client, 'get_pull_request', new_callable=AsyncMock) as mock_get_pr:
            with patch.object(self.server.azure_client, 'get_pull_request_changes', new_callable=AsyncMock) as mock_get_changes:
                mock_get_pr.return_value = mock_pr
                mock_get_changes.return_value = mock_changes
                
                # Call the method
                result = await self.server._setup_tools.__wrapped__(self.server).review_and_confirm(
                    repository_id="test_repo",
                    pull_request_id=123,
                    project="test_project",
                    organization="test_org"
                )
                
                # Verify security issues are mentioned in the response
                self.assertIn("SECURITY ANALYSIS:", result)
                self.assertIn("CRITICAL SECURITY ISSUES FOUND:", result)
                self.assertIn("password", result.lower())
    
    def test_security_detector_integration(self):
        """Test that SecurityDetector properly detects RevealPassword methods"""
        detector = SecurityDetector()
        
        test_content = '''
public class UserAccount {
    private string userPassword;
    
    public string RevealPassword() {
        return this.userPassword;
    }
    
    public override string ToString() {
        return $"User: password={userPassword}";
    }
}'''
        
        issues = detector.analyze_file_security("UserAccount.cs", test_content)
        
        # Should detect both RevealPassword and ToString issues
        self.assertGreaterEqual(len(issues), 2)
        
        # Check for RevealPassword detection
        reveal_issues = [i for i in issues if "RevealPassword" in i["content"]]
        self.assertEqual(len(reveal_issues), 1)
        self.assertEqual(reveal_issues[0]["line_number"], 5)
        self.assertEqual(reveal_issues[0]["severity"], "error")
        
        # Check for ToString detection  
        tostring_issues = [i for i in issues if "ToString" in i["content"]]
        self.assertEqual(len(tostring_issues), 1)
        self.assertEqual(tostring_issues[0]["line_number"], 9)
        self.assertEqual(tostring_issues[0]["severity"], "error")


if __name__ == '__main__':
    # Run async tests
    import asyncio
    
    async def run_async_tests():
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMCPSecurityIntegration)
        
        for test in suite:
            if hasattr(test._testMethodName, '__code__') and asyncio.iscoroutinefunction(getattr(test, test._testMethodName)):
                # This is an async test
                try:
                    await getattr(test, test._testMethodName)()
                    print(f"✓ {test._testMethodName}")
                except Exception as e:
                    print(f"✗ {test._testMethodName}: {e}")
            else:
                # Regular test
                try:
                    test.setUp()
                    getattr(test, test._testMethodName)()
                    print(f"✓ {test._testMethodName}")
                except Exception as e:
                    print(f"✗ {test._testMethodName}: {e}")
    
    asyncio.run(run_async_tests())