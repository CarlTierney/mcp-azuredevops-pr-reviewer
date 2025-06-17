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