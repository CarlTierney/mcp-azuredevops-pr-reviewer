#!/usr/bin/env python3
"""
Developer Productivity Analysis Module
"""

import pandas as pd
from collections import defaultdict

class ProductivityAnalyzer:
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
    
    def analyze_productivity_metrics(self):
        """Analyze Azure DevOps productivity metrics"""
        print("\n=== ENHANCED PRODUCTIVITY METRICS ===")
        
        developer_metrics = defaultdict(lambda: {
            'total_commits': 0,
            'productive_commits': 0,
            'feature_commits': 0,
            'bug_fix_commits': 0,
            'maintenance_commits': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'pull_requests': 0,
            'prs_completed': 0
        })
        
        # Analyze commits
        for commit in self.base_analyzer.commits:
            author_info = self.base_analyzer.get_author_info(commit.get('author', {}))
            author_key = author_info['unique_name']
            
            developer_metrics[author_key]['total_commits'] += 1
            
            # Classify commit type based on comment
            comment = commit.get('comment', '').lower()
            if any(word in comment for word in ['fix', 'bug', 'error', 'issue']):
                developer_metrics[author_key]['bug_fix_commits'] += 1
            elif any(word in comment for word in ['refactor', 'cleanup', 'improve', 'optimize']):
                developer_metrics[author_key]['maintenance_commits'] += 1
            elif any(word in comment for word in ['add', 'new', 'feature', 'implement']):
                developer_metrics[author_key]['feature_commits'] += 1
            
            # Count as productive if it has a meaningful comment
            if len(comment.strip()) > 10:
                developer_metrics[author_key]['productive_commits'] += 1
        
        # Analyze pull requests
        for pr in self.base_analyzer.pull_requests:
            author_info = self.base_analyzer.get_author_info(pr.get('createdBy', {}))
            author_key = author_info['unique_name']
            
            developer_metrics[author_key]['pull_requests'] += 1
            
            if pr.get('status') == 'completed':
                developer_metrics[author_key]['prs_completed'] += 1
        
        # Create productivity DataFrame
        productivity_data = []
        for author_key, metrics in developer_metrics.items():
            if metrics['total_commits'] == 0:
                continue
                
            productivity_data.append({
                'Developer': author_key,
                'Total_Commits': metrics['total_commits'],
                'Productive_Commits': metrics['productive_commits'],
                'Feature_Commits': metrics['feature_commits'],
                'Bug_Fix_Commits': metrics['bug_fix_commits'],
                'Maintenance_Commits': metrics['maintenance_commits'],
                'Pull_Requests': metrics['pull_requests'],
                'PRs_Completed': metrics['prs_completed'],
                'PR_Completion_Rate': (metrics['prs_completed'] / max(1, metrics['pull_requests'])) * 100,
                'Productivity_Ratio': (metrics['productive_commits'] / max(1, metrics['total_commits'])) * 100
            })
        
        df_productivity = pd.DataFrame(productivity_data)
        if not df_productivity.empty:
            df_productivity = df_productivity.sort_values('Productive_Commits', ascending=False)
            
            print(df_productivity.to_string(index=False))
            df_productivity.to_csv(f"{self.base_analyzer.data_dir}/azdo_productivity_metrics.csv", index=False)
        
        return df_productivity
