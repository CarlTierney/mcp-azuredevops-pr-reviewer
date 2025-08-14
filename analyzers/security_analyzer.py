"""
Security Insights Analyzer
Analyzes security-related patterns in commits and code changes
"""

import pandas as pd
import re
from collections import defaultdict
from datetime import datetime


class SecurityAnalyzer:
    """Analyzes security-related patterns and potential vulnerabilities"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        
        # Security-related keywords and patterns
        self.security_keywords = {
            'authentication': ['auth', 'login', 'password', 'credential', 'token', 'oauth', 'jwt', 'session'],
            'authorization': ['permission', 'role', 'access', 'privilege', 'admin', 'rbac', 'acl'],
            'encryption': ['encrypt', 'decrypt', 'crypto', 'hash', 'salt', 'cipher', 'ssl', 'tls'],
            'vulnerability_fixes': ['fix', 'patch', 'security', 'vulnerability', 'cve', 'xss', 'injection', 'csrf'],
            'sensitive_data': ['api_key', 'secret', 'private', 'sensitive', 'confidential', 'pii', 'gdpr'],
            'security_config': ['cors', 'csp', 'hsts', 'firewall', 'waf', 'security-header'],
            'input_validation': ['sanitize', 'validate', 'escape', 'filter', 'whitelist', 'blacklist'],
            'audit': ['audit', 'log', 'monitor', 'track', 'compliance', 'forensic']
        }
        
        # Potentially risky patterns
        self.risky_patterns = {
            'hardcoded_secrets': [
                r'(?i)(password|pwd|passwd|pass)\s*=\s*["\'][^"\']+["\']',
                r'(?i)(api[_-]?key|apikey)\s*=\s*["\'][^"\']+["\']',
                r'(?i)(secret|token)\s*=\s*["\'][^"\']+["\']'
            ],
            'unsafe_functions': [
                r'eval\s*\(',
                r'exec\s*\(',
                r'system\s*\(',
                r'os\.system',
                r'subprocess\.call.*shell\s*=\s*True'
            ],
            'sql_patterns': [
                r'(?i)select\s+\*\s+from',
                r'(?i)drop\s+table',
                r'(?i)delete\s+from',
                r'string\.format.*(?i)(select|insert|update|delete)'
            ],
            'debug_code': [
                r'(?i)debug\s*=\s*true',
                r'console\.(log|debug|trace)',
                r'print\s*\(',
                r'(?i)todo|fixme|hack|xxx'
            ]
        }
    
    def analyze_security_insights(self):
        """Analyze security-related patterns in commits"""
        print("\n[SECURE] Analyzing Security Insights...")
        
        security_metrics = []
        
        # 1. Analyze commit messages for security keywords
        commit_security = self._analyze_commit_messages()
        
        # 2. Analyze file changes for security patterns
        file_security = self._analyze_file_changes()
        
        # 3. Analyze security-related file types
        file_type_security = self._analyze_security_file_types()
        
        # 4. Analyze developer security contributions
        developer_security = self._analyze_developer_security_focus()
        
        # 5. Compile security timeline
        security_timeline = self._create_security_timeline()
        
        # Create comprehensive security report
        security_summary = {
            'Analysis_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Total_Commits_Analyzed': len(self.analyzer.commits),
            'Security_Related_Commits': commit_security['total_security_commits'],
            'Security_Commit_Percentage': round(commit_security['security_percentage'], 2),
            'Vulnerability_Fixes': commit_security['vulnerability_fixes'],
            'Authentication_Changes': commit_security['auth_changes'],
            'Encryption_Updates': commit_security['encryption_updates'],
            'Security_Config_Changes': file_type_security['config_changes'],
            'Potential_Risk_Patterns': file_security['risk_patterns_found'],
            'Developers_With_Security_Focus': len(developer_security['security_developers']),
            'Recent_Security_Activity': security_timeline['recent_activity']
        }
        
        # Detailed metrics by category
        for category, count in commit_security['category_counts'].items():
            security_metrics.append({
                'Metric_Type': 'Commit Analysis',
                'Category': category.replace('_', ' ').title(),
                'Count': count,
                'Percentage': round((count / len(self.analyzer.commits) * 100) if self.analyzer.commits else 0, 2),
                'Risk_Level': self._assess_risk_level(category, count),
                'Details': f"Found in commit messages and descriptions"
            })
        
        # File security patterns
        for pattern_type, details in file_security['pattern_details'].items():
            security_metrics.append({
                'Metric_Type': 'Code Pattern Analysis',
                'Category': pattern_type.replace('_', ' ').title(),
                'Count': details['count'],
                'Percentage': round(details['percentage'], 2),
                'Risk_Level': details['risk_level'],
                'Details': details['details']
            })
        
        # Security file types
        for file_type, count in file_type_security['file_types'].items():
            security_metrics.append({
                'Metric_Type': 'Security File Analysis',
                'Category': file_type,
                'Count': count,
                'Percentage': round((count / file_type_security['total_files'] * 100) if file_type_security['total_files'] > 0 else 0, 2),
                'Risk_Level': 'Info',
                'Details': f"Security-related file type"
            })
        
        # Developer security focus
        for dev_name, dev_data in developer_security['developer_details'].items():
            if dev_data['security_commits'] > 0:
                security_metrics.append({
                    'Metric_Type': 'Developer Security Contribution',
                    'Category': dev_name,
                    'Count': dev_data['security_commits'],
                    'Percentage': round(dev_data['security_percentage'], 2),
                    'Risk_Level': 'Positive',
                    'Details': f"Primary focus: {dev_data['primary_focus']}"
                })
        
        # Convert to DataFrame
        df_security = pd.DataFrame(security_metrics)
        
        # Save security analysis
        output_file = f"{self.analyzer.data_dir}/azdo_security_insights.csv"
        df_security.to_csv(output_file, index=False)
        print(f"[OK] Security insights saved to: {output_file}")
        
        # Save summary
        summary_file = f"{self.analyzer.data_dir}/azdo_security_summary.csv"
        pd.DataFrame([security_summary]).to_csv(summary_file, index=False)
        print(f"[OK] Security summary saved to: {summary_file}")
        
        # Print insights
        self._print_security_insights(security_summary, df_security)
        
        return df_security
    
    def _analyze_commit_messages(self):
        """Analyze commit messages for security-related content"""
        results = {
            'total_security_commits': 0,
            'security_percentage': 0,
            'vulnerability_fixes': 0,
            'auth_changes': 0,
            'encryption_updates': 0,
            'category_counts': defaultdict(int)
        }
        
        if not self.analyzer.commits:
            return results
        
        for commit in self.analyzer.commits:
            message = commit.get('comment', '').lower()
            is_security_related = False
            
            for category, keywords in self.security_keywords.items():
                if any(keyword in message for keyword in keywords):
                    is_security_related = True
                    results['category_counts'][category] += 1
                    
                    if category == 'vulnerability_fixes':
                        results['vulnerability_fixes'] += 1
                    elif category == 'authentication':
                        results['auth_changes'] += 1
                    elif category == 'encryption':
                        results['encryption_updates'] += 1
            
            if is_security_related:
                results['total_security_commits'] += 1
        
        results['security_percentage'] = (results['total_security_commits'] / len(self.analyzer.commits) * 100) if self.analyzer.commits else 0
        
        return results
    
    def _analyze_file_changes(self):
        """Analyze file changes for security patterns"""
        results = {
            'risk_patterns_found': 0,
            'pattern_details': {},
            'files_with_risks': set()
        }
        
        if not self.analyzer.detailed_commits:
            return results
        
        pattern_counts = defaultdict(int)
        
        for commit in self.analyzer.detailed_commits:
            if 'changes' in commit:
                for change in commit['changes']:
                    if 'item' in change and 'path' in change['item']:
                        file_path = change['item']['path'].lower()
                        
                        # Check for risky patterns in file paths
                        for pattern_type, patterns in self.risky_patterns.items():
                            for pattern in patterns:
                                if re.search(pattern, file_path):
                                    pattern_counts[pattern_type] += 1
                                    results['files_with_risks'].add(file_path)
        
        results['risk_patterns_found'] = sum(pattern_counts.values())
        
        for pattern_type, count in pattern_counts.items():
            results['pattern_details'][pattern_type] = {
                'count': count,
                'percentage': (count / len(self.analyzer.detailed_commits) * 100) if self.analyzer.detailed_commits else 0,
                'risk_level': self._assess_pattern_risk(pattern_type),
                'details': self._get_pattern_description(pattern_type)
            }
        
        return results
    
    def _analyze_security_file_types(self):
        """Analyze security-related file types"""
        results = {
            'file_types': defaultdict(int),
            'config_changes': 0,
            'total_files': 0
        }
        
        security_extensions = {
            'Security Config': ['.htaccess', '.htpasswd', 'web.config', 'security.xml'],
            'Certificates': ['.pem', '.crt', '.key', '.pfx', '.p12'],
            'Environment': ['.env', '.env.example', '.env.local'],
            'Authentication': ['auth.js', 'auth.py', 'login.', 'authentication.'],
            'Encryption': ['crypto.', 'encrypt.', 'decrypt.']
        }
        
        if self.analyzer.detailed_commits:
            for commit in self.analyzer.detailed_commits:
                if 'changes' in commit:
                    for change in commit['changes']:
                        if 'item' in change and 'path' in change['item']:
                            file_path = change['item']['path'].lower()
                            results['total_files'] += 1
                            
                            for file_type, patterns in security_extensions.items():
                                if any(pattern in file_path for pattern in patterns):
                                    results['file_types'][file_type] += 1
                                    if file_type == 'Security Config':
                                        results['config_changes'] += 1
        
        return results
    
    def _analyze_developer_security_focus(self):
        """Analyze which developers focus on security"""
        results = {
            'security_developers': [],
            'developer_details': {}
        }
        
        developer_stats = defaultdict(lambda: {
            'total_commits': 0,
            'security_commits': 0,
            'categories': defaultdict(int)
        })
        
        for commit in self.analyzer.commits:
            developer = commit.get('author', {}).get('name', 'Unknown')
            message = commit.get('comment', '').lower()
            
            developer_stats[developer]['total_commits'] += 1
            
            for category, keywords in self.security_keywords.items():
                if any(keyword in message for keyword in keywords):
                    developer_stats[developer]['security_commits'] += 1
                    developer_stats[developer]['categories'][category] += 1
                    break
        
        for developer, stats in developer_stats.items():
            if stats['security_commits'] > 0:
                security_percentage = (stats['security_commits'] / stats['total_commits'] * 100)
                
                if security_percentage > 10:  # Developer with >10% security focus
                    results['security_developers'].append(developer)
                
                primary_focus = max(stats['categories'], key=stats['categories'].get) if stats['categories'] else 'General'
                
                results['developer_details'][developer] = {
                    'security_commits': stats['security_commits'],
                    'total_commits': stats['total_commits'],
                    'security_percentage': security_percentage,
                    'primary_focus': primary_focus.replace('_', ' ').title()
                }
        
        return results
    
    def _create_security_timeline(self):
        """Create timeline of security-related activities"""
        timeline = {
            'recent_activity': 'Low',
            'monthly_trends': defaultdict(int)
        }
        
        security_commits_by_date = []
        
        for commit in self.analyzer.commits:
            message = commit.get('comment', '').lower()
            commit_date = commit.get('author', {}).get('date', '')
            
            is_security = any(
                any(keyword in message for keyword in keywords)
                for keywords in self.security_keywords.values()
            )
            
            if is_security and commit_date:
                try:
                    date_obj = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                    month_key = date_obj.strftime('%Y-%m')
                    timeline['monthly_trends'][month_key] += 1
                    security_commits_by_date.append(date_obj)
                except:
                    pass
        
        # Assess recent activity
        if security_commits_by_date:
            recent_date = max(security_commits_by_date)
            days_since = (datetime.now() - recent_date.replace(tzinfo=None)).days
            
            if days_since < 7:
                timeline['recent_activity'] = 'High'
            elif days_since < 30:
                timeline['recent_activity'] = 'Medium'
            else:
                timeline['recent_activity'] = 'Low'
        
        return timeline
    
    def _assess_risk_level(self, category, count):
        """Assess risk level based on category and count"""
        if category in ['vulnerability_fixes', 'security_config']:
            return 'Critical' if count > 10 else 'High' if count > 5 else 'Medium'
        elif category in ['authentication', 'authorization', 'encryption']:
            return 'High' if count > 15 else 'Medium' if count > 5 else 'Low'
        else:
            return 'Info'
    
    def _assess_pattern_risk(self, pattern_type):
        """Assess risk level for specific patterns"""
        high_risk = ['hardcoded_secrets', 'unsafe_functions', 'sql_patterns']
        medium_risk = ['debug_code']
        
        if pattern_type in high_risk:
            return 'High'
        elif pattern_type in medium_risk:
            return 'Medium'
        else:
            return 'Low'
    
    def _get_pattern_description(self, pattern_type):
        """Get description for pattern types"""
        descriptions = {
            'hardcoded_secrets': 'Potential hardcoded credentials or API keys',
            'unsafe_functions': 'Use of potentially unsafe functions',
            'sql_patterns': 'SQL statements that may be vulnerable',
            'debug_code': 'Debug code or TODO comments'
        }
        return descriptions.get(pattern_type, 'Security pattern detected')
    
    def _print_security_insights(self, summary, df_security):
        """Print security analysis insights"""
        print("\n[SECURITY] Security Analysis Summary:")
        print(f"  Total commits analyzed: {summary['Total_Commits_Analyzed']}")
        print(f"  Security-related commits: {summary['Security_Related_Commits']} ({summary['Security_Commit_Percentage']}%)")
        print(f"  Vulnerability fixes: {summary['Vulnerability_Fixes']}")
        print(f"  Authentication changes: {summary['Authentication_Changes']}")
        print(f"  Recent security activity: {summary['Recent_Security_Activity']}")
        
        if not df_security.empty:
            high_risk = df_security[df_security['Risk_Level'].isin(['High', 'Critical'])]
            if not high_risk.empty:
                print("\n[WARNING] High Risk Items:")
                for _, row in high_risk.head(5).iterrows():
                    print(f"  - {row['Category']}: {row['Count']} occurrences ({row['Risk_Level']})")
        
        print(f"\n[INFO] Security-focused developers: {summary['Developers_With_Security_Focus']}")