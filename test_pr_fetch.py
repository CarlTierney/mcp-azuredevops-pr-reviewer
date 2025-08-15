#!/usr/bin/env python
"""Test script to verify PR content fetching is working"""

import asyncio
import json
from azure_pr_reviewer.config import Settings
from azure_pr_reviewer.azure_client import AzureDevOpsClient
from azure_pr_reviewer.code_reviewer import CodeReviewer

async def test_pr_fetch():
    """Test fetching PR 1364 with full content"""
    print("Initializing Azure client...")
    settings = Settings()
    client = AzureDevOpsClient(settings)
    reviewer = CodeReviewer(settings)
    
    print(f"Fetching PR #1364 from Zinnia repository...")
    
    # Get PR details
    pr = await client.get_pull_request(
        "itdept0907", "Fidem", "Zinnia", 1364
    )
    print(f"[OK] PR Title: {pr.title}")
    print(f"[OK] Created by: {pr.created_by.display_name}")
    
    # Get PR changes with content
    print("\nFetching file changes...")
    changes = await client.get_pull_request_changes(
        "itdept0907", "Fidem", "Zinnia", 1364
    )
    
    print(f"[OK] Found {len(changes)} file(s) changed")
    
    for change in changes:
        print(f"\nFile: {change['path']}")
        print(f"   Type: {change['change_type']}")
        print(f"   Has old content: {'YES' if change.get('old_content') else 'NO'}")
        print(f"   Has new content: {'YES' if change.get('new_content') else 'NO'}")
        
        if change.get('old_content'):
            print(f"   Old content size: {len(change['old_content'])} bytes")
        if change.get('new_content'):
            print(f"   New content size: {len(change['new_content'])} bytes")
            
        # Show a snippet of the diff if available
        if change.get('old_content') and change.get('new_content'):
            old_lines = change['old_content'].splitlines()
            new_lines = change['new_content'].splitlines()
            print(f"   Lines changed: {len(old_lines)} -> {len(new_lines)}")
            
            # Try to show a small diff preview
            print("\n   Sample of changes (first difference found):")
            for i, (old, new) in enumerate(zip(old_lines[:100], new_lines[:100])):
                if old != new:
                    print(f"   Line {i+1}:")
                    print(f"   - {old[:80]}")
                    if len(old) > 80:
                        print("...")
                    print(f"   + {new[:80]}")
                    if len(new) > 80:
                        print("...")
                    break
    
    # Test the review data preparation
    print("\n\nPreparing review data...")
    review_data = reviewer.prepare_review_data(pr, changes)
    print(f"[OK] Review data prepared")
    print(f"[OK] File types detected: {list(review_data.file_type_summary.keys())}")
    
    # Check if content is in the review prompt
    if "```diff" in review_data.review_prompt or "```" in review_data.review_prompt:
        print("[OK] Code content included in review prompt")
    else:
        print("[FAIL] No code content found in review prompt")
    
    return review_data

if __name__ == "__main__":
    print("=" * 60)
    print("PR Content Fetch Test")
    print("=" * 60)
    
    try:
        review_data = asyncio.run(test_pr_fetch())
        print("\n" + "=" * 60)
        print("[SUCCESS] Test completed successfully!")
        
        # Save the review data for inspection
        with open("test_pr_1364_data.json", "w") as f:
            # Convert to JSON-serializable format
            json_data = {
                "pr_details": review_data.pr_details,
                "file_count": len(review_data.changes),
                "has_content": any(c.get("new_content") or c.get("old_content") for c in review_data.changes),
                "file_types": review_data.file_type_summary,
                "prompt_length": len(review_data.review_prompt)
            }
            json.dump(json_data, f, indent=2)
            print(f"[OK] Review data saved to test_pr_1364_data.json")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()