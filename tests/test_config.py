"""Unit tests for configuration settings"""

import unittest
import os
from unittest.mock import patch, Mock
from azure_pr_reviewer.config import Settings


class TestSettings(unittest.TestCase):
    """Test suite for Settings configuration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Store original environment variables
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'test-org',
        'AZURE_DEVOPS_PAT': 'test-pat-123',
        'AZURE_USER_EMAIL': 'user@example.com',
        'AZURE_DEVOPS_PROJECT': 'test-project'
    })
    def test_settings_from_env_vars(self):
        """Test loading settings from environment variables"""
        settings = Settings()
        
        self.assertEqual(settings.azure_organization, 'test-org')
        self.assertEqual(settings.azure_pat, 'test-pat-123')
        self.assertEqual(settings.azure_user_email, 'user@example.com')
        self.assertEqual(settings.azure_project, 'test-project')
    
    def test_default_settings(self):
        """Test default settings values"""
        settings = Settings()
        
        # Review settings defaults
        self.assertEqual(settings.auto_approve_threshold, 0.9)
        self.assertEqual(settings.max_file_size_kb, 500)
        self.assertEqual(settings.review_model, "claude-3-5-sonnet-20241022")
        self.assertIsNone(settings.custom_review_prompt_file)
        
        # MCP Server settings defaults
        self.assertEqual(settings.server_name, "azure-pr-reviewer")
        self.assertEqual(settings.log_level, "INFO")
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'my-org',
        'AZURE_DEVOPS_PAT': 'my-pat',
        'CUSTOM_REVIEW_PROMPT_FILE': '/path/to/prompt.txt'
    })
    def test_custom_review_prompt_file(self):
        """Test custom review prompt file setting"""
        settings = Settings()
        
        self.assertEqual(settings.custom_review_prompt_file, '/path/to/prompt.txt')
    
    def test_validate_settings_success(self):
        """Test successful validation with required settings"""
        settings = Settings(
            azure_organization="test-org",
            azure_pat="test-pat"
        )
        
        result = settings.validate_settings()
        self.assertTrue(result)
    
    def test_validate_settings_missing_org(self):
        """Test validation failure when organization is missing"""
        settings = Settings(azure_pat="test-pat")
        
        with self.assertRaises(ValueError) as context:
            settings.validate_settings()
        
        self.assertIn("AZURE_DEVOPS_ORG is required", str(context.exception))
    
    def test_validate_settings_missing_pat(self):
        """Test validation failure when PAT is missing"""
        settings = Settings(azure_organization="test-org")
        
        with self.assertRaises(ValueError) as context:
            settings.validate_settings()
        
        self.assertIn("AZURE_DEVOPS_PAT is required", str(context.exception))
    
    def test_validate_settings_missing_both(self):
        """Test validation failure when both required fields are missing"""
        settings = Settings()
        
        with self.assertRaises(ValueError) as context:
            settings.validate_settings()
        
        error_message = str(context.exception)
        self.assertIn("AZURE_DEVOPS_ORG is required", error_message)
        self.assertIn("AZURE_DEVOPS_PAT is required", error_message)
    
    def test_model_config(self):
        """Test model configuration settings"""
        settings = Settings()
        
        self.assertEqual(settings.model_config["env_file"], ".env")
        self.assertEqual(settings.model_config["env_file_encoding"], "utf-8")
        self.assertEqual(settings.model_config["extra"], "allow")
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'test-org',
        'AZURE_DEVOPS_PAT': 'test-pat',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_log_level_override(self):
        """Test overriding log level"""
        # Note: LOG_LEVEL is not directly mapped in the Settings class,
        # but log_level has a default. This tests the default behavior.
        settings = Settings()
        
        # Should still be INFO as LOG_LEVEL env var is not mapped
        self.assertEqual(settings.log_level, "INFO")
        
        # But we can set it directly
        settings = Settings(log_level="DEBUG")
        self.assertEqual(settings.log_level, "DEBUG")
    
    def test_settings_with_partial_env(self):
        """Test settings with partial environment variables"""
        with patch.dict(os.environ, {'AZURE_DEVOPS_ORG': 'partial-org'}):
            settings = Settings()
            
            self.assertEqual(settings.azure_organization, 'partial-org')
            self.assertEqual(settings.azure_pat, '')  # Default empty string
            self.assertIsNone(settings.azure_user_email)  # Default None
            self.assertIsNone(settings.azure_project)  # Default None
    
    def test_settings_field_descriptions(self):
        """Test that field descriptions are properly set"""
        # This test verifies the field configurations are correct
        settings = Settings()
        
        # Check that the settings object has the expected attributes
        self.assertTrue(hasattr(settings, 'azure_organization'))
        self.assertTrue(hasattr(settings, 'azure_pat'))
        self.assertTrue(hasattr(settings, 'azure_user_email'))
        self.assertTrue(hasattr(settings, 'azure_project'))
        self.assertTrue(hasattr(settings, 'auto_approve_threshold'))
        self.assertTrue(hasattr(settings, 'max_file_size_kb'))
        self.assertTrue(hasattr(settings, 'review_model'))
        self.assertTrue(hasattr(settings, 'custom_review_prompt_file'))
        self.assertTrue(hasattr(settings, 'server_name'))
        self.assertTrue(hasattr(settings, 'log_level'))
    
    def test_settings_type_validation(self):
        """Test type validation for settings"""
        # Test with invalid types
        settings = Settings(
            auto_approve_threshold=0.95,  # Should be float
            max_file_size_kb=1000  # Should be int
        )
        
        self.assertIsInstance(settings.auto_approve_threshold, float)
        self.assertIsInstance(settings.max_file_size_kb, int)
        self.assertEqual(settings.auto_approve_threshold, 0.95)
        self.assertEqual(settings.max_file_size_kb, 1000)


if __name__ == '__main__':
    unittest.main()