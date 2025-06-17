"""
Unit tests for DataCollector
"""

import unittest
import tempfile
import shutil
import json
import os
from unittest.mock import Mock, patch

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer
from analyzers.data_collector import DataCollector

class TestDataCollector(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.base_analyzer = BaseAnalyzer(
            org_name="test_org",
            project_name="test_project",
            repo_name="test_repo",
            pat_token="test_token",
            data_dir=self.temp_dir
        )
        self.collector = DataCollector(self.base_analyzer)
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test collector initialization"""
        self.assertIsNotNone(self.collector.analyzer)
        self.assertEqual(self.collector.analyzer.org_name, "test_org")
    
    @patch('requests.get')
    @patch.object(BaseAnalyzer, 'get_repository_id')
    def test_collect_commits(self, mock_get_repo_id, mock_get):
        """Test commit collection"""
        mock_get_repo_id.return_value = "repo123"
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [
                {
                    'commitId': 'abc123',
                    'author': {'name': 'John Doe', 'email': 'john@example.com', 'date': '2023-01-01T12:00:00Z'},
                    'comment': 'Test commit'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test the internal _collect_commits method
        result = self.collector._collect_commits("repo123")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['commitId'], 'abc123')
    
    @patch('requests.get')
    @patch.object(BaseAnalyzer, 'get_repository_id')
    def test_collect_pull_requests(self, mock_get_repo_id, mock_get):
        """Test pull request collection"""
        mock_get_repo_id.return_value = "repo123"
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [
                {
                    'pullRequestId': 1,
                    'title': 'Test PR',
                    'status': 'completed',
                    'createdBy': {'name': 'John Doe', 'email': 'john@example.com'},
                    'creationDate': '2023-01-01T10:00:00Z'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test the internal _collect_pull_requests method
        result = self.collector._collect_pull_requests("repo123")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['pullRequestId'], 1)
    
    @patch('requests.get')
    def test_collect_detailed_commits(self, mock_get):
        """Test detailed commit collection"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'changes': [
                {
                    'item': {'path': '/src/Program.cs', 'isFolder': False},
                    'changeType': 'add'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test commits
        test_commits = [
            {'commitId': 'abc123'},
            {'commitId': 'def456'}
        ]
        
        # Test the internal _collect_detailed_commits method
        self.collector._collect_detailed_commits("repo123", test_commits)
        
        # Check that detailed commit files were created
        detailed_dir = os.path.join(self.temp_dir, "detailed_commits")
        self.assertTrue(os.path.exists(detailed_dir))
    
    def test_load_collected_data(self):
        """Test loading collected data from files"""
        # Create test data files
        commits_data = [
            {
                'commitId': 'abc123',
                'author': {'name': 'John Doe', 'email': 'john@example.com', 'date': '2023-01-01T12:00:00Z'},
                'comment': 'Test commit'
            }
        ]
        
        prs_data = [
            {
                'pullRequestId': 1,
                'title': 'Test PR',
                'status': 'completed'
            }
        ]
        
        # Save test data
        with open(os.path.join(self.temp_dir, "commits.json"), 'w') as f:
            json.dump(commits_data, f)
            
        with open(os.path.join(self.temp_dir, "pull_requests.json"), 'w') as f:
            json.dump(prs_data, f)
        
        # Create detailed commits directory and file
        detailed_dir = os.path.join(self.temp_dir, "detailed_commits")
        os.makedirs(detailed_dir, exist_ok=True)
        
        detailed_data = {'changes': []}
        with open(os.path.join(detailed_dir, "abc123.json"), 'w') as f:
            json.dump(detailed_data, f)
        
        # Test loading
        self.collector.load_collected_data()
        
        # Verify data was loaded
        self.assertEqual(len(self.base_analyzer.commits), 1)
        self.assertEqual(len(self.base_analyzer.pull_requests), 1)
        self.assertEqual(len(self.base_analyzer.detailed_commits), 1)
        self.assertEqual(self.base_analyzer.commits[0]['commitId'], 'abc123')
    
    def test_filter_commits_by_date(self):
        """Test date filtering of commits"""
        commits = [
            {
                'commitId': 'abc123',
                'author': {'date': '2023-01-01T12:00:00Z'}
            },
            {
                'commitId': 'def456', 
                'author': {'date': '2023-06-01T12:00:00Z'}
            },
            {
                'commitId': 'ghi789',
                'author': {'date': '2024-01-01T12:00:00Z'}
            }
        ]
        
        # Set date range
        self.base_analyzer.date_from_dt = self.base_analyzer.date_from_dt.replace(year=2023, month=1, day=1)
        self.base_analyzer.date_to_dt = self.base_analyzer.date_to_dt.replace(year=2023, month=12, day=31)
        
        filtered = self.collector._filter_commits_by_date(commits)
        
        # Should include 2023 commits but not 2024
        self.assertEqual(len(filtered), 2)
        commit_ids = [c['commitId'] for c in filtered]
        self.assertIn('abc123', commit_ids)
        self.assertIn('def456', commit_ids)
        self.assertNotIn('ghi789', commit_ids)
    
    def test_collect_work_items(self):
        """Test work item collection"""
        # Setup commits with work item references
        self.base_analyzer.commits = [
            {
                'commitId': 'abc123',
                'comment': 'Fix bug #123'
            },
            {
                'commitId': 'def456',
                'comment': 'Implement feature #456 and #789'
            }
        ]
        
        # Create commits.json file
        with open(os.path.join(self.temp_dir, "commits.json"), 'w') as f:
            json.dump(self.base_analyzer.commits, f)
        
        with patch('requests.get') as mock_get:
            # Mock API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'value': [
                    {'id': 123, 'title': 'Bug fix'},
                    {'id': 456, 'title': 'New feature'}
                ]
            }
            mock_get.return_value = mock_response
            
            result = self.collector._collect_work_items()
            
            self.assertIsInstance(result, list)
            # Should extract work item IDs from commit messages
            # and make API call to get work item details

if __name__ == '__main__':
    unittest.main()
