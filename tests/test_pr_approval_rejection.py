"""Test PR approval and rejection functionality"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from azure_pr_reviewer.server import AzurePRReviewerServer
from azure_pr_reviewer.config import Settings


class TestPRApprovalRejection(unittest.TestCase):
    """Test PR approval and rejection tools in MCP server"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.server = None
        with patch('azure_pr_reviewer.server.Settings') as mock_settings:
            with patch('azure_pr_reviewer.server.AzureDevOpsClient'):
                with patch('azure_pr_reviewer.server.CodeReviewer'):
                    mock_settings_instance = Mock(spec=Settings)
                    mock_settings_instance.azure_organization = "test_org"
                    mock_settings_instance.azure_project = "test_project"
                    mock_settings_instance.azure_pat = "test_pat"
                    mock_settings.return_value = mock_settings_instance
                    
                    self.server = AzurePRReviewerServer()
                    self.server.azure_client = AsyncMock()
    
    def test_approve_tool_requires_confirmation(self):
        """Test that approve tool requires confirmation"""
        # Get the approve_pull_request tool
        tools = [t for t in self.server.server._tools if t.name == "approve_pull_request"]
        self.assertEqual(len(tools), 1, "approve_pull_request tool not found")
        
        tool = tools[0]
        
        # Test without confirmation
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=123,
            confirm=False
        ))
        
        self.assertIn("APPROVAL CONFIRMATION REQUIRED", result)
        self.assertIn("confirm=True", result)
        
        # Verify no actual approval happened
        self.server.azure_client.approve_pull_request.assert_not_called()
    
    def test_approve_with_confirmation_succeeds(self):
        """Test that approval works with confirmation"""
        tools = [t for t in self.server.server._tools if t.name == "approve_pull_request"]
        tool = tools[0]
        
        # Mock PR details
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.created_by.display_name = "Test Author"
        
        self.server.azure_client.get_pull_request.return_value = mock_pr
        self.server.azure_client.approve_pull_request.return_value = mock_pr
        
        # Test with confirmation
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=123,
            confirm=True,
            comment="Looks good to me"
        ))
        
        self.assertIn("APPROVED", result)
        self.assertIn("PR #123", result)
        self.assertIn("Test PR", result)
        
        # Verify approval was called
        self.server.azure_client.approve_pull_request.assert_called_once()
    
    def test_reject_tool_requires_confirmation(self):
        """Test that reject tool requires confirmation"""
        tools = [t for t in self.server.server._tools if t.name == "reject_pull_request"]
        self.assertEqual(len(tools), 1, "reject_pull_request tool not found")
        
        tool = tools[0]
        
        # Test without confirmation
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=456,
            reason="Security vulnerabilities found",
            confirm=False
        ))
        
        self.assertIn("REJECTION CONFIRMATION REQUIRED", result)
        self.assertIn("confirm=True", result)
        
        # Verify no actual rejection happened
        self.server.azure_client.post_review_to_azure.assert_not_called()
    
    def test_reject_requires_detailed_reason(self):
        """Test that rejection requires a detailed reason"""
        tools = [t for t in self.server.server._tools if t.name == "reject_pull_request"]
        tool = tools[0]
        
        # Test with short reason
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=456,
            reason="Bad",
            confirm=True
        ))
        
        self.assertIn("at least 10 characters", result)
        self.server.azure_client.post_review_to_azure.assert_not_called()
    
    def test_reject_with_confirmation_succeeds(self):
        """Test that rejection works with confirmation and valid reason"""
        tools = [t for t in self.server.server._tools if t.name == "reject_pull_request"]
        tool = tools[0]
        
        # Mock PR details
        mock_pr = Mock()
        mock_pr.pull_request_id = 456
        mock_pr.title = "Problematic PR"
        mock_pr.created_by.display_name = "Test Author"
        
        self.server.azure_client.get_pull_request.return_value = mock_pr
        self.server.azure_client.post_review_to_azure.return_value = {"comments_posted": 1}
        self.server.azure_client.add_pull_request_comments.return_value = []
        self.server.azure_client._get_timestamp.return_value = "2024-01-15 10:00:00 UTC"
        
        # Test with confirmation and valid reason
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=456,
            reason="Critical security vulnerabilities found in authentication module",
            confirm=True,
            require_changes=True
        ))
        
        self.assertIn("REJECTED", result)
        self.assertIn("PR #456", result)
        self.assertIn("Problematic PR", result)
        
        # Verify rejection was called
        self.server.azure_client.post_review_to_azure.assert_called_once()
        
        # Check review data
        call_args = self.server.azure_client.post_review_to_azure.call_args[0]
        review_data = call_args[4]
        self.assertEqual(review_data["approved"], False)
        self.assertEqual(review_data["severity"], "critical")
        self.assertIn("REJECTED", review_data["summary"])
    
    def test_set_vote_with_valid_values(self):
        """Test set_pr_vote tool with valid vote values"""
        tools = [t for t in self.server.server._tools if t.name == "set_pr_vote"]
        self.assertEqual(len(tools), 1, "set_pr_vote tool not found")
        
        tool = tools[0]
        
        self.server.azure_client.update_pull_request_vote.return_value = None
        
        # Test different vote values
        vote_tests = [
            ("approve", 10),
            ("approve_with_suggestions", 5),
            ("no_vote", 0),
            ("wait_for_author", -5),
            ("reject", -10)
        ]
        
        for vote_string, expected_value in vote_tests:
            with self.subTest(vote=vote_string):
                result = asyncio.run(tool.function(
                    repository_id="test_repo",
                    pull_request_id=789,
                    vote=vote_string
                ))
                
                self.assertIn("Vote updated successfully", result)
                self.assertIn(f"Vote value: {expected_value}", result)
                
                # Verify correct vote value was passed
                call_args = self.server.azure_client.update_pull_request_vote.call_args[0]
                self.assertEqual(call_args[4], expected_value)
    
    def test_set_vote_with_invalid_value(self):
        """Test set_pr_vote tool rejects invalid vote values"""
        tools = [t for t in self.server.server._tools if t.name == "set_pr_vote"]
        tool = tools[0]
        
        # Test with invalid vote
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=789,
            vote="maybe"
        ))
        
        self.assertIn("Invalid vote", result)
        self.assertIn("Must be one of", result)
        
        # Verify no vote update happened
        self.server.azure_client.update_pull_request_vote.assert_not_called()
    
    def test_set_vote_with_comment(self):
        """Test set_pr_vote tool with optional comment"""
        tools = [t for t in self.server.server._tools if t.name == "set_pr_vote"]
        tool = tools[0]
        
        self.server.azure_client.update_pull_request_vote.return_value = None
        self.server.azure_client.add_pull_request_comments.return_value = []
        
        # Test with comment
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=789,
            vote="approve_with_suggestions",
            comment="Great work! Just a few minor suggestions."
        ))
        
        self.assertIn("Vote updated successfully", result)
        self.assertIn("Comment added", result)
        
        # Verify comment was posted
        self.server.azure_client.add_pull_request_comments.assert_called_once()
        
        # Check comment content
        call_args = self.server.azure_client.add_pull_request_comments.call_args[0]
        comments = call_args[4]
        self.assertEqual(len(comments), 1)
        self.assertIn("Vote Updated", comments[0]["content"])
        self.assertIn("Great work", comments[0]["content"])
        self.assertIn("Azure PR Reviewer v2.0.0", comments[0]["content"])
    
    def test_rejection_includes_version_signature(self):
        """Test that rejection comments include version signature"""
        tools = [t for t in self.server.server._tools if t.name == "reject_pull_request"]
        tool = tools[0]
        
        # Mock PR and client
        mock_pr = Mock()
        mock_pr.pull_request_id = 999
        mock_pr.title = "Test PR"
        mock_pr.created_by.display_name = "Author"
        
        self.server.azure_client.get_pull_request.return_value = mock_pr
        self.server.azure_client.post_review_to_azure.return_value = {"comments_posted": 1}
        self.server.azure_client.add_pull_request_comments.return_value = []
        self.server.azure_client._get_timestamp.return_value = "2024-01-15 10:00:00 UTC"
        
        # Perform rejection
        result = asyncio.run(tool.function(
            repository_id="test_repo",
            pull_request_id=999,
            reason="Multiple critical issues found in the implementation",
            confirm=True
        ))
        
        # Check that rejection comment was posted
        self.server.azure_client.add_pull_request_comments.assert_called_once()
        
        # Verify signature in comment
        call_args = self.server.azure_client.add_pull_request_comments.call_args[0]
        comments = call_args[4]
        self.assertEqual(len(comments), 1)
        comment_content = comments[0]["content"]
        
        self.assertIn("Azure PR Reviewer v2.0.0", comment_content)
        self.assertIn("Timestamp:", comment_content)


if __name__ == '__main__':
    unittest.main()