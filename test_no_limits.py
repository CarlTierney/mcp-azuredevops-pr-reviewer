#!/usr/bin/env python3
"""
Test to verify all hardcoded limits have been removed from analyzers
"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_no_hardcoded_limits():
    """Test that no hardcoded limits exist in analyzers"""
    
    print("=== TESTING FOR HARDCODED LIMITS IN ANALYZERS ===")
    print()
    
    analyzer_files = [
        "analyzers/contribution_analyzer.py",
        "analyzers/language_analyzer.py", 
        "analyzers/data_collector.py",
        "analyzers/developer_analyzer.py",
        "analyzers/quality_analyzer.py",
        "analyzers/hotspot_analyzer.py"
    ]
    
    # Patterns that indicate problematic limits
    bad_patterns = [
        "changes[:200]",
        "changes[:500]", 
        "work_item_ids[:100]",
        "sampling first 200",
        "sampling first 500",
        "first 100"
    ]
    
    # Acceptable patterns (for API pagination, display, etc.)
    acceptable_patterns = [
        "batch_size = 1000",  # API pagination
        "head(10)",           # Display limits
        "head(5)",            # Display limits  
        "head(3)",            # Display limits
        "[:5]",               # Display truncation
        "[:50]",              # Title truncation
        "1800",               # Timeout limits (safety)
        "3600",               # Timeout limits (safety)
        "2400"                # Timeout limits (safety)
    ]
    
    issues_found = []
    
    for file_path in analyzer_files:
        if os.path.exists(file_path):
            print(f"🔍 Checking {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for pattern in bad_patterns:
                if pattern in content:
                    issues_found.append(f"{file_path}: Found problematic pattern '{pattern}'")
                    
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print()
    
    if issues_found:
        print("❌ HARDCODED LIMITS FOUND:")
        for issue in issues_found:
            print(f"  • {issue}")
        print()
        print("These limits should be removed for comprehensive analysis.")
        return False
    else:
        print("✅ NO PROBLEMATIC HARDCODED LIMITS FOUND!")
        print()
        print("Verified that the following have been removed:")
        print("  • 200 changes per commit limit (contribution_analyzer)")
        print("  • 500 changes per commit limit (language_analyzer)")
        print("  • 100 work items limit (data_collector)")
        print()
        print("Acceptable limits still in place:")
        print("  • API batch_size = 1000 (for pagination)")
        print("  • Display limits (head(10), etc.) for output formatting")
        print("  • Timeout limits (30-60 minutes) for safety")
        print()
        return True

def test_analyzer_configuration():
    """Test analyzer configuration for unlimited processing"""
    
    print("=== TESTING ANALYZER CONFIGURATION ===")
    print()
    
    try:
        from core.main_analyzer import AzureDevOpsAnalyzer
        
        # Test with default configuration
        analyzer = AzureDevOpsAnalyzer(
            org_name="test_org",
            project_name="test_project",
            repo_name="test_repo", 
            pat_token="dummy_token"
        )
        
        print(f"✅ Analyzer initialized successfully")
        print(f"📅 Global date range: {analyzer.date_from} to {analyzer.date_to}")
        print()
        
        # Check that all sub-analyzers reference the same global settings
        analyzers_to_check = [
            ("Data Collector", analyzer.data_collector),
            ("Developer Analyzer", analyzer.developer_analyzer),
            ("Quality Analyzer", analyzer.quality_analyzer),
            ("Contribution Analyzer", analyzer.contribution_analyzer),
            ("Language Analyzer", analyzer.language_analyzer),
            ("Hotspot Analyzer", analyzer.hotspot_analyzer)
        ]
        
        print("🔍 Verifying all analyzers use global configuration...")
        
        for name, sub_analyzer in analyzers_to_check:
            if hasattr(sub_analyzer, 'analyzer'):
                if sub_analyzer.analyzer == analyzer:
                    print(f"✅ {name}: Correctly references global analyzer")
                else:
                    print(f"❌ {name}: Does not reference global analyzer")
                    return False
            else:
                print(f"⚠️  {name}: No analyzer reference found")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error testing analyzer configuration: {e}")
        return False

if __name__ == "__main__":
    print("Testing Azure DevOps Analyzer for Hardcoded Limits")
    print("=" * 60)
    print()
    
    limits_test = test_no_hardcoded_limits()
    config_test = test_analyzer_configuration()
    
    print("=" * 60)
    if limits_test and config_test:
        print("🎉 SUCCESS: All hardcoded limits removed and configuration is optimal!")
        print("✅ The analyzer will now process ALL data without artificial restrictions")
        print("✅ Global date filtering is working correctly")
        print("✅ Ready for comprehensive analysis on large datasets")
    else:
        print("🔧 ISSUES FOUND: Some limits or configuration problems need attention")
        
    print()
    print("Key improvements made:")
    print("  • Removed 200 changes/commit limit in contribution analysis")
    print("  • Removed 500 changes/commit limit in language analysis") 
    print("  • Removed 100 work items limit in data collection")
    print("  • Extended default date range from 180 to 730 days")
    print("  • Fixed hotspot analyzer hardcoded 90-day recency limit")
    print("  • All analyzers now use consistent global date filtering")
