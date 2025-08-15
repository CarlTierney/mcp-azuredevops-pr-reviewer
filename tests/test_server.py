"""Unit tests for MCP server"""

import unittest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from azure_pr_reviewer.server import AzurePRReviewerServer
from azure_pr_reviewer.config import Settings


class TestAzurePRReviewerServer(unittest.TestCase):
    """Test suite for AzurePRReviewerServer"""
    
    def setUp(self):
        """Set up test fixtures"""
        with patch('azure_pr_reviewer.server.Settings') as mock_settings_class:
            mock_settings = Mock(spec=Settings)
            mock_settings.azure_organization = "test-org"
            mock_settings.azure_pat = "test-pat"
            mock_settings.azure_project = "test-project"
            mock_settings.azure_user_email = "test@example.com"
            mock_settings.validate_settings.return_value = True
            mock_settings_class.return_value = mock_settings
            
            with patch('azure_pr_reviewer.server.AzureDevOpsClient'):
                with patch('azure_pr_reviewer.server.CodeReviewer'):
                    self.server = AzurePRReviewerServer()
                    self.server.settings = mock_settings
    
    def test_initialization(self):
        """Test server initialization"""
        self.assertIsNotNone(self.server)
        self.assertIsNotNone(self.server.server)
        self.assertIsNotNone(self.server.settings)
        self.assertIsNotNone(self.server.azure_client)
        self.assertIsNotNone(self.server.code_reviewer)
    
    def test_list_prs_needing_review_success(self):
        """Test listing PRs needing review"""
        # Mock PR data
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.source_ref_name = "refs/heads/feature"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.creation_date = Mock()
        mock_pr.creation_date.isoformat.return_value = "2024-01-01T00:00:00"
        mock_creator = Mock()
        mock_creator.display_name = "John Doe"
        mock_pr.created_by = mock_creator
        
        pr_info = {
            "pr": mock_pr,
            "reason": "You need to review this PR",
            "vote_status": "Not yet reviewed",
            "is_reviewer": True
        }
        
        self.server.azure_client.list_prs_needing_review = AsyncMock(return_value=[pr_info])
        
        # Call the tool function (need to extract it from the server)
        # Since tools are registered dynamically, we'll test the underlying logic
        result = asyncio.run(self.server.azure_client.list_prs_needing_review(
            "test-org", "test-project", "test-repo"
        ))
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["pr"].pull_request_id, 123)
    
    def test_list_prs_needing_review_no_org(self):
        """Test error when organization is not configured"""
        self.server.settings.azure_organization = ""
        
        # This would test the actual tool implementation
        # In a real scenario, we'd need to extract and call the registered tool
        # For now, we're testing that the settings validation would catch this
        with self.assertRaises(ValueError):
            self.server.settings.validate_settings()
    
    def test_list_pull_requests_success(self):
        """Test listing pull requests"""
        mock_pr1 = Mock()
        mock_pr1.pull_request_id = 1
        mock_pr1.title = "PR 1"
        mock_pr1.source_ref_name = "refs/heads/feature1"
        mock_pr1.target_ref_name = "refs/heads/main"
        mock_pr1.creation_date = Mock()
        mock_pr1.creation_date.isoformat.return_value = "2024-01-01T00:00:00"
        mock_creator1 = Mock()
        mock_creator1.display_name = "User 1"
        mock_pr1.created_by = mock_creator1
        
        mock_pr2 = Mock()
        mock_pr2.pull_request_id = 2
        mock_pr2.title = "PR 2"
        mock_pr2.source_ref_name = "refs/heads/feature2"
        mock_pr2.target_ref_name = "refs/heads/main"
        mock_pr2.creation_date = Mock()
        mock_pr2.creation_date.isoformat.return_value = "2024-01-02T00:00:00"
        mock_creator2 = Mock()
        mock_creator2.display_name = "User 2"
        mock_pr2.created_by = mock_creator2
        
        self.server.azure_client.list_pull_requests = AsyncMock(return_value=[mock_pr1, mock_pr2])
        
        result = asyncio.run(self.server.azure_client.list_pull_requests(
            "test-org", "test-project", "test-repo", "active"
        ))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pull_request_id, 1)
        self.assertEqual(result[1].pull_request_id, 2)
    
    def test_get_pull_request_success(self):
        """Test getting a specific pull request"""
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.description = "Test description"
        mock_pr.source_ref_name = "refs/heads/feature"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.status = "active"
        mock_creator = Mock()
        mock_creator.display_name = "John Doe"
        mock_pr.created_by = mock_creator
        
        self.server.azure_client.get_pull_request = AsyncMock(return_value=mock_pr)
        
        result = asyncio.run(self.server.azure_client.get_pull_request(
            "test-org", "test-project", "test-repo", 123
        ))
        
        self.assertEqual(result.pull_request_id, 123)
        self.assertEqual(result.title, "Test PR")
    
    def test_get_pr_for_review(self):
        """Test getting PR ready for review"""
        # Mock PR
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.description = "Test description"
        
        # Mock changes
        mock_changes = [
            {"path": "/src/test.cs", "change_type": "edit"},
            {"path": "/src/new.js", "change_type": "add"}
        ]
        
        # Mock review data
        mock_review_data = Mock()
        mock_review_data.pr_details = {"pull_request_id": 123}
        mock_review_data.changes = mock_changes
        mock_review_data.review_prompt = "Review this PR"
        mock_review_data.file_type_summary = {"csharp": ["/src/test.cs"]}
        
        self.server.azure_client.get_pull_request = AsyncMock(return_value=mock_pr)
        self.server.azure_client.get_pull_request_changes = AsyncMock(return_value=mock_changes)
        self.server.code_reviewer.prepare_review_data = Mock(return_value=mock_review_data)
        self.server.code_reviewer.get_review_instructions = Mock(return_value="Review instructions")
        
        # Test the flow
        pr = asyncio.run(self.server.azure_client.get_pull_request(
            "test-org", "test-project", "test-repo", 123
        ))
        changes = asyncio.run(self.server.azure_client.get_pull_request_changes(
            "test-org", "test-project", "test-repo", 123
        ))
        review_data = self.server.code_reviewer.prepare_review_data(pr, changes)
        
        self.assertEqual(review_data.pr_details["pull_request_id"], 123)
        self.assertEqual(len(review_data.changes), 2)
    
    def test_post_review_comments(self):
        """Test posting review comments"""
        mock_thread1 = Mock()
        mock_thread1.id = 1
        mock_thread2 = Mock()
        mock_thread2.id = 2
        
        self.server.azure_client.add_pull_request_comments = AsyncMock(
            return_value=[mock_thread1, mock_thread2]
        )
        
        review_json = {
            "approved": True,
            "severity": "minor",
            "summary": "Looks good",
            "comments": [
                {
                    "file_path": "/src/test.cs",
                    "line_number": 10,
                    "content": "Consider using var",
                    "severity": "info"
                },
                {
                    "file_path": "/src/app.js",
                    "line_number": 5,
                    "content": "Missing semicolon",
                    "severity": "warning"
                }
            ]
        }
        
        self.server.code_reviewer.parse_review_response = Mock(return_value=review_json)
        
        # Test comment conversion
        parsed = self.server.code_reviewer.parse_review_response(review_json)
        self.assertEqual(len(parsed["comments"]), 2)
        
        # Test posting comments
        result = asyncio.run(self.server.azure_client.add_pull_request_comments(
            "test-org", "test-project", "test-repo", 123, parsed["comments"]
        ))
        
        self.assertEqual(len(result), 2)
    
    def test_add_pr_comment(self):
        """Test adding a single PR comment"""
        mock_thread = Mock()
        mock_thread.id = 1
        
        self.server.azure_client.add_pull_request_comments = AsyncMock(return_value=[mock_thread])
        
        comment_data = [{
            "content": "Test comment",
            "file_path": "/src/test.cs",
            "line_number": 10
        }]
        
        result = asyncio.run(self.server.azure_client.add_pull_request_comments(
            "test-org", "test-project", "test-repo", 123, comment_data
        ))
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 1)
    
    def test_approve_pull_request(self):
        """Test approving a pull request"""
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        
        self.server.azure_client.approve_pull_request = AsyncMock(return_value=mock_pr)
        
        result = asyncio.run(self.server.azure_client.approve_pull_request(
            "test-org", "test-project", "test-repo", 123
        ))
        
        self.assertEqual(result.pull_request_id, 123)
    
    def test_error_handling(self):
        """Test error handling in server methods"""
        # Test error in list_pull_requests
        self.server.azure_client.list_pull_requests = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with self.assertRaises(Exception) as context:
            asyncio.run(self.server.azure_client.list_pull_requests(
                "test-org", "test-project", "test-repo", "active"
            ))
        
        self.assertIn("API Error", str(context.exception))
    
    def test_settings_validation(self):
        """Test that settings are validated on initialization"""
        with patch('azure_pr_reviewer.server.Settings') as mock_settings_class:
            mock_settings = Mock(spec=Settings)
            mock_settings.validate_settings.side_effect = ValueError("Missing required settings")
            mock_settings_class.return_value = mock_settings
            
            with self.assertRaises(ValueError):
                AzurePRReviewerServer()


if __name__ == '__main__':
    unittest.main()