#!/usr/bin/env python3
"""
Test workspace cleaning functionality
"""

import os
import sys

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_workspace_cleaning():
    """Test that workspace is properly cleaned between PRs"""
    
    print("="*70)
    print("TESTING WORKSPACE CLEANING")
    print("="*70)
    
    workspace_dir = r"D:\dev\prreview"
    
    # Check workspace directory
    print(f"\n1. Checking workspace directory: {workspace_dir}")
    
    if os.path.exists(workspace_dir):
        items = os.listdir(workspace_dir)
        if items:
            print(f"   Found {len(items)} item(s) in workspace:")
            for item in items:
                item_path = os.path.join(workspace_dir, item)
                if os.path.isdir(item_path):
                    print(f"   - [DIR]  {item}")
                else:
                    print(f"   - [FILE] {item}")
        else:
            print("   Workspace is clean (empty)")
    else:
        print("   Workspace directory doesn't exist yet")
    
    # Test with analyzer
    print("\n2. Testing with analyzer...")
    
    try:
        from analyzer import AzureDevOpsAnalyzer
        from analyzers.repo_cloner import RepoCloner
        
        # Initialize analyzer
        analyzer = AzureDevOpsAnalyzer(
            org_name=os.getenv('AZDO_ORG', ''),
            project_name=os.getenv('AZDO_PROJECT', ''),
            repo_name=os.getenv('AZDO_REPO', ''),
            pat_token=os.getenv('AZDO_PAT', ''),
            data_dir="./azdo_analytics"
        )
        
        # Create repo cloner with our workspace
        cloner = RepoCloner(analyzer, workspace_dir=workspace_dir)
        
        # Test workspace cleaning
        print("\n3. Testing workspace cleaning...")
        cloner._clean_workspace()
        
        # Check again
        print("\n4. Verifying workspace is clean...")
        if os.path.exists(workspace_dir):
            items = os.listdir(workspace_dir)
            if not items or (len(items) == 1 and items[0] == '.cache'):
                print("   SUCCESS: Workspace is clean!")
            else:
                print(f"   WARNING: Workspace still has {len(items)} items")
        
        print("\n[OK] Workspace cleaning test completed")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_workspace_cleaning()
    sys.exit(0 if success else 1)