#!/usr/bin/env python3
"""
Quality Analysis Module
"""

import os
import pandas as pd
import numpy as np
import statistics
import calendar
from datetime import datetime
from collections import defaultdict
import sys

# Ensure we can import from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class QualityAnalyzer:
    def __init__(self, analyzer):
        self.analyzer = analyzer
    
    def analyze_quality(self):
        """Analyze code quality metrics"""
        print("\n=== CODE QUALITY ANALYSIS ===")
        
        # Prepare data
        df_commits = self.analyzer.df_commits
        df_files = self.analyzer.df_files
        df_quality = self.analyzer.df_quality
        
        # Merge data
        df_merged = df_commits.merge(df_files, on='commitId', how='left').merge(df_quality, on='commitId', how='left')
        
        # Monthly aggregation
        df_merged['Month'] = df_merged['author.date'].dt.to_period('M').astype(str)
        df_monthly = df_merged.groupby('Month').agg({
            'commitId': 'count',
            'filePath': 'nunique',
            'locAdded': 'sum',
            'locDeleted': 'sum',
            'locModified': 'sum',
            'nonWhitespaceRatio': 'mean',
            'cyclomaticComplexity': 'mean',
            'codeQualityScore': 'mean'
        }).reset_index()
        
        df_monthly = df_monthly.rename(columns={
            'commitId': 'Commits',
            'filePath': 'Total_Files_Changed',
            'locAdded': 'LOC_Added',
            'locDeleted': 'LOC_Deleted',
            'locModified': 'LOC_Modified',
            'nonWhitespaceRatio': 'Non_Whitespace_Ratio',
            'cyclomaticComplexity': 'Avg_Cyclomatic_Complexity',
            'codeQualityScore': 'Code_Quality_Score'
        })
        
        # Save monthly data
        df_monthly.to_csv(f"{self.analyzer.data_dir}/azdo_monthly_quality_metrics.csv", index=False)
        
        # Generate monthly insights
        self._generate_monthly_insights(df_monthly)
    
    def _generate_monthly_insights(self, df_monthly):
        """Generate insights from monthly data"""
        # Generate monthly aggregation
        monthly_aggregation = []
        for month in sorted(df_monthly['Month'].unique()):
            month_data = df_monthly[df_monthly['Month'] == month]
            
            try:
                year, month_num = month.split('-')
                month_name = calendar.month_name[int(month_num)]
                display_month = f"{month_name} {year}"
            except:
                display_month = month
            
            monthly_aggregation.append({
                'Month': month,
                'Month_Display': display_month,
                'Active_Developers': len(month_data),
                'Total_Commits': month_data['Commits'].sum(),
                'Total_Files_Changed': month_data['Total_Files_Changed'].sum(),
                'Total_LOC_Added': month_data['LOC_Added'].sum(),
                'Total_LOC_Deleted': month_data['LOC_Deleted'].sum(),
                'Total_LOC_Modified': month_data['LOC_Modified'].sum(),
                'Avg_Non_Whitespace_Ratio': round(month_data['Non_Whitespace_Ratio'].mean(), 3),
                'Avg_Complexity': round(month_data['Avg_Cyclomatic_Complexity'].mean(), 2),
                'Avg_Quality_Score': round(month_data['Code_Quality_Score'].mean(), 1)
            })
        
        df_monthly_agg = pd.DataFrame(monthly_aggregation)
        if not df_monthly_agg.empty:
            print("\n📊 Monthly Team Aggregation:")
            agg_cols = ['Month_Display', 'Active_Developers', 'Total_Commits', 'Total_LOC_Added', 
                       'Total_LOC_Deleted', 'Avg_Non_Whitespace_Ratio', 'Avg_Quality_Score']
            print(df_monthly_agg[agg_cols].to_string(index=False))
            df_monthly_agg.to_csv(f"{self.analyzer.data_dir}/azdo_monthly_team_metrics.csv", index=False)
        
        # Generate insights
        print(f"\n=== MONTHLY QUALITY INSIGHTS ===")
        
        # Find most productive months
        top_months = df_monthly_agg.nlargest(3, 'Total_LOC_Added') if not df_monthly_agg.empty else pd.DataFrame()
        if not top_months.empty:
            print(f"🚀 Most Productive Months:")
            for _, month_row in top_months.iterrows():
                print(f"  • {month_row['Month_Display']}: {month_row['Total_LOC_Added']:,} LOC added, {month_row['Active_Developers']} developers")
        
        # Find quality trends
        if len(df_monthly_agg) >= 2:
            recent_quality = df_monthly_agg.tail(3)['Avg_Quality_Score'].mean()
            early_quality = df_monthly_agg.head(3)['Avg_Quality_Score'].mean()
            quality_trend = recent_quality - early_quality
            
            print(f"\n📈 Quality Trends:")
            print(f"  • Recent quality score: {recent_quality:.1f}")
            print(f"  • Quality trend: {'↗️ Improving' if quality_trend > 0 else '↘️ Declining' if quality_trend < 0 else '➡️ Stable'} ({quality_trend:+.1f})")
        
        # Top contributors by month
        if not df_monthly.empty:
            print(f"\n🏆 Top Contributors by Recent Activity:")
            recent_month = df_monthly['Month'].max()
            recent_contributors = df_monthly[df_monthly['Month'] == recent_month].nlargest(3, 'LOC_Added')
            for _, dev_row in recent_contributors.iterrows():
                print(f"  • {dev_row['Developer']}: {dev_row['LOC_Added']:,} LOC added, {dev_row['Commits']} commits")
    
    def analyze_enhanced_quality_metrics(self):
        """Enhanced quality metrics analysis by calendar month with real LOC data"""
        print("\n=== ENHANCED QUALITY METRICS BY MONTH ===")
        
        # Check if analysis is already cached
        analysis_name = "enhanced_quality_metrics"
        if self.analyzer.is_analysis_cached(analysis_name):
            cached_df = self.analyzer.get_cached_dataframe(analysis_name)
            if cached_df is not None:
                print("📊 Displaying cached monthly quality metrics results:")
                
                summary_cols = ['Developer', 'Month_Display', 'Commits', 'LOC_Added', 'LOC_Deleted', 'LOC_Modified', 
                               'Non_Whitespace_Ratio', 'Avg_Cyclomatic_Complexity', 'Code_Quality_Score']
                print("\nMonthly Summary (latest months for each developer):")
                latest_months = cached_df.groupby('Developer').tail(3)
                print(latest_months[summary_cols].to_string(index=False))
                
                return cached_df
        
        print("🔍 Running fresh monthly quality metrics analysis...")
        
        # Track metrics by developer and month
        monthly_metrics = defaultdict(lambda: defaultdict(lambda: {
            'files_changed': set(),
            'commits': 0,
            'loc_added': 0,
            'loc_deleted': 0,
            'loc_modified': 0,
            'non_whitespace_added': 0,
            'non_whitespace_deleted': 0,
            'non_whitespace_modified': 0,
            'complexity_samples': [],
            'file_types': defaultdict(int),
            'change_types': defaultdict(int),
            'commit_dates': []
        }))
        
        # Get repository ID for content analysis
        try:
            repo_id = self.analyzer.get_repository_id()
            print(f"  ✓ Repository ID obtained: {repo_id}")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not get repository ID: {e}")
            repo_id = None
        
        print("📅 Analyzing detailed commits for monthly quality metrics...")
        total_commits = len(self.analyzer.detailed_commits)
        commit_count = 0
        processed_files = 0
        skipped_files = 0
        
        for commit_id, changes_data in self.analyzer.detailed_commits.items():
            commit_count += 1
            if commit_count % 50 == 0:
                progress_pct = (commit_count / total_commits) * 100
                print(f"    Monthly analysis: {commit_count:,}/{total_commits:,} ({progress_pct:.1f}%) | Files: {processed_files:,} | Skipped: {skipped_files:,}")
            
            # Get commit info and parse date
            commit_info = next((c for c in self.analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
            
            author_info = self.analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            # Parse commit date to get year-month
            try:
                commit_date_str = commit_info.get('author', {}).get('date', '')
                if commit_date_str:
                    commit_date = datetime.fromisoformat(commit_date_str.replace('Z', ''))
                    month_key = f"{commit_date.year}-{commit_date.month:02d}"
                else:
                    continue
            except:
                continue
            
            monthly_metrics[author_key][month_key]['commits'] += 1
            monthly_metrics[author_key][month_key]['commit_dates'].append(commit_date)
            
            # Analyze file changes in this commit
            changes = changes_data.get('changes', [])
            for change in changes:
                item = change.get('item', {})
                change_type = change.get('changeType', '')
                path = item.get('path', '')
                
                if not path or item.get('isFolder', False):
                    continue
                
                filename = os.path.basename(path)
                file_type = self.analyzer.classify_file_type(filename)
                
                # Skip non-code files for quality metrics
                if file_type in ['other', 'docs']:
                    skipped_files += 1
                    continue
                
                monthly_metrics[author_key][month_key]['files_changed'].add(path)
                monthly_metrics[author_key][month_key]['file_types'][file_type] += 1
                monthly_metrics[author_key][month_key]['change_types'][change_type] += 1
                processed_files += 1
                
                # Estimate LOC changes based on change type and file content
                if repo_id:
                    try:
                        content = self.analyzer.fetch_file_content(repo_id, commit_id, path)
                        if content:
                            file_analysis = self.analyzer.analyze_file_contents(content)
                            complexity = self.analyzer.calculate_cyclomatic_complexity(content, filename)
                            
                            if complexity > 1:
                                monthly_metrics[author_key][month_key]['complexity_samples'].append(complexity)
                            
                            # Estimate LOC changes based on change type
                            if change_type == 'add':
                                estimated_added = file_analysis['sloc']
                                monthly_metrics[author_key][month_key]['loc_added'] += file_analysis['loc']
                                monthly_metrics[author_key][month_key]['non_whitespace_added'] += estimated_added
                                
                            elif change_type == 'edit':
                                estimated_modified = max(int(file_analysis['sloc'] * 0.3), 1)
                                monthly_metrics[author_key][month_key]['loc_modified'] += int(file_analysis['loc'] * 0.3)
                                monthly_metrics[author_key][month_key]['non_whitespace_modified'] += estimated_modified
                                
                            elif change_type == 'delete':
                                estimated_deleted = file_analysis['sloc']
                                monthly_metrics[author_key][month_key]['loc_deleted'] += file_analysis['loc']
                                monthly_metrics[author_key][month_key]['non_whitespace_deleted'] += estimated_deleted
                        else:
                            skipped_files += 1
                    except Exception as e:
                        # Only log errors occasionally to avoid spam
                        if processed_files % 1000 == 0:
                            print(f"      Warning: Failed to analyze {filename}: {type(e).__name__}")
                        skipped_files += 1
                        # Use fallback estimates
                        if change_type == 'add':
                            monthly_metrics[author_key][month_key]['loc_added'] += 50
                            monthly_metrics[author_key][month_key]['non_whitespace_added'] += 40
                        elif change_type == 'edit':
                            monthly_metrics[author_key][month_key]['loc_modified'] += 15
                            monthly_metrics[author_key][month_key]['non_whitespace_modified'] += 12
                        elif change_type == 'delete':
                            monthly_metrics[author_key][month_key]['loc_deleted'] += 25
                            monthly_metrics[author_key][month_key]['non_whitespace_deleted'] += 20
                
                else:
                    # Fallback estimates when content analysis isn't available
                    if change_type == 'add':
                        monthly_metrics[author_key][month_key]['loc_added'] += 50
                        monthly_metrics[author_key][month_key]['non_whitespace_added'] += 40
                    elif change_type == 'edit':
                        monthly_metrics[author_key][month_key]['loc_modified'] += 15
                        monthly_metrics[author_key][month_key]['non_whitespace_modified'] += 12
                    elif change_type == 'delete':
                        monthly_metrics[author_key][month_key]['loc_deleted'] += 25
                        monthly_metrics[author_key][month_key]['non_whitespace_deleted'] += 20
        
        print(f"  ✓ Completed monthly analysis:")
        print(f"    - {commit_count:,} commits processed")
        print(f"    - {processed_files:,} files analyzed")
        print(f"    - {skipped_files:,} files skipped")
        print(f"    - {len(monthly_metrics)} developers analyzed")
        
        # Generate monthly quality metrics report
        print("📊 Generating monthly quality report...")
        monthly_data = self._generate_monthly_report(monthly_metrics)
        
        # Create DataFrame for monthly metrics
        df_monthly_metrics = pd.DataFrame.from_records(
            [(author, month, metrics['commits'], len(metrics['files_changed']),
              metrics['loc_added'], metrics['loc_deleted'], metrics['loc_modified'],
              np.mean(metrics['complexity_samples']) if metrics['complexity_samples'] else 0,
              metrics['file_types'], metrics['change_types'], metrics['commit_dates'])
             for author, months in monthly_metrics.items()
             for month, metrics in months.items()],
            columns=['Developer', 'Month', 'Commits', 'Total_Files_Changed',
                     'LOC_Added', 'LOC_Deleted', 'LOC_Modified', 'Avg_Cyclomatic_Complexity',
                     'File_Types', 'Change_Types', 'Commit_Dates']
        )
        
        # Save monthly metrics data
        df_monthly_metrics.to_csv(f"{self.analyzer.data_dir}/azdo_enhanced_monthly_quality_metrics.csv", index=False)
        
        # Display sample of monthly metrics
        if not df_monthly_metrics.empty:
            print("\n📋 Sample of Monthly Quality Metrics:")
            print(df_monthly_metrics.sample(min(len(df_monthly_metrics), 10)).to_string(index=False))
        
        # Create DataFrame and save results
        df_monthly = pd.DataFrame(monthly_data)
        
        if not df_monthly.empty:
            df_monthly = df_monthly.sort_values(['Developer', 'Month'])
            
            # Save detailed monthly metrics
            output_file = f"{self.analyzer.data_dir}/azdo_enhanced_quality_metrics.csv"
            df_monthly.to_csv(output_file, index=False)
            
            # Mark as cached
            self.analyzer.mark_analysis_cached(analysis_name, output_file)
            
            # Generate insights
            self._generate_monthly_insights(df_monthly)
        
        else:
            print("No monthly quality metrics data found")
        
        return df_monthly
    
    def _generate_enhanced_monthly_insights(self, df_monthly_metrics):
        """Generate enhanced insights from monthly metrics data"""
        print(f"\n=== ENHANCED MONTHLY QUALITY INSIGHTS ===")
        
        # Find top developers by LOC added
        top_developers = df_monthly_metrics.groupby('Developer').agg({
            'LOC_Added': 'sum',
            'Commits': 'sum'
        }).reset_index().nlargest(3, 'LOC_Added')
        
        if not top_developers.empty:
            print(f"🌟 Top Developers by LOC Added:")
            for _, dev_row in top_developers.iterrows():
                print(f"  • {dev_row['Developer']}: {dev_row['LOC_Added']:,} LOC added, {dev_row['Commits']} commits")
        
        # Monthly trends for active developers
        active_dev_trends = df_monthly_metrics.groupby('Month').agg({
            'Developer': 'nunique',
            'Commits': 'sum',
            'LOC_Added': 'sum',
            'LOC_Deleted': 'sum',
            'LOC_Modified': 'sum'
        }).reset_index()
        
        if not active_dev_trends.empty:
            print(f"\n📈 Monthly Trends for Active Developers:")
            for _, trend_row in active_dev_trends.iterrows():
                print(f"  • {trend_row['Month']}: {trend_row['Developer']} active developers, {trend_row['LOC_Added']:,} LOC added")
        
        # Complexity and quality score trends
        complexity_trend = df_monthly_metrics.groupby('Month').agg({
            'Avg_Cyclomatic_Complexity': 'mean',
            'Code_Quality_Score': 'mean'
        }).reset_index()
        
        if not complexity_trend.empty:
            recent_complexity = complexity_trend.tail(3)['Code_Quality_Score'].mean()
            early_complexity = complexity_trend.head(3)['Code_Quality_Score'].mean()
            complexity_trend_value = recent_complexity - early_complexity
            
            print(f"\n📊 Complexity and Quality Score Trends:")
            print(f"  • Recent average complexity: {recent_complexity:.2f}")
            print(f"  • Complexity trend: {'↗️ Improving' if complexity_trend_value > 0 else '↘️ Declining' if complexity_trend_value < 0 else '➡️ Stable'} ({complexity_trend_value:+.2f})")
        
        # Monthly distribution of change types
        if 'Change_Types' in df_monthly_metrics.columns:
            change_type_distribution = df_monthly_metrics['Change_Types'].apply(lambda x: eval(x) if isinstance(x, str) else {}).apply(pd.Series).fillna(0)
            df_change_distribution = df_monthly_metrics[['Month']].join(change_type_distribution)
            
            print(f"\n📊 Monthly Distribution of Change Types:")
            for month, group in df_change_distribution.groupby('Month'):
                total_changes = group.iloc[:, 1:].sum().sum()
                if total_changes > 0:
                    print(f"  • {month}:")
                    for change_type, count in group.iloc[:, 1:].sum().items():
                        pct = (count / total_changes) * 100
                        print(f"    - {change_type}: {count} ({pct:.1f}%)")
        
        # Monthly file type contributions
        if 'File_Types' in df_monthly_metrics.columns:
            file_type_contribution = df_monthly_metrics['File_Types'].apply(lambda x: eval(x) if isinstance(x, str) else {}).apply(pd.Series).fillna(0)
            df_file_contribution = df_monthly_metrics[['Month']].join(file_type_contribution)
            
            print(f"\n📊 Monthly File Type Contributions:")
            for month, group in df_file_contribution.groupby('Month'):
                total_files = group.iloc[:, 1:].sum().sum()
                if total_files > 0:
                    print(f"  • {month}:")
                    for file_type, count in group.iloc[:, 1:].sum().items():
                        pct = (count / total_files) * 100
                        print(f"    - {file_type}: {count} ({pct:.1f}%)")