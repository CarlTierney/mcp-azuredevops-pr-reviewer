"""Unit tests for Azure DevOps client"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import asyncio
from azure_pr_reviewer.azure_client import AzureDevOpsClient
from azure_pr_reviewer.config import Settings


class TestAzureDevOpsClient(unittest.TestCase):
    """Test suite for AzureDevOpsClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.azure_organization = "test-org"
        self.mock_settings.azure_pat = "test-pat"
        self.mock_settings.azure_user_email = "test@example.com"
        self.mock_settings.azure_project = "test-project"
        
        with patch('azure_pr_reviewer.azure_client.Connection'):
            self.client = AzureDevOpsClient(self.mock_settings)
            self.client.git_client = Mock()
    
    def test_initialization(self):
        """Test client initialization"""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.settings, self.mock_settings)
    
    @patch('azure_pr_reviewer.azure_client.BasicAuthentication')
    @patch('azure_pr_reviewer.azure_client.Connection')
    def test_initialize_connection(self, mock_connection, mock_auth):
        """Test connection initialization"""
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_connection_instance = Mock()
        mock_connection.return_value = mock_connection_instance
        mock_connection_instance.clients.get_git_client.return_value = Mock()
        
        client = AzureDevOpsClient(self.mock_settings)
        
        mock_auth.assert_called_once_with('', 'test-pat')
        mock_connection.assert_called_once_with(
            base_url="https://dev.azure.com/test-org",
            creds=mock_auth_instance
        )
    
    def test_list_pull_requests(self):
        """Test listing pull requests"""
        mock_pr1 = Mock()
        mock_pr1.pull_request_id = 1
        mock_pr1.title = "Test PR 1"
        
        mock_pr2 = Mock()
        mock_pr2.pull_request_id = 2
        mock_pr2.title = "Test PR 2"
        
        self.client.git_client.get_pull_requests.return_value = [mock_pr1, mock_pr2]
        
        result = asyncio.run(self.client.list_pull_requests(
            "test-org", "test-project", "test-repo", "active"
        ))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pull_request_id, 1)
        self.assertEqual(result[1].pull_request_id, 2)
        
        self.client.git_client.get_pull_requests.assert_called_once()
    
    def test_list_pull_requests_error(self):
        """Test error handling in list_pull_requests"""
        self.client.git_client.get_pull_requests.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception) as context:
            asyncio.run(self.client.list_pull_requests(
                "test-org", "test-project", "test-repo", "active"
            ))
        
        self.assertIn("API Error", str(context.exception))
    
    def test_get_current_user_success(self):
        """Test getting current user information"""
        with patch('azure_pr_reviewer.azure_client.ProfileClient') as mock_profile_client_class:
            mock_profile_client = Mock()
            mock_profile = Mock()
            mock_profile.id = "user-123"
            mock_profile.display_name = "Test User"
            mock_profile.email_address = "test@example.com"
            mock_profile.unique_name = "test@example.com"
            
            self.client.connection.clients.get_profile_client.return_value = mock_profile_client
            mock_profile_client.get_profile.return_value = mock_profile
            
            result = asyncio.run(self.client.get_current_user())
            
            self.assertEqual(result["id"], "user-123")
            self.assertEqual(result["display_name"], "Test User")
            self.assertEqual(result["email"], "test@example.com")
            mock_profile_client.get_profile.assert_called_once_with("me")
    
    def test_get_current_user_fallback(self):
        """Test fallback when profile API fails"""
        with patch('azure_pr_reviewer.azure_client.ProfileClient') as mock_profile_client_class:
            mock_profile_client = Mock()
            mock_profile_client.get_profile.side_effect = Exception("Profile API failed")
            self.client.connection.clients.get_profile_client.return_value = mock_profile_client
            
            result = asyncio.run(self.client.get_current_user())
            
            self.assertEqual(result["email"], "test@example.com")
            self.assertEqual(result["display_name"], "test")
    
    def test_list_prs_needing_review(self):
        """Test listing PRs that need review"""
        # Mock PR with reviewer needing to review
        mock_pr1 = Mock()
        mock_pr1.pull_request_id = 1
        mock_pr1.title = "PR needing review"
        mock_reviewer = Mock()
        mock_reviewer.display_name = "Carl Tierney"
        mock_reviewer.unique_name = "test@example.com"
        mock_reviewer.vote = 0  # No vote yet
        mock_pr1.reviewers = [mock_reviewer]
        
        # Mock PR with no reviewers
        mock_pr2 = Mock()
        mock_pr2.pull_request_id = 2
        mock_pr2.title = "PR with no reviewers"
        mock_pr2.reviewers = []
        
        # Mock PR already approved
        mock_pr3 = Mock()
        mock_pr3.pull_request_id = 3
        mock_pr3.title = "Already approved PR"
        mock_reviewer2 = Mock()
        mock_reviewer2.display_name = "Carl Tierney"
        mock_reviewer2.unique_name = "test@example.com"
        mock_reviewer2.vote = 10  # Approved
        mock_pr3.reviewers = [mock_reviewer2]
        
        self.client.git_client.get_pull_requests.return_value = [mock_pr1, mock_pr2, mock_pr3]
        
        with patch.object(self.client, 'get_current_user') as mock_get_user:
            mock_get_user.return_value = {"email": "test@example.com"}
            
            result = asyncio.run(self.client.list_prs_needing_review(
                "test-org", "test-project", "test-repo"
            ))
        
        self.assertEqual(len(result), 2)  # Should return PR1 and PR2, not PR3
        self.assertEqual(result[0]["pr"].pull_request_id, 1)
        self.assertEqual(result[0]["reason"], "You need to review this PR (status: Not yet reviewed)")
        self.assertEqual(result[1]["pr"].pull_request_id, 2)
        self.assertEqual(result[1]["reason"], "No reviewers assigned")
    
    def test_get_pull_request(self):
        """Test getting a specific pull request"""
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        
        self.client.git_client.get_pull_request.return_value = mock_pr
        
        result = asyncio.run(self.client.get_pull_request(
            "test-org", "test-project", "test-repo", 123
        ))
        
        self.assertEqual(result.pull_request_id, 123)
        self.assertEqual(result.title, "Test PR")
        self.client.git_client.get_pull_request.assert_called_once_with(
            repository_id="test-repo",
            pull_request_id=123,
            project="test-project"
        )
    
    def test_get_pull_request_changes(self):
        """Test getting PR changes"""
        # Mock PR
        mock_pr = Mock()
        mock_pr.target_ref_name = "refs/heads/main"
        
        # Mock commit
        mock_commit = Mock()
        mock_commit.commit_id = "abc123"
        mock_commit.comment = "Feature commit"  # Add comment attribute
        
        # Mock change
        mock_change = Mock()
        mock_change.item = Mock()
        mock_change.item.path = "/src/test.cs"
        mock_change.item.is_folder = False  # Add is_folder attribute
        mock_change.change_type = "edit"
        mock_change.original_path = None
        
        mock_changes = Mock()
        mock_changes.changes = [mock_change]
        
        with patch.object(self.client, 'get_pull_request') as mock_get_pr:
            mock_get_pr.return_value = mock_pr
            self.client.git_client.get_pull_request_commits.return_value = [mock_commit]
            self.client.git_client.get_changes.return_value = mock_changes
            self.client.git_client.get_item_content.return_value = b"test content"
            
            result = asyncio.run(self.client.get_pull_request_changes(
                "test-org", "test-project", "test-repo", 123
            ))
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/src/test.cs")
        self.assertEqual(result[0]["change_type"], "edit")
        self.assertEqual(result[0]["new_content"], "test content")
    
    def test_add_pull_request_comments(self):
        """Test adding comments to a PR"""
        mock_thread = Mock()
        mock_thread.id = 1
        
        self.client.git_client.create_thread.return_value = mock_thread
        
        comments = [
            {
                "content": "Test comment",
                "file_path": "/src/test.cs",
                "line_number": 10
            },
            {
                "content": "General comment",
                "file_path": None,
                "line_number": None
            }
        ]
        
        result = asyncio.run(self.client.add_pull_request_comments(
            "test-org", "test-project", "test-repo", 123, comments
        ))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(self.client.git_client.create_thread.call_count, 2)
    
    def test_approve_pull_request(self):
        """Test approving a pull request"""
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        
        with patch.object(self.client, 'get_pull_request') as mock_get_pr:
            mock_get_pr.return_value = mock_pr
            with patch.object(self.client, 'add_pull_request_comments') as mock_add_comments:
                mock_add_comments.return_value = []
                
                result = asyncio.run(self.client.approve_pull_request(
                    "test-org", "test-project", "test-repo", 123
                ))
        
        self.assertEqual(result.pull_request_id, 123)
        mock_add_comments.assert_called_once()
        # Check that approval comment was added
        call_args = mock_add_comments.call_args[0]
        self.assertIn("approved", call_args[4][0]["content"].lower())


if __name__ == '__main__':
    unittest.main()