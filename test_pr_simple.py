#!/usr/bin/env python3
"""
Test script to analyze PR 1364 - Simple version without emojis
"""

import os
import sys
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded configuration from .env file")
except ImportError:
    pass

from analyzer import AzureDevOpsAnalyzer

def test_pr_analysis():
    """Test PR analysis for PR 1364"""
    
    # Configuration
    org_name = os.getenv('AZDO_ORG', '')
    project_name = os.getenv('AZDO_PROJECT', '')
    repo_name = os.getenv('AZDO_REPO', '')
    pat_token = os.getenv('AZDO_PAT', '')
    
    if not all([org_name, project_name, repo_name, pat_token]):
        print("[ERROR] Missing Azure DevOps configuration!")
        return False
    
    print("\n" + "="*70)
    print("ANALYZING PR #1364")
    print("="*70)
    
    try:
        # Initialize analyzer
        analyzer = AzureDevOpsAnalyzer(
            org_name=org_name,
            project_name=project_name,
            repo_name=repo_name,
            pat_token=pat_token,
            data_dir="./azdo_analytics"
        )
        
        # Analyze PR
        print("\n[ANALYZING] PR #1364...")
        analysis = analyzer.analyze_pull_request(1364)
        
        if 'error' in analysis:
            print(f"[ERROR] Analysis failed: {analysis['error']}")
            return False
        
        # Display results
        print("\n" + "="*70)
        print("PR #1364 ANALYSIS RESULTS")
        print("="*70)
        
        # Basic info
        info = analysis.get('basic_info', {})
        print(f"\nTitle: {info.get('title', 'N/A')}")
        print(f"Author: {info.get('author', 'Unknown')}")
        print(f"Status: {info.get('status', 'Unknown')}")
        print(f"Branch: {info.get('source_branch', '')} -> {info.get('target_branch', '')}")
        
        # Description
        print(f"\nDescription:")
        print(info.get('description', 'No description'))
        
        # Code changes
        changes = analysis.get('code_changes', {})
        print(f"\nCode Changes:")
        print(f"  Files changed: {changes.get('files_changed', 0)}")
        print(f"  Total changes: {changes.get('total_changes', 0)} lines")
        print(f"  Change size: {changes.get('change_size_category', 'unknown')}")
        
        # Review metrics
        quality = analysis.get('review_quality', {})
        print(f"\nReview Metrics:")
        print(f"  Reviewers: {quality.get('reviewer_count', 0)}")
        print(f"  Approvals: {quality.get('approvals', 0)}")
        print(f"  Rejections: {quality.get('rejections', 0)}")
        print(f"  Comments: {quality.get('comment_count', 0)}")
        print(f"  Review Score: {quality.get('review_depth_score', 0)}/100")
        
        # Risks
        risks = analysis.get('risks', [])
        if risks:
            print(f"\nIdentified Risks ({len(risks)}):")
            for risk in risks:
                print(f"  [{risk['severity'].upper()}] {risk['description']}")
                print(f"    Recommendation: {risk['recommendation']}")
        
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\nRecommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Statistics
        stats = analysis.get('statistics', {})
        print(f"\nStatistics:")
        print(f"  Duration: {stats.get('duration_days', 'N/A')} days")
        print(f"  Files changed: {stats.get('files_changed', 0)}")
        print(f"  Work items: {len(stats.get('work_items', []))}")
        
        # PR-specific issues
        print(f"\nPR-Specific Analysis:")
        description_lower = info.get('description', '').lower()
        title_lower = info.get('title', '').lower()
        
        if 'hotfix' in description_lower:
            print("  - This is a HOTFIX")
        if 'doesn\'t have integration tests' in description_lower:
            print("  - WARNING: No integration tests included")
        if 'unable to delete invite' in title_lower:
            print("  - Purpose: Fix invite deletion functionality")
        if '20780' in description_lower:
            print("  - Linked to work item #20780")
        
        # Final review decision
        print("\n" + "="*70)
        print("REVIEW DECISION")
        print("="*70)
        
        has_high_risks = any(r['severity'] == 'high' for r in risks)
        no_tests = 'doesn\'t have integration tests' in description_lower
        low_review = quality.get('review_depth_score', 0) < 30
        
        if has_high_risks and no_tests:
            print("\nDECISION: REQUEST CHANGES")
            print("Reason: High-risk hotfix without tests")
            print("Action: Add test coverage before approval")
        elif low_review:
            print("\nDECISION: NEEDS MORE REVIEW")
            print("Reason: Insufficient review participation")
            print("Action: Request additional reviewers")
        else:
            print("\nDECISION: APPROVE WITH COMMENTS")
            print("Reason: Acceptable risk level")
            print("Action: Consider recommendations above")
        
        # Save results
        output_file = "./azdo_analytics/pr_1364_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n[SAVED] Full analysis saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pr_analysis()
    sys.exit(0 if success else 1)