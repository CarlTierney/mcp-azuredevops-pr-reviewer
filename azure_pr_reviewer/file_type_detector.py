"""File type detection and prompt selection system"""

import os
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re

class FileType(Enum):
    """Enumeration of supported file types for review"""
    CSHARP = "csharp"
    RAZOR_VIEW = "razor_view"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SQL = "sql"
    MARKDOWN = "markdown"
    TEST_CSHARP = "test_csharp"
    TEST_JAVASCRIPT = "test_javascript"
    CONFIG = "config"
    JSON = "json"
    XML = "xml"
    CSS = "css"
    HTML = "html"
    PYTHON = "python"
    YAML = "yaml"
    JAVA = "java"
    # Package management files
    PACKAGE_JAVASCRIPT = "package_javascript"
    PACKAGE_CSHARP = "package_csharp"
    PACKAGE_PYTHON = "package_python"
    PACKAGE_JAVA = "package_java"
    DEFAULT = "default"


class FileTypeDetector:
    """Detects file types and determines appropriate review prompts"""
    
    # File extension mappings
    EXTENSION_MAP = {
        '.cs': FileType.CSHARP,
        '.cshtml': FileType.RAZOR_VIEW,
        '.razor': FileType.RAZOR_VIEW,
        '.js': FileType.JAVASCRIPT,
        '.jsx': FileType.JAVASCRIPT,
        '.ts': FileType.TYPESCRIPT,
        '.tsx': FileType.TYPESCRIPT,
        '.sql': FileType.SQL,
        '.md': FileType.MARKDOWN,
        '.markdown': FileType.MARKDOWN,
        '.json': FileType.JSON,
        '.xml': FileType.XML,
        '.config': FileType.CONFIG,
        '.css': FileType.CSS,
        '.scss': FileType.CSS,
        '.less': FileType.CSS,
        '.html': FileType.HTML,
        '.htm': FileType.HTML,
        '.py': FileType.PYTHON,
        '.yml': FileType.YAML,
        '.yaml': FileType.YAML,
        '.java': FileType.JAVA,
        '.gradle': FileType.PACKAGE_JAVA,
        '.kts': FileType.PACKAGE_JAVA,  # Gradle Kotlin DSL
    }
    
    # Package management file names
    PACKAGE_FILES = {
        # JavaScript/Node.js
        'package.json': FileType.PACKAGE_JAVASCRIPT,
        'package-lock.json': FileType.PACKAGE_JAVASCRIPT,
        'yarn.lock': FileType.PACKAGE_JAVASCRIPT,
        'pnpm-lock.yaml': FileType.PACKAGE_JAVASCRIPT,
        'npm-shrinkwrap.json': FileType.PACKAGE_JAVASCRIPT,
        # C#/.NET
        'packages.config': FileType.PACKAGE_CSHARP,
        'Directory.Packages.props': FileType.PACKAGE_CSHARP,
        'Directory.Build.props': FileType.PACKAGE_CSHARP,
        'paket.dependencies': FileType.PACKAGE_CSHARP,
        'paket.lock': FileType.PACKAGE_CSHARP,
        # Python
        'requirements.txt': FileType.PACKAGE_PYTHON,
        'requirements-dev.txt': FileType.PACKAGE_PYTHON,
        'requirements-test.txt': FileType.PACKAGE_PYTHON,
        'setup.py': FileType.PACKAGE_PYTHON,
        'setup.cfg': FileType.PACKAGE_PYTHON,
        'pyproject.toml': FileType.PACKAGE_PYTHON,
        'Pipfile': FileType.PACKAGE_PYTHON,
        'Pipfile.lock': FileType.PACKAGE_PYTHON,
        'poetry.lock': FileType.PACKAGE_PYTHON,
        'environment.yml': FileType.PACKAGE_PYTHON,
        'environment.yaml': FileType.PACKAGE_PYTHON,
        'conda.yaml': FileType.PACKAGE_PYTHON,
        # Java
        'pom.xml': FileType.PACKAGE_JAVA,
        'build.gradle': FileType.PACKAGE_JAVA,
        'build.gradle.kts': FileType.PACKAGE_JAVA,
        'settings.gradle': FileType.PACKAGE_JAVA,
        'settings.gradle.kts': FileType.PACKAGE_JAVA,
        'gradle.properties': FileType.PACKAGE_JAVA,
        'ivy.xml': FileType.PACKAGE_JAVA,
        'build.xml': FileType.PACKAGE_JAVA,  # Ant
    }
    
    # Test file patterns
    TEST_PATTERNS = {
        'csharp': [
            r'.*\.Tests?\.cs$',
            r'.*Test\.cs$',
            r'.*Tests\.cs$',
            r'.*Spec\.cs$',
            r'.*\.Test\.',
            r'.*\.Tests\.',
            r'.*\.IntegrationTests?\.',
            r'.*\.UnitTests?\.'
        ],
        'javascript': [
            r'.*\.test\.js$',
            r'.*\.spec\.js$',
            r'.*\.test\.ts$',
            r'.*\.spec\.ts$',
            r'.*\.test\.jsx$',
            r'.*\.test\.tsx$',
            r'__tests__/.*\.(js|ts|jsx|tsx)$',
            r'.*\.e2e\.(js|ts)$'
        ]
    }
    
    @classmethod
    def detect_file_type(cls, file_path: str, content: Optional[str] = None) -> FileType:
        """
        Detect the type of a file based on its path and optionally its content
        
        Args:
            file_path: Path to the file
            content: Optional file content for deeper analysis
            
        Returns:
            FileType enum value
        """
        # Normalize path
        file_path = file_path.replace('\\', '/')
        file_name = os.path.basename(file_path).lower()
        
        # Check package management files first (highest priority)
        # Try exact match first
        if file_name in cls.PACKAGE_FILES:
            return cls.PACKAGE_FILES[file_name]
        
        # Try case-insensitive match for some files
        for pkg_file, pkg_type in cls.PACKAGE_FILES.items():
            if file_name.lower() == pkg_file.lower():
                return pkg_type
        
        # Check for .csproj files (C# package files)
        if file_name.endswith('.csproj') or file_name.endswith('.vbproj') or file_name.endswith('.fsproj'):
            return FileType.PACKAGE_CSHARP
        
        # Check if it's a test file
        if cls._is_test_file(file_path):
            if file_path.endswith('.cs'):
                return FileType.TEST_CSHARP
            elif any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
                return FileType.TEST_JAVASCRIPT
        
        # Check file extension
        _, ext = os.path.splitext(file_name)
        if ext in cls.EXTENSION_MAP:
            file_type = cls.EXTENSION_MAP[ext]
            
            # Special handling for Razor views with embedded JavaScript
            if file_type == FileType.RAZOR_VIEW and content:
                if cls._has_significant_javascript(content):
                    return FileType.RAZOR_VIEW  # Keep as Razor but we'll handle JS in the prompt
            
            # Special case for package.json that might be named differently
            if file_type == FileType.JSON and 'dependencies' in (content or ''):
                return FileType.PACKAGE_JAVASCRIPT
            
            return file_type
        
        # Check for specific file names
        if file_name in ['dockerfile', 'containerfile']:
            return FileType.CONFIG
        elif file_name in ['makefile', 'rakefile']:
            return FileType.CONFIG
        elif file_name.startswith('.') and not ext:  # Dotfiles like .gitignore, .env
            return FileType.CONFIG
        
        # Default fallback
        return FileType.DEFAULT
    
    @classmethod
    def _is_test_file(cls, file_path: str) -> bool:
        """Check if a file is a test file based on naming patterns"""
        # Check C# test patterns
        for pattern in cls.TEST_PATTERNS['csharp']:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        
        # Check JavaScript/TypeScript test patterns
        for pattern in cls.TEST_PATTERNS['javascript']:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def _has_significant_javascript(cls, content: str) -> bool:
        """Check if a Razor view has significant JavaScript content"""
        # Look for script tags
        script_pattern = r'<script[^>]*>.*?</script>'
        scripts = re.findall(script_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if scripts:
            # Calculate total JavaScript content length
            total_js_length = sum(len(script) for script in scripts)
            # If JS content is more than 20% of file or more than 500 chars, it's significant
            return total_js_length > 500 or total_js_length > len(content) * 0.2
        
        # Check for @section Scripts
        if '@section Scripts' in content or '@section scripts' in content:
            return True
        
        return False
    
    @classmethod
    def get_prompt_file_for_type(cls, file_type: FileType) -> str:
        """
        Get the appropriate prompt file name for a given file type
        
        Args:
            file_type: The detected file type
            
        Returns:
            Name of the prompt file to use
        """
        prompt_map = {
            FileType.CSHARP: "csharp_review_prompt.txt",
            FileType.RAZOR_VIEW: "razor_view_review_prompt.txt",
            FileType.JAVASCRIPT: "javascript_review_prompt.txt",
            FileType.TYPESCRIPT: "typescript_review_prompt.txt",
            FileType.SQL: "sql_review_prompt.txt",
            FileType.MARKDOWN: "markdown_review_prompt.txt",
            FileType.TEST_CSHARP: "test_csharp_review_prompt.txt",
            FileType.TEST_JAVASCRIPT: "test_javascript_review_prompt.txt",
            FileType.CONFIG: "config_review_prompt.txt",
            FileType.JSON: "json_review_prompt.txt",
            FileType.XML: "xml_review_prompt.txt",
            FileType.CSS: "css_review_prompt.txt",
            FileType.HTML: "html_review_prompt.txt",
            FileType.PYTHON: "python_review_prompt.txt",
            FileType.YAML: "yaml_review_prompt.txt",
            FileType.JAVA: "java_review_prompt.txt",
            # Package dependency files
            FileType.PACKAGE_JAVASCRIPT: "javascript_packages_review_prompt.txt",
            FileType.PACKAGE_CSHARP: "csharp_packages_review_prompt.txt",
            FileType.PACKAGE_PYTHON: "python_packages_review_prompt.txt",
            FileType.PACKAGE_JAVA: "java_packages_review_prompt.txt",
            FileType.DEFAULT: "default_review_prompt.txt"
        }
        
        return prompt_map.get(file_type, "default_review_prompt.txt")
    
    @classmethod
    def analyze_pr_files(cls, changes: List[Dict]) -> Dict[FileType, List[str]]:
        """
        Analyze all files in a PR and group them by type
        
        Args:
            changes: List of file changes from PR
            
        Returns:
            Dictionary mapping file types to lists of file paths
        """
        file_groups = {}
        
        for change in changes:
            file_path = change.get('path', '')
            content = change.get('new_content', '') or change.get('old_content', '')
            
            file_type = cls.detect_file_type(file_path, content)
            
            if file_type not in file_groups:
                file_groups[file_type] = []
            
            file_groups[file_type].append(file_path)
        
        return file_groups
    
    @classmethod
    def get_dominant_file_type(cls, changes: List[Dict]) -> FileType:
        """
        Determine the dominant file type in a PR for selecting primary review focus
        
        Args:
            changes: List of file changes from PR
            
        Returns:
            The most common or most important file type
        """
        file_groups = cls.analyze_pr_files(changes)
        
        if not file_groups:
            return FileType.DEFAULT
        
        # Priority order for determining dominant type
        priority = [
            FileType.CSHARP,
            FileType.RAZOR_VIEW,
            FileType.TYPESCRIPT,
            FileType.JAVASCRIPT,
            FileType.SQL,
            FileType.TEST_CSHARP,
            FileType.TEST_JAVASCRIPT
        ]
        
        # Check priority types first
        for file_type in priority:
            if file_type in file_groups and len(file_groups[file_type]) > 0:
                return file_type
        
        # Return the type with most files
        return max(file_groups.keys(), key=lambda k: len(file_groups[k]))
    
    @classmethod
    def should_use_mixed_review(cls, changes: List[Dict]) -> bool:
        """
        Determine if a PR has mixed file types requiring multiple review approaches
        
        Args:
            changes: List of file changes from PR
            
        Returns:
            True if PR contains multiple significant file types
        """
        file_groups = cls.analyze_pr_files(changes)
        
        # Count significant file types (excluding config, markdown, etc.)
        significant_types = [
            FileType.CSHARP, FileType.RAZOR_VIEW, FileType.JAVASCRIPT,
            FileType.TYPESCRIPT, FileType.SQL, FileType.TEST_CSHARP,
            FileType.TEST_JAVASCRIPT
        ]
        
        significant_count = sum(
            1 for ft in significant_types 
            if ft in file_groups and len(file_groups[ft]) > 0
        )
        
        return significant_count > 1