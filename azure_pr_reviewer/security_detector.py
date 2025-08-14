"""Comprehensive security detector for all file types"""

import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class SecurityDetector:
    """Detects security issues across all file types"""
    
    def __init__(self):
        # Simplified password-related security patterns to avoid over-detection
        self.password_exposure_patterns = [
            # Only catch obvious password exposure (avoid duplicates with specific checks)
            (r'\bpassword.*\.(get|show|reveal|display|expose|return)\b', 'Property/method exposes password'),
            (r'(public|export|global).*password\s*=', 'Public password assignment'),
            (r'password\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded password'),
            (r'(http|api|url).*password=', 'Password in URL parameter'),
            (r'password\s*==\s*["\'][^"\']+["\']', 'Password comparison with literal'),
            (r'["\']\s*password\s*["\']\s*:\s*', 'Password in JSON structure'),
        ]
        
        # Sensitive data patterns beyond passwords (limited to avoid noise)
        self.sensitive_data_patterns = [
            (r'\b(api[_-]?key|secret[_-]?key)\b.*[:=]\s*["\'][^"\']+["\']', 'Hardcoded API/secret key'),
            (r'\b(connection[_-]?string)\b.*[:=]\s*["\'][^"\']+["\']', 'Hardcoded connection string'),
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
            
            # RevealPassword method detection
            if 'revealpassword' in line_lower and ('public' in line_lower or 'private' in line_lower or 'protected' in line_lower):
                line_issues.append("RevealPassword method exposes sensitive password information")
            
            # Password return statements
            if line_stripped.startswith('return') and 'password' in line_lower:
                line_issues.append("Method returns password value directly")
            
            # Password logging
            if ('log' in line_lower or 'console' in line_lower) and 'password' in line_lower and not line_lower.strip().startswith('//'):
                line_issues.append("Password logging detected - sensitive data should never be logged")
            
            # ToString with password
            if 'tostring' in line_lower and ('override' in line_lower or 'public' in line_lower) and self._contains_password_in_method(lines, line_num):
                line_issues.append("ToString method exposes password information")
            
            # General password exposure patterns
            for pattern, description in self.password_exposure_patterns:
                if re.search(pattern, line_lower, re.IGNORECASE):
                    # Check if we already have this type of issue
                    if not any(desc in description for desc in line_issues):
                        line_issues.append(description)
            
            # Sensitive data patterns
            for pattern, description in self.sensitive_data_patterns:
                if re.search(pattern, line_lower, re.IGNORECASE):
                    if not any(desc in description for desc in line_issues):
                        line_issues.append(description)
            
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