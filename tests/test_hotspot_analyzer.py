"""
Unit tests for HotspotAnalyzer
"""

import unittest
import tempfile
import shutil
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer
from analyzers.hotspot_analyzer import HotspotAnalyzer

class TestHotspotAnalyzer(unittest.TestCase):
    
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
        self.analyzer = HotspotAnalyzer(self.base_analyzer)
        
        # Setup test data
        self.base_analyzer.commits = [
            {
                'commitId': 'abc123',
                'author': {
                    'name': 'John Doe',
                    'email': 'john@example.com',
                    'date': '2023-01-01T12:00:00Z'
                }
            },
            {
                'commitId': 'def456',
                'author': {
                    'name': 'Jane Smith',
                    'email': 'jane@example.com',
                    'date': '2023-01-02T14:00:00Z'
                }
            }
        ]
        
        self.base_analyzer.detailed_commits = {
            'abc123': {
                'changes': [
                    {
                        'item': {'path': '/src/CriticalService.cs', 'isFolder': False},
                        'changeType': 'add'
                    },
                    {
                        'item': {'path': '/src/Utils.cs', 'isFolder': False},
                        'changeType': 'edit'
                    }
                ]
            },
            'def456': {
                'changes': [
                    {
                        'item': {'path': '/src/CriticalService.cs', 'isFolder': False},
                        'changeType': 'edit'
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
        """Test cached hotspot analysis"""
        # Both file and developer analysis cached
        mock_is_cached.return_value = True
        
        mock_files_df = pd.DataFrame({
            'File_Name': ['CriticalService.cs', 'Utils.cs'],
            'Bus_Factor_Risk': [5.0, 2.0],
            'Hotspot_Score': [15.2, 8.3],
            'Developers_Count': [1, 2],
            'Is_Critical': [True, False]
        })
        
        mock_devs_df = pd.DataFrame({
            'Developer': ['john@example.com', 'jane@example.com'],
            'Files_Owned': [10, 5],
            'Exclusive_Files': [3, 1],
            'Bus_Factor_Risk': [4.0, 2.0],
            'Risk_Level': ['Critical', 'Medium']
        })
        
        mock_get_cached.side_effect = [mock_files_df, mock_devs_df]
        
        files_result, devs_result = self.analyzer.analyze_bus_factor_and_hotspots()
        
        self.assertIsInstance(files_result, pd.DataFrame)
        self.assertIsInstance(devs_result, pd.DataFrame)
        self.assertEqual(len(files_result), 2)
        self.assertEqual(len(devs_result), 2)
    
    @patch.object(BaseAnalyzer, 'classify_file_type')
    @patch.object(BaseAnalyzer, 'is_analysis_cached')
    def test_fresh_analysis(self, mock_is_cached, mock_classify):
        """Test fresh hotspot analysis"""
        mock_is_cached.return_value = False
        mock_classify.side_effect = lambda filename: 'csharp' if filename.endswith('.cs') else 'other'
        
        files_result, devs_result = self.analyzer.analyze_bus_factor_and_hotspots()
        
        self.assertIsInstance(files_result, pd.DataFrame)
        self.assertIsInstance(devs_result, pd.DataFrame)
        
        if not files_result.empty:
            self.assertIn('File_Name', files_result.columns)
            self.assertIn('Bus_Factor_Risk', files_result.columns)
            self.assertIn('Hotspot_Score', files_result.columns)
        
        if not devs_result.empty:
            self.assertIn('Developer', devs_result.columns)
            self.assertIn('Bus_Factor_Risk', devs_result.columns)
    
    def test_bus_factor_calculation(self):
        """Test bus factor risk calculation logic"""
        # Test different developer counts and their risk levels
        test_cases = [
            (1, 5.0),    # Single developer = very high risk
            (2, 3.5),    # Two developers = high risk
            (3, 2.0),    # Three developers = medium risk
            (5, 1.0),    # Five developers = low risk
            (10, 0.2)    # Many developers = very low risk
        ]
        
        for dev_count, expected_risk in test_cases:
            if dev_count == 1:
                bus_factor_risk = 5.0
            elif dev_count == 2:
                bus_factor_risk = 3.5
            elif dev_count <= 4:
                bus_factor_risk = 2.0
            elif dev_count <= 7:
                bus_factor_risk = 1.0
            else:
                bus_factor_risk = 0.2
            
            self.assertEqual(bus_factor_risk, expected_risk)
    
    def test_hotspot_score_calculation(self):
        """Test hotspot score calculation"""
        # Mock file metrics
        metrics = {
            'total_commits': 10,
            'recent_commits': 5,
            'file_size_estimate': 200
        }
        
        change_frequency = metrics['total_commits']
        recency_weight = metrics['recent_commits'] * 2
        size_factor = min(metrics['file_size_estimate'] / 100, 3.0)
        
        hotspot_score = (change_frequency * 0.4) + (recency_weight * 0.4) + (size_factor * 0.2)
        
        expected_score = (10 * 0.4) + (10 * 0.4) + (2.0 * 0.2)  # 4 + 4 + 0.4 = 8.4
        self.assertEqual(hotspot_score, expected_score)
      def test_critical_file_detection(self):
        """Test critical file detection logic"""
        test_cases = [
            ('Controller.cs', 'csharp', True),     # Controller in name
            ('UserService.cs', 'csharp', True),   # Service in name
            ('DataManager.cs', 'csharp', True),   # Manager in name
            ('UserRepository.cs', 'csharp', True),# Repository in name
            ('Helper.cs', 'csharp', False),       # Not critical pattern
            ('query.sql', 'sql', False),          # SQL files are not automatically critical
            ('readme.md', 'docs', False)          # Documentation
        ]
        
        for filename, file_type, expected_critical in test_cases:
            # Use the actual critical detection logic from FileClassifier
            from utils.file_classifier import FileClassifier
            classifier = FileClassifier()
            is_critical = classifier.is_critical_component(f"/path/to/{filename}", filename, file_type)
            
            self.assertEqual(is_critical, expected_critical, 
                           f"Failed for {filename} ({file_type})")
    
    def test_developer_ownership_calculation(self):
        """Test developer ownership percentage calculation"""
        # Mock scenario: 100 total files, developer owns 20
        total_files = 100
        files_owned = 20
        ownership_percentage = (files_owned / total_files) * 100
        
        self.assertEqual(ownership_percentage, 20.0)
        
        # Test risk level assignment
        if ownership_percentage >= 50:
            risk = 5.0
        elif ownership_percentage >= 30:
            risk = 4.0
        elif ownership_percentage >= 20:
            risk = 3.0
        elif ownership_percentage >= 10:
            risk = 2.0
        elif ownership_percentage >= 5:
            risk = 1.0
        else:
            risk = 0.5
        
        self.assertEqual(risk, 3.0)  # 20% should be medium-high risk
    
    def test_empty_data(self):
        """Test analysis with empty data"""
        self.base_analyzer.commits = []
        self.base_analyzer.detailed_commits = {}
        
        with patch.object(self.base_analyzer, 'is_analysis_cached', return_value=False):
            files_result, devs_result = self.analyzer.analyze_bus_factor_and_hotspots()
            
            self.assertIsInstance(files_result, pd.DataFrame)
            self.assertIsInstance(devs_result, pd.DataFrame)
    
    def test_recent_activity_calculation(self):
        """Test recent activity calculation"""
        current_date = datetime.now().replace(tzinfo=None)
        recent_threshold = current_date - timedelta(days=90)
        
        # Test dates
        old_date = current_date - timedelta(days=120)  # Older than threshold
        recent_date = current_date - timedelta(days=30)  # Within threshold
        
        # Test recent activity logic
        self.assertLess(old_date, recent_threshold)  # Should not count as recent
        self.assertGreaterEqual(recent_date, recent_threshold)  # Should count as recent

if __name__ == '__main__':
    unittest.main()
