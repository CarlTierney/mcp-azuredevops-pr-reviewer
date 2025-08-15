"""Comprehensive unit tests for expanded security pattern detection"""

import unittest
from azure_pr_reviewer.security_detector import SecurityDetector


class TestExpandedSecurityPatterns(unittest.TestCase):
    """Test comprehensive security detection patterns"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = SecurityDetector()
    
    def test_password_exposure_patterns(self):
        """Test detection of various password exposure patterns"""
        
        test_cases = [
            # RevealPassword methods
            ("public string RevealPassword() { return password; }", True, "RevealPassword"),
            ("private string getPassword() { return this.password; }", True, "password"),
            ("public string showPassword() { return pwd; }", True, "password"),
            
            # Property exposure
            ("password.get()", True, "password"),
            ("user.password.value", True, "password"),
            ("return password.text", True, "password"),
            
            # Public assignment
            ("public string password = \"secret123\";", True, "password"),
            ("global password: \"mypassword\"", True, "password"),
            
            # Hardcoded passwords
            ("password = \"hardcoded123\";", True, "password"),
            ("pwd: \"secret123\"", True, "password"),
            
            # URL parameters
            ("https://api.example.com?password=secret", True, "password"),
            ("api_url&password=test123", True, "password"),
            
            # JSON structures
            ("\"password\": \"secret123\"", True, "password"),
            ("'password': 'test123'", True, "password"),
        ]
        
        for code, should_detect, keyword in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("test.cs", code)
                if should_detect:
                    self.assertGreater(len(issues), 0, f"Should detect issue in: {code}")
                    self.assertIn(keyword.lower(), issues[0]["content"].lower())
                else:
                    self.assertEqual(len(issues), 0, f"Should not detect issue in: {code}")
    
    def test_connection_string_patterns(self):
        """Test detection of connection string leaks"""
        
        test_cases = [
            # Connection strings with passwords
            ("connectionString = \"Server=localhost;Database=test;User=admin;Password=secret123;\";", True),
            ("string connStr = \"Data Source=server;Initial Catalog=db;User ID=user;Password=pass;\";", True),
            ("mongodb://admin:password123@localhost:27017/mydb", True),
            ("mysql://user:secret@localhost:3306/database", True),
            ("postgresql://username:password@host:5432/dbname", True),
            
            # Non-integrated authentication
            ("Trusted_Connection=false;User ID=admin;Password=secret;", True),
            ("Integrated Security=no;pwd=mypassword;", True),
            
            # Provider connections
            ("Provider=SQLOLEDB;Server=localhost;Database=test;User ID=sa;Password=admin123;", True),
            
            # Safe connections (should not trigger)
            ("Trusted_Connection=true;Integrated Security=SSPI;", False),
            ("connectionString = Environment.GetEnvironmentVariable(\"DB_CONNECTION\");", False),
        ]
        
        for code, should_detect in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("config.cs", code)
                if should_detect:
                    self.assertGreater(len(issues), 0, f"Should detect connection string issue in: {code}")
                    self.assertTrue(any("CONNECTION" in issue["content"] for issue in issues))
                else:
                    self.assertEqual(len(issues), 0, f"Should not detect issue in: {code}")
    
    def test_token_and_api_key_patterns(self):
        """Test detection of API keys, tokens, and secrets"""
        
        test_cases = [
            # API Keys
            ("apiKey = \"AIzaSyDXQF4dGHgF_abc123def456ghi789jkl\";", True, "API"),
            ("api_key: \"sk-1234567890abcdef1234567890abcdef\";", True, "API"),
            
            # Secret Keys
            ("secretKey = \"abc123def456ghi789jkl012mno345pqr\";", True, "secret"),
            ("secret_key: \"very_long_secret_key_here_123456789\";", True, "secret"),
            
            # Access Tokens
            ("accessToken = \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\";", True, "TOKEN"),
            ("access_token: \"ghp_1234567890abcdef1234567890abcdef12345678\";", True, "TOKEN"),
            
            # Bearer Tokens
            ("bearerToken = \"Bearer abc123def456ghi789jkl012mno345\";", True, "TOKEN"),
            
            # Client Secrets
            ("clientSecret = \"1234567890abcdef1234567890abcdef\";", True, "secret"),
            
            # JWT Tokens
            ("jwt = \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ\";", True, "jwt"),
            
            # Authorization headers
            ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\";", True, "Authorization"),
            
            # Short values should not trigger (avoid false positives)
            ("apiKey = \"short\";", False, ""),
            ("token = \"abc\";", False, ""),
        ]
        
        for code, should_detect, keyword in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("app.js", code)
                if should_detect:
                    self.assertGreater(len(issues), 0, f"Should detect token/key issue in: {code}")
                    if keyword:
                        self.assertTrue(any(keyword.upper() in issue["content"].upper() for issue in issues))
                else:
                    self.assertEqual(len(issues), 0, f"Should not detect issue in: {code}")
    
    def test_cloud_service_secrets(self):
        """Test detection of cloud service specific secrets"""
        
        test_cases = [
            # AWS Credentials
            ("AWS_ACCESS_KEY_ID = \"AKIAIOSFODNN7EXAMPLE\";", True, "AWS"),
            ("aws_secret_access_key: \"wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\";", True, "AWS"),
            
            # Azure Secrets
            ("azure_client_secret = \"abc123~def456_ghi789-jkl012.mno345\";", True, "Azure"),
            
            # GCP Service Account (long base64 key)
            ("gcp_service_account_key = \"" + "a" * 500 + "\";", True, "GCP"),
        ]
        
        for code, should_detect, keyword in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("config.py", code)
                if should_detect:
                    self.assertGreater(len(issues), 0, f"Should detect cloud secret in: {code}")
                    self.assertTrue(any(keyword.upper() in issue["content"].upper() for issue in issues))
                else:
                    self.assertEqual(len(issues), 0, f"Should not detect issue in: {code}")
    
    def test_certificate_patterns(self):
        """Test detection of certificates and private keys in code"""
        
        test_cases = [
            # Private keys
            ("-----BEGIN PRIVATE KEY-----", True),
            ("-----BEGIN RSA PRIVATE KEY-----", True),
            ("-----BEGIN CERTIFICATE-----", True),
            
            # SSL certificates
            ("sslCert = \"MIIEpAIBAAKCAQEA7dGKEUZU9vdNTYjUKBk1F...\";", True),
            
            # Certificate thumbprints
            ("thumbprint = \"1234567890abcdef1234567890abcdef12345678\";", True),
            ("fingerprint: \"abcdef1234567890abcdef1234567890abcdef12\";", True),
        ]
        
        for code, should_detect in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("security.cs", code)
                if should_detect:
                    self.assertGreater(len(issues), 0, f"Should detect certificate issue in: {code}")
                    self.assertTrue(any("CERTIFICATE" in issue["content"] or "PRIVATE" in issue["content"] 
                                      or "thumbprint" in issue["content"].lower() for issue in issues))
                else:
                    self.assertEqual(len(issues), 0, f"Should not detect issue in: {code}")
    
    def test_logging_detection(self):
        """Test detection of sensitive data in logging statements"""
        
        test_cases = [
            # Console logging
            ("Console.WriteLine($\"Password: {password}\");", True),
            ("console.log('User password: ' + userPassword);", True),
            ("System.out.println(\"Secret: \" + secret);", True),
            
            # Logger usage
            ("logger.info(\"User logged in with password: \" + pwd);", True),
            ("log.debug($\"Token: {accessToken}\");", True),
            
            # Response writing
            ("response.write(\"Connection string: \" + connStr);", True),
            
            # Safe logging (should not trigger)
            ("Console.WriteLine(\"User logged in successfully\");", False),
            ("logger.info(\"Authentication completed\");", False),
        ]
        
        for code, should_detect in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("logger.cs", code)
                if should_detect:
                    self.assertGreater(len(issues), 0, f"Should detect logging issue in: {code}")
                    self.assertTrue(any("logged" in issue["content"].lower() or "CRITICAL" in issue["content"] for issue in issues))
                else:
                    self.assertEqual(len(issues), 0, f"Should not detect logging issue in: {code}")
    
    def test_configuration_file_detection(self):
        """Test detection of secrets in configuration files"""
        
        config_content = '''
        {
          "database": {
            "password": "secretDatabasePassword123",
            "connectionString": "Server=prod;Password=secret123;"
          },
          "api": {
            "key": "AIzaSyDXQF4dGHgF_reallyLongApiKey123456789"
          }
        }
        '''
        
        issues = self.detector.analyze_file_security("appsettings.json", config_content)
        
        # Should detect multiple issues in config file
        self.assertGreater(len(issues), 0, "Should detect issues in configuration file")
        
        # Check that different types of issues are detected
        issue_contents = [issue["content"] for issue in issues]
        all_content = " ".join(issue_contents).upper()
        
        # Should detect password and API key
        self.assertTrue(any("PASSWORD" in content for content in issue_contents))
    
    def test_no_false_positives_in_comments(self):
        """Test that commented code doesn't trigger false positives"""
        
        test_cases = [
            "// This method used to have RevealPassword but was removed",
            "/* connectionString = \"Server=test;Password=old;\"; */",
            "# apiKey = \"old_key_that_was_removed\"",
            "<!-- password field removed from config -->",
        ]
        
        for code in test_cases:
            with self.subTest(code=code):
                issues = self.detector.analyze_file_security("test.cs", code)
                self.assertEqual(len(issues), 0, f"Should not detect issues in commented code: {code}")
    
    def test_consolidated_multiple_issues_per_line(self):
        """Test that multiple security issues on the same line are consolidated"""
        
        # Line with multiple security issues
        code = "public string RevealPassword() { logger.info($\"Password: {password}\"); return password; }"
        
        issues = self.detector.analyze_file_security("BadSecurity.cs", code)
        
        # Should consolidate into one issue per line
        self.assertEqual(len(issues), 1, "Should consolidate multiple issues on same line")
        
        # Should mention multiple types of issues in the consolidated message
        issue_content = issues[0]["content"].upper()
        self.assertIn("CRITICAL", issue_content)
        # Should have RevealPassword and logging issues mentioned
        self.assertTrue("REVEALPASSWORD" in issue_content or "PASSWORD" in issue_content)
    
    def test_comprehensive_real_world_scenarios(self):
        """Test realistic code scenarios with security issues"""
        
        # Realistic C# class with multiple security issues
        vulnerable_code = '''
public class UserService {
    private string connectionString = "Server=prod;Database=users;User=admin;Password=prod123!;";
    private string apiKey = "AIzaSyDXQF4dGHgF_realApiKey123456789abcdef";
    
    public string RevealPassword() {
        return this.password;
    }
    
    public void LogUserData(string username, string password) {
        Console.WriteLine($"Login attempt: {username} with password {password}");
        logger.Info($"API Key being used: {apiKey}");
    }
    
    public override string ToString() {
        return $"User service with connection: {connectionString}";
    }
    
    public string GetDatabaseConnection() {
        return connectionString; // Returns connection string with embedded password
    }
}
'''
        
        issues = self.detector.analyze_file_security("UserService.cs", vulnerable_code)
        
        # Should detect multiple different types of security issues
        self.assertGreater(len(issues), 3, "Should detect multiple security issues in realistic code")
        
        # Check for different categories of issues
        issue_contents = [issue["content"] for issue in issues]
        all_content = " ".join(issue_contents).upper()
        
        # Should detect connection string, API key, RevealPassword, and logging issues
        security_categories = ["CONNECTION", "API", "REVEALPASSWORD", "PASSWORD", "TOKEN", "CRITICAL"]
        detected_categories = [cat for cat in security_categories if cat in all_content]
        
        self.assertGreater(len(detected_categories), 2, 
                          f"Should detect multiple security categories. Found: {detected_categories}")


if __name__ == '__main__':
    unittest.main()