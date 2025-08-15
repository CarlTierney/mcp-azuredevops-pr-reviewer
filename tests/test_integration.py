"""Integration tests for Azure PR Reviewer"""

import unittest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from azure_pr_reviewer.server import AzurePRReviewerServer
from azure_pr_reviewer.azure_client import AzureDevOpsClient
from azure_pr_reviewer.code_reviewer import CodeReviewer
from azure_pr_reviewer.config import Settings
from azure_pr_reviewer.file_type_detector import FileTypeDetector, FileType


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete PR review workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.azure_organization = "test-org"
        self.mock_settings.azure_pat = "test-pat"
        self.mock_settings.azure_project = "test-project"
        self.mock_settings.azure_user_email = "test@example.com"
        self.mock_settings.custom_review_prompt_file = None
        self.mock_settings.auto_approve_threshold = 0.9
        self.mock_settings.max_file_size_kb = 500
        self.mock_settings.validate_settings = Mock(return_value=True)
    
    @patch('azure_pr_reviewer.azure_client.Connection')
    @patch('azure_pr_reviewer.azure_client.BasicAuthentication')
    def test_full_pr_review_workflow(self, mock_auth, mock_connection):
        """Test the complete PR review workflow from listing to commenting"""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_connection_instance = Mock()
        mock_connection.return_value = mock_connection_instance
        mock_git_client = Mock()
        mock_connection_instance.clients.get_git_client.return_value = mock_git_client
        
        # Create client and reviewer
        client = AzureDevOpsClient(self.mock_settings)
        reviewer = CodeReviewer(self.mock_settings)
        
        # Step 1: List PRs needing review
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Feature: Add new functionality"
        mock_pr.description = "This PR adds new features"
        mock_pr.source_ref_name = "refs/heads/feature-branch"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.status = "active"
        mock_pr.creation_date = Mock()
        mock_pr.creation_date.isoformat.return_value = "2024-01-01T00:00:00"
        
        mock_creator = Mock()
        mock_creator.display_name = "John Doe"
        mock_pr.created_by = mock_creator
        
        mock_reviewer_user = Mock()
        mock_reviewer_user.display_name = "Test User"
        mock_reviewer_user.unique_name = "test@example.com"
        mock_reviewer_user.vote = 0  # Not yet reviewed
        mock_pr.reviewers = [mock_reviewer_user]
        
        mock_git_client.get_pull_requests.return_value = [mock_pr]
        
        # Mock get_current_user
        with patch.object(client, 'get_current_user') as mock_get_user:
            mock_get_user.return_value = {"email": "test@example.com", "display_name": "Test User"}
            
            prs_needing_review = asyncio.run(client.list_prs_needing_review(
                "test-org", "test-project", "test-repo"
            ))
        
        self.assertEqual(len(prs_needing_review), 1)
        self.assertEqual(prs_needing_review[0]["pr"].pull_request_id, 123)
        
        # Step 2: Get PR details and changes
        mock_git_client.get_pull_request.return_value = mock_pr
        
        pr_details = asyncio.run(client.get_pull_request(
            "test-org", "test-project", "test-repo", 123
        ))
        
        self.assertEqual(pr_details.pull_request_id, 123)
        
        # Mock commits and changes
        mock_commit = Mock()
        mock_commit.commit_id = "abc123def456"
        mock_commit.comment = "Fix calculation bug"
        mock_git_client.get_pull_request_commits.return_value = [mock_commit]
        
        mock_change1 = Mock()
        mock_change1.item = Mock()
        mock_change1.item.path = "/src/Calculator.cs"
        mock_change1.item.is_folder = False
        mock_change1.change_type = "edit"
        mock_change1.original_path = None
        
        mock_change2 = Mock()
        mock_change2.item = Mock()
        mock_change2.item.path = "/tests/CalculatorTests.cs"
        mock_change2.item.is_folder = False
        mock_change2.change_type = "add"
        mock_change2.original_path = None
        
        mock_changes_response = Mock()
        mock_changes_response.changes = [mock_change1, mock_change2]
        mock_git_client.get_changes.return_value = mock_changes_response
        
        # Mock file content - return generators as the API does
        mock_git_client.get_item_content.side_effect = [
            iter([b"public class Calculator { public int Add(int a, int b) { return a - b; } }"]),  # New content with bug!
            iter([b"public class Calculator { public int Add(int a, int b) { return a + b; } }"]),  # Old content (correct)
            iter([b"[Test] public void TestAdd() { Assert.AreEqual(5, calculator.Add(2, 3)); }"])   # New test file
        ]
        
        changes = asyncio.run(client.get_pull_request_changes(
            "test-org", "test-project", "test-repo", 123
        ))
        
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0]["path"], "/src/Calculator.cs")
        self.assertEqual(changes[1]["path"], "/tests/CalculatorTests.cs")
        
        # Step 3: Prepare review data
        review_data = reviewer.prepare_review_data(pr_details, changes)
        
        self.assertEqual(review_data.pr_details["pull_request_id"], 123)
        self.assertEqual(len(review_data.changes), 2)
        self.assertIn("csharp", review_data.file_type_summary)
        self.assertIn("test_csharp", review_data.file_type_summary)
        
        # Step 4: Simulate review response
        review_response = {
            "approved": False,
            "severity": "critical",
            "summary": "Found a critical bug in the Calculator class",
            "comments": [
                {
                    "file_path": "/src/Calculator.cs",
                    "line_number": 1,
                    "content": "CRITICAL: The Add method returns subtraction instead of addition!",
                    "severity": "error"
                },
                {
                    "file_path": "/tests/CalculatorTests.cs",
                    "line_number": 1,
                    "content": "Good test coverage for the Add method",
                    "severity": "info"
                }
            ]
        }
        
        parsed_review = reviewer.parse_review_response(review_response)
        
        self.assertFalse(parsed_review["approved"])
        self.assertEqual(parsed_review["severity"], "critical")
        self.assertEqual(len(parsed_review["comments"]), 2)
        
        # Step 5: Post comments to PR
        mock_thread1 = Mock()
        mock_thread1.id = 1
        mock_thread2 = Mock()
        mock_thread2.id = 2
        
        mock_git_client.create_thread.side_effect = [mock_thread1, mock_thread2]
        
        threads = asyncio.run(client.add_pull_request_comments(
            "test-org", "test-project", "test-repo", 123,
            parsed_review["comments"]
        ))
        
        self.assertEqual(len(threads), 2)
        self.assertEqual(mock_git_client.create_thread.call_count, 2)
    
    def test_file_type_detection_in_review_flow(self):
        """Test that file type detection properly influences review prompts"""
        reviewer = CodeReviewer(self.mock_settings)
        
        # Create a mixed PR with different file types
        mock_pr = Mock()
        mock_pr.pull_request_id = 456
        mock_pr.title = "Mixed language PR"
        mock_pr.description = "Contains C#, JavaScript, and SQL"
        mock_pr.source_ref_name = "refs/heads/mixed-feature"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.status = "active"
        mock_pr.created_by = Mock()
        mock_pr.created_by.display_name = "Developer"
        
        changes = [
            {
                "path": "/src/DataAccess.cs",
                "change_type": "edit",
                "new_content": "public class DataAccess { }",
                "old_content": "public class OldDataAccess { }"
            },
            {
                "path": "/wwwroot/app.js",
                "change_type": "add",
                "new_content": "const app = () => { console.log('app'); };"
            },
            {
                "path": "/db/migrations/001_init.sql",
                "change_type": "add",
                "new_content": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"
            },
            {
                "path": "/tests/DataAccessTests.cs",
                "change_type": "add",
                "new_content": "[Test] public void TestDataAccess() { }"
            }
        ]
        
        # Prepare review data
        review_data = reviewer.prepare_review_data(mock_pr, changes)
        
        # Verify file types were correctly detected
        self.assertIn("csharp", review_data.file_type_summary)
        self.assertIn("javascript", review_data.file_type_summary)
        self.assertIn("sql", review_data.file_type_summary)
        self.assertIn("test_csharp", review_data.file_type_summary)
        
        # Verify the review prompt contains file-type specific instructions
        self.assertIn("C# Files", review_data.review_prompt)
        self.assertIn("JavaScript Files", review_data.review_prompt)
        self.assertIn("SQL Files", review_data.review_prompt)
        
        # Check that mixed review is triggered
        file_types = FileTypeDetector.analyze_pr_files(changes)
        should_use_mixed = FileTypeDetector.should_use_mixed_review(changes)
        self.assertTrue(should_use_mixed)
    
    def test_package_file_review_flow(self):
        """Test review flow for package management files"""
        reviewer = CodeReviewer(self.mock_settings)
        
        mock_pr = Mock()
        mock_pr.pull_request_id = 789
        mock_pr.title = "Update dependencies"
        mock_pr.description = "Security updates for packages"
        mock_pr.source_ref_name = "refs/heads/update-deps"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.status = "active"
        mock_pr.created_by = Mock()
        mock_pr.created_by.display_name = "Security Bot"
        
        changes = [
            {
                "path": "package.json",
                "change_type": "edit",
                "new_content": '{"dependencies": {"react": "^18.0.0"}}',
                "old_content": '{"dependencies": {"react": "^17.0.0"}}'
            },
            {
                "path": "MyProject.csproj",
                "change_type": "edit",
                "new_content": '<PackageReference Include="Newtonsoft.Json" Version="13.0.2" />',
                "old_content": '<PackageReference Include="Newtonsoft.Json" Version="12.0.3" />'
            },
            {
                "path": "requirements.txt",
                "change_type": "edit",
                "new_content": "django==4.2.0\nrequests==2.31.0",
                "old_content": "django==3.2.0\nrequests==2.28.0"
            }
        ]
        
        review_data = reviewer.prepare_review_data(mock_pr, changes)
        
        # Verify package file types were detected
        self.assertIn("package_javascript", review_data.file_type_summary)
        self.assertIn("package_csharp", review_data.file_type_summary)
        self.assertIn("package_python", review_data.file_type_summary)
        
        # Verify appropriate prompts would be selected
        file_types = FileTypeDetector.analyze_pr_files(changes)
        for file_type in file_types:
            prompt_file = FileTypeDetector.get_prompt_file_for_type(file_type)
            self.assertIn("packages", prompt_file)
    
    @patch('azure_pr_reviewer.server.FastMCP')
    @patch('azure_pr_reviewer.server.AzureDevOpsClient')
    @patch('azure_pr_reviewer.server.CodeReviewer')
    def test_mcp_server_integration(self, mock_reviewer_class, mock_client_class, mock_mcp):
        """Test MCP server integration"""
        # Setup mocks
        mock_mcp_instance = Mock()
        mock_mcp.return_value = mock_mcp_instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_reviewer = Mock()
        mock_reviewer_class.return_value = mock_reviewer
        
        # Create server with mocked settings
        with patch('azure_pr_reviewer.server.Settings') as mock_settings_class:
            mock_settings_class.return_value = self.mock_settings
            server = AzurePRReviewerServer()
        
        # Verify server was initialized
        self.assertIsNotNone(server)
        self.assertEqual(server.settings, self.mock_settings)
        self.assertEqual(server.azure_client, mock_client)
        self.assertEqual(server.code_reviewer, mock_reviewer)
        
        # Verify MCP server was created
        mock_mcp.assert_called_once_with("azure-pr-reviewer")
        
        # Verify settings were validated
        self.mock_settings.validate_settings.assert_called_once()
    
    def test_error_recovery_workflow(self):
        """Test error handling and recovery in the review workflow"""
        with patch('azure_pr_reviewer.azure_client.Connection') as mock_connection:
            mock_connection_instance = Mock()
            mock_connection.return_value = mock_connection_instance
            mock_git_client = Mock()
            mock_connection_instance.clients.get_git_client.return_value = mock_git_client
            
            client = AzureDevOpsClient(self.mock_settings)
            reviewer = CodeReviewer(self.mock_settings)
            
            # Simulate API error when listing PRs
            mock_git_client.get_pull_requests.side_effect = Exception("API rate limit exceeded")
            
            with self.assertRaises(Exception) as context:
                asyncio.run(client.list_pull_requests(
                    "test-org", "test-project", "test-repo", "active"
                ))
            
            self.assertIn("API rate limit", str(context.exception))
            
            # Reset and test partial data handling
            mock_git_client.get_pull_requests.side_effect = None
            mock_pr = Mock()
            mock_pr.pull_request_id = 999
            mock_pr.title = None  # Missing title
            mock_pr.description = None  # Missing description
            mock_pr.source_ref_name = "refs/heads/broken"
            mock_pr.target_ref_name = "refs/heads/main"
            mock_pr.created_by = None  # Missing creator
            mock_pr.status = "active"
            
            # Should handle missing data gracefully
            review_data = reviewer.prepare_review_data(mock_pr, [])
            
            self.assertEqual(review_data.pr_details["title"], None)
            self.assertEqual(review_data.pr_details["description"], "No description provided")
            self.assertEqual(review_data.pr_details["created_by"], "Unknown")


if __name__ == '__main__':
    unittest.main()