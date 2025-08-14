#!/usr/bin/env python3
"""
Repository Health Trends Analysis Module
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from ..utils.file_classifier import FileClassifier

class HealthTrendsAnalyzer:
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
        self.file_classifier = FileClassifier()
    
    def analyze_repository_health_trends(self):
        """Analyze repository health trends and predictive metrics"""
        print("\n=== REPOSITORY HEALTH TREND ANALYSIS ===")
        
        # Initialize health metrics by time period
        weekly_metrics = defaultdict(lambda: {
            'total_commits': 0,
            'active_developers': set(),
            'files_changed': set(),
            'test_files_changed': set(),
            'config_files_changed': set(),
            'critical_files_changed': set(),
            'total_lines_changed': 0,
            'bug_fixes': 0,
            'features_added': 0,
            'refactoring_commits': 0,
            'hotspot_changes': 0,
            'new_files_created': 0,
            'files_deleted': 0,
            'complexity_changes': [],
            'review_coverage': 0,
            'collaboration_score': 0
        })
        
        # Analyze commits by week
        for commit in self.base_analyzer.commits:
            try:
                commit_date_str = commit.get('author', {}).get('date', '')
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                week_key = commit_date.strftime('%Y-W%U')
                
                author_info = self.base_analyzer.get_author_info(commit.get('author', {}))
                author_key = author_info['unique_name']
                
                weekly_metrics[week_key]['total_commits'] += 1
                weekly_metrics[week_key]['active_developers'].add(author_key)
                
                # Classify commit type
                comment = commit.get('comment', '').lower()
                if any(word in comment for word in ['fix', 'bug', 'error', 'issue']):
                    weekly_metrics[week_key]['bug_fixes'] += 1
                elif any(word in comment for word in ['add', 'new', 'feature']):
                    weekly_metrics[week_key]['features_added'] += 1
                elif any(word in comment for word in ['refactor', 'cleanup', 'improve']):
                    weekly_metrics[week_key]['refactoring_commits'] += 1
                    
            except (ValueError, AttributeError):
                continue
        
        # Analyze detailed commits for file-level health metrics
        for commit_id, changes_data in self.base_analyzer.detailed_commits.items():
            commit_info = next((c for c in self.base_analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
            
            try:
                commit_date_str = commit_info.get('author', {}).get('date', '')
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                week_key = commit_date.strftime('%Y-W%U')
            except:
                continue
            
            changes = changes_data.get('changes', [])
            for change in changes:
                item = change.get('item', {})
                change_type = change.get('changeType', '')
                path = item.get('path', '')
                
                if not path or item.get('isFolder', False):
                    continue
                
                filename = os.path.basename(path)
                file_type = self.file_classifier.classify_file_type(filename)
                
                weekly_metrics[week_key]['files_changed'].add(path)
                
                # Track specific file types
                if file_type in ['test_csharp', 'test_sql']:
                    weekly_metrics[week_key]['test_files_changed'].add(path)
                elif file_type in ['dotnet_config', 'config']:
                    weekly_metrics[week_key]['config_files_changed'].add(path)
                
                if self.file_classifier.is_critical_component(path, filename, file_type):
                    weekly_metrics[week_key]['critical_files_changed'].add(path)
                
                # Track file operations
                if change_type == 'add':
                    weekly_metrics[week_key]['new_files_created'] += 1
                elif change_type == 'delete':
                    weekly_metrics[week_key]['files_deleted'] += 1
        
        # Calculate health scores and trends
        health_data = []
        sorted_weeks = sorted(weekly_metrics.keys())
        
        for i, week in enumerate(sorted_weeks):
            metrics = weekly_metrics[week]
            
            # Convert sets to counts
            active_devs = len(metrics['active_developers'])
            files_changed = len(metrics['files_changed'])
            test_files_changed = len(metrics['test_files_changed'])
            critical_files_changed = len(metrics['critical_files_changed'])
            
            # Calculate health indicators
            test_coverage_trend = (test_files_changed / max(1, files_changed)) * 100
            developer_diversity = min(100, active_devs * 20)  # More diverse = healthier
            stability_score = max(0, 100 - (critical_files_changed * 10))  # Fewer critical changes = more stable
            
            # Calculate change velocity
            change_velocity = metrics['total_commits'] + files_changed
            
            # Calculate maintenance ratio
            maintenance_commits = metrics['bug_fixes'] + metrics['refactoring_commits']
            total_commits = metrics['total_commits']
            maintenance_ratio = (maintenance_commits / max(1, total_commits)) * 100
            
            # Calculate innovation ratio
            innovation_commits = metrics['features_added']
            innovation_ratio = (innovation_commits / max(1, total_commits)) * 100
            
            # Overall health score (composite)
            health_score = np.mean([
                min(100, test_coverage_trend * 2),  # Test coverage importance
                developer_diversity,
                stability_score,
                min(100, 100 - maintenance_ratio),  # Lower maintenance = healthier
                min(100, innovation_ratio * 2)  # Innovation is healthy
            ])
            
            # Calculate trend (compare with previous weeks)
            health_trend = 0
            if i >= 3:  # Need at least 4 weeks for trend
                recent_scores = []
                for j in range(max(0, i-3), i):
                    prev_week = sorted_weeks[j]
                    prev_metrics = weekly_metrics[prev_week]
                    prev_score = np.mean([
                        min(100, (len(prev_metrics['test_files_changed']) / max(1, len(prev_metrics['files_changed']))) * 200),
                        min(100, len(prev_metrics['active_developers']) * 20),
                        max(0, 100 - (len(prev_metrics['critical_files_changed']) * 10))
                    ])
                    recent_scores.append(prev_score)
                
                if len(recent_scores) > 1:
                    # Simple linear trend
                    x = np.arange(len(recent_scores))
                    slope = np.polyfit(x, recent_scores, 1)[0]
                    health_trend = slope
            
            health_data.append({
                'Week': week,
                'Total_Commits': metrics['total_commits'],
                'Active_Developers': active_devs,
                'Files_Changed': files_changed,
                'Test_Files_Changed': test_files_changed,
                'Critical_Files_Changed': critical_files_changed,
                'New_Files_Created': metrics['new_files_created'],
                'Files_Deleted': metrics['files_deleted'],
                'Bug_Fixes': metrics['bug_fixes'],
                'Features_Added': metrics['features_added'],
                'Refactoring_Commits': metrics['refactoring_commits'],
                'Test_Coverage_Trend': round(test_coverage_trend, 1),
                'Developer_Diversity_Score': round(developer_diversity, 1),
                'Stability_Score': round(stability_score, 1),
                'Maintenance_Ratio': round(maintenance_ratio, 1),
                'Innovation_Ratio': round(innovation_ratio, 1),
                'Change_Velocity': change_velocity,
                'Health_Score': round(health_score, 1),
                'Health_Trend': round(health_trend, 2)
            })
        
        df_health_trends = pd.DataFrame(health_data)
        if not df_health_trends.empty:
            df_health_trends = df_health_trends.sort_values('Week')
            
            print(df_health_trends.to_string(index=False))
            df_health_trends.to_csv(f"{self.base_analyzer.data_dir}/azdo_repository_health_trends.csv", index=False)
            
            # Generate health insights
            self._generate_health_insights(df_health_trends)
        
        return df_health_trends
    
    def _generate_health_insights(self, df_health_trends):
        """Generate insights about repository health trends"""
        if df_health_trends.empty:
            return
        
        print("\n=== REPOSITORY HEALTH INSIGHTS ===")
        
        # Calculate overall trends
        recent_weeks = df_health_trends.tail(4)
        avg_health_score = recent_weeks['Health_Score'].mean()
        health_trend = recent_weeks['Health_Trend'].mean()
        
        print(f"[STATS] Current Health Status:")
        print(f"   • Average health score (last 4 weeks): {avg_health_score:.1f}/100")
        print(f"   • Health trend: {'[CHART] Improving' if health_trend > 0 else '📉 Declining' if health_trend < 0 else '➡️ Stable'}")
        
        # Identify concerning trends
        if recent_weeks['Maintenance_Ratio'].mean() > 50:
            print(f"   [WARNING] High maintenance burden: {recent_weeks['Maintenance_Ratio'].mean():.1f}%")
        
        if recent_weeks['Test_Coverage_Trend'].mean() < 20:
            print(f"   [WARNING] Low test coverage trend: {recent_weeks['Test_Coverage_Trend'].mean():.1f}%")
        
        if recent_weeks['Developer_Diversity_Score'].mean() < 40:
            print(f"   [WARNING] Low developer diversity: {recent_weeks['Developer_Diversity_Score'].mean():.1f}%")
        
        # Positive indicators
        if recent_weeks['Innovation_Ratio'].mean() > 30:
            print(f"   [OK] Strong innovation: {recent_weeks['Innovation_Ratio'].mean():.1f}% of commits")
        
        if recent_weeks['Stability_Score'].mean() > 80:
            print(f"   [OK] High stability: {recent_weeks['Stability_Score'].mean():.1f}% stability score")
