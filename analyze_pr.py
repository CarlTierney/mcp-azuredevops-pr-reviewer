#!/usr/bin/env python3
"""
Pull Request Analyzer CLI
Analyze specific pull requests or PR patterns from Azure DevOps
"""

import os
import sys
import argparse
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[INFO] Loaded configuration from .env file")
except ImportError:
    pass

from analyzer import AzureDevOpsAnalyzer
from analyzers.pr_review_analyzer import PRReviewAnalyzer
from analyzers.pr_fetcher import PRFetcher


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Analyze Azure DevOps Pull Requests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single PR
  python analyze_pr.py --pr 1364
  
  # Analyze multiple PRs
  python analyze_pr.py --pr 1364 1365 1366
  
  # Analyze recent PR patterns
  python analyze_pr.py --patterns --days 30
  
  # Fetch PR details without analysis
  python analyze_pr.py --fetch 1364
  
  # List recent PRs
  python analyze_pr.py --list --status active --top 10
  
  # Analyze PRs by author
  python analyze_pr.py --list --author "John Doe" --analyze
        """
    )
    
    # PR selection arguments
    parser.add_argument('--pr', nargs='+', type=int, 
                       help='PR number(s) to analyze')
    parser.add_argument('--fetch', type=int,
                       help='Fetch PR details without analysis')
    parser.add_argument('--list', action='store_true',
                       help='List PRs based on filters')
    
    # Filter arguments
    parser.add_argument('--status', choices=['all', 'active', 'completed', 'abandoned'],
                       default='all', help='PR status filter')
    parser.add_argument('--author', type=str,
                       help='Filter by PR author')
    parser.add_argument('--source-branch', type=str,
                       help='Filter by source branch')
    parser.add_argument('--target-branch', type=str,
                       help='Filter by target branch')
    parser.add_argument('--top', type=int, default=20,
                       help='Number of PRs to retrieve (default: 20)')
    
    # Analysis options
    parser.add_argument('--patterns', action='store_true',
                       help='Analyze patterns across recent PRs')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days for pattern analysis (default: 30)')
    parser.add_argument('--analyze', action='store_true',
                       help='Analyze listed PRs')
    
    # Configuration overrides
    parser.add_argument('--org', type=str,
                       help='Azure DevOps organization')
    parser.add_argument('--project', type=str,
                       help='Azure DevOps project')
    parser.add_argument('--repo', type=str,
                       help='Repository name')
    parser.add_argument('--pat', type=str,
                       help='Personal Access Token')
    
    # Output options
    parser.add_argument('--output-dir', type=str, default='./azdo_analytics',
                       help='Output directory for results')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output')
    
    return parser.parse_args()


def get_configuration(args):
    """Get configuration from environment or arguments"""
    config = {
        'org_name': args.org or os.getenv('AZDO_ORG', ''),
        'project_name': args.project or os.getenv('AZDO_PROJECT', ''),
        'repo_name': args.repo or os.getenv('AZDO_REPO', ''),
        'pat_token': args.pat or os.getenv('AZDO_PAT', ''),
        'data_dir': args.output_dir
    }
    
    # Validate required parameters
    missing = [k for k, v in config.items() if not v and k != 'data_dir']
    if missing:
        print("❌ Error: Missing required configuration!")
        print(f"   Missing: {', '.join(missing)}")
        print("\nSet these via environment variables or command line arguments:")
        print("  Environment: AZDO_ORG, AZDO_PROJECT, AZDO_REPO, AZDO_PAT")
        print("  Arguments: --org, --project, --repo, --pat")
        sys.exit(1)
    
    return config


def list_pull_requests(analyzer, args):
    """List pull requests based on filters"""
    pr_fetcher = PRFetcher(analyzer)
    
    print(f"\n[LIST] Fetching PRs (status: {args.status}, limit: {args.top})")
    
    prs = pr_fetcher.fetch_pull_requests(
        status=args.status,
        top=args.top,
        source_branch=args.source_branch,
        target_branch=args.target_branch,
        author=args.author
    )
    
    if not prs:
        print("No pull requests found matching criteria")
        return []
    
    print(f"\n{'ID':<8} {'Status':<12} {'Author':<20} {'Title':<50}")
    print("-" * 90)
    
    pr_ids = []
    for pr in prs:
        pr_id = pr.get('pullRequestId')
        status = pr.get('status', 'unknown')
        author = pr.get('createdBy', {}).get('displayName', 'Unknown')[:19]
        title = pr.get('title', 'No Title')[:49]
        
        print(f"{pr_id:<8} {status:<12} {author:<20} {title:<50}")
        pr_ids.append(pr_id)
    
    return pr_ids


def fetch_pr_details(analyzer, pr_id):
    """Fetch and save PR details"""
    pr_fetcher = PRFetcher(analyzer)
    
    print(f"\n[FETCH] Fetching details for PR #{pr_id}")
    
    pr_data = pr_fetcher.fetch_pull_request(pr_id)
    if not pr_data:
        print(f"Failed to fetch PR #{pr_id}")
        return False
    
    # Save the data
    pr_fetcher.save_pr_data(pr_id)
    
    # Print summary
    print(f"\n[SUMMARY] PR #{pr_id}")
    print(f"  Title: {pr_data.get('title', 'No Title')}")
    print(f"  Author: {pr_data.get('createdBy', {}).get('displayName', 'Unknown')}")
    print(f"  Status: {pr_data.get('status', 'unknown')}")
    print(f"  Created: {pr_data.get('creationDate', 'unknown')}")
    
    reviewers = pr_data.get('reviewers', [])
    if reviewers:
        print(f"  Reviewers: {len(reviewers)}")
        for reviewer in reviewers[:5]:
            vote = reviewer.get('vote', 0)
            vote_str = '✅' if vote > 0 else '❌' if vote < 0 else '⏳'
            print(f"    - {reviewer.get('displayName', 'Unknown')} {vote_str}")
    
    return True


def analyze_pull_requests(analyzer, pr_ids):
    """Analyze one or more pull requests"""
    pr_analyzer = PRReviewAnalyzer(analyzer)
    
    if len(pr_ids) == 1:
        # Single PR analysis
        analysis = pr_analyzer.analyze_single_pr(pr_ids[0])
        return analysis
    else:
        # Multiple PR comparison
        df_comparison = pr_analyzer.analyze_multiple_prs(pr_ids)
        
        if not df_comparison.empty:
            print("\n[COMPARISON] PR Analysis Summary")
            print(df_comparison.to_string())
        
        return df_comparison


def analyze_pr_patterns(analyzer, days):
    """Analyze patterns across recent PRs"""
    pr_analyzer = PRReviewAnalyzer(analyzer)
    
    patterns = pr_analyzer.analyze_pr_patterns(days=days)
    
    print(f"\n[PATTERNS] Analysis for last {days} days")
    print(f"  Total PRs: {patterns['total_prs']}")
    
    print("\n  Status Distribution:")
    for status, count in patterns['status_distribution'].items():
        print(f"    {status}: {count}")
    
    print("\n  Quality Metrics:")
    for metric, value in patterns['quality_metrics'].items():
        if isinstance(value, float):
            print(f"    {metric.replace('_', ' ').title()}: {value:.2%}")
        else:
            print(f"    {metric.replace('_', ' ').title()}: {value}")
    
    print("\n  Review Patterns:")
    for key, value in patterns['review_patterns'].items():
        if isinstance(value, float):
            print(f"    {key.replace('_', ' ').title()}: {value:.2f}")
        else:
            print(f"    {key.replace('_', ' ').title()}: {value}")
    
    return patterns


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Get configuration
    config = get_configuration(args)
    
    print("[START] Azure DevOps Pull Request Analyzer")
    print(f"  Organization: {config['org_name']}")
    print(f"  Project: {config['project_name']}")
    print(f"  Repository: {config['repo_name']}")
    
    # Initialize analyzer
    try:
        analyzer = AzureDevOpsAnalyzer(
            org_name=config['org_name'],
            project_name=config['project_name'],
            repo_name=config['repo_name'],
            pat_token=config['pat_token'],
            data_dir=config['data_dir']
        )
    except Exception as e:
        print(f"❌ Error initializing analyzer: {e}")
        sys.exit(1)
    
    # Execute requested action
    try:
        if args.pr:
            # Analyze specific PRs
            analyze_pull_requests(analyzer, args.pr)
        
        elif args.fetch:
            # Fetch PR details
            fetch_pr_details(analyzer, args.fetch)
        
        elif args.list:
            # List PRs
            pr_ids = list_pull_requests(analyzer, args)
            
            if args.analyze and pr_ids:
                # Analyze listed PRs
                print(f"\n[ANALYZE] Analyzing {len(pr_ids)} PRs...")
                analyze_pull_requests(analyzer, pr_ids[:10])  # Limit to 10 for performance
        
        elif args.patterns:
            # Analyze patterns
            analyze_pr_patterns(analyzer, args.days)
        
        else:
            # No specific action, show help
            print("\n❓ No action specified. Use --help for usage information")
            print("\nQuick examples:")
            print("  Analyze a PR:        python analyze_pr.py --pr 1364")
            print("  List active PRs:     python analyze_pr.py --list --status active")
            print("  Analyze patterns:    python analyze_pr.py --patterns --days 30")
    
    except KeyboardInterrupt:
        print("\n[CANCELLED] Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    print("\n[COMPLETE] Pull request analysis finished")
    print(f"Results saved to: {config['data_dir']}")


if __name__ == "__main__":
    main()