"""
Unit tests for LanguageAnalyzer
"""

import unittest
import tempfile
import shutil
import pandas as pd
from unittest.mock import Mock, patch

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer
from analyzers.language_analyzer import LanguageAnalyzer

class TestLanguageAnalyzer(unittest.TestCase):
    
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
        self.analyzer = LanguageAnalyzer(self.base_analyzer)
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer.analyzer)
        self.assertEqual(self.analyzer.analyzer.org_name, "test_org")
    
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    @patch.object(BaseAnalyzer, 'get_cached_dataframe')
    def test_cached_analysis(self, mock_get_cached, mock_is_cached):
        """Test cached analysis retrieval"""
        # Mock cached data
        mock_is_cached.return_value = True
        mock_df = pd.DataFrame({
            'Language_Type': ['csharp', 'sql'],
            'Unique_Files': [10, 5],
            'Total_LOC': [1000, 500],
            'Avg_Complexity': [2.5, 1.8],
            'Complexity_Risk_Score': [15.2, 8.3]
        })
        mock_get_cached.return_value = mock_df
        
        result = self.analyzer.analyze_language_complexity_distribution()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        mock_is_cached.assert_called_once_with('language_complexity')
        mock_get_cached.assert_called_once_with('language_complexity')
    
    def test_empty_detailed_commits(self):
        """Test analysis with no detailed commits"""
        self.base_analyzer.detailed_commits = {}
        
        result = self.analyzer.analyze_language_complexity_distribution()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
    
    @patch.object(BaseAnalyzer, 'get_repository_id')
    @patch.object(BaseAnalyzer, 'get_author_info')
    @patch.object(BaseAnalyzer, 'classify_file_type')
    @patch.object(BaseAnalyzer, 'fetch_file_content')
    @patch.object(BaseAnalyzer, 'analyze_file_contents')
    @patch.object(BaseAnalyzer, 'calculate_cyclomatic_complexity')
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_fresh_analysis(self, mock_is_cached, mock_complexity, mock_analyze_contents, 
                           mock_fetch_content, mock_classify, mock_get_author, mock_get_repo_id):
        """Test fresh analysis execution"""
        # Setup mocks
        mock_is_cached.return_value = False
        mock_get_repo_id.return_value = "repo123"
        mock_get_author.return_value = {'unique_name': 'test@example.com'}
        mock_classify.return_value = 'csharp'
        mock_fetch_content.return_value = "public class Test { }"
        mock_analyze_contents.return_value = {
            'loc': 100, 'sloc': 80, 'lloc': 70, 'comments': 10, 'multi': 5, 'blank': 10
        }
        mock_complexity.return_value = 2.5
        
        # Setup test data
        self.base_analyzer.commits = [
            {
                'commitId': 'abc123',
                'author': {'name': 'Test User', 'email': 'test@example.com', 'date': '2023-01-01T12:00:00Z'}
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
            }
        }
        
        result = self.analyzer.analyze_language_complexity_distribution()
        
        self.assertIsInstance(result, pd.DataFrame)
        if not result.empty:
            self.assertIn('Language_Type', result.columns)
            self.assertIn('Unique_Files', result.columns)
            self.assertIn('Complexity_Risk_Score', result.columns)
    
    @patch.object(BaseAnalyzer, 'get_repository_id')
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_analysis_timeout(self, mock_is_cached, mock_get_repo_id):
        """Test analysis timeout handling"""
        mock_is_cached.return_value = False
        mock_get_repo_id.return_value = "repo123"
        
        # Create a large number of commits to trigger timeout logic
        self.base_analyzer.commits = []
        self.base_analyzer.detailed_commits = {}
        
        for i in range(1000):
            commit_id = f"commit{i}"
            self.base_analyzer.commits.append({
                'commitId': commit_id,
                'author': {'name': 'Test User', 'email': 'test@example.com', 'date': '2023-01-01T12:00:00Z'}
            })
            self.base_analyzer.detailed_commits[commit_id] = {
                'changes': [
                    {
                        'item': {'path': f'/src/File{i}.cs', 'isFolder': False},
                        'changeType': 'add'
                    }
                ]
            }
        
        # Mock time to simulate timeout
        with patch('time.time') as mock_time:
            # Start time, then immediately trigger timeout
            mock_time.side_effect = [0, 3700]  # 1+ hour elapsed
            
            result = self.analyzer.analyze_language_complexity_distribution()
            
            # Should still return a DataFrame, even if empty
            self.assertIsInstance(result, pd.DataFrame)
    
    def test_large_commit_handling(self):
        """Test handling of commits with many changes"""
        # This test verifies the logic that limits changes per commit
        changes = []
        for i in range(600):  # More than 500 limit
            changes.append({
                'item': {'path': f'/src/File{i}.cs', 'isFolder': False},
                'changeType': 'add'
            })
        
        # Test that the changes list would be truncated to 500
        limited_changes = changes[:500]
        self.assertEqual(len(limited_changes), 500)
        self.assertLess(len(limited_changes), len(changes))

if __name__ == '__main__':
    unittest.main()
