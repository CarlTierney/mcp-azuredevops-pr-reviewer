#!/usr/bin/env python3
"""
Commit Timing Analysis Module
"""

import pandas as pd
import numpy as np
import statistics
import sys
import os
from datetime import datetime
from collections import defaultdict

# Ensure we can import from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class TimingAnalyzer:
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
    
    def analyze_commit_timing(self):
        """Analyze calendar time between commits and commit patterns"""
        print("\n=== COMMIT TIMING ANALYSIS ===")
        
        # Sort commits by date
        commits_with_dates = []
        for commit in self.base_analyzer.commits:
            author_info = self.base_analyzer.get_author_info(commit.get('author', {}))
            author_key = author_info['unique_name']
            
            try:
                # Extract commit date
                commit_date_str = commit.get('author', {}).get('date', '')
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00')) if commit_date_str else None
                
                if commit_date:
                    commits_with_dates.append({
                        'commit_id': commit.get('commitId', ''),
                        'author': author_key,
                        'date': commit_date,
                        'comment': commit.get('comment', '')
                    })
            except (ValueError, AttributeError):
                continue
        
        # Sort by date
        commits_with_dates.sort(key=lambda x: x['date'])
        
        # Calculate time between commits by author
        author_timing_data = defaultdict(list)
        author_first_commits = {}
        author_last_commits = {}
        author_commit_days = defaultdict(set)  # Track unique days with commits
        
        for i, commit in enumerate(commits_with_dates):
            author = commit['author']
            commit_date = commit['date']
            
            # Track first and last commit date by author
            if author not in author_first_commits:
                author_first_commits[author] = commit_date
            author_last_commits[author] = commit_date
            
            # Track unique days with commits
            commit_day = commit_date.date()
            author_commit_days[author].add(commit_day)
            
            # Find previous commit by same author
            prev_date = None
            for j in range(i-1, -1, -1):
                if commits_with_dates[j]['author'] == author:
                    prev_date = commits_with_dates[j]['date']
                    break
                    
            if prev_date:
                time_diff = (commit_date - prev_date).total_seconds() / 3600  # Hours
                author_timing_data[author].append(time_diff)
        
        # Calculate timing metrics
        timing_data = []
        for author, time_diffs in author_timing_data.items():
            if not time_diffs:
                continue
                
            total_commits = len(time_diffs) + 1  # Add 1 for first commit
            active_days = len(author_commit_days[author])
            first_commit = author_first_commits[author]
            last_commit = author_last_commits[author]
            
            # Calculate total active period in days
            active_period_days = (last_commit - first_commit).days + 1
            
            # Calculate commit frequency
            commits_per_day = total_commits / max(1, active_period_days)
            commits_per_active_day = total_commits / max(1, active_days)
            
            # Calculate average and median time between commits
            avg_hours_between_commits = sum(time_diffs) / max(1, len(time_diffs))
            median_hours_between_commits = statistics.median(time_diffs) if time_diffs else 0
            
            # Calculate "working hours" percentage (commits during 9 AM - 5 PM on weekdays)
            business_hours_commits = 0
            weekend_commits = 0
            night_commits = 0
            
            for commit in commits_with_dates:
                if commit['author'] == author:
                    dt = commit['date']
                    is_weekend = dt.weekday() >= 5  # 5=Saturday, 6=Sunday
                    is_business_hours = 9 <= dt.hour < 17
                    is_night = dt.hour < 6 or dt.hour >= 22
                    
                    if is_weekend:
                        weekend_commits += 1
                    if is_business_hours and not is_weekend:
                        business_hours_commits += 1
                    if is_night:
                        night_commits += 1
            
            business_hours_pct = (business_hours_commits / total_commits) * 100
            weekend_pct = (weekend_commits / total_commits) * 100
            night_pct = (night_commits / total_commits) * 100
            
            timing_data.append({
                'Developer': author,
                'Total_Commits': total_commits,
                'Active_Days': active_days,
                'Active_Period_Days': active_period_days,
                'Commits_Per_Day': round(commits_per_day, 2),
                'Commits_Per_Active_Day': round(commits_per_active_day, 2),
                'Avg_Hours_Between_Commits': round(avg_hours_between_commits, 2),
                'Median_Hours_Between_Commits': round(median_hours_between_commits, 2),
                'Business_Hours_Commits_Pct': round(business_hours_pct, 1),
                'Weekend_Commits_Pct': round(weekend_pct, 1),
                'Night_Commits_Pct': round(night_pct, 1),
                'First_Commit': first_commit.strftime('%Y-%m-%d'),
                'Last_Commit': last_commit.strftime('%Y-%m-%d')
            })
        
        df_timing = pd.DataFrame(timing_data)
        if not df_timing.empty:
            df_timing = df_timing.sort_values('Total_Commits', ascending=False)
            
            print(df_timing.to_string(index=False))
            df_timing.to_csv(f"{self.base_analyzer.data_dir}/azdo_commit_timing_metrics.csv", index=False)
        
        return df_timing
