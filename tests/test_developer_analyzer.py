"""
Unit tests for DeveloperAnalyzer
"""

import unittest
import tempfile
import shutil
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer
from analyzers.developer_analyzer import DeveloperAnalyzer

class TestDeveloperAnalyzer(unittest.TestCase):
    
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
        self.analyzer = DeveloperAnalyzer(self.base_analyzer)
        
        # Setup test commits
        self.base_analyzer.commits = [
            {
                'commitId': 'abc123',
                'author': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'date': '2023-01-01T09:00:00Z'
                },
                'comment': 'Initial commit'
            },
            {
                'commitId': 'def456', 
                'author': {
                    'name': 'Jane Smith',
                    'email': 'jane@example.com',
                    'date': '2023-01-02T14:30:00Z'
                },
                'comment': 'Add new feature'
            }
        ]
        
        self.base_analyzer.detailed_commits = {
            'abc123': {
                'changes': [
                    {
                        'item': {'path': '/src/Program.cs', 'isFolder': False},
                        'changeType': 'add'
                    }
                ]
            },
            'def456': {
                'changes': [
                    {
                        'item': {'path': '/src/Feature.cs', 'isFolder': False},
                        'changeType': 'add'
                    }
                ]
            }
        }
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer.analyzer)
        self.assertEqual(self.analyzer.analyzer.org_name, "test_org")
    
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    @patch.object(BaseAnalyzer, 'get_cached_dataframe')
    def test_cached_developer_activity(self, mock_get_cached, mock_is_cached):
        """Test cached developer activity analysis"""
        mock_is_cached.return_value = True
        mock_df = pd.DataFrame({
            'Developer': ['john@example.com', 'jane@example.com'],
            'Total_Commits': [10, 8],
            'Total_Files_Changed': [25, 20],
            'LOC_Net_Change': [500, 300],
            'Primary_File_Type': ['csharp', 'sql'],
            'Most_Active_Day': ['Monday', 'Tuesday'],
            'Consistency_Ratio': [0.8, 0.7]
        })
        mock_get_cached.return_value = mock_df
        
        result = self.analyzer.analyze_developer_activity()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        mock_is_cached.assert_called_once_with('developer_activity')
    
    @patch.object(BaseAnalyzer, 'get_repository_id')
    @patch.object(BaseAnalyzer, 'classify_file_type')
    @patch.object(BaseAnalyzer, 'fetch_file_content')
    @patch.object(BaseAnalyzer, 'analyze_file_contents')
    @patch.object(BaseAnalyzer, 'calculate_cyclomatic_complexity')
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_fresh_developer_activity(self, mock_is_cached, mock_complexity, mock_analyze_contents,
                                    mock_fetch_content, mock_classify, mock_get_repo_id):
        """Test fresh developer activity analysis"""
        # Setup mocks
        mock_is_cached.return_value = False
        mock_get_repo_id.return_value = "repo123"
        mock_classify.return_value = 'csharp'
        mock_fetch_content.return_value = "public class Test { }"
        mock_analyze_contents.return_value = {
            'loc': 50, 'sloc': 40, 'lloc': 35, 'comments': 5, 'multi': 2, 'blank': 8
        }
        mock_complexity.return_value = 2.0
        
        result = self.analyzer.analyze_developer_activity()
        
        self.assertIsInstance(result, pd.DataFrame)
        if not result.empty:
            self.assertIn('Developer', result.columns)
            self.assertIn('Total_Commits', result.columns)
            self.assertIn('LOC_Net_Change', result.columns)
            
            # Check that we have data for our test developers
            developers = result['Developer'].tolist()
            self.assertIn('john@example.com', developers)
            self.assertIn('jane@example.com', developers)
    
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_cached_pull_request_metrics(self, mock_is_cached):
        """Test cached pull request metrics analysis"""
        mock_is_cached.return_value = True
        
        # Setup test pull requests
        self.base_analyzer.pull_requests = [
            {
                'pullRequestId': 1,
                'title': 'Test PR',
                'status': 'completed',
                'createdBy': {'name': 'John Doe', 'email': 'john@example.com'},
                'creationDate': '2023-01-01T10:00:00Z',
                'completionDate': '2023-01-01T11:00:00Z',
                'sourceRefName': 'refs/heads/feature',
                'targetRefName': 'refs/heads/main',
                'reviewers': [
                    {'vote': 10},  # Approved
                    {'vote': 0}    # No vote
                ]
            }
        ]
        
        with patch.object(self.base_analyzer, 'get_cached_dataframe') as mock_get_cached:
            mock_df = pd.DataFrame({
                'PR_ID': [1],
                'Title': ['Test PR'],
                'Status': ['completed'],
                'Author': ['john@example.com'],
                'Duration_Hours': [1.0],
                'Reviewer_Count': [2],
                'Approvals': [1]
            })
            mock_get_cached.return_value = mock_df
            
            result = self.analyzer.analyze_pull_request_metrics()
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)
    
    def test_empty_commits(self):
        """Test analysis with no commits"""
        self.base_analyzer.commits = []
        self.base_analyzer.detailed_commits = {}
        
        result = self.analyzer.analyze_developer_activity()
        
        self.assertIsInstance(result, pd.DataFrame)
    
    def test_empty_pull_requests(self):
        """Test PR analysis with no pull requests"""
        self.base_analyzer.pull_requests = []
        
        result = self.analyzer.analyze_pull_request_metrics()
        
        self.assertIsInstance(result, pd.DataFrame)
        # Should be empty since no PRs
        self.assertTrue(result.empty)
    
    def test_malformed_commit_data(self):
        """Test handling of malformed commit data"""
        # Add commit with missing/invalid data
        self.base_analyzer.commits.append({
            'commitId': 'malformed',
            'author': {},  # Missing name/email
            # Missing date
        })
        
        self.base_analyzer.detailed_commits['malformed'] = {
            'changes': [
                {
                    'item': {'path': '', 'isFolder': True},  # Empty path, is folder
                    'changeType': 'add'
                }
            ]
        }
        
        with patch.object(self.base_analyzer, 'is_analysis_cached', return_value=False):
            result = self.analyzer.analyze_developer_activity()
            
            # Should still return a DataFrame
            self.assertIsInstance(result, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
