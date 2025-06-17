#!/usr/bin/env python3
"""
Advanced Developer Contributions Analysis Module
"""

import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from ..utils.file_classifier import FileClassifier

class AdvancedContributionsAnalyzer:
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
        self.file_classifier = FileClassifier()
    
    def analyze_advanced_developer_contributions(self):
        """Advanced analysis of developer contributions with velocity and collaboration metrics"""
        print("\n=== ADVANCED DEVELOPER CONTRIBUTION ANALYSIS ===")
        
        # Initialize comprehensive metrics
        developer_metrics = defaultdict(lambda: {
            'contributions': {
                'commits': 0,
                'lines_added': 0,
                'lines_deleted': 0,
                'files_touched': set(),
                'unique_files': set(),
                'pull_requests_created': 0,
                'pull_requests_reviewed': 0,
                'work_items_linked': 0
            },
            'velocity': {
                'commits_per_week': [],
                'lines_per_commit': [],
                'commit_consistency': 0,
                'velocity_trend': 0,
                'productivity_score': 0
            },
            'collaboration': {
                'collaborators': set(),
                'files_shared': defaultdict(set),
                'review_participation': 0,
                'mentoring_score': 0,
                'knowledge_sharing': 0
            },
            'quality_indicators': {
                'defect_fixes': 0,
                'feature_additions': 0,
                'refactoring_commits': 0,
                'test_commits': 0,
                'documentation_commits': 0,
                'quality_score': 0
            },
            'temporal_patterns': {
                'active_weeks': set(),
                'commit_hours': [],
                'work_pattern': 'unknown',
                'consistency_score': 0
            },
            'expertise_areas': defaultdict(int),
            'impact_metrics': {
                'critical_file_changes': 0,
                'architecture_changes': 0,
                'high_value_contributions': 0,
                'innovation_score': 0
            }
        })
        
        # Analyze commits for contribution patterns
        commits_by_week = defaultdict(lambda: defaultdict(int))
        
        for commit in self.base_analyzer.commits:
            author_info = self.base_analyzer.get_author_info(commit.get('author', {}))
            author_key = author_info['unique_name']
            
            # Extract commit date and week
            try:
                commit_date_str = commit.get('author', {}).get('date', '')
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                week_key = commit_date.strftime('%Y-W%U')
                
                # Track temporal patterns
                developer_metrics[author_key]['temporal_patterns']['active_weeks'].add(week_key)
                developer_metrics[author_key]['temporal_patterns']['commit_hours'].append(commit_date.hour)
                commits_by_week[week_key][author_key] += 1
                
            except (ValueError, AttributeError):
                commit_date = None
            
            # Basic contribution tracking
            developer_metrics[author_key]['contributions']['commits'] += 1
            
            # Analyze commit message for quality indicators
            comment = commit.get('comment', '').lower()
            if any(word in comment for word in ['fix', 'bug', 'error', 'issue', 'resolve']):
                developer_metrics[author_key]['quality_indicators']['defect_fixes'] += 1
            elif any(word in comment for word in ['add', 'new', 'feature', 'implement', 'create']):
                developer_metrics[author_key]['quality_indicators']['feature_additions'] += 1
            elif any(word in comment for word in ['refactor', 'cleanup', 'improve', 'optimize', 'restructure']):
                developer_metrics[author_key]['quality_indicators']['refactoring_commits'] += 1
            elif any(word in comment for word in ['test', 'spec', 'unit', 'integration']):
                developer_metrics[author_key]['quality_indicators']['test_commits'] += 1
            elif any(word in comment for word in ['doc', 'readme', 'comment', 'documentation']):
                developer_metrics[author_key]['quality_indicators']['documentation_commits'] += 1
        
        # Analyze detailed commits for file-level metrics
        for commit_id, changes_data in self.base_analyzer.detailed_commits.items():
            commit_info = next((c for c in self.base_analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
                
            author_info = self.base_analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            changes = changes_data.get('changes', [])
            lines_in_commit = 0
            files_in_commit = set()
            
            for change in changes:
                item = change.get('item', {})
                path = item.get('path', '')
                
                if not path or item.get('isFolder', False):
                    continue
                    
                filename = os.path.basename(path)
                file_type = self.file_classifier.classify_file_type(filename)
                
                files_in_commit.add(path)
                developer_metrics[author_key]['contributions']['files_touched'].add(path)
                developer_metrics[author_key]['contributions']['unique_files'].add(path)
                
                # Track expertise areas
                architecture_area = self.file_classifier.classify_architecture_area(path, filename)
                developer_metrics[author_key]['expertise_areas'][architecture_area] += 1
                
                # Check if this is a critical file
                if self.file_classifier.is_critical_component(path, filename, file_type):
                    developer_metrics[author_key]['impact_metrics']['critical_file_changes'] += 1
                
                # Estimate lines changed (rough approximation)
                estimated_lines = 10  # Default estimate per file change
                lines_in_commit += estimated_lines
            
            # Track velocity metrics
            developer_metrics[author_key]['velocity']['lines_per_commit'].append(lines_in_commit)
            developer_metrics[author_key]['contributions']['lines_added'] += lines_in_commit
            
            # Track collaboration (files worked on by multiple developers)
            for file_path in files_in_commit:
                for other_dev, other_metrics in developer_metrics.items():
                    if other_dev != author_key and file_path in other_metrics['contributions']['files_touched']:
                        developer_metrics[author_key]['collaboration']['collaborators'].add(other_dev)
                        developer_metrics[author_key]['collaboration']['files_shared'][file_path].add(other_dev)
        
        # Analyze pull requests for review participation
        for pr in self.base_analyzer.pull_requests:
            author_info = self.base_analyzer.get_author_info(pr.get('createdBy', {}))
            author_key = author_info['unique_name']
            
            developer_metrics[author_key]['contributions']['pull_requests_created'] += 1
            
            # Track reviewers (if available in data)
            reviewers = pr.get('reviewers', [])
            for reviewer in reviewers:
                reviewer_info = self.base_analyzer.get_author_info(reviewer)
                reviewer_key = reviewer_info['unique_name']
                developer_metrics[reviewer_key]['contributions']['pull_requests_reviewed'] += 1
                developer_metrics[reviewer_key]['collaboration']['review_participation'] += 1
        
        # Calculate derived metrics
        for author_key, metrics in developer_metrics.items():
            # Calculate velocity metrics
            if metrics['temporal_patterns']['active_weeks']:
                weeks_active = len(metrics['temporal_patterns']['active_weeks'])
                commits_per_week = metrics['contributions']['commits'] / weeks_active
                metrics['velocity']['commits_per_week'] = commits_per_week
                
                # Calculate consistency (coefficient of variation)
                weekly_commits = []
                for week in metrics['temporal_patterns']['active_weeks']:
                    weekly_commits.append(commits_by_week.get(week, {}).get(author_key, 0))
                
                if len(weekly_commits) > 1:
                    cv = np.std(weekly_commits) / max(1, np.mean(weekly_commits))
                    metrics['velocity']['commit_consistency'] = max(0, 1 - cv)  # Higher = more consistent
            
            # Calculate average lines per commit
            if metrics['velocity']['lines_per_commit']:
                avg_lines = np.mean(metrics['velocity']['lines_per_commit'])
                metrics['velocity']['lines_per_commit'] = avg_lines
            
            # Calculate work pattern
            if metrics['temporal_patterns']['commit_hours']:
                hours = metrics['temporal_patterns']['commit_hours']
                avg_hour = np.mean(hours)
                if 6 <= avg_hour <= 18:
                    metrics['temporal_patterns']['work_pattern'] = 'business_hours'
                elif 18 <= avg_hour <= 22:
                    metrics['temporal_patterns']['work_pattern'] = 'evening'
                else:
                    metrics['temporal_patterns']['work_pattern'] = 'flexible'
            
            # Calculate quality score
            total_commits = metrics['contributions']['commits']
            if total_commits > 0:
                quality_commits = (metrics['quality_indicators']['feature_additions'] +
                                 metrics['quality_indicators']['test_commits'] +
                                 metrics['quality_indicators']['documentation_commits'])
                metrics['quality_indicators']['quality_score'] = (quality_commits / total_commits) * 100
            
            # Calculate collaboration metrics
            metrics['collaboration']['knowledge_sharing'] = len(metrics['collaboration']['files_shared'])
            
            # Calculate productivity score (composite metric)
            productivity_components = [
                min(100, metrics['contributions']['commits'] * 2),  # Commit volume
                min(100, metrics['velocity']['commit_consistency'] * 100),  # Consistency
                min(100, metrics['quality_indicators']['quality_score']),  # Quality
                min(100, len(metrics['collaboration']['collaborators']) * 10)  # Collaboration
            ]
            metrics['velocity']['productivity_score'] = np.mean(productivity_components)
        
        # Convert to DataFrame
        contribution_data = []
        for author_key, metrics in developer_metrics.items():
            if metrics['contributions']['commits'] == 0:
                continue
            
            # Determine primary expertise
            if metrics['expertise_areas']:
                primary_expertise = max(metrics['expertise_areas'].items(), key=lambda x: x[1])[0]
                expertise_percentage = (metrics['expertise_areas'][primary_expertise] / 
                                      sum(metrics['expertise_areas'].values())) * 100
            else:
                primary_expertise = 'unknown'
                expertise_percentage = 0
            
            contribution_data.append({
                'Developer': author_key,
                'Total_Commits': metrics['contributions']['commits'],
                'Unique_Files_Touched': len(metrics['contributions']['unique_files']),
                'Lines_Added_Est': metrics['contributions']['lines_added'],
                'Pull_Requests_Created': metrics['contributions']['pull_requests_created'],
                'Pull_Requests_Reviewed': metrics['contributions']['pull_requests_reviewed'],
                'Commits_Per_Week': round(metrics['velocity'].get('commits_per_week', 0), 2),
                'Avg_Lines_Per_Commit': round(metrics['velocity'].get('lines_per_commit', 0), 1),
                'Commit_Consistency': round(metrics['velocity']['commit_consistency'], 2),
                'Productivity_Score': round(metrics['velocity']['productivity_score'], 1),
                'Collaborators': len(metrics['collaboration']['collaborators']),
                'Knowledge_Sharing_Score': metrics['collaboration']['knowledge_sharing'],
                'Review_Participation': metrics['collaboration']['review_participation'],
                'Quality_Score': round(metrics['quality_indicators']['quality_score'], 1),
                'Feature_Commits': metrics['quality_indicators']['feature_additions'],
                'Bug_Fix_Commits': metrics['quality_indicators']['defect_fixes'],
                'Test_Commits': metrics['quality_indicators']['test_commits'],
                'Refactoring_Commits': metrics['quality_indicators']['refactoring_commits'],
                'Critical_File_Changes': metrics['impact_metrics']['critical_file_changes'],
                'Primary_Expertise': f"{primary_expertise} ({expertise_percentage:.0f}%)",
                'Work_Pattern': metrics['temporal_patterns']['work_pattern'],
                'Active_Weeks': len(metrics['temporal_patterns']['active_weeks'])
            })
        
        df_advanced_contributions = pd.DataFrame(contribution_data)
        if not df_advanced_contributions.empty:
            df_advanced_contributions = df_advanced_contributions.sort_values('Productivity_Score', ascending=False)
            
            print(df_advanced_contributions.to_string(index=False))
            df_advanced_contributions.to_csv(f"{self.base_analyzer.data_dir}/azdo_advanced_developer_contributions.csv", index=False)
        
        return df_advanced_contributions
