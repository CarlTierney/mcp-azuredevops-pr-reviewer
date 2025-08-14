#!/usr/bin/env python3
"""
Test script to analyze PR 1364
"""

import os
import sys
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

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
        print("❌ Error: Missing Azure DevOps configuration!")
        print("Please ensure your .env file contains:")
        print("  AZDO_ORG=your_organization")
        print("  AZDO_PROJECT=your_project")
        print("  AZDO_REPO=your_repository")
        print("  AZDO_PAT=your_pat_token")
        return False
    
    print("\n" + "="*70)
    print("TESTING PR ANALYSIS FOR PR #1364")
    print("="*70)
    print(f"Organization: {org_name}")
    print(f"Project: {project_name}")
    print(f"Repository: {repo_name}")
    print("="*70)
    
    try:
        # Initialize analyzer
        print("\n[INIT] Initializing Azure DevOps Analyzer...")
        analyzer = AzureDevOpsAnalyzer(
            org_name=org_name,
            project_name=project_name,
            repo_name=repo_name,
            pat_token=pat_token,
            data_dir="./azdo_analytics"
        )
        
        # Fetch PR details
        print("\n[FETCH] Fetching PR #1364...")
        pr_data = analyzer.fetch_pull_request(1364)
        
        if not pr_data:
            print("❌ Failed to fetch PR #1364")
            print("This could mean:")
            print("  1. PR doesn't exist")
            print("  2. No access permissions")
            print("  3. Wrong repository")
            return False
        
        # Display basic info
        print("\n[INFO] PR #1364 Basic Information:")
        print(f"  Title: {pr_data.get('title', 'N/A')}")
        print(f"  Description: {pr_data.get('description', 'N/A')[:200]}...")
        print(f"  Author: {pr_data.get('createdBy', {}).get('displayName', 'Unknown')}")
        print(f"  Status: {pr_data.get('status', 'Unknown')}")
        print(f"  Created: {pr_data.get('creationDate', 'Unknown')}")
        print(f"  Source Branch: {pr_data.get('sourceRefName', '').replace('refs/heads/', '')}")
        print(f"  Target Branch: {pr_data.get('targetRefName', '').replace('refs/heads/', '')}")
        
        # Reviewers
        reviewers = pr_data.get('reviewers', [])
        print(f"\n[REVIEWERS] {len(reviewers)} reviewer(s):")
        for reviewer in reviewers:
            vote = reviewer.get('vote', 0)
            vote_symbol = '✅ Approved' if vote > 0 else '❌ Rejected' if vote < 0 else '⏳ Pending'
            print(f"  - {reviewer.get('displayName', 'Unknown')}: {vote_symbol}")
            if reviewer.get('isRequired', False):
                print(f"    (Required reviewer)")
        
        # Perform detailed analysis
        print("\n[ANALYZE] Performing detailed analysis of PR #1364...")
        analysis = analyzer.analyze_pull_request(1364)
        
        if 'error' in analysis:
            print(f"❌ Analysis failed: {analysis['error']}")
            return False
        
        # Display analysis results
        print("\n[RESULTS] Analysis Summary:")
        
        # Code changes
        changes = analysis.get('code_changes', {})
        print(f"\n📝 Code Changes:")
        print(f"  Files changed: {changes.get('files_changed', 0)}")
        print(f"  Additions: +{changes.get('total_additions', 0)}")
        print(f"  Deletions: -{changes.get('total_deletions', 0)}")
        print(f"  Change size: {changes.get('change_size_category', 'unknown')}")
        
        # Review quality
        quality = analysis.get('review_quality', {})
        print(f"\n👥 Review Quality:")
        print(f"  Review Depth Score: {quality.get('review_depth_score', 0)}/100")
        print(f"  Comments: {quality.get('comment_count', 0)}")
        print(f"  Threads: {quality.get('thread_count', 0)}")
        print(f"  Active discussions: {quality.get('active_threads', 0)}")
        
        # Collaboration
        collab = analysis.get('collaboration', {})
        print(f"\n🤝 Collaboration:")
        print(f"  Collaboration Score: {collab.get('collaboration_score', 0)}/100")
        print(f"  Unique participants: {collab.get('unique_participants', 0)}")
        
        # Risks
        risks = analysis.get('risks', [])
        if risks:
            print(f"\n⚠️ Identified Risks:")
            for risk in risks:
                severity_color = '🔴' if risk['severity'] == 'high' else '🟡' if risk['severity'] == 'medium' else '🟢'
                print(f"  {severity_color} [{risk['severity'].upper()}] {risk['description']}")
                print(f"     → Recommendation: {risk['recommendation']}")
        else:
            print(f"\n✅ No significant risks identified")
        
        # Recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        # Timeline
        timeline = analysis.get('timeline', {})
        if timeline.get('total_duration_days') is not None:
            print(f"\n⏱️ Timeline:")
            print(f"  Total duration: {timeline['total_duration_days']} days")
            if timeline.get('time_to_first_review_hours'):
                print(f"  Time to first review: {timeline['time_to_first_review_hours']:.1f} hours")
        
        # Check for specific issues mentioned in the PR
        print(f"\n🔍 Specific PR #1364 Analysis:")
        
        # Check if it's a hotfix without tests (as mentioned in description)
        description = pr_data.get('description', '').lower()
        if 'hotfix' in description:
            print("  ⚠️ This is marked as a HOTFIX")
        if 'doesn\'t have integration tests' in description or 'no integration tests' in description:
            print("  ⚠️ PR explicitly states: No Integration Tests")
        if 'unable to delete invite' in pr_data.get('title', '').lower():
            print("  🎯 Purpose: Fix for invite deletion functionality")
        
        # Work items
        work_items = analysis.get('statistics', {}).get('work_items', [])
        if work_items:
            print(f"\n📋 Linked Work Items:")
            for item in work_items:
                print(f"  - #{item.get('id', 'N/A')}: {item.get('title', 'N/A')}")
        
        # Save results
        output_file = "./azdo_analytics/pr_1364_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': str(os.popen('date /t').read().strip() if sys.platform == 'win32' else os.popen('date').read().strip()),
                'pr_data': pr_data,
                'analysis': analysis
            }, f, indent=2, default=str)
        
        print(f"\n[SAVED] Complete results saved to: {output_file}")
        
        # Final verdict
        print("\n" + "="*70)
        print("PR #1364 REVIEW SUMMARY")
        print("="*70)
        
        # Decision logic
        has_risks = len(risks) > 0
        is_hotfix = 'hotfix' in description
        no_tests = 'doesn\'t have integration tests' in description or not any('test' in str(f).lower() for f in changes.get('most_changed_files', []))
        low_review_score = quality.get('review_depth_score', 0) < 50
        
        if has_risks and no_tests:
            print("🔴 RECOMMENDATION: Request Changes")
            print("   - Missing tests for a hotfix is risky")
            print("   - Consider adding at least basic test coverage")
        elif low_review_score:
            print("🟡 RECOMMENDATION: Needs More Review")
            print("   - Low review participation detected")
            print("   - Request additional reviewers for thoroughness")
        else:
            print("🟢 RECOMMENDATION: Approve with Comments")
            print("   - PR appears ready for merge")
            print("   - Consider addressing any recommendations above")
        
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pr_analysis()
    sys.exit(0 if success else 1)