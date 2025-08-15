"""Unit tests for file type detection"""

import unittest
from azure_pr_reviewer.file_type_detector import FileTypeDetector, FileType


class TestFileTypeDetector(unittest.TestCase):
    """Test suite for FileTypeDetector"""
    
    def test_detect_file_type_csharp(self):
        """Test detecting C# files"""
        # Note: "test.cs" is detected as TEST_CSHARP due to the test pattern
        self.assertEqual(FileTypeDetector.detect_file_type("MyClass.cs"), FileType.CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("/src/MyClass.cs"), FileType.CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("C:\\project\\file.cs"), FileType.CSHARP)
    
    def test_detect_file_type_razor(self):
        """Test detecting Razor view files"""
        self.assertEqual(FileTypeDetector.detect_file_type("Index.cshtml"), FileType.RAZOR_VIEW)
        self.assertEqual(FileTypeDetector.detect_file_type("Component.razor"), FileType.RAZOR_VIEW)
        self.assertEqual(FileTypeDetector.detect_file_type("/Views/Home/Index.cshtml"), FileType.RAZOR_VIEW)
    
    def test_detect_file_type_javascript(self):
        """Test detecting JavaScript files"""
        self.assertEqual(FileTypeDetector.detect_file_type("script.js"), FileType.JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("component.jsx"), FileType.JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("/src/app.js"), FileType.JAVASCRIPT)
    
    def test_detect_file_type_typescript(self):
        """Test detecting TypeScript files"""
        self.assertEqual(FileTypeDetector.detect_file_type("app.ts"), FileType.TYPESCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("component.tsx"), FileType.TYPESCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("/src/types.ts"), FileType.TYPESCRIPT)
    
    def test_detect_file_type_sql(self):
        """Test detecting SQL files"""
        self.assertEqual(FileTypeDetector.detect_file_type("query.sql"), FileType.SQL)
        self.assertEqual(FileTypeDetector.detect_file_type("/db/migrations/001_init.sql"), FileType.SQL)
    
    def test_detect_file_type_markdown(self):
        """Test detecting Markdown files"""
        self.assertEqual(FileTypeDetector.detect_file_type("README.md"), FileType.MARKDOWN)
        self.assertEqual(FileTypeDetector.detect_file_type("CHANGELOG.markdown"), FileType.MARKDOWN)
    
    def test_detect_file_type_python(self):
        """Test detecting Python files"""
        self.assertEqual(FileTypeDetector.detect_file_type("script.py"), FileType.PYTHON)
        self.assertEqual(FileTypeDetector.detect_file_type("/src/main.py"), FileType.PYTHON)
    
    def test_detect_file_type_java(self):
        """Test detecting Java files"""
        self.assertEqual(FileTypeDetector.detect_file_type("Main.java"), FileType.JAVA)
        self.assertEqual(FileTypeDetector.detect_file_type("/src/com/example/App.java"), FileType.JAVA)
    
    def test_detect_file_type_package_files(self):
        """Test detecting package management files"""
        # JavaScript packages
        self.assertEqual(FileTypeDetector.detect_file_type("package.json"), FileType.PACKAGE_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("package-lock.json"), FileType.PACKAGE_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("yarn.lock"), FileType.PACKAGE_JAVASCRIPT)
        
        # C# packages
        self.assertEqual(FileTypeDetector.detect_file_type("packages.config"), FileType.PACKAGE_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("MyProject.csproj"), FileType.PACKAGE_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("Directory.Packages.props"), FileType.PACKAGE_CSHARP)
        
        # Python packages
        self.assertEqual(FileTypeDetector.detect_file_type("requirements.txt"), FileType.PACKAGE_PYTHON)
        self.assertEqual(FileTypeDetector.detect_file_type("setup.py"), FileType.PACKAGE_PYTHON)
        self.assertEqual(FileTypeDetector.detect_file_type("pyproject.toml"), FileType.PACKAGE_PYTHON)
        self.assertEqual(FileTypeDetector.detect_file_type("Pipfile"), FileType.PACKAGE_PYTHON)
        
        # Java packages
        self.assertEqual(FileTypeDetector.detect_file_type("pom.xml"), FileType.PACKAGE_JAVA)
        self.assertEqual(FileTypeDetector.detect_file_type("build.gradle"), FileType.PACKAGE_JAVA)
        self.assertEqual(FileTypeDetector.detect_file_type("build.gradle.kts"), FileType.PACKAGE_JAVA)
    
    def test_detect_file_type_test_files(self):
        """Test detecting test files"""
        # C# test files
        self.assertEqual(FileTypeDetector.detect_file_type("MyTest.cs"), FileType.TEST_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("MyTests.cs"), FileType.TEST_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("MyClass.Test.cs"), FileType.TEST_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("MyClass.Tests.cs"), FileType.TEST_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("MySpec.cs"), FileType.TEST_CSHARP)
        self.assertEqual(FileTypeDetector.detect_file_type("test.cs"), FileType.TEST_CSHARP)  # "test.cs" is a test file
        
        # JavaScript test files
        self.assertEqual(FileTypeDetector.detect_file_type("app.test.js"), FileType.TEST_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("app.spec.js"), FileType.TEST_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("app.test.ts"), FileType.TEST_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("app.spec.ts"), FileType.TEST_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("__tests__/app.js"), FileType.TEST_JAVASCRIPT)
        self.assertEqual(FileTypeDetector.detect_file_type("app.e2e.js"), FileType.TEST_JAVASCRIPT)
    
    def test_detect_file_type_config_files(self):
        """Test detecting configuration files"""
        self.assertEqual(FileTypeDetector.detect_file_type("web.config"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type("app.config"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type("dockerfile"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type("Dockerfile"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type("makefile"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type("Makefile"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type(".gitignore"), FileType.CONFIG)
        self.assertEqual(FileTypeDetector.detect_file_type(".env"), FileType.CONFIG)
    
    def test_detect_file_type_web_files(self):
        """Test detecting web files"""
        self.assertEqual(FileTypeDetector.detect_file_type("index.html"), FileType.HTML)
        self.assertEqual(FileTypeDetector.detect_file_type("page.htm"), FileType.HTML)
        self.assertEqual(FileTypeDetector.detect_file_type("styles.css"), FileType.CSS)
        self.assertEqual(FileTypeDetector.detect_file_type("main.scss"), FileType.CSS)
        self.assertEqual(FileTypeDetector.detect_file_type("theme.less"), FileType.CSS)
    
    def test_detect_file_type_data_files(self):
        """Test detecting data files"""
        self.assertEqual(FileTypeDetector.detect_file_type("data.json"), FileType.JSON)
        self.assertEqual(FileTypeDetector.detect_file_type("config.xml"), FileType.XML)
        self.assertEqual(FileTypeDetector.detect_file_type("config.yml"), FileType.YAML)
        self.assertEqual(FileTypeDetector.detect_file_type("config.yaml"), FileType.YAML)
    
    def test_detect_file_type_with_content(self):
        """Test file type detection with content analysis"""
        # Razor view with significant JavaScript
        razor_content = """
        @model MyModel
        <script>
            function complexFunction() {
                // 600 characters of JavaScript
                """ + "x" * 600 + """
            }
        </script>
        """
        self.assertEqual(
            FileTypeDetector.detect_file_type("Index.cshtml", razor_content),
            FileType.RAZOR_VIEW
        )
        
        # JSON file that's actually a package.json
        package_content = '{"name": "my-app", "dependencies": {"react": "^17.0.0"}}'
        self.assertEqual(
            FileTypeDetector.detect_file_type("config.json", package_content),
            FileType.PACKAGE_JAVASCRIPT
        )
    
    def test_detect_file_type_default(self):
        """Test default file type for unknown extensions"""
        self.assertEqual(FileTypeDetector.detect_file_type("unknown.xyz"), FileType.DEFAULT)
        self.assertEqual(FileTypeDetector.detect_file_type("noextension"), FileType.DEFAULT)
    
    def test_is_test_file(self):
        """Test identifying test files"""
        # C# test files
        self.assertTrue(FileTypeDetector._is_test_file("MyTest.cs"))
        self.assertTrue(FileTypeDetector._is_test_file("MyTests.cs"))
        self.assertTrue(FileTypeDetector._is_test_file("Something.Test.cs"))
        self.assertTrue(FileTypeDetector._is_test_file("Project.UnitTests.dll"))  # Pattern matches .UnitTests.
        
        # JavaScript test files
        self.assertTrue(FileTypeDetector._is_test_file("app.test.js"))
        self.assertTrue(FileTypeDetector._is_test_file("app.spec.ts"))
        self.assertTrue(FileTypeDetector._is_test_file("__tests__/component.jsx"))
        
        # Non-test files
        self.assertFalse(FileTypeDetector._is_test_file("MyClass.cs"))
        self.assertFalse(FileTypeDetector._is_test_file("app.js"))
        # "TestHelper.cs" doesn't match the patterns (patterns look for suffix "Test.cs" not prefix)
        self.assertFalse(FileTypeDetector._is_test_file("TestHelper.cs"))
    
    def test_has_significant_javascript(self):
        """Test detecting significant JavaScript in Razor views"""
        # Significant JavaScript (> 500 chars)
        content1 = "<script>" + "x" * 600 + "</script>"
        self.assertTrue(FileTypeDetector._has_significant_javascript(content1))
        
        # Significant JavaScript (> 20% of content)
        content2 = "short" + "<script>" + "x" * 10 + "</script>"
        self.assertTrue(FileTypeDetector._has_significant_javascript(content2))
        
        # Has @section Scripts
        content3 = "@section Scripts { console.log('test'); }"
        self.assertTrue(FileTypeDetector._has_significant_javascript(content3))
        
        # Not significant JavaScript
        content4 = "lots of HTML content " * 100 + "<script>alert('hi');</script>"
        self.assertFalse(FileTypeDetector._has_significant_javascript(content4))
        
        # No JavaScript
        content5 = "<div>Just HTML</div>"
        self.assertFalse(FileTypeDetector._has_significant_javascript(content5))
    
    def test_get_prompt_file_for_type(self):
        """Test getting prompt file names for different file types"""
        self.assertEqual(
            FileTypeDetector.get_prompt_file_for_type(FileType.CSHARP),
            "csharp_review_prompt.txt"
        )
        self.assertEqual(
            FileTypeDetector.get_prompt_file_for_type(FileType.JAVASCRIPT),
            "javascript_review_prompt.txt"
        )
        self.assertEqual(
            FileTypeDetector.get_prompt_file_for_type(FileType.PACKAGE_PYTHON),
            "python_packages_review_prompt.txt"
        )
        self.assertEqual(
            FileTypeDetector.get_prompt_file_for_type(FileType.DEFAULT),
            "default_review_prompt.txt"
        )
    
    def test_analyze_pr_files(self):
        """Test analyzing PR files and grouping by type"""
        changes = [
            {"path": "/src/main.cs", "new_content": "class Main {}"},
            {"path": "/src/app.js", "new_content": "console.log();"},
            {"path": "/src/test.cs", "new_content": "class Test {}"},  # This will be TEST_CSHARP
            {"path": "/db/query.sql", "new_content": "SELECT * FROM users;"},
            {"path": "package.json", "new_content": '{"dependencies": {}}'}
        ]
        
        result = FileTypeDetector.analyze_pr_files(changes)
        
        self.assertIn(FileType.CSHARP, result)
        self.assertIn(FileType.JAVASCRIPT, result)
        self.assertIn(FileType.SQL, result)
        self.assertIn(FileType.PACKAGE_JAVASCRIPT, result)
        self.assertIn(FileType.TEST_CSHARP, result)  # test.cs is detected as test file
        
        self.assertEqual(len(result[FileType.CSHARP]), 1)  # Only main.cs
        self.assertEqual(len(result[FileType.TEST_CSHARP]), 1)  # test.cs
        self.assertEqual(len(result[FileType.JAVASCRIPT]), 1)
        self.assertEqual(len(result[FileType.SQL]), 1)
        self.assertEqual(len(result[FileType.PACKAGE_JAVASCRIPT]), 1)
    
    def test_get_dominant_file_type(self):
        """Test determining dominant file type in PR"""
        # C# dominant (priority)
        changes1 = [
            {"path": "/src/main.cs"},
            {"path": "/src/app.js"},
            {"path": "README.md"}
        ]
        self.assertEqual(FileTypeDetector.get_dominant_file_type(changes1), FileType.CSHARP)
        
        # JavaScript dominant (no C#)
        changes2 = [
            {"path": "/src/app.js"},
            {"path": "/src/component.js"},
            {"path": "README.md"}
        ]
        self.assertEqual(FileTypeDetector.get_dominant_file_type(changes2), FileType.JAVASCRIPT)
        
        # Most files wins when no priority types
        changes3 = [
            {"path": "file1.json"},
            {"path": "file2.json"},
            {"path": "file3.json"},
            {"path": "README.md"}
        ]
        self.assertEqual(FileTypeDetector.get_dominant_file_type(changes3), FileType.JSON)
        
        # Empty changes
        self.assertEqual(FileTypeDetector.get_dominant_file_type([]), FileType.DEFAULT)
    
    def test_should_use_mixed_review(self):
        """Test determining if PR needs mixed review approach"""
        # Single significant type - no mixed review
        changes1 = [
            {"path": "/src/file1.cs"},
            {"path": "/src/file2.cs"},
            {"path": "README.md"}
        ]
        self.assertFalse(FileTypeDetector.should_use_mixed_review(changes1))
        
        # Multiple significant types - use mixed review
        changes2 = [
            {"path": "/src/file.cs"},
            {"path": "/src/app.js"},
            {"path": "/db/query.sql"}
        ]
        self.assertTrue(FileTypeDetector.should_use_mixed_review(changes2))
        
        # Non-significant types don't trigger mixed review
        changes3 = [
            {"path": "/src/file.cs"},
            {"path": "README.md"},
            {"path": "config.json"}
        ]
        self.assertFalse(FileTypeDetector.should_use_mixed_review(changes3))
        
        # Test files count as significant
        changes4 = [
            {"path": "/src/MyTest.cs"},
            {"path": "/src/app.test.js"}
        ]
        self.assertTrue(FileTypeDetector.should_use_mixed_review(changes4))


if __name__ == '__main__':
    unittest.main()