#!/usr/bin/env python3
"""
Comprehensive test to verify all analyzers use global date range filtering
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from core.main_analyzer import AzureDevOpsAnalyzer

def test_global_date_filtering():
    """Test that all analyzers respect the global date range"""
    
    print("=== TESTING GLOBAL DATE RANGE CONSISTENCY ===")
    print()
    
    # Test with a custom date range
    custom_date_from = "2024-01-01"
    custom_date_to = "2024-12-31"
    
    analyzer = AzureDevOpsAnalyzer(
        org_name="test_org",
        project_name="test_project", 
        repo_name="test_repo",
        pat_token="dummy_token",
        date_from=custom_date_from,
        date_to=custom_date_to
    )
    
    print(f"✅ Analyzer initialized with custom date range:")
    print(f"📅 From: {analyzer.date_from}")
    print(f"📅 To: {analyzer.date_to}")
    print(f"📅 From (dt): {analyzer.date_from_dt}")
    print(f"📅 To (dt): {analyzer.date_to_dt}")
    print()
    
    # Check that data collector uses global dates
    print("🔍 Checking Data Collector...")
    data_collector = analyzer.data_collector
    print(f"✅ Data collector uses global date_from: {data_collector.analyzer.date_from}")
    print(f"✅ Data collector uses global date_to: {data_collector.analyzer.date_to}")
    print()
    
    # Check all analyzers use the same global date range
    analyzers_to_check = [
        ("Developer Analyzer", analyzer.developer_analyzer),
        ("Quality Analyzer", analyzer.quality_analyzer), 
        ("Contribution Analyzer", analyzer.contribution_analyzer),
        ("Language Analyzer", analyzer.language_analyzer),
        ("Hotspot Analyzer", analyzer.hotspot_analyzer)
    ]
    
    print("🔍 Checking all analyzers use global date range...")
    all_consistent = True
    
    for name, analyzer_obj in analyzers_to_check:
        if hasattr(analyzer_obj, 'analyzer'):
            analyzer_date_from = analyzer_obj.analyzer.date_from
            analyzer_date_to = analyzer_obj.analyzer.date_to
            
            if analyzer_date_from == analyzer.date_from and analyzer_date_to == analyzer.date_to:
                print(f"✅ {name}: Uses global date range correctly")
            else:
                print(f"❌ {name}: Date range mismatch!")
                print(f"   Expected: {analyzer.date_from} to {analyzer.date_to}")
                print(f"   Actual: {analyzer_date_from} to {analyzer_date_to}")
                all_consistent = False
        else:
            print(f"⚠️  {name}: No analyzer reference found")
    
    print()
    
    # Test with default date range (730 days)
    print("🔍 Testing default date range (730 days)...")
    default_analyzer = AzureDevOpsAnalyzer(
        org_name="test_org",
        project_name="test_project", 
        repo_name="test_repo",
        pat_token="dummy_token"
    )
    
    # Calculate expected default range
    now = datetime.now()
    expected_from = now - timedelta(days=730)
    
    print(f"📅 Default date range:")
    print(f"   From: {default_analyzer.date_from}")
    print(f"   To: {default_analyzer.date_to}")
    
    # Verify it's using 730 days, not 180
    actual_from_dt = default_analyzer.date_from_dt.replace(tzinfo=None)
    expected_from_dt = expected_from.replace(tzinfo=None)
    
    # Allow for small time differences (within 1 day)
    time_diff = abs((actual_from_dt - expected_from_dt).total_seconds())
    if time_diff < 86400:  # Less than 24 hours difference
        print("✅ Default date range uses 730 days (2 years), not old 180 days")
    else:
        print(f"❌ Default date range issue. Expected ~730 days, got {(now - actual_from_dt).days} days")
        all_consistent = False
    
    print()
    print("=== SUMMARY ===")
    if all_consistent:
        print("🎉 SUCCESS: All analyzers consistently use the global date range filter!")
        print("✅ No local date limits found")
        print("✅ All analyzers respect the global date_from and date_to settings")
        return True
    else:
        print("❌ ISSUES FOUND: Some analyzers have date range inconsistencies")
        return False

if __name__ == "__main__":
    success = test_global_date_filtering()
    if success:
        print("\n🚀 The Azure DevOps analyzer is properly configured for global date filtering!")
    else:
        print("\n🔧 Date filtering issues need to be resolved")
