# Azure DevOps Analytics Unit Tests

This directory contains comprehensive unit tests for the Azure DevOps Analytics system.

## Test Structure

- `test_base_analyzer.py` - Tests for the base analyzer functionality
- `test_language_analyzer.py` - Tests for language complexity analysis
- `test_developer_analyzer.py` - Tests for developer activity analysis  
- `test_contribution_analyzer.py` - Tests for contribution metrics analysis
- `test_data_collector.py` - Tests for data collection from Azure DevOps APIs
- `run_tests.py` - Test runner script

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test Module
```bash
python tests/run_tests.py test_base_analyzer
python tests/run_tests.py test_language_analyzer
python tests/run_tests.py test_developer_analyzer
python tests/run_tests.py test_contribution_analyzer
python tests/run_tests.py test_data_collector
```

### Run Individual Test Classes
```bash
python -m unittest tests.test_base_analyzer.TestBaseAnalyzer
python -m unittest tests.test_language_analyzer.TestLanguageAnalyzer.test_cached_analysis
```

## Test Coverage

The tests cover:

- **Initialization and Configuration** - Proper setup of analyzers
- **Data Processing** - File classification, content analysis, complexity calculation
- **Caching** - Cache validation, loading, and saving
- **API Integration** - Mocked Azure DevOps API calls
- **Error Handling** - Malformed data, timeouts, API failures
- **Edge Cases** - Empty data, large datasets, invalid inputs

## Mock Strategy

Tests use `unittest.mock` to:
- Mock Azure DevOps API responses
- Simulate file content and analysis results
- Control timing and timeout scenarios
- Test caching behavior without actual file I/O

## Test Data

Tests use realistic but minimal test data to verify:
- Commit parsing and author extraction
- File type classification
- Complexity calculation
- Timing analysis
- Contribution scoring

## Dependencies

Tests require:
- `unittest` (built-in)
- `pandas`
- `numpy` 
- `requests` (for mocking)

No external API calls are made during testing.
