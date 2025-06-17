"""
Unit tests for BaseAnalyzer
"""

import unittest
import os
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer

class TestBaseAnalyzer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = BaseAnalyzer(
            org_name="test_org",
            project_name="test_project", 
            repo_name="test_repo",
            pat_token="test_token",
            data_dir=self.temp_dir
        )
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertEqual(self.analyzer.org_name, "test_org")
        self.assertEqual(self.analyzer.project_name, "test_project")
        self.assertEqual(self.analyzer.repo_name, "test_repo")
        self.assertTrue(os.path.exists(self.analyzer.cache_dir))
    
    def test_classify_file_type(self):
        """Test file type classification"""
        # Test C# files
        self.assertEqual(self.analyzer.classify_file_type("Program.cs"), "csharp")
        self.assertEqual(self.analyzer.classify_file_type("test.vb"), "csharp")
        
        # Test project files
        self.assertEqual(self.analyzer.classify_file_type("project.csproj"), "csharp_project")
        self.assertEqual(self.analyzer.classify_file_type("solution.sln"), "csharp_project")
        
        # Test SQL files
        self.assertEqual(self.analyzer.classify_file_type("query.sql"), "sql")
        self.assertEqual(self.analyzer.classify_file_type("proc.tsql"), "sql")
        
        # Test web files
        self.assertEqual(self.analyzer.classify_file_type("page.aspx"), "web_dotnet")
        self.assertEqual(self.analyzer.classify_file_type("view.cshtml"), "web_dotnet")
        self.assertEqual(self.analyzer.classify_file_type("script.js"), "web_client")
        
        # Test test files
        self.assertEqual(self.analyzer.classify_file_type("UnitTest.cs"), "test_csharp")
        self.assertEqual(self.analyzer.classify_file_type("TestQuery.sql"), "test_sql")
        
        # Test config files
        self.assertEqual(self.analyzer.classify_file_type("web.config"), "dotnet_config")
        self.assertEqual(self.analyzer.classify_file_type("appsettings.json"), "dotnet_config")
        
        # Test other files
        self.assertEqual(self.analyzer.classify_file_type("readme.md"), "docs")
        self.assertEqual(self.analyzer.classify_file_type("unknown.xyz"), "other")
    
    def test_get_author_info(self):
        """Test author information extraction"""
        # Test with complete author data
        author_data = {
            'name': 'John Doe',
            'email': 'john.doe@example.com'
        }
        result = self.analyzer.get_author_info(author_data)
        self.assertEqual(result['display_name'], 'John Doe')
        self.assertEqual(result['unique_name'], 'john.doe@example.com')
        self.assertEqual(result['email'], 'john.doe@example.com')
        
        # Test with missing data
        result = self.analyzer.get_author_info({})
        self.assertEqual(result['display_name'], 'Unknown')
        self.assertEqual(result['unique_name'], 'unknown@unknown.com')
        
        # Test with None
        result = self.analyzer.get_author_info(None)
        self.assertEqual(result['display_name'], 'Unknown')
    
    def test_analyze_file_contents(self):
        """Test file content analysis"""
        # Test with valid Python code
        code = """def hello_world():
    print("Hello, World!")
    return True

# This is a comment
if __name__ == "__main__":
    hello_world()
"""
        result = self.analyzer.analyze_file_contents(code)
        self.assertGreater(result['loc'], 0)
        self.assertGreater(result['sloc'], 0)
        
        # Test with empty content
        result = self.analyzer.analyze_file_contents("")
        self.assertEqual(result['loc'], 0)
        
        # Test with None
        result = self.analyzer.analyze_file_contents(None)
        self.assertEqual(result['loc'], 0)
    
    def test_calculate_cyclomatic_complexity(self):
        """Test cyclomatic complexity calculation"""
        # Test with simple code
        simple_code = "def simple(): return 1"
        complexity = self.analyzer.calculate_cyclomatic_complexity(simple_code, "test.py")
        self.assertGreaterEqual(complexity, 1)
        
        # Test with complex code
        complex_code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            return "big"
        else:
            return "small"
    else:
        return "negative"
"""
        complexity = self.analyzer.calculate_cyclomatic_complexity(complex_code, "test.py")
        self.assertGreater(complexity, 1)
        
        # Test with non-code file
        complexity = self.analyzer.calculate_cyclomatic_complexity("some text", "readme.txt")
        self.assertEqual(complexity, 1)
    
    def test_is_valid_text_content(self):
        """Test text content validation"""
        # Valid text content
        self.assertTrue(self.analyzer._is_valid_text_content("Hello, World!"))
        
        # Empty content
        self.assertFalse(self.analyzer._is_valid_text_content(""))
        
        # Binary-like content
        binary_content = "".join(chr(i) for i in range(256))
        self.assertFalse(self.analyzer._is_valid_text_content(binary_content))
        
        # Very long lines (minified)
        long_line = "a" * 2000
        self.assertFalse(self.analyzer._is_valid_text_content(long_line))
    
    def test_is_likely_binary(self):
        """Test binary content detection"""
        # Text content
        self.assertFalse(self.analyzer._is_likely_binary("Hello, World!"))
        
        # Binary content with null bytes
        self.assertTrue(self.analyzer._is_likely_binary("Hello\x00World"))
        
        # Content with many non-printable characters
        binary_content = "".join(chr(i) for i in range(32))
        self.assertTrue(self.analyzer._is_likely_binary(binary_content))
    
    def test_calculate_data_hash(self):
        """Test data hash calculation"""
        # Set up some test data
        self.analyzer.commits = [{'commitId': 'abc123'}, {'commitId': 'def456'}]
        self.analyzer.detailed_commits = {'abc123': {}, 'def456': {}}
        
        hash1 = self.analyzer.calculate_data_hash()
        self.assertIsNotNone(hash1)
        
        # Hash should be consistent
        hash2 = self.analyzer.calculate_data_hash()
        self.assertEqual(hash1, hash2)
        
        # Hash should change when data changes
        self.analyzer.commits.append({'commitId': 'ghi789'})
        hash3 = self.analyzer.calculate_data_hash()
        self.assertNotEqual(hash1, hash3)
    
    def test_cache_operations(self):
        """Test cache save and load operations"""
        # Test saving cache info
        cache_info = {
            'test_analysis': {
                'data_hash': 'test_hash',
                'output_file': 'test_file.csv',
                'timestamp': '2023-01-01 12:00:00'
            }
        }
        self.analyzer.save_cache_info(cache_info)
        
        # Test loading cache info
        loaded_info = self.analyzer.load_cache_info()
        self.assertEqual(loaded_info['test_analysis']['data_hash'], 'test_hash')
        
        # Test cache validity check
        self.assertFalse(self.analyzer.is_analysis_cached('test_analysis'))  # File doesn't exist
    
    @patch('requests.get')
    def test_fetch_file_content(self, mock_get):
        """Test file content fetching"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "file content"
        mock_get.return_value = mock_response
        
        content = self.analyzer.fetch_file_content("repo123", "commit456", "/path/to/file.cs")
        self.assertEqual(content, "file content")
        
        # Test with problematic file extension
        content = self.analyzer.fetch_file_content("repo123", "commit456", "/path/to/file.exe")
        self.assertIsNone(content)
        
        # Mock failed response
        mock_response.status_code = 404
        content = self.analyzer.fetch_file_content("repo123", "commit456", "/path/to/file.cs")
        self.assertIsNone(content)

if __name__ == '__main__':
    unittest.main()
