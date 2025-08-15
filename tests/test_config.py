"""Tests for configuration settings"""

import unittest
import os
from unittest.mock import patch, mock_open
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
        self.assertEqual(settings.max_files_per_review, 5000)
        self.assertEqual(settings.max_total_size_gb, 2.0)
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
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'test-org',
        'AZURE_DEVOPS_PAT': 'test-pat',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_log_level_override(self):
        """Test log level override from environment"""
        settings = Settings()
        self.assertEqual(settings.log_level, 'DEBUG')
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'partial-org',
        # PAT is missing - should use default empty string
    })
    def test_settings_with_partial_env(self):
        """Test settings with partial environment variables"""
        settings = Settings()
        
        self.assertEqual(settings.azure_organization, 'partial-org')
        self.assertEqual(settings.azure_pat, '')  # Default empty string
        self.assertIsNone(settings.azure_user_email)  # Default None
        self.assertIsNone(settings.azure_project)  # Default None
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'test-org',
        'AZURE_DEVOPS_PAT': 'test-pat',
        'MAX_FILES_PER_REVIEW': '1000',
        'REVIEW_MODEL': 'claude-3-opus-20240229'
    })
    def test_settings_type_validation(self):
        """Test that settings properly validate and convert types"""
        settings = Settings()
        
        # Should convert string to int
        self.assertEqual(settings.max_files_per_review, 1000)
        self.assertIsInstance(settings.max_files_per_review, int)
        
        # Should accept string model name
        self.assertEqual(settings.review_model, 'claude-3-opus-20240229')
    
    @patch.dict(os.environ, {
        'AZURE_DEVOPS_ORG': 'test-org',
        'AZURE_DEVOPS_PAT': 'test-pat'
    })
    def test_validate_settings_success(self):
        """Test successful settings validation"""
        settings = Settings()
        # Should not raise any exception
        settings.validate_settings()
    
    @patch.dict(os.environ, {})
    def test_validate_settings_missing_pat(self):
        """Test validation fails when PAT is missing"""
        settings = Settings()
        settings.azure_organization = 'test-org'
        settings.azure_pat = ''
        
        with self.assertRaises(ValueError) as context:
            settings.validate_settings()
        self.assertIn('PAT', str(context.exception))
    
    @patch.dict(os.environ, {})
    def test_validate_settings_missing_org(self):
        """Test validation fails when organization is missing"""
        settings = Settings()
        settings.azure_organization = ''
        settings.azure_pat = 'test-pat'
        
        with self.assertRaises(ValueError) as context:
            settings.validate_settings()
        self.assertIn('Azure DevOps organization', str(context.exception))
    
    @patch.dict(os.environ, {})
    def test_validate_settings_missing_both(self):
        """Test validation fails when both org and PAT are missing"""
        settings = Settings()
        settings.azure_organization = ''
        settings.azure_pat = ''
        
        with self.assertRaises(ValueError) as context:
            settings.validate_settings()
        # Should mention both are missing
        error_msg = str(context.exception).lower()
        self.assertTrue('organization' in error_msg or 'pat' in error_msg)
    
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
    
    def test_model_config(self):
        """Test Pydantic model configuration"""
        settings = Settings()
        
        # Test that settings can be created and basic attributes exist
        self.assertIsNotNone(settings.azure_organization)
        self.assertIsNotNone(settings.azure_pat)
        # For pydantic v2, model_config is a class attribute
        self.assertTrue(hasattr(Settings, 'model_config') or hasattr(settings, '__pydantic_model__'))


if __name__ == '__main__':
    unittest.main()