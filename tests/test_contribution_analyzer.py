"""
Unit tests for ContributionAnalyzer
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
from analyzers.contribution_analyzer import ContributionAnalyzer

class TestContributionAnalyzer(unittest.TestCase):
    
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
        self.analyzer = ContributionAnalyzer(self.base_analyzer)
        
        # Setup test data
        self.base_analyzer.commits = [
            {
                'commitId': 'abc123',
                'author': {
                    'name': 'John Doe',
                    'email': 'john@example.com', 
                    'date': '2023-01-01T09:00:00Z'
                },
                'comment': 'Initial commit with detailed description'
            },
            {
                'commitId': 'def456',
                'author': {
                    'name': 'John Doe', 
                    'email': 'john@example.com',
                    'date': '2023-01-01T15:30:00Z'
                },
                'comment': 'Fix bug'
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
                        'item': {'path': '/src/Utils.cs', 'isFolder': False},
                        'changeType': 'edit'
                    }
                ]
            }
        }
        
        self.base_analyzer.pull_requests = [
            {
                'pullRequestId': 1,
                'createdBy': {'name': 'John Doe', 'email': 'john@example.com'},
                'reviewers': [
                    {'vote': 10, 'displayName': 'Jane Smith', 'uniqueName': 'jane@example.com'}
                ]
            }
        ]
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer.analyzer)
        self.assertEqual(self.analyzer.analyzer.org_name, "test_org")
    
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    @patch.object(BaseAnalyzer, 'get_cached_dataframe')
    def test_cached_commit_timing(self, mock_get_cached, mock_is_cached):
        """Test cached commit timing analysis"""
        mock_is_cached.return_value = True
        mock_df = pd.DataFrame({
            'Developer': ['john@example.com'],
            'Total_Commits': [2],
            'LOC_Net_Change': [150],
            'Non_Whitespace_Ratio': [0.8],
            'Business_Hours_Commits_Pct': [50.0],
            'Overall_Contribution_Score': [75.5]
        })
        mock_get_cached.return_value = mock_df
        
        result = self.analyzer.analyze_commit_timing()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        mock_is_cached.assert_called_once_with('contribution_metrics')
    
    @patch.object(BaseAnalyzer, 'get_repository_id')
    @patch.object(BaseAnalyzer, 'classify_file_type')
    @patch.object(BaseAnalyzer, 'fetch_file_content')
    @patch.object(BaseAnalyzer, 'analyze_file_contents')
    @patch.object(BaseAnalyzer, 'calculate_cyclomatic_complexity')
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_fresh_commit_timing(self, mock_is_cached, mock_complexity, mock_analyze_contents,
                                mock_fetch_content, mock_classify, mock_get_repo_id):
        """Test fresh commit timing analysis"""
        # Setup mocks
        mock_is_cached.return_value = False
        mock_get_repo_id.return_value = "repo123"
        mock_classify.return_value = 'csharp'
        mock_fetch_content.return_value = "public class Test { public void Method() { } }"
        mock_analyze_contents.return_value = {
            'loc': 100, 'sloc': 80, 'lloc': 70, 'comments': 10, 'multi': 5, 'blank': 15
        }
        mock_complexity.return_value = 3.0
        
        result = self.analyzer.analyze_commit_timing()
        
        self.assertIsInstance(result, pd.DataFrame)
        if not result.empty:
            self.assertIn('Developer', result.columns)
            self.assertIn('Total_Commits', result.columns)
            self.assertIn('Business_Hours_Commits_Pct', result.columns)
            self.assertIn('Overall_Contribution_Score', result.columns)
            
            # Check developer is in results
            developers = result['Developer'].tolist()
            self.assertIn('john@example.com', developers)
    
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_cached_advanced_contributions(self, mock_is_cached):
        """Test cached advanced contributions analysis"""
        mock_is_cached.return_value = True
        
        with patch.object(self.base_analyzer, 'get_cached_dataframe') as mock_get_cached:
            mock_df = pd.DataFrame({
                'Developer': ['john@example.com'],
                'Productivity_Score': [80.0],
                'Quality_Score': [75.0],
                'Knowledge_Sharing_Score': [70.0],
                'Overall_Score': [75.0]
            })
            mock_get_cached.return_value = mock_df
            
            result = self.analyzer.analyze_advanced_developer_contributions()
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)
            mock_is_cached.assert_called_once_with('advanced_developer_contributions')
    
    def test_timing_calculation(self):
        """Test timing calculation between commits"""
        # This tests the logic for calculating time differences between commits
        commits_with_dates = [
            {
                'author': 'john@example.com',
                'date': datetime(2023, 1, 1, 9, 0, 0),
                'commit_id': 'abc123'
            },
            {
                'author': 'john@example.com', 
                'date': datetime(2023, 1, 1, 15, 30, 0),
                'commit_id': 'def456'
            }
        ]
        
        # Calculate time difference
        time_diff = (commits_with_dates[1]['date'] - commits_with_dates[0]['date']).total_seconds() / 3600
        self.assertEqual(time_diff, 6.5)  # 6.5 hours difference
    
    def test_work_pattern_analysis(self):
        """Test work pattern analysis"""
        commit_dates = [
            datetime(2023, 1, 1, 9, 0, 0),   # Sunday, 9 AM (weekend, business hours)
            datetime(2023, 1, 2, 14, 0, 0),  # Monday, 2 PM (weekday, business hours)
            datetime(2023, 1, 2, 22, 0, 0),  # Monday, 10 PM (weekday, night)
            datetime(2023, 1, 7, 10, 0, 0),  # Saturday, 10 AM (weekend, business hours)
        ]
        
        business_hours_commits = 0
        weekend_commits = 0
        night_commits = 0
        
        for commit_date in commit_dates:
            is_weekend = commit_date.weekday() >= 5  # 5=Saturday, 6=Sunday
            is_business_hours = 9 <= commit_date.hour < 17
            is_night = commit_date.hour < 6 or commit_date.hour >= 22
            
            if is_weekend:
                weekend_commits += 1
            if is_business_hours and not is_weekend:
                business_hours_commits += 1
            if is_night:
                night_commits += 1
        
        total_commits = len(commit_dates)
        business_hours_pct = (business_hours_commits / total_commits) * 100
        weekend_pct = (weekend_commits / total_commits) * 100
        night_pct = (night_commits / total_commits) * 100
        
        self.assertEqual(business_hours_pct, 25.0)  # 1 out of 4
        self.assertEqual(weekend_pct, 50.0)         # 2 out of 4
        self.assertEqual(night_pct, 25.0)           # 1 out of 4
    
    def test_empty_data(self):
        """Test analysis with empty data"""
        self.base_analyzer.commits = []
        self.base_analyzer.detailed_commits = {}
        self.base_analyzer.pull_requests = []
        
        with patch.object(self.base_analyzer, 'is_analysis_cached', return_value=False):
            result = self.analyzer.analyze_commit_timing()
            self.assertIsInstance(result, pd.DataFrame)
            
            result = self.analyzer.analyze_advanced_developer_contributions()
            self.assertIsInstance(result, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()
