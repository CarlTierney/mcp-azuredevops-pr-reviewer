"""
Pull Request Review Analyzer
Analyzes PR review patterns, quality, and provides detailed insights
"""

import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional
import re


class PRReviewAnalyzer:
    """Analyzes pull request review patterns and quality"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        from analyzers.pr_fetcher import PRFetcher
        self.pr_fetcher = PRFetcher(base_analyzer)
    
    def analyze_single_pr(self, pr_id: int) -> Dict[str, Any]:
        """Perform comprehensive analysis of a single PR"""
        print(f"\n[ANALYZE] Analyzing Pull Request #{pr_id}...")
        
        # Fetch PR data
        pr_data = self.pr_fetcher.fetch_pull_request(pr_id)
        if not pr_data:
            return {'error': f'Could not fetch PR #{pr_id}'}
        
        # Get PR statistics
        stats = self.pr_fetcher.get_pr_statistics(pr_id)
        
        # Perform detailed analysis
        analysis = {
            'pr_id': pr_id,
            'basic_info': self._analyze_basic_info(pr_data),
            'review_quality': self._analyze_review_quality(pr_data),
            'code_changes': self._analyze_code_changes(pr_id),
            'collaboration': self._analyze_collaboration(pr_data),
            'timeline': self._analyze_timeline(pr_data),
            'risks': self._identify_risks(pr_data, stats),
            'recommendations': self._generate_recommendations(pr_data, stats),
            'statistics': stats
        }
        
        # Print analysis summary
        self._print_pr_analysis(analysis)
        
        # Save detailed analysis
        self._save_pr_analysis(pr_id, analysis)
        
        return analysis
    
    def analyze_multiple_prs(self, pr_ids: List[int]) -> pd.DataFrame:
        """Analyze multiple PRs and create comparison"""
        print(f"\n[ANALYZE] Analyzing {len(pr_ids)} Pull Requests...")
        
        analyses = []
        for pr_id in pr_ids:
            analysis = self.analyze_single_pr(pr_id)
            if 'error' not in analysis:
                analyses.append(self._flatten_analysis(analysis))
        
        if not analyses:
            print("[WARNING] No PRs could be analyzed")
            return pd.DataFrame()
        
        df = pd.DataFrame(analyses)
        
        # Save comparison
        output_file = f"{self.analyzer.data_dir}/pr_comparison_analysis.csv"
        df.to_csv(output_file, index=False)
        print(f"[OK] PR comparison saved to: {output_file}")
        
        return df
    
    def analyze_pr_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Analyze patterns across recent PRs"""
        print(f"\n[ANALYZE] Analyzing PR patterns for last {days} days...")
        
        # Fetch recent PRs
        prs = self.pr_fetcher.fetch_pull_requests(status="all", top=200)
        
        # Filter by date
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_prs = []
        for pr in prs:
            creation_date_str = pr.get('creationDate', '')
            if creation_date_str:
                creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                if creation_date.replace(tzinfo=None) >= cutoff_date:
                    recent_prs.append(pr)
        
        patterns = {
            'total_prs': len(recent_prs),
            'time_period_days': days,
            'status_distribution': self._analyze_status_distribution(recent_prs),
            'review_patterns': self._analyze_review_patterns(recent_prs),
            'branch_patterns': self._analyze_branch_patterns(recent_prs),
            'timing_patterns': self._analyze_timing_patterns(recent_prs),
            'author_patterns': self._analyze_author_patterns(recent_prs),
            'quality_metrics': self._calculate_quality_metrics(recent_prs)
        }
        
        # Save patterns analysis
        self._save_patterns_analysis(patterns)
        
        return patterns
    
    def _analyze_basic_info(self, pr_data: Dict) -> Dict:
        """Extract basic PR information"""
        return {
            'title': pr_data.get('title', ''),
            'description': pr_data.get('description', ''),
            'author': pr_data.get('createdBy', {}).get('displayName', 'Unknown'),
            'status': pr_data.get('status', ''),
            'source_branch': pr_data.get('sourceRefName', '').replace('refs/heads/', ''),
            'target_branch': pr_data.get('targetRefName', '').replace('refs/heads/', ''),
            'merge_status': pr_data.get('mergeStatus', ''),
            'is_draft': pr_data.get('isDraft', False),
            'creation_date': pr_data.get('creationDate', ''),
            'completion_date': pr_data.get('completionDate', '')
        }
    
    def _analyze_review_quality(self, pr_data: Dict) -> Dict:
        """Analyze the quality of PR reviews"""
        reviewers = pr_data.get('reviewers', [])
        threads = pr_data.get('threads', [])
        
        quality = {
            'reviewer_count': len(reviewers),
            'approvals': sum(1 for r in reviewers if r.get('vote', 0) > 0),
            'rejections': sum(1 for r in reviewers if r.get('vote', 0) < 0),
            'waiting_for_author': sum(1 for r in reviewers if r.get('vote', 0) == -5),
            'required_reviewers': sum(1 for r in reviewers if r.get('isRequired', False)),
            'thread_count': len(threads),
            'comment_count': sum(len(t.get('comments', [])) for t in threads),
            'resolved_threads': sum(1 for t in threads if t.get('status', '') == 'closed'),
            'active_threads': sum(1 for t in threads if t.get('status', '') == 'active')
        }
        
        # Calculate review depth score
        quality['review_depth_score'] = self._calculate_review_depth_score(quality)
        
        # Analyze comment sentiment and types
        comment_analysis = self._analyze_comments(threads)
        quality.update(comment_analysis)
        
        return quality
    
    def _analyze_code_changes(self, pr_id: int) -> Dict:
        """Analyze code changes in the PR"""
        changes = self.pr_fetcher.fetch_pr_changes(pr_id)
        
        if not changes:
            return {
                'files_changed': 0,
                'total_additions': 0,
                'total_deletions': 0,
                'change_size_category': 'empty'
            }
        
        total_additions = sum(c.get('additions', 0) for c in changes)
        total_deletions = sum(c.get('deletions', 0) for c in changes)
        total_changes = total_additions + total_deletions
        
        # Categorize change size
        if total_changes < 50:
            size_category = 'small'
        elif total_changes < 250:
            size_category = 'medium'
        elif total_changes < 1000:
            size_category = 'large'
        else:
            size_category = 'extra_large'
        
        # Analyze file types
        file_types = defaultdict(int)
        for change in changes:
            file_path = change.get('path', '')
            if '.' in file_path:
                ext = file_path.split('.')[-1].lower()
                file_types[ext] += 1
        
        return {
            'files_changed': len(changes),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_changes': total_changes,
            'change_size_category': size_category,
            'file_types': dict(file_types),
            'most_changed_files': [c['path'] for c in sorted(changes, 
                                   key=lambda x: x.get('additions', 0) + x.get('deletions', 0), 
                                   reverse=True)[:5]]
        }
    
    def _analyze_collaboration(self, pr_data: Dict) -> Dict:
        """Analyze collaboration patterns in the PR"""
        reviewers = pr_data.get('reviewers', [])
        threads = pr_data.get('threads', [])
        
        # Analyze reviewer participation
        reviewer_participation = {}
        for reviewer in reviewers:
            name = reviewer.get('displayName', 'Unknown')
            reviewer_participation[name] = {
                'vote': reviewer.get('vote', 0),
                'is_required': reviewer.get('isRequired', False),
                'has_declined': reviewer.get('hasDeclined', False)
            }
        
        # Analyze thread participation
        thread_participants = set()
        for thread in threads:
            for comment in thread.get('comments', []):
                author = comment.get('author', {}).get('displayName', 'Unknown')
                thread_participants.add(author)
        
        return {
            'reviewer_participation': reviewer_participation,
            'thread_participants': list(thread_participants),
            'unique_participants': len(thread_participants),
            'reviewer_response_rate': len([r for r in reviewers if r.get('vote', 0) != 0]) / len(reviewers) if reviewers else 0,
            'collaboration_score': self._calculate_collaboration_score(reviewers, threads)
        }
    
    def _analyze_timeline(self, pr_data: Dict) -> Dict:
        """Analyze PR timeline and key events"""
        timeline = {
            'creation_date': pr_data.get('creationDate', ''),
            'first_review': None,
            'first_approval': None,
            'completion_date': pr_data.get('completionDate', ''),
            'key_events': []
        }
        
        # Find first review and approval
        for reviewer in pr_data.get('reviewers', []):
            vote = reviewer.get('vote', 0)
            vote_date = reviewer.get('votedFor', [{}])[0].get('reviewerVoteDate') if reviewer.get('votedFor') else None
            
            if vote_date:
                if timeline['first_review'] is None:
                    timeline['first_review'] = vote_date
                if vote > 0 and timeline['first_approval'] is None:
                    timeline['first_approval'] = vote_date
        
        # Calculate durations
        if timeline['creation_date']:
            created = datetime.fromisoformat(timeline['creation_date'].replace('Z', '+00:00'))
            
            if timeline['first_review']:
                first_review = datetime.fromisoformat(timeline['first_review'].replace('Z', '+00:00'))
                timeline['time_to_first_review_hours'] = (first_review - created).total_seconds() / 3600
            
            if timeline['completion_date']:
                completed = datetime.fromisoformat(timeline['completion_date'].replace('Z', '+00:00'))
                timeline['total_duration_hours'] = (completed - created).total_seconds() / 3600
                timeline['total_duration_days'] = (completed - created).days
        
        return timeline
    
    def _identify_risks(self, pr_data: Dict, stats: Dict) -> List[Dict]:
        """Identify potential risks in the PR"""
        risks = []
        
        # Large PR risk
        if stats.get('files_changed', 0) > 20:
            risks.append({
                'type': 'size',
                'severity': 'high',
                'description': f"Large PR with {stats['files_changed']} files changed",
                'recommendation': 'Consider breaking into smaller PRs'
            })
        
        # No tests risk
        changes = self.pr_fetcher.fetch_pr_changes(pr_data.get('pullRequestId'))
        test_files = [c for c in changes if 'test' in c.get('path', '').lower()]
        if not test_files and stats.get('files_changed', 0) > 5:
            risks.append({
                'type': 'testing',
                'severity': 'medium',
                'description': 'No test files modified',
                'recommendation': 'Add tests for the changes'
            })
        
        # Long review time risk
        duration_days = stats.get('duration_days')
        if duration_days and duration_days > 7:
            risks.append({
                'type': 'timeline',
                'severity': 'medium',
                'description': f"PR open for {duration_days} days",
                'recommendation': 'Long-running PRs accumulate conflicts'
            })
        
        # Low review participation
        reviewers = pr_data.get('reviewers', [])
        if reviewers and len([r for r in reviewers if r.get('vote', 0) != 0]) < len(reviewers) / 2:
            risks.append({
                'type': 'review',
                'severity': 'low',
                'description': 'Low reviewer participation',
                'recommendation': 'Follow up with pending reviewers'
            })
        
        # Hotfix without tests (based on title/description)
        title = pr_data.get('title', '').lower()
        description = pr_data.get('description', '').lower()
        if ('hotfix' in title or 'hotfix' in description) and not test_files:
            risks.append({
                'type': 'hotfix',
                'severity': 'high',
                'description': 'Hotfix without tests',
                'recommendation': 'Add tests even for hotfixes to prevent regression'
            })
        
        return risks
    
    def _generate_recommendations(self, pr_data: Dict, stats: Dict) -> List[str]:
        """Generate recommendations for the PR"""
        recommendations = []
        
        # Based on size
        if stats.get('files_changed', 0) > 30:
            recommendations.append("Consider splitting this PR into smaller, more focused changes")
        
        # Based on review quality
        if stats.get('comments_count', 0) < 3 and stats.get('files_changed', 0) > 10:
            recommendations.append("Encourage more detailed code review comments")
        
        # Based on timeline
        duration_days = stats.get('duration_days')
        if duration_days is not None and duration_days > 5:
            recommendations.append("Try to merge PRs within 3-5 days to avoid conflicts")
        
        # Based on description
        if len(pr_data.get('description', '')) < 50:
            recommendations.append("Add more detailed description explaining the changes")
        
        # Based on work items
        if not stats.get('work_items'):
            recommendations.append("Link PR to relevant work items for better tracking")
        
        return recommendations
    
    def _calculate_review_depth_score(self, quality: Dict) -> float:
        """Calculate a score representing review depth (0-100)"""
        score = 0
        
        # Reviewer participation (30 points)
        if quality['reviewer_count'] > 0:
            score += min(quality['approvals'] / quality['reviewer_count'] * 30, 30)
        
        # Comments and discussions (40 points)
        score += min(quality['comment_count'] * 2, 40)
        
        # Thread resolution (30 points)
        if quality['thread_count'] > 0:
            score += (quality['resolved_threads'] / quality['thread_count']) * 30
        
        return round(score, 1)
    
    def _calculate_collaboration_score(self, reviewers: List, threads: List) -> float:
        """Calculate collaboration score (0-100)"""
        score = 0
        
        # Reviewer diversity (40 points)
        if len(reviewers) >= 2:
            score += 40
        elif len(reviewers) == 1:
            score += 20
        
        # Discussion quality (60 points)
        total_comments = sum(len(t.get('comments', [])) for t in threads)
        score += min(total_comments * 5, 60)
        
        return round(score, 1)
    
    def _analyze_comments(self, threads: List) -> Dict:
        """Analyze comment patterns and sentiment"""
        comment_types = {
            'suggestions': 0,
            'questions': 0,
            'approvals': 0,
            'concerns': 0,
            'discussions': 0
        }
        
        for thread in threads:
            for comment in thread.get('comments', []):
                content = comment.get('content', '').lower()
                
                # Categorize comments
                if '?' in content:
                    comment_types['questions'] += 1
                if any(word in content for word in ['suggest', 'consider', 'should', 'could']):
                    comment_types['suggestions'] += 1
                if any(word in content for word in ['lgtm', 'looks good', 'approved', 'great']):
                    comment_types['approvals'] += 1
                if any(word in content for word in ['concern', 'issue', 'problem', 'bug']):
                    comment_types['concerns'] += 1
                if len(thread.get('comments', [])) > 2:
                    comment_types['discussions'] += 1
        
        return {
            'comment_types': comment_types,
            'has_substantive_feedback': comment_types['suggestions'] + comment_types['concerns'] > 0
        }
    
    def _flatten_analysis(self, analysis: Dict) -> Dict:
        """Flatten nested analysis dictionary for DataFrame"""
        flat = {
            'pr_id': analysis['pr_id'],
            'title': analysis['basic_info']['title'],
            'author': analysis['basic_info']['author'],
            'status': analysis['basic_info']['status'],
            'source_branch': analysis['basic_info']['source_branch'],
            'target_branch': analysis['basic_info']['target_branch'],
            'files_changed': analysis['code_changes']['files_changed'],
            'total_changes': analysis['code_changes']['total_changes'],
            'change_size': analysis['code_changes']['change_size_category'],
            'reviewer_count': analysis['review_quality']['reviewer_count'],
            'approvals': analysis['review_quality']['approvals'],
            'comment_count': analysis['review_quality']['comment_count'],
            'review_depth_score': analysis['review_quality']['review_depth_score'],
            'collaboration_score': analysis['collaboration']['collaboration_score'],
            'risk_count': len(analysis['risks']),
            'recommendation_count': len(analysis['recommendations'])
        }
        
        # Add duration if available
        if 'duration_days' in analysis['statistics']:
            flat['duration_days'] = analysis['statistics']['duration_days']
        
        return flat
    
    def _analyze_status_distribution(self, prs: List) -> Dict:
        """Analyze distribution of PR statuses"""
        distribution = defaultdict(int)
        for pr in prs:
            status = pr.get('status', 'unknown')
            distribution[status] += 1
        return dict(distribution)
    
    def _analyze_review_patterns(self, prs: List) -> Dict:
        """Analyze review patterns across PRs"""
        patterns = {
            'avg_reviewers': 0,
            'avg_approval_rate': 0,
            'avg_comment_count': 0,
            'prs_without_comments': 0
        }
        
        total_reviewers = 0
        total_approvals = 0
        total_comments = 0
        
        for pr in prs:
            reviewers = pr.get('reviewers', [])
            total_reviewers += len(reviewers)
            total_approvals += sum(1 for r in reviewers if r.get('vote', 0) > 0)
            
            # Would need to fetch threads for accurate comment count
            # For now, using a simplified approach
            if len(reviewers) == 0:
                patterns['prs_without_comments'] += 1
        
        if prs:
            patterns['avg_reviewers'] = total_reviewers / len(prs)
            patterns['avg_approval_rate'] = total_approvals / total_reviewers if total_reviewers > 0 else 0
        
        return patterns
    
    def _analyze_branch_patterns(self, prs: List) -> Dict:
        """Analyze branch naming and targeting patterns"""
        source_branches = defaultdict(int)
        target_branches = defaultdict(int)
        
        for pr in prs:
            source = pr.get('sourceRefName', '').replace('refs/heads/', '')
            target = pr.get('targetRefName', '').replace('refs/heads/', '')
            
            # Categorize source branches
            if 'feature/' in source:
                source_branches['feature'] += 1
            elif 'bugfix/' in source or 'fix/' in source:
                source_branches['bugfix'] += 1
            elif 'hotfix/' in source:
                source_branches['hotfix'] += 1
            else:
                source_branches['other'] += 1
            
            target_branches[target] += 1
        
        return {
            'source_branch_types': dict(source_branches),
            'target_branches': dict(target_branches)
        }
    
    def _analyze_timing_patterns(self, prs: List) -> Dict:
        """Analyze timing patterns of PRs"""
        patterns = {
            'avg_duration_hours': 0,
            'prs_merged_same_day': 0,
            'prs_open_over_week': 0
        }
        
        total_duration = 0
        completed_count = 0
        
        for pr in prs:
            creation_date_str = pr.get('creationDate', '')
            completion_date_str = pr.get('completionDate', '')
            
            if creation_date_str and completion_date_str:
                created = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                completed = datetime.fromisoformat(completion_date_str.replace('Z', '+00:00'))
                duration = completed - created
                
                total_duration += duration.total_seconds() / 3600
                completed_count += 1
                
                if duration.days == 0:
                    patterns['prs_merged_same_day'] += 1
                elif duration.days > 7:
                    patterns['prs_open_over_week'] += 1
        
        if completed_count > 0:
            patterns['avg_duration_hours'] = total_duration / completed_count
        
        return patterns
    
    def _analyze_author_patterns(self, prs: List) -> Dict:
        """Analyze PR author patterns"""
        author_stats = defaultdict(lambda: {'count': 0, 'completed': 0, 'abandoned': 0})
        
        for pr in prs:
            author = pr.get('createdBy', {}).get('displayName', 'Unknown')
            status = pr.get('status', '')
            
            author_stats[author]['count'] += 1
            if status == 'completed':
                author_stats[author]['completed'] += 1
            elif status == 'abandoned':
                author_stats[author]['abandoned'] += 1
        
        # Find top contributors
        top_authors = sorted(author_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        
        return {
            'unique_authors': len(author_stats),
            'top_contributors': [{'name': name, **stats} for name, stats in top_authors],
            'author_distribution': dict(author_stats)
        }
    
    def _calculate_quality_metrics(self, prs: List) -> Dict:
        """Calculate overall quality metrics"""
        metrics = {
            'completion_rate': 0,
            'abandonment_rate': 0,
            'avg_review_participation': 0,
            'prs_with_required_reviewers': 0
        }
        
        if not prs:
            return metrics
        
        completed = sum(1 for pr in prs if pr.get('status') == 'completed')
        abandoned = sum(1 for pr in prs if pr.get('status') == 'abandoned')
        
        metrics['completion_rate'] = completed / len(prs)
        metrics['abandonment_rate'] = abandoned / len(prs)
        
        total_participation = 0
        required_reviewer_count = 0
        
        for pr in prs:
            reviewers = pr.get('reviewers', [])
            if reviewers:
                voted = sum(1 for r in reviewers if r.get('vote', 0) != 0)
                total_participation += voted / len(reviewers)
            
            if any(r.get('isRequired', False) for r in reviewers):
                required_reviewer_count += 1
        
        metrics['avg_review_participation'] = total_participation / len(prs) if prs else 0
        metrics['prs_with_required_reviewers'] = required_reviewer_count
        
        return metrics
    
    def _print_pr_analysis(self, analysis: Dict):
        """Print PR analysis summary to console"""
        print("\n" + "=" * 70)
        print(f"PULL REQUEST #{analysis['pr_id']} ANALYSIS")
        print("=" * 70)
        
        # Basic info
        info = analysis['basic_info']
        print(f"\nTitle: {info['title']}")
        print(f"Author: {info['author']}")
        print(f"Status: {info['status']}")
        print(f"Branch: {info['source_branch']} -> {info['target_branch']}")
        
        # Code changes
        changes = analysis['code_changes']
        print(f"\nCode Changes:")
        print(f"  Files: {changes['files_changed']}")
        print(f"  Additions: +{changes['total_additions']}")
        print(f"  Deletions: -{changes['total_deletions']}")
        print(f"  Size: {changes['change_size_category']}")
        
        # Review quality
        quality = analysis['review_quality']
        print(f"\nReview Quality:")
        print(f"  Reviewers: {quality['reviewer_count']}")
        print(f"  Approvals: {quality['approvals']}")
        print(f"  Comments: {quality['comment_count']}")
        print(f"  Review Depth Score: {quality['review_depth_score']}/100")
        
        # Collaboration
        collab = analysis['collaboration']
        print(f"\nCollaboration:")
        print(f"  Unique Participants: {collab['unique_participants']}")
        print(f"  Collaboration Score: {collab['collaboration_score']}/100")
        
        # Risks
        if analysis['risks']:
            print(f"\nIdentified Risks:")
            for risk in analysis['risks']:
                print(f"  [{risk['severity'].upper()}] {risk['description']}")
                print(f"    -> {risk['recommendation']}")
        
        # Recommendations
        if analysis['recommendations']:
            print(f"\nRecommendations:")
            for i, rec in enumerate(analysis['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "=" * 70)
    
    def _save_pr_analysis(self, pr_id: int, analysis: Dict):
        """Save PR analysis to file"""
        import json
        
        output_file = f"{self.analyzer.data_dir}/pr_{pr_id}_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"\n[OK] Detailed analysis saved to: {output_file}")
    
    def _save_patterns_analysis(self, patterns: Dict):
        """Save patterns analysis to file"""
        import json
        
        output_file = f"{self.analyzer.data_dir}/pr_patterns_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2, default=str)
        
        print(f"[OK] PR patterns analysis saved to: {output_file}")
        
        # Also create a summary CSV
        summary_data = []
        summary_data.append({
            'Metric': 'Total PRs Analyzed',
            'Value': patterns['total_prs']
        })
        summary_data.append({
            'Metric': 'Time Period (days)',
            'Value': patterns['time_period_days']
        })
        
        for status, count in patterns['status_distribution'].items():
            summary_data.append({
                'Metric': f'PRs - {status}',
                'Value': count
            })
        
        for metric, value in patterns['quality_metrics'].items():
            summary_data.append({
                'Metric': metric.replace('_', ' ').title(),
                'Value': round(value, 2) if isinstance(value, float) else value
            })
        
        df_summary = pd.DataFrame(summary_data)
        csv_file = f"{self.analyzer.data_dir}/pr_patterns_summary.csv"
        df_summary.to_csv(csv_file, index=False)
        print(f"[OK] PR patterns summary saved to: {csv_file}")