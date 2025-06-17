#!/usr/bin/env python3
"""
File classification and content analysis utilities
"""

import os
import radon.complexity as radon_cc
import radon.raw as radon_raw

class FileClassifier:
    def __init__(self):
        # Enhanced file type classifications optimized for C#/SQL environments
        self.code_extensions = {
            'csharp': ['.cs', '.vb', '.fs'],
            'csharp_project': ['.csproj', '.vbproj', '.fsproj', '.sln'],
            'dotnet_config': ['.config', '.settings', '.resx', '.xaml'],
            'sql': ['.sql', '.tsql'],
            'sql_server': ['.dacpac', '.bacpac', '.sqlproj'],
            'database': ['.mdf', '.ldf', '.bak'],
            'web_dotnet': ['.aspx', '.ascx', '.master', '.cshtml', '.vbhtml', '.razor'],
            'web_client': ['.html', '.css', '.scss', '.sass', '.less', '.js', '.ts', '.jsx', '.tsx'],
            'api_specs': ['.json', '.yaml', '.yml', '.xml', '.wsdl'],
            'test_csharp': ['.cs'],  # Will be detected by path analysis
            'config': ['.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.appsettings.json'],
            'docs': ['.md', '.rst', '.txt', '.doc', '.docx'],
            'scripts': ['.ps1', '.bat', '.cmd', '.sh'],
            'other': []
        }
        
        # Architecture patterns for better health assessment
        self.architecture_patterns = {
            'controllers': ['controller', 'api', 'endpoint'],
            'services': ['service', 'manager', 'handler', 'business'],
            'models': ['model', 'dto', 'entity', 'domain', 'viewmodel'],
            'repositories': ['repository', 'dataaccess', 'dal'],
            'infrastructure': ['config', 'startup', 'program', 'middleware'],
            'tests': ['test', 'spec', 'unittest', 'integration']
        }
    
    def classify_file_type(self, filename):
        """Enhanced file classification for C#/SQL environments"""
        if not filename:
            return 'other'
            
        filename_lower = filename.lower()
        ext = os.path.splitext(filename_lower)[1]
        
        # Special handling for test files
        if any(test_indicator in filename_lower for test_indicator in ['test', 'tests', 'spec', 'specs', 'unittest']):
            if ext == '.cs':
                return 'test_csharp'
            elif ext == '.sql':
                return 'test_sql'
        
        # Special handling for appsettings files
        if 'appsettings' in filename_lower and ext == '.json':
            return 'dotnet_config'
            
        # Migration files
        if 'migration' in filename_lower and ext in ['.cs', '.sql']:
            return 'database_migration'
            
        # Check standard extensions
        for lang, extensions in self.code_extensions.items():
            if ext in extensions:
                return lang
                
        return 'other'
    
    def classify_architecture_area(self, file_path, filename):
        """Classify files into architecture areas"""
        path_lower = file_path.lower()
        filename_lower = filename.lower()
        
        for area, patterns in self.architecture_patterns.items():
            for pattern in patterns:
                if pattern in path_lower or pattern in filename_lower:
                    return area
        
        # Default classification based on file type
        file_type = self.classify_file_type(filename)
        if file_type in ['csharp', 'web_dotnet']:
            return 'application'
        elif file_type in ['sql', 'sql_server']:
            return 'database'
        elif file_type in ['config', 'dotnet_config']:
            return 'infrastructure'
        else:
            return 'other'
    
    def is_critical_component(self, file_path, filename, file_type):
        """Determine if a file/component is critical to the system"""
        critical_indicators = [
            'startup', 'program.cs', 'main.cs', 'global.asax',
            'web.config', 'app.config', 'appsettings.json',
            'dockerfile', 'docker-compose', '.csproj', '.sln',
            'migration', 'seed', 'schema'
        ]
        
        path_lower = file_path.lower()
        filename_lower = filename.lower()
        
        # Check for critical file patterns
        for indicator in critical_indicators:
            if indicator in filename_lower or indicator in path_lower:
                return True
        
        # Check for core business logic patterns
        business_patterns = ['service', 'controller', 'manager', 'handler', 'core', 'business']
        for pattern in business_patterns:
            if pattern in path_lower and file_type in ['csharp', 'sql']:
                return True
        
        return False

class ContentAnalyzer:
    @staticmethod
    def calculate_cyclomatic_complexity(code, filename):
        """Calculate cyclomatic complexity for code snippet"""
        if not code or not isinstance(code, str):
            return 1  # Minimum complexity
            
        # Only analyze code files that can have complexity measured
        ext = os.path.splitext(filename.lower())[1] if filename else ''
        if ext not in ['.cs', '.vb', '.fs', '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c']:
            return 1
            
        try:
            # Use radon to calculate complexity for supported languages
            results = radon_cc.cc_visit(code)
            if results:
                # Average complexity of all functions/classes
                return sum(item.complexity for item in results) / len(results)
            else:
                # If no functions found, use minimum complexity
                return 1
        except Exception:
            # Fallback to minimum complexity if analysis fails
            return 1
    
    @staticmethod
    def analyze_file_contents(content):
        """Analyze file contents for metrics like LOC and complexity"""
        if not content or not isinstance(content, str):
            return {
                'loc': 0,
                'sloc': 0,  # Source lines of code (non-blank)
                'lloc': 0,  # Logical lines of code
                'comments': 0,
                'multi': 0,  # Multi-line strings/comments
                'blank': 0
            }
            
        try:
            # Use radon to analyze raw metrics
            raw_metrics = radon_raw.analyze(content)
            return {
                'loc': raw_metrics.loc,  # Lines of code
                'sloc': raw_metrics.sloc,  # Source lines of code (non-blank)
                'lloc': raw_metrics.lloc,  # Logical lines of code
                'comments': raw_metrics.comments,
                'multi': raw_metrics.multi,  # Multi-line strings/comments
                'blank': raw_metrics.blank
            }
        except Exception:
            # Fallback to simple line counting if radon fails
            lines = content.splitlines()
            non_blank_lines = sum(1 for line in lines if line.strip())
            return {
                'loc': len(lines),
                'sloc': non_blank_lines,
                'lloc': non_blank_lines,
                'comments': 0,
                'multi': 0,
                'blank': len(lines) - non_blank_lines
            }
    
    @staticmethod
    def detect_anti_patterns(content, filename, file_type):
        """Detect common anti-patterns in code"""
        anti_patterns = []
        if not content:
            return anti_patterns
        
        lines = content.splitlines()
        content_lower = content.lower()
        
        # General anti-patterns
        if len(lines) > 1000:
            anti_patterns.append("Large_File")
        
        # Count long methods/functions (rough estimate)
        long_methods = sum(1 for line in lines if len(line.strip()) > 120)
        if long_methods > len(lines) * 0.2:
            anti_patterns.append("Long_Lines")
        
        # C# specific anti-patterns
        if file_type in ['csharp', 'test_csharp']:
            if 'catch (exception' in content_lower and 'throw;' not in content_lower:
                anti_patterns.append("Swallowed_Exceptions")
            
            if content_lower.count('public static') > 10:
                anti_patterns.append("Excessive_Static_Usage")
            
            if 'thread.sleep' in content_lower:
                anti_patterns.append("Thread_Sleep_Usage")
            
            # Detect God classes (many public methods)
            public_methods = content_lower.count('public ') - content_lower.count('public class')
            if public_methods > 20:
                anti_patterns.append("God_Class")
        
        # SQL specific anti-patterns
        elif file_type in ['sql', 'sql_server']:
            if 'select *' in content_lower:
                anti_patterns.append("Select_Star")
            
            if content_lower.count('cursor') > 0:
                anti_patterns.append("Cursor_Usage")
            
            if 'nolock' in content_lower:
                anti_patterns.append("NoLock_Hint")
            
            if content_lower.count('union') > 5:
                anti_patterns.append("Excessive_Unions")
        
        return anti_patterns
    
    @staticmethod
    def analyze_sql_debt(content, filename):
        """Analyze SQL-specific technical debt"""
        content_lower = content.lower()
        
        # Stored procedure debt indicators
        procedure_debt = 0
        if 'create procedure' in content_lower or 'alter procedure' in content_lower:
            # Complex procedures
            if len(content.splitlines()) > 100:
                procedure_debt += 2
            if content_lower.count('cursor') > 0:
                procedure_debt += 3
            if content_lower.count('goto') > 0:
                procedure_debt += 2
            if content_lower.count('try') == 0 and len(content.splitlines()) > 50:
                procedure_debt += 1  # No error handling
        
        # View complexity
        view_complexity = 0
        if 'create view' in content_lower or 'alter view' in content_lower:
            # Nested subqueries
            view_complexity += content_lower.count('select') - 1
            # Multiple joins
            view_complexity += content_lower.count('join')
            # Complex expressions
            view_complexity += content_lower.count('case when')
        
        return {
            'procedure_debt': procedure_debt,
            'view_complexity': view_complexity
        }
    
    @staticmethod
    def analyze_test_debt(content, filename):
        """Analyze test-specific debt indicators"""
        debt_indicators = []
        if not content:
            return debt_indicators
        
        content_lower = content.lower()
        lines = content.splitlines()
        
        # Test smells
        if 'thread.sleep' in content_lower:
            debt_indicators.append("Sleep_In_Tests")
        
        if len(lines) > 200:
            debt_indicators.append("Large_Test_File")
        
        # C# test specific
        if '.cs' in filename.lower():
            if '[ignore]' in content_lower or '[fact(skip' in content_lower:
                debt_indicators.append("Ignored_Tests")
            
            if content_lower.count('assert') < 5 and len(lines) > 50:
                debt_indicators.append("Few_Assertions")
            
            if 'hardcoded' in content_lower or '127.0.0.1' in content or 'localhost' in content_lower:
                debt_indicators.append("Hardcoded_Dependencies")
        
        return debt_indicators
