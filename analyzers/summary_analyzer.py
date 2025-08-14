"""
Summary Report Analyzer
Generates comprehensive summary report combining all analysis results
"""

import pandas as pd
import os
from datetime import datetime
import json
import glob


class SummaryAnalyzer:
    """Generates comprehensive summary report from all analysis outputs"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        
    def generate_enhanced_summary_report(self):
        """Generate comprehensive summary report combining all metrics"""
        print("\n[SUMMARY] Generating Enhanced Summary Report...")
        
        summary_rows = []
        
        # 1. Repository Overview
        summary_rows.append({
            'Category': 'Repository Overview',
            'Metric': 'Analysis Date',
            'Value': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Details': f"Analysis period: {self.analyzer.date_from} to {self.analyzer.date_to}"
        })
        
        summary_rows.append({
            'Category': 'Repository Overview',
            'Metric': 'Organization',
            'Value': self.analyzer.org_name,
            'Details': f"Project: {self.analyzer.project_name}, Repo: {self.analyzer.repo_name}"
        })
        
        summary_rows.append({
            'Category': 'Repository Overview',
            'Metric': 'Total Commits',
            'Value': len(self.analyzer.commits),
            'Details': f"Detailed commits analyzed: {len(self.analyzer.detailed_commits)}"
        })
        
        # 2. Developer Metrics
        contrib_file = f"{self.analyzer.data_dir}/azdo_contribution_metrics.csv"
        if os.path.exists(contrib_file):
            df_contrib = pd.read_csv(contrib_file)
            
            summary_rows.append({
                'Category': 'Developer Activity',
                'Metric': 'Active Developers',
                'Value': len(df_contrib),
                'Details': f"Contributors with commits in analysis period"
            })
            
            if not df_contrib.empty:
                top_contributor = df_contrib.iloc[0]
                summary_rows.append({
                    'Category': 'Developer Activity',
                    'Metric': 'Top Contributor',
                    'Value': top_contributor['Developer'],
                    'Details': f"Score: {top_contributor.get('Overall_Contribution_Score', 'N/A')}/100"
                })
                
                if 'Overall_Contribution_Score' in df_contrib.columns:
                    avg_score = df_contrib['Overall_Contribution_Score'].mean()
                    summary_rows.append({
                        'Category': 'Developer Activity',
                        'Metric': 'Average Contribution Score',
                        'Value': f"{avg_score:.1f}",
                        'Details': f"Standard deviation: {df_contrib['Overall_Contribution_Score'].std():.1f}"
                    })
        
        # 3. Code Quality Metrics
        quality_file = f"{self.analyzer.data_dir}/azdo_enhanced_quality_metrics.csv"
        if os.path.exists(quality_file):
            df_quality = pd.read_csv(quality_file)
            if not df_quality.empty and 'Quality_Score' in df_quality.columns:
                latest_quality = df_quality.iloc[-1]
                summary_rows.append({
                    'Category': 'Code Quality',
                    'Metric': 'Latest Quality Score',
                    'Value': f"{latest_quality['Quality_Score']:.1f}",
                    'Details': f"Month: {latest_quality.get('Month', 'N/A')}"
                })
                
                avg_quality = df_quality['Quality_Score'].mean()
                summary_rows.append({
                    'Category': 'Code Quality',
                    'Metric': 'Average Quality Score',
                    'Value': f"{avg_quality:.1f}",
                    'Details': f"Trend: {self._calculate_trend(df_quality, 'Quality_Score')}"
                })
        
        # 4. Language Complexity
        lang_file = f"{self.analyzer.data_dir}/azdo_language_complexity.csv"
        if os.path.exists(lang_file):
            df_lang = pd.read_csv(lang_file)
            
            summary_rows.append({
                'Category': 'Language Analysis',
                'Metric': 'Languages Used',
                'Value': len(df_lang),
                'Details': ', '.join(df_lang['Language_Type'].head(5).tolist()) if not df_lang.empty else 'N/A'
            })
            
            if 'Unique_Files' in df_lang.columns:
                total_files = df_lang['Unique_Files'].sum()
                summary_rows.append({
                    'Category': 'Language Analysis',
                    'Metric': 'Total Unique Files',
                    'Value': total_files,
                    'Details': f"Across {len(df_lang)} language types"
                })
            
            if not df_lang.empty and 'Risk_Score' in df_lang.columns:
                highest_risk = df_lang.loc[df_lang['Risk_Score'].idxmax()]
                summary_rows.append({
                    'Category': 'Language Analysis',
                    'Metric': 'Highest Risk Language',
                    'Value': highest_risk['Language_Type'],
                    'Details': f"Risk Score: {highest_risk['Risk_Score']:.2f}"
                })
        
        # 5. Hotspot Analysis
        hotspot_file = f"{self.analyzer.data_dir}/azdo_file_hotspots_analysis.csv"
        if os.path.exists(hotspot_file):
            df_hotspots = pd.read_csv(hotspot_file)
            
            summary_rows.append({
                'Category': 'Risk Analysis',
                'Metric': 'Files Analyzed',
                'Value': len(df_hotspots),
                'Details': 'Total files with commit activity'
            })
            
            if 'Is_Critical' in df_hotspots.columns:
                critical_files = df_hotspots['Is_Critical'].sum()
                summary_rows.append({
                    'Category': 'Risk Analysis',
                    'Metric': 'Critical Files',
                    'Value': critical_files,
                    'Details': f"{(critical_files/len(df_hotspots)*100):.1f}% of total files"
                })
            
            if 'Bus_Factor_Risk' in df_hotspots.columns:
                high_risk_files = (df_hotspots['Bus_Factor_Risk'] >= 3.0).sum()
                summary_rows.append({
                    'Category': 'Risk Analysis',
                    'Metric': 'High Bus Factor Risk',
                    'Value': high_risk_files,
                    'Details': f"Files with risk score >= 3.0"
                })
        
        # 6. Bus Factor Analysis
        bus_factor_file = f"{self.analyzer.data_dir}/azdo_bus_factor_analysis.csv"
        if os.path.exists(bus_factor_file):
            df_bus = pd.read_csv(bus_factor_file)
            
            if 'Bus_Factor_Risk' in df_bus.columns:
                high_risk_devs = (df_bus['Bus_Factor_Risk'] >= 3.0).sum()
                summary_rows.append({
                    'Category': 'Bus Factor',
                    'Metric': 'High Risk Developers',
                    'Value': high_risk_devs,
                    'Details': f"Developers who are single points of failure"
                })
                
                avg_risk = df_bus['Bus_Factor_Risk'].mean()
                summary_rows.append({
                    'Category': 'Bus Factor',
                    'Metric': 'Average Bus Factor Risk',
                    'Value': f"{avg_risk:.2f}",
                    'Details': f"Scale: 1 (low) to 5 (critical)"
                })
        
        # 7. Pull Request Metrics
        pr_file = f"{self.analyzer.data_dir}/azdo_pull_request_metrics.csv"
        if os.path.exists(pr_file):
            df_pr = pd.read_csv(pr_file)
            
            summary_rows.append({
                'Category': 'Pull Requests',
                'Metric': 'Total PRs',
                'Value': len(df_pr),
                'Details': 'Pull requests in analysis period'
            })
            
            if 'Duration_Days' in df_pr.columns and not df_pr.empty:
                avg_duration = df_pr['Duration_Days'].mean()
                summary_rows.append({
                    'Category': 'Pull Requests',
                    'Metric': 'Average PR Duration',
                    'Value': f"{avg_duration:.1f} days",
                    'Details': f"Median: {df_pr['Duration_Days'].median():.1f} days"
                })
        
        # 8. Productivity Metrics
        prod_file = f"{self.analyzer.data_dir}/azdo_productivity_metrics.csv"
        if os.path.exists(prod_file):
            df_prod = pd.read_csv(prod_file)
            
            if 'Productivity_Score' in df_prod.columns and not df_prod.empty:
                top_productive = df_prod.nlargest(1, 'Productivity_Score').iloc[0]
                summary_rows.append({
                    'Category': 'Productivity',
                    'Metric': 'Most Productive Developer',
                    'Value': top_productive['Developer'],
                    'Details': f"Score: {top_productive['Productivity_Score']:.1f}"
                })
                
                avg_prod = df_prod['Productivity_Score'].mean()
                summary_rows.append({
                    'Category': 'Productivity',
                    'Metric': 'Average Productivity',
                    'Value': f"{avg_prod:.1f}",
                    'Details': f"Across {len(df_prod)} developers"
                })
        
        # 9. Repository Health
        health_file = f"{self.analyzer.data_dir}/azdo_repository_health_trends.csv"
        if os.path.exists(health_file):
            df_health = pd.read_csv(health_file)
            
            if not df_health.empty and 'Health_Score' in df_health.columns:
                latest_health = df_health.iloc[-1]
                summary_rows.append({
                    'Category': 'Repository Health',
                    'Metric': 'Current Health Score',
                    'Value': f"{latest_health['Health_Score']:.1f}",
                    'Details': f"Month: {latest_health.get('Month', 'N/A')}"
                })
                
                health_trend = self._calculate_trend(df_health, 'Health_Score')
                summary_rows.append({
                    'Category': 'Repository Health',
                    'Metric': 'Health Trend',
                    'Value': health_trend,
                    'Details': f"Based on last 3 months"
                })
        
        # Convert to DataFrame and save
        df_summary = pd.DataFrame(summary_rows)
        
        # Save as CSV
        output_file = f"{self.analyzer.data_dir}/azdo_enhanced_summary_report.csv"
        df_summary.to_csv(output_file, index=False)
        print(f"[OK] Enhanced summary report saved to: {output_file}")
        
        # Also save as JSON for programmatic access
        json_file = f"{self.analyzer.data_dir}/azdo_enhanced_summary_report.json"
        summary_dict = {}
        for _, row in df_summary.iterrows():
            category = row['Category']
            if category not in summary_dict:
                summary_dict[category] = {}
            summary_dict[category][row['Metric']] = {
                'value': row['Value'],
                'details': row['Details']
            }
        
        with open(json_file, 'w') as f:
            json.dump(summary_dict, f, indent=2, default=str)
        print(f"[OK] Summary JSON saved to: {json_file}")
        
        # Print summary to console
        self._print_summary(df_summary)
        
        return df_summary
    
    def _calculate_trend(self, df, column):
        """Calculate trend for a metric"""
        if len(df) < 2:
            return "Insufficient data"
        
        # Get last 3 values or all if less than 3
        recent_values = df[column].tail(3).tolist()
        
        if len(recent_values) >= 2:
            change = recent_values[-1] - recent_values[0]
            pct_change = (change / recent_values[0] * 100) if recent_values[0] != 0 else 0
            
            if pct_change > 5:
                return f"Improving (+{pct_change:.1f}%)"
            elif pct_change < -5:
                return f"Declining ({pct_change:.1f}%)"
            else:
                return f"Stable ({pct_change:+.1f}%)"
        
        return "Stable"
    
    def _print_summary(self, df_summary):
        """Print formatted summary to console"""
        print("\n" + "=" * 70)
        print("ENHANCED ANALYSIS SUMMARY")
        print("=" * 70)
        
        current_category = None
        for _, row in df_summary.iterrows():
            if row['Category'] != current_category:
                current_category = row['Category']
                print(f"\n[{current_category.upper()}]")
            
            print(f"  {row['Metric']}: {row['Value']}")
            if row['Details'] and row['Details'] != 'N/A':
                print(f"    Details: {row['Details']}")
        
        print("\n" + "=" * 70)