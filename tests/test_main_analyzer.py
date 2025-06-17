"""
Unit tests for Main AzureDevOpsAnalyzer
"""

import unittest
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.main_analyzer import AzureDevOpsAnalyzer

class TestMainAnalyzer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = AzureDevOpsAnalyzer(
            org_name="test_org",
            project_name="test_project",
            repo_name="test_repo",
            pat_token="test_token",
            data_dir=self.temp_dir,
            date_from="2023-01-01",
            date_to="2023-12-31"
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test main analyzer initialization"""
        self.assertEqual(self.analyzer.org_name, "test_org")
        self.assertEqual(self.analyzer.project_name, "test_project")
        self.assertEqual(self.analyzer.repo_name, "test_repo")
        
        # Check that all sub-analyzers are initialized
        self.assertIsNotNone(self.analyzer.data_collector)
        self.assertIsNotNone(self.analyzer.developer_analyzer)
        self.assertIsNotNone(self.analyzer.quality_analyzer)
        self.assertIsNotNone(self.analyzer.hotspot_analyzer)
        self.assertIsNotNone(self.analyzer.language_analyzer)
        self.assertIsNotNone(self.analyzer.contribution_analyzer)
    
    def test_date_initialization(self):
        """Test date range initialization"""
        # Test with custom dates
        analyzer = AzureDevOpsAnalyzer(
            org_name="test",
            project_name="test",
            repo_name="test",
            pat_token="test",
            date_from="2023-01-01",
            date_to="2023-06-30"
        )
        
        self.assertIn("2023-01-01", analyzer.date_from)
        self.assertIn("2023-06-30", analyzer.date_to)
    
    @patch('analyzers.data_collector.DataCollector.collect_all_data')
    @patch('analyzers.data_collector.DataCollector.load_collected_data')
    def test_collect_all_data(self, mock_load, mock_collect):
        """Test data collection orchestration"""
        mock_collect.return_value = "repo123"
        
        result = self.analyzer.collect_all_data()
        
        self.assertEqual(result, "repo123")
        mock_collect.assert_called_once()
    
    @patch('analyzers.data_collector.DataCollector.load_collected_data')
    def test_load_data_methods(self, mock_load):
        """Test data loading method aliases"""
        # Test all load method aliases
        self.analyzer.load_collected_data()
        self.analyzer.load_data()
        
        # Should call the data collector method twice
        self.assertEqual(mock_load.call_count, 2)
    
    def test_analyze_repository_basic_stats(self):
        """Test basic repository statistics"""
        # Setup test data
        self.analyzer.commits = [
            {'commitId': 'abc123', 'author': {'name': 'John', 'email': 'john@test.com'}},
            {'commitId': 'def456', 'author': {'name': 'Jane', 'email': 'jane@test.com'}}
        ]
        self.analyzer.detailed_commits = {'abc123': {}, 'def456': {}}
        self.analyzer.pull_requests = [{'pullRequestId': 1}]
        
        # Should not raise an exception
        self.analyzer.analyze_repository_basic_stats()
        
        # Test with no commits
        self.analyzer.commits = []
        self.analyzer.analyze_repository_basic_stats()
    
    @patch('analyzers.developer_analyzer.DeveloperAnalyzer.analyze_developer_activity')
    def test_analyze_developer_activity(self, mock_analyze):
        """Test developer activity analysis delegation"""
        mock_df = Mock()
        mock_analyze.return_value = mock_df
        
        result = self.analyzer.analyze_developer_activity()
        
        self.assertEqual(result, mock_df)
        mock_analyze.assert_called_once()
    
    @patch('analyzers.developer_analyzer.DeveloperAnalyzer.analyze_pull_request_metrics')
    def test_analyze_pull_requests(self, mock_analyze):
        """Test pull request analysis delegation"""
        mock_df = Mock()
        mock_analyze.return_value = mock_df
        
        # Test both method names
        result1 = self.analyzer.analyze_pull_requests()
        result2 = self.analyzer.analyze_pull_request_metrics()
        
        self.assertEqual(result1, mock_df)
        self.assertEqual(result2, mock_df)
        self.assertEqual(mock_analyze.call_count, 2)
    
    @patch('analyzers.quality_analyzer.QualityAnalyzer.analyze_enhanced_quality_metrics')
    def test_analyze_enhanced_quality_metrics(self, mock_analyze):
        """Test quality metrics analysis delegation"""
        mock_df = Mock()
        mock_analyze.return_value = mock_df
        
        result = self.analyzer.analyze_enhanced_quality_metrics()
        
        self.assertEqual(result, mock_df)
        mock_analyze.assert_called_once()
    
    @patch('analyzers.contribution_analyzer.ContributionAnalyzer.analyze_commit_timing')
    def test_analyze_commit_timing(self, mock_analyze):
        """Test commit timing analysis delegation"""
        mock_df = Mock()
        mock_analyze.return_value = mock_df
        
        result = self.analyzer.analyze_commit_timing()
        
        self.assertEqual(result, mock_df)
        mock_analyze.assert_called_once()
    
    @patch('analyzers.language_analyzer.LanguageAnalyzer.analyze_language_complexity_distribution')
    def test_analyze_language_complexity(self, mock_analyze):
        """Test language complexity analysis delegation"""
        mock_df = Mock()
        mock_analyze.return_value = mock_df
        
        result = self.analyzer.analyze_language_complexity_distribution()
        
        self.assertEqual(result, mock_df)
        mock_analyze.assert_called_once()
    
    @patch('analyzers.hotspot_analyzer.HotspotAnalyzer.analyze_bus_factor_and_hotspots')
    def test_analyze_bus_factor_and_hotspots(self, mock_analyze):
        """Test hotspot analysis delegation"""
        mock_files_df = Mock()
        mock_devs_df = Mock()
        mock_analyze.return_value = (mock_files_df, mock_devs_df)
        
        files_result, devs_result = self.analyzer.analyze_bus_factor_and_hotspots()
        
        self.assertEqual(files_result, mock_files_df)
        self.assertEqual(devs_result, mock_devs_df)
        mock_analyze.assert_called_once()
    
    @patch('analyzers.contribution_analyzer.ContributionAnalyzer.analyze_advanced_developer_contributions')
    def test_analyze_advanced_developer_contributions(self, mock_analyze):
        """Test advanced contributions analysis delegation"""
        mock_df = Mock()
        mock_analyze.return_value = mock_df
        
        result = self.analyzer.analyze_advanced_developer_contributions()
        
        self.assertEqual(result, mock_df)
        mock_analyze.assert_called_once()
    
    def test_analyze_security_insights(self):
        """Test security analysis placeholder"""
        # Should not raise an exception
        self.analyzer.analyze_security_insights()
    
    def test_analyze_knowledge_management(self):
        """Test knowledge management placeholder"""
        # Should not raise an exception
        self.analyzer.analyze_knowledge_management()
    
    @patch.object(AzureDevOpsAnalyzer, 'collect_all_data')
    @patch.object(AzureDevOpsAnalyzer, 'load_collected_data')
    @patch.object(AzureDevOpsAnalyzer, 'analyze_repository_basic_stats')
    @patch.object(AzureDevOpsAnalyzer, 'analyze_developer_activity')
    @patch.object(AzureDevOpsAnalyzer, 'analyze_pull_requests')
    @patch('glob.glob')
    def test_run_complete_analysis_success(self, mock_glob, mock_pr, mock_dev, mock_basic, mock_load, mock_collect):
        """Test successful complete analysis run"""
        # Setup mocks
        mock_collect.return_value = "repo123"
        self.analyzer.commits = [{'commitId': 'test'}]  # Non-empty commits
        mock_glob.return_value = ['test1.csv', 'test2.csv']
        
        result = self.analyzer.run_complete_analysis()
        
        self.assertTrue(result)
        mock_collect.assert_called_once()
        mock_load.assert_called_once()
        mock_basic.assert_called_once()
        mock_dev.assert_called_once()
        mock_pr.assert_called_once()
    
    @patch.object(AzureDevOpsAnalyzer, 'collect_all_data')
    @patch.object(AzureDevOpsAnalyzer, 'load_collected_data')
    def test_run_complete_analysis_no_commits(self, mock_load, mock_collect):
        """Test complete analysis with no commits"""
        mock_collect.return_value = "repo123"
        self.analyzer.commits = []  # Empty commits
        
        result = self.analyzer.run_complete_analysis()
        
        self.assertFalse(result)
        mock_collect.assert_called_once()
        mock_load.assert_called_once()
    
    @patch.object(AzureDevOpsAnalyzer, 'collect_all_data')
    def test_run_complete_analysis_exception(self, mock_collect):
        """Test complete analysis with exception"""
        mock_collect.side_effect = Exception("Test error")
        
        result = self.analyzer.run_complete_analysis()
        
        self.assertFalse(result)
    
    @patch('pandas.read_csv')
    def test_generate_analysis_summary(self, mock_read_csv):
        """Test analysis summary generation"""
        # Setup test data
        self.analyzer.commits = [{'commitId': 'test'}]
        self.analyzer.detailed_commits = {'test': {}}
        
        # Mock CSV files
        mock_contrib_df = Mock()
        mock_contrib_df.iloc = [Mock()]
        mock_contrib_df.iloc[0] = {'Developer': 'test@example.com'}
        mock_contrib_df['Overall_Contribution_Score'] = Mock()
        mock_contrib_df['Overall_Contribution_Score'].mean.return_value = 75.0
        mock_contrib_df.__len__ = Mock(return_value=1)
        
        mock_read_csv.return_value = mock_contrib_df
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            # Should not raise an exception
            self.analyzer.generate_analysis_summary()
            
            # Check that summary file would be created
            summary_file = os.path.join(self.temp_dir, "analysis_summary.json")
            # File creation is mocked, but method should complete

if __name__ == '__main__':
    unittest.main()
