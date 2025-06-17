"""
Test runner for Azure DevOps Analytics unit tests
"""

import unittest
import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def run_all_tests():
    """Run all unit tests"""
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_module):
    """Run tests for a specific module"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_module)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1

def run_specific_module_tests():
    """Run tests for specific modules with detailed output"""
    test_modules = [
        'test_base_analyzer',
        'test_data_collector', 
        'test_developer_analyzer',
        'test_contribution_analyzer',
        'test_language_analyzer',
        'test_hotspot_analyzer',
        'test_quality_analyzer',
        'test_main_analyzer'
    ]
    
    print("Available test modules:")
    for i, module in enumerate(test_modules, 1):
        print(f"  {i}. {module}")
    
    try:
        choice = input("\nEnter module number (or 'all' for all tests): ").strip()
        
        if choice.lower() == 'all':
            return run_all_tests()
        
        module_index = int(choice) - 1
        if 0 <= module_index < len(test_modules):
            return run_specific_test(test_modules[module_index])
        else:
            print("Invalid choice")
            return 1
            
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled")
        return 1

def run_coverage_report():
    """Run tests with coverage reporting if available"""
    try:
        import coverage
        
        # Start coverage
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests
        result = run_all_tests()
        
        # Stop and report coverage
        cov.stop()
        cov.save()
        
        print("\n" + "="*60)
        print("COVERAGE REPORT")
        print("="*60)
        cov.report()
        
        return result
        
    except ImportError:
        print("Coverage package not available. Install with: pip install coverage")
        return run_all_tests()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '--coverage':
            exit_code = run_coverage_report()
        elif arg == '--interactive':
            exit_code = run_specific_module_tests()
        else:
            # Run specific test module
            exit_code = run_specific_test(arg)
    else:
        # Run all tests
        print("Running all Azure DevOps Analytics unit tests...")
        print("Use --interactive for module selection or --coverage for coverage report")
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
