"""Unit tests for code reviewer functionality"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from azure_pr_reviewer.code_reviewer import CodeReviewer, ReviewData
from azure_pr_reviewer.file_type_detector import FileType
from azure_pr_reviewer.config import Settings


class TestCodeReviewer(unittest.TestCase):
    """Test suite for CodeReviewer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = Mock(spec=Settings)
        self.mock_settings.custom_review_prompt_file = None
        self.reviewer = CodeReviewer(self.mock_settings)
    
    def test_initialization(self):
        """Test CodeReviewer initialization"""
        self.assertIsNotNone(self.reviewer)
        self.assertEqual(self.reviewer.settings, self.mock_settings)
        self.assertIsNotNone(self.reviewer.file_detector)
    
    def test_prepare_review_data(self):
        """Test preparing review data for a PR"""
        # Mock PR details
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.description = "Test description"
        mock_pr.source_ref_name = "refs/heads/feature-branch"
        mock_pr.target_ref_name = "refs/heads/main"
        mock_pr.status = "active"
        mock_creator = Mock()
        mock_creator.display_name = "John Doe"
        mock_pr.created_by = mock_creator
        
        # Mock changes
        changes = [
            {
                "path": "/src/test.cs",
                "change_type": "edit",
                "new_content": "public class Test {}",
                "old_content": "public class OldTest {}"
            },
            {
                "path": "/src/new.js",
                "change_type": "add",
                "new_content": "console.log('test');"
            }
        ]
        
        with patch.object(self.reviewer.file_detector, 'analyze_pr_files') as mock_analyze:
            mock_analyze.return_value = {
                FileType.CSHARP: ["/src/test.cs"],
                FileType.JAVASCRIPT: ["/src/new.js"]
            }
            
            result = self.reviewer.prepare_review_data(mock_pr, changes)
        
        self.assertIsInstance(result, ReviewData)
        self.assertEqual(result.pr_details["pull_request_id"], 123)
        self.assertEqual(result.pr_details["title"], "Test PR")
        self.assertEqual(result.pr_details["created_by"], "John Doe")
        self.assertEqual(len(result.changes), 2)
        self.assertIn("csharp", result.file_type_summary)
        self.assertIn("javascript", result.file_type_summary)
    
    def test_get_review_instructions_no_file_types(self):
        """Test getting review instructions with no file types"""
        with patch.object(self.reviewer, '_get_prompt_for_type') as mock_get_prompt:
            mock_get_prompt.return_value = "Default prompt"
            
            result = self.reviewer.get_review_instructions()
            
            mock_get_prompt.assert_called_once_with(FileType.DEFAULT)
            self.assertEqual(result, "Default prompt")
    
    def test_get_review_instructions_single_type(self):
        """Test getting review instructions for single file type"""
        file_types = {FileType.CSHARP: ["/src/test.cs", "/src/test2.cs"]}
        
        with patch.object(self.reviewer.file_detector, 'should_use_mixed_review') as mock_mixed:
            mock_mixed.return_value = False
            with patch.object(self.reviewer, '_get_prompt_for_type') as mock_get_prompt:
                mock_get_prompt.return_value = "C# prompt"
                
                result = self.reviewer.get_review_instructions(file_types)
                
                mock_get_prompt.assert_called_once_with(FileType.CSHARP)
                self.assertEqual(result, "C# prompt")
    
    def test_get_review_instructions_mixed_types(self):
        """Test getting review instructions for mixed file types"""
        file_types = {
            FileType.CSHARP: ["/src/test.cs"],
            FileType.JAVASCRIPT: ["/src/test.js"]
        }
        
        with patch.object(self.reviewer.file_detector, 'should_use_mixed_review') as mock_mixed:
            mock_mixed.return_value = True
            with patch.object(self.reviewer, '_get_combined_prompt') as mock_combined:
                mock_combined.return_value = "Combined prompt"
                
                result = self.reviewer.get_review_instructions(file_types)
                
                mock_combined.assert_called_once_with(file_types)
                self.assertEqual(result, "Combined prompt")
    
    def test_get_prompt_for_type_custom_file(self):
        """Test getting prompt from custom file"""
        self.mock_settings.custom_review_prompt_file = "custom_prompt.txt"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Custom review prompt content")
            temp_file = f.name
        
        try:
            self.mock_settings.custom_review_prompt_file = temp_file
            result = self.reviewer._get_prompt_for_type(FileType.CSHARP)
            self.assertEqual(result, "Custom review prompt content")
        finally:
            os.unlink(temp_file)
    
    def test_get_prompt_for_type_default_fallback(self):
        """Test fallback to default prompt"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            with patch.object(self.reviewer, '_get_default_prompt') as mock_default:
                mock_default.return_value = "Default prompt"
                
                result = self.reviewer._get_prompt_for_type(FileType.CSHARP)
                
                mock_default.assert_called_once()
                self.assertEqual(result, "Default prompt")
    
    def test_get_combined_prompt(self):
        """Test creating combined prompt for multiple file types"""
        file_types = {
            FileType.CSHARP: ["/src/test.cs"],
            FileType.JAVASCRIPT: ["/src/test.js"],
            FileType.SQL: ["/db/query.sql"]
        }
        
        result = self.reviewer._get_combined_prompt(file_types)
        
        self.assertIn("Multi-Type Code Review", result)
        self.assertIn("csharp", result)
        self.assertIn("javascript", result)
        self.assertIn("sql", result)
        self.assertIn("Response Format", result)
    
    def test_get_condensed_guidelines(self):
        """Test getting condensed guidelines for different file types"""
        # Test C# guidelines
        csharp_guidelines = self.reviewer._get_condensed_guidelines(FileType.CSHARP)
        self.assertIn("SOLID", csharp_guidelines)
        self.assertIn("async/await", csharp_guidelines)
        
        # Test JavaScript guidelines
        js_guidelines = self.reviewer._get_condensed_guidelines(FileType.JAVASCRIPT)
        self.assertIn("const/let", js_guidelines)
        self.assertIn("Promises", js_guidelines)
        
        # Test SQL guidelines
        sql_guidelines = self.reviewer._get_condensed_guidelines(FileType.SQL)
        self.assertIn("SQL injection", sql_guidelines)
        self.assertIn("parameterized", sql_guidelines)
    
    def test_get_response_format(self):
        """Test getting response format"""
        result = self.reviewer._get_response_format()
        
        self.assertIn("Response Format", result)
        self.assertIn("approved", result)
        self.assertIn("severity", result)
        self.assertIn("comments", result)
        self.assertIn("Severity Guidelines", result)
    
    def test_build_review_prompt(self):
        """Test building review prompt"""
        mock_pr = Mock()
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_pr.description = "Test description"
        mock_pr.source_ref_name = "refs/heads/feature"
        mock_pr.target_ref_name = "refs/heads/main"
        
        changes = [
            {"path": "/src/test.cs", "change_type": "edit"},
            {"path": "/src/new.js", "change_type": "add"}
        ]
        
        file_type_summary = {
            FileType.CSHARP: ["/src/test.cs"],
            FileType.JAVASCRIPT: ["/src/new.js"]
        }
        
        with patch.object(self.reviewer, 'get_review_instructions') as mock_instructions:
            mock_instructions.return_value = "Review instructions"
            
            result = self.reviewer._build_review_prompt(mock_pr, changes, file_type_summary)
        
        self.assertIn("Pull Request #123", result)
        self.assertIn("Test PR", result)
        self.assertIn("File Type Summary", result)
        self.assertIn("Review Instructions", result)
    
    def test_add_change_to_prompt_delete(self):
        """Test adding deleted file to prompt"""
        change = {"path": "/src/deleted.cs", "change_type": "delete"}
        prompt_parts = []
        
        self.reviewer._add_change_to_prompt(change, prompt_parts)
        
        self.assertEqual(len(prompt_parts), 1)
        self.assertIn("Deleted", prompt_parts[0])
        self.assertIn("/src/deleted.cs", prompt_parts[0])
    
    def test_add_change_to_prompt_add(self):
        """Test adding new file to prompt"""
        change = {
            "path": "/src/new.cs",
            "change_type": "add",
            "new_content": "public class NewClass {}"
        }
        prompt_parts = []
        
        self.reviewer._add_change_to_prompt(change, prompt_parts)
        
        self.assertIn("Added", prompt_parts[0])
        self.assertIn("/src/new.cs", prompt_parts[0])
        self.assertIn("public class NewClass", prompt_parts[1])
    
    def test_add_change_to_prompt_edit(self):
        """Test adding edited file to prompt"""
        change = {
            "path": "/src/edited.cs",
            "change_type": "edit",
            "old_content": "public class OldClass {}",
            "new_content": "public class NewClass {}"
        }
        prompt_parts = []
        
        with patch.object(self.reviewer, '_create_simple_diff') as mock_diff:
            mock_diff.return_value = "- OldClass\n+ NewClass"
            
            self.reviewer._add_change_to_prompt(change, prompt_parts)
        
        self.assertIn("Modified", prompt_parts[0])
        self.assertIn("/src/edited.cs", prompt_parts[0])
        mock_diff.assert_called_once()
    
    def test_create_simple_diff(self):
        """Test creating simple diff"""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nline2_modified\nline3\nline4"
        
        result = self.reviewer._create_simple_diff(old_content, new_content)
        
        self.assertIn("  line1", result)  # Unchanged line
        self.assertIn("- line2", result)  # Removed line
        self.assertIn("+ line2_modified", result)  # Added line
        self.assertIn("+ line4", result)  # New line at end
    
    def test_create_simple_diff_truncation(self):
        """Test diff truncation for large files"""
        old_lines = [f"line{i}" for i in range(600)]
        new_lines = [f"newline{i}" for i in range(600)]
        old_content = "\n".join(old_lines)
        new_content = "\n".join(new_lines)
        
        result = self.reviewer._create_simple_diff(old_content, new_content)
        
        self.assertIn("... (diff truncated)", result)
        # Should have maximum 500 line pairs
        diff_lines = result.split("\n")
        self.assertLessEqual(len(diff_lines), 1001)  # 500*2 + truncation message
    
    def test_parse_review_response_valid(self):
        """Test parsing valid review response"""
        review_json = {
            "approved": True,
            "severity": "minor",
            "summary": "Looks good",
            "comments": [
                {
                    "file_path": "/src/test.cs",
                    "line_number": 10,
                    "content": "Consider using var",
                    "severity": "info"
                }
            ]
        }
        
        result = self.reviewer.parse_review_response(review_json)
        
        self.assertTrue(result["approved"])
        self.assertEqual(result["severity"], "minor")
        self.assertEqual(result["summary"], "Looks good")
        self.assertEqual(len(result["comments"]), 1)
    
    def test_parse_review_response_invalid(self):
        """Test parsing invalid review response"""
        review_json = {"invalid": "data"}
        
        result = self.reviewer.parse_review_response(review_json)
        
        self.assertFalse(result["approved"])
        self.assertEqual(result["severity"], "minor")
        self.assertEqual(result["summary"], "Could not parse review response")
        self.assertEqual(result["comments"], [])
    
    def test_parse_review_response_partial(self):
        """Test parsing partial review response"""
        review_json = {
            "approved": True,
            "summary": "Partial review"
            # Missing severity and comments
        }
        
        result = self.reviewer.parse_review_response(review_json)
        
        self.assertTrue(result["approved"])
        self.assertEqual(result["severity"], "minor")  # Default
        self.assertEqual(result["summary"], "Partial review")
        self.assertEqual(result["comments"], [])  # Default empty list


if __name__ == '__main__':
    unittest.main()