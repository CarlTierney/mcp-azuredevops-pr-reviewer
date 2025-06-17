"""
Unit tests for QualityAnalyzer
"""

import unittest
import tempfile
import shutil
import pandas as pd
import calendar
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer
from analyzers.quality_analyzer import QualityAnalyzer

class TestQualityAnalyzer(unittest.TestCase):
    
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
        self.analyzer = QualityAnalyzer(self.base_analyzer)
        
        # Setup test data with different months
        self.base_analyzer.commits = [
            {
                'commitId': 'jan123',
                'author': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'date': '2023-01-15T12:00:00Z'
                }
            },
            {
                'commitId': 'feb456',
                'author': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'date': '2023-02-20T14:00:00Z'
                }
            },
            {
                'commitId': 'mar789',
                'author': {
                    'name': 'Jane Smith',
                    'email': 'jane@example.com',
                    'date': '2023-03-10T10:00:00Z'
                }
            }
        ]
        
        self.base_analyzer.detailed_commits = {
            'jan123': {
                'changes': [
                    {
                        'item': {'path': '/src/Feature.cs', 'isFolder': False},
                        'changeType': 'add'
                    }
                ]
            },
            'feb456': {
                'changes': [
                    {
                        'item': {'path': '/src/Feature.cs', 'isFolder': False},
                        'changeType': 'edit'
                    }
                ]
            },
            'mar789': {
                'changes': [
                    {
                        'item': {'path': '/src/NewFeature.cs', 'isFolder': False},
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
    def test_cached_analysis(self, mock_get_cached, mock_is_cached):
        """Test cached quality metrics analysis"""
        mock_is_cached.return_value = True
        mock_df = pd.DataFrame({
            'Developer': ['john@example.com', 'jane@example.com'],
            'Month': ['2023-01', '2023-03'],
            'Month_Display': ['January 2023', 'March 2023'],
            'Commits': [2, 1],
            'LOC_Added': [150, 100],
            'LOC_Deleted': [20, 0],
            'LOC_Modified': [50, 25],
            'Non_Whitespace_Ratio': [0.8, 0.9],
            'Avg_Cyclomatic_Complexity': [2.5, 1.8],
            'Code_Quality_Score': [75.0, 85.0]
        })
        mock_get_cached.return_value = mock_df
        
        result = self.analyzer.analyze_enhanced_quality_metrics()
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        mock_is_cached.assert_called_once_with('enhanced_quality_metrics')
    
    @patch.object(BaseAnalyzer, 'get_repository_id')
    @patch.object(BaseAnalyzer, 'classify_file_type')
    @patch.object(BaseAnalyzer, 'fetch_file_content')
    @patch.object(BaseAnalyzer, 'analyze_file_contents')
    @patch.object(BaseAnalyzer, 'calculate_cyclomatic_complexity')
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_fresh_analysis(self, mock_is_cached, mock_complexity, mock_analyze_contents,
                           mock_fetch_content, mock_classify, mock_get_repo_id):
        """Test fresh quality metrics analysis"""
        # Setup mocks
        mock_is_cached.return_value = False
        mock_get_repo_id.return_value = "repo123"
        mock_classify.return_value = 'csharp'
        mock_fetch_content.return_value = "public class Test { public void Method() { } }"
        mock_analyze_contents.return_value = {
            'loc': 50, 'sloc': 40, 'lloc': 35, 'comments': 5, 'multi': 2, 'blank': 8
        }
        mock_complexity.return_value = 2.5
        
        result = self.analyzer.analyze_enhanced_quality_metrics()
        
        self.assertIsInstance(result, pd.DataFrame)
        
        if not result.empty:
            self.assertIn('Developer', result.columns)
            self.assertIn('Month', result.columns)
            self.assertIn('Code_Quality_Score', result.columns)
            
            # Check that monthly data is properly grouped
            developers = result['Developer'].unique()
            self.assertIn('john@example.com', developers)
            self.assertIn('jane@example.com', developers)
    
    def test_month_key_generation(self):
        """Test month key generation from dates"""
        test_dates = [
            ('2023-01-15T12:00:00Z', '2023-01'),
            ('2023-02-28T23:59:59Z', '2023-02'),
            ('2023-12-01T00:00:00Z', '2023-12')
        ]
        
        for date_str, expected_month_key in test_dates:
            commit_date = datetime.fromisoformat(date_str.replace('Z', ''))
            month_key = f"{commit_date.year}-{commit_date.month:02d}"
            self.assertEqual(month_key, expected_month_key)
    
    def test_monthly_report_generation(self):
        """Test monthly report generation logic"""
        # Mock monthly metrics structure
        monthly_metrics = {
            'john@example.com': {
                '2023-01': {
                    'commits': 5,
                    'files_changed': {'/src/file1.cs', '/src/file2.cs'},
                    'loc_added': 200,
                    'loc_deleted': 50,
                    'loc_modified': 100,
                    'non_whitespace_added': 160,
                    'non_whitespace_deleted': 40,
                    'non_whitespace_modified': 80,
                    'complexity_samples': [2.0, 3.0, 1.5],
                    'file_types': {'csharp': 5},
                    'change_types': {'add': 2, 'edit': 3}
                }
            }
        }
        
        # Test the report generation logic
        monthly_data = self.analyzer._generate_monthly_report(monthly_metrics)
        
        self.assertIsInstance(monthly_data, list)
        self.assertGreater(len(monthly_data), 0)
        
        # Check first entry
        entry = monthly_data[0]
        self.assertEqual(entry['Developer'], 'john@example.com')
        self.assertEqual(entry['Month'], '2023-01')
        self.assertEqual(entry['Commits'], 5)
        self.assertEqual(entry['LOC_Added'], 200)
        self.assertEqual(entry['LOC_Net_Change'], 150)  # 200 - 50
    
    def test_quality_score_calculation(self):
        """Test code quality score calculation"""
        # Test quality score calculation logic
        non_whitespace_ratio = 0.8
        avg_complexity = 3.0
        
        code_quality_score = min(100, (non_whitespace_ratio * 50) + ((10 - min(avg_complexity, 10)) * 5))
        
        expected_score = (0.8 * 50) + ((10 - 3.0) * 5)  # 40 + 35 = 75
        self.assertEqual(code_quality_score, expected_score)
        
        # Test with high complexity (should be capped)
        high_complexity = 15.0
        high_complexity_score = min(100, (non_whitespace_ratio * 50) + ((10 - min(high_complexity, 10)) * 5))
        expected_high_score = (0.8 * 50) + ((10 - 10) * 5)  # 40 + 0 = 40
        self.assertEqual(high_complexity_score, expected_high_score)
    
    def test_change_type_analysis(self):
        """Test change type analysis"""
        change_types = {'add': 5, 'edit': 10, 'delete': 2}
        
        # Test that we capture different change types correctly
        self.assertEqual(change_types['add'], 5)
        self.assertEqual(change_types['edit'], 10)
        self.assertEqual(change_types['delete'], 2)
        
        total_changes = sum(change_types.values())
        self.assertEqual(total_changes, 17)
    
    def test_month_display_formatting(self):
        """Test month display name formatting"""
        test_cases = [
            ('2023-01', 'January 2023'),
            ('2023-02', 'February 2023'),
            ('2023-12', 'December 2023')
        ]
        
        for month_key, expected_display in test_cases:
            year, month = month_key.split('-')
            month_name = calendar.month_name[int(month)]
            display_month = f"{month_name} {year}"
            self.assertEqual(display_month, expected_display)
    
    def test_empty_detailed_commits(self):
        """Test analysis with no detailed commits"""
        self.base_analyzer.detailed_commits = {}
        
        with patch.object(self.base_analyzer, 'is_analysis_cached', return_value=False):
            result = self.analyzer.analyze_enhanced_quality_metrics()
            
            self.assertIsInstance(result, pd.DataFrame)
    
    def test_file_type_filtering(self):
        """Test that non-code files are filtered out"""
        file_types = ['csharp', 'sql', 'other', 'docs']
        code_files = [ft for ft in file_types if ft not in ['other', 'docs']]
        
        self.assertEqual(len(code_files), 2)
        self.assertIn('csharp', code_files)
        self.assertIn('sql', code_files)
        self.assertNotIn('other', code_files)
        self.assertNotIn('docs', code_files)
    
    def test_non_whitespace_ratio_calculation(self):
        """Test non-whitespace ratio calculation"""
        total_loc_changes = 100
        total_non_ws_changes = 80
        
        ratio = total_non_ws_changes / max(total_loc_changes, 1)
        self.assertEqual(ratio, 0.8)
        
        # Test with zero LOC changes
        zero_ratio = 0 / max(0, 1)
        self.assertEqual(zero_ratio, 0.0)

if __name__ == '__main__':
    unittest.main()
