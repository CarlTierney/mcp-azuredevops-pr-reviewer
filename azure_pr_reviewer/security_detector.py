"""Comprehensive security detector for all file types"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class SecurityDetector:
    """Detects security issues across all file types"""
    
    def __init__(self):
        # Comprehensive password exposure detection patterns
        self.password_exposure_patterns = [
            # Method/property names that expose passwords
            (r'\b(reveal|get|show|display|expose|return|fetch|retrieve).*password\b', 'Method exposes password'),
            (r'\bpassword.*\.(get|show|reveal|display|expose|return|value|text)\b', 'Property exposes password'),
            (r'\b(public|export|global).*password\s*[=:]', 'Public password assignment'),
            (r'password\s*[:=]\s*["\'][^"\']{3,}["\']', 'Hardcoded password value'),
            (r'(http|api|url|uri).*[?&]password=', 'Password in URL parameter'),
            (r'password\s*[!=]==?\s*["\'][^"\']+["\']', 'Password comparison with literal'),
            (r'["\']\s*password\s*["\']\s*:\s*["\'][^"\']+["\']', 'Password in JSON/object structure'),
            (r'\bpassword\s*\+\s*', 'Password concatenation (potential exposure)'),
            (r'\$\{?password\}?', 'Password variable interpolation'),
        ]
        
        # Connection string detection patterns
        self.connection_string_patterns = [
            (r'\b(connection[_-]?string|connectionstring)\s*[:=]\s*["\'][^"\']*password[^"\']*["\']', 'Connection string with embedded password'),
            (r'\b(data\s+source|server|database)\s*=.*password\s*=', 'Database connection with password'),
            (r'\b(mongodb|mysql|postgresql|mssql|oracle)://[^\s]*:[^\s]*@', 'Database URL with credentials'),
            (r'\b(trusted_connection|integrated\s+security)\s*=\s*(false|no).*password', 'Non-integrated auth with password'),
            (r'\b(uid|user\s+id)\s*=.*pwd\s*=', 'Database connection with user/password'),
            (r'\b(provider|driver)\s*=.*password\s*=', 'Data provider connection with password'),
        ]
        
        # API keys, tokens, and secrets detection
        self.token_patterns = [
            (r'\b(api[_-]?key|apikey)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded API key'),
            (r'\b(secret[_-]?key|secretkey)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded secret key'),
            (r'\b(access[_-]?token|accesstoken)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded access token'),
            (r'\b(bearer[_-]?token|bearertoken)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded bearer token'),
            (r'\b(refresh[_-]?token|refreshtoken)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded refresh token'),
            (r'\b(private[_-]?key|privatekey)\s*[:=]\s*["\'][a-zA-Z0-9+/=]{32,}["\']', 'Hardcoded private key'),
            (r'\b(client[_-]?secret|clientsecret)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded client secret'),
            (r'\b(oauth[_-]?token|oauthtoken)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', 'Hardcoded OAuth token'),
            (r'\bauthorization\s*[:=]\s*["\']bearer\s+[a-zA-Z0-9]{16,}["\']', 'Authorization header with token'),
            (r'\b(jwt|token)\s*[:=]\s*["\']ey[a-zA-Z0-9+/=]{16,}["\']', 'JWT token hardcoded'),
        ]
        
        # Cloud service specific patterns
        self.cloud_secrets_patterns = [
            (r'\b(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']AKIA[0-9A-Z]{16}["\']', 'AWS Access Key ID'),
            (r'\b(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\'][a-zA-Z0-9+/]{40}["\']', 'AWS Secret Access Key'),
            (r'\b(azure[_-]?client[_-]?secret)\s*[:=]\s*["\'][a-zA-Z0-9~._-]{34,}["\']', 'Azure Client Secret'),
            (r'\b(gcp[_-]?service[_-]?account[_-]?key)\s*[:=]\s*["\'][a-zA-Z0-9+/=]{500,}["\']', 'GCP Service Account Key'),
        ]
        
        # Certificate and key patterns
        self.certificate_patterns = [
            (r'-----BEGIN\s+(PRIVATE\s+KEY|RSA\s+PRIVATE\s+KEY|CERTIFICATE)', 'Private key or certificate in code'),
            (r'\b(ssl[_-]?cert|certificate)\s*[:=]\s*["\'][^"\']{50,}["\']', 'SSL certificate hardcoded'),
            (r'\b(thumbprint|fingerprint)\s*[:=]\s*["\'][a-fA-F0-9]{40,}["\']', 'Certificate thumbprint'),
        ]
    
    def analyze_file_security(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze file for security issues - ONE consolidated comment per line"""
        
        if not content:
            return []
        
        # Group ALL issues by line number to consolidate
        from collections import defaultdict
        issues_by_line = defaultdict(list)
        lines = content.split('\n')
        
        # Check each line for ALL security issues
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            line_stripped = line.strip()
            
            # Skip empty lines and comments
            if not line_stripped or self._is_comment_line(line_stripped, file_path):
                continue
            
            # Collect ALL security issues for this line
            line_issues = []
            
            # 1. RevealPassword method detection (high priority)
            if 'revealpassword' in line_lower and ('public' in line_lower or 'private' in line_lower or 'protected' in line_lower):
                line_issues.append("CRITICAL: RevealPassword method exposes sensitive password information")
            
            # 2. Password return statements
            if line_stripped.startswith('return') and 'password' in line_lower:
                line_issues.append("CRITICAL: Method returns password value directly")
            
            # 3. Password logging (console, logger, debug, etc.)
            if self._is_logging_statement(line_lower) and self._contains_sensitive_data(line_lower):
                line_issues.append("CRITICAL: Sensitive data logged - passwords/secrets should never be logged")
            
            # 4. ToString with password
            if 'tostring' in line_lower and ('override' in line_lower or 'public' in line_lower) and self._contains_password_in_method(lines, line_num):
                line_issues.append("CRITICAL: ToString method exposes password information")
            
            # 5. Check all password exposure patterns
            for pattern, description in self.password_exposure_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if not self._is_duplicate_issue(description, line_issues):
                        line_issues.append(f"PASSWORD EXPOSURE: {description}")
            
            # 6. Check connection string patterns
            for pattern, description in self.connection_string_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if not self._is_duplicate_issue(description, line_issues):
                        line_issues.append(f"CONNECTION STRING LEAK: {description}")
            
            # 7. Check token/API key patterns
            for pattern, description in self.token_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if not self._is_duplicate_issue(description, line_issues):
                        line_issues.append(f"TOKEN LEAK: {description}")
            
            # 8. Check cloud service secrets
            for pattern, description in self.cloud_secrets_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if not self._is_duplicate_issue(description, line_issues):
                        line_issues.append(f"CLOUD SECRET LEAK: {description}")
            
            # 9. Check certificate patterns
            for pattern, description in self.certificate_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    if not self._is_duplicate_issue(description, line_issues):
                        line_issues.append(f"CERTIFICATE LEAK: {description}")
            
            # 10. Additional context-specific checks
            line_issues.extend(self._check_context_specific_issues(line, line_lower, file_path))
            
            # If we found issues for this line, consolidate into ONE comment
            if line_issues:
                # Remove duplicates and consolidate
                unique_issues = list(dict.fromkeys(line_issues))  # Preserve order, remove duplicates
                consolidated_message = ", ".join(unique_issues)
                
                issues_by_line[line_num] = {
                    "file_path": file_path,
                    "line_number": line_num,
                    "content": f"CRITICAL SECURITY: {consolidated_message}",
                    "severity": "error",
                    "issue_type": "security",
                    "line_content": line_stripped
                }
                logger.warning(f"Security issues found at {file_path}:{line_num} - {len(unique_issues)} issues consolidated")
        
        # Return ONE issue per line (consolidated)
        return list(issues_by_line.values())
    
    def _is_comment_line(self, line: str, file_path: str) -> bool:
        """Check if line is a comment based on file type"""
        
        line = line.strip()
        
        # C#, Java, JavaScript, TypeScript comments
        if file_path.endswith(('.cs', '.java', '.js', '.ts', '.tsx', '.jsx')):
            return line.startswith('//') or line.startswith('/*') or line.startswith('*')
        
        # Python comments
        elif file_path.endswith('.py'):
            return line.startswith('#')
        
        # SQL comments
        elif file_path.endswith('.sql'):
            return line.startswith('--') or line.startswith('/*')
        
        # HTML/XML comments
        elif file_path.endswith(('.html', '.xml', '.xaml')):
            return line.startswith('<!--')
        
        # CSS comments
        elif file_path.endswith('.css'):
            return line.startswith('/*')
        
        # Shell script comments
        elif file_path.endswith(('.sh', '.bash')):
            return line.startswith('#')
        
        return False
    
    def _contains_password_in_method(self, lines: List[str], method_start: int) -> bool:
        """Check if a method contains password in its body"""
        # Look for the method body (next few lines)
        for i in range(method_start, min(len(lines), method_start + 10)):
            if 'password' in lines[i].lower():
                return True
        return False
    
    def _is_logging_statement(self, line: str) -> bool:
        """Check if line is a logging statement"""
        logging_keywords = [
            'console.writeline', 'console.write', 'console.log',
            'log.info', 'log.debug', 'log.warn', 'log.error', 'log.trace',
            'logger.info', 'logger.debug', 'logger.warn', 'logger.error', 'logger.trace',
            'system.out.print', 'system.err.print',
            'debug.print', 'trace.write',
            'print(', 'println(',
            'response.write', 'response.send'
        ]
        return any(keyword in line for keyword in logging_keywords)
    
    def _contains_sensitive_data(self, line: str) -> bool:
        """Check if line contains sensitive data keywords"""
        sensitive_keywords = [
            'password', 'passwd', 'pwd',
            'secret', 'token', 'key',
            'credential', 'auth',
            'connection', 'connectionstring'
        ]
        return any(keyword in line for keyword in sensitive_keywords)
    
    def _is_duplicate_issue(self, description: str, existing_issues: List[str]) -> bool:
        """Check if this issue type already exists"""
        # Extract key words from description to check for duplicates
        key_words = description.lower().split()
        for existing in existing_issues:
            existing_words = existing.lower().split()
            # If there's significant overlap, consider it a duplicate
            overlap = set(key_words) & set(existing_words)
            if len(overlap) >= 2:  # At least 2 words in common
                return True
        return False
    
    def _check_context_specific_issues(self, line: str, line_lower: str, file_path: str) -> List[str]:
        """Check for context-specific security issues"""
        issues = []
        
        # Configuration files specific checks
        if file_path.endswith(('.config', '.xml', '.json', '.yaml', '.yml', '.properties', '.env')):
            # Check for sensitive values in config files
            if re.search(r'["\']\s*[a-zA-Z0-9+/=]{20,}\s*["\']', line):
                if any(word in line_lower for word in ['password', 'secret', 'key', 'token']):
                    issues.append("CONFIGURATION LEAK: Sensitive value in configuration file")
        
        # Code files specific checks
        if file_path.endswith(('.cs', '.java', '.js', '.ts', '.py', '.php')):
            # Check for base64 encoded secrets
            if re.search(r'["\'][A-Za-z0-9+/]{40,}={0,2}["\']', line):
                if any(word in line_lower for word in ['secret', 'key', 'token', 'password']):
                    issues.append("ENCODED SECRET: Base64 encoded secret detected")
            
            # Check for environment variable exposure
            if re.search(r'environment\.(get|getenv|getenvironmentvariable)', line_lower):
                if any(word in line_lower for word in ['password', 'secret', 'key', 'token']):
                    # This is actually good practice, but flag if it's being logged
                    if self._is_logging_statement(line_lower):
                        issues.append("ENVIRONMENT LEAK: Environment variable with secret being logged")
        
        # SQL files specific checks
        if file_path.endswith(('.sql', '.ddl')):
            if re.search(r'(password|secret)\s*=', line_lower):
                issues.append("SQL CREDENTIAL: Password or secret in SQL file")
        
        return issues
    
    def get_security_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Get security recommendations based on found issues"""
        
        recommendations = []
        
        password_issues = [i for i in issues if i.get('issue_type') == 'password_exposure']
        sensitive_data_issues = [i for i in issues if i.get('issue_type') == 'sensitive_data']
        
        if password_issues:
            recommendations.extend([
                "IMMEDIATE: Remove all methods that expose, return, or reveal password information",
                "REQUIRED: Ensure passwords are only used for validation/comparison, never exposed",
                "POLICY: No password values should ever be accessible through any public interface",
                "SECURITY: Review all logging statements to ensure no sensitive data is logged",
            ])
        
        if sensitive_data_issues:
            recommendations.extend([
                "REVIEW: Audit all sensitive data handling for proper encryption and access control",
                "SECURE: Move sensitive configuration to secure environment variables",
            ])
        
        return recommendations

def analyze_pr_security(changes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Analyze all PR changes for security issues"""
    
    detector = SecurityDetector()
    all_issues = []
    
    for change in changes:
        file_path = change.get('path', '')
        content = change.get('new_content', '')
        
        if content:
            file_issues = detector.analyze_file_security(file_path, content)
            all_issues.extend(file_issues)
    
    recommendations = detector.get_security_recommendations(all_issues)
    
    return all_issues, recommendations