"""
Bus Factor and Hotspots Analysis Module
"""

import os
import pandas as pd
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Ensure we can import from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class HotspotAnalyzer:
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer

    def analyze_bus_factor_and_hotspots(self):
        """Analyze bus factor and hotspots for ALL repository files"""
        print("\n=== BUS FACTOR & HOTSPOTS ANALYSIS ===")
        
        # Track metrics for each file and developer
        file_metrics = defaultdict(lambda: {
            'developers': set(),
            'total_commits': 0,
            'total_changes': 0,
            'recent_commits': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'complexity_score': 0,
            'last_modified': None,
            'file_size_estimate': 0,
            'change_frequency': 0
        })
        
        developer_metrics = defaultdict(lambda: {
            'files_owned': set(),
            'total_commits': 0,
            'total_file_changes': 0,
            'ownership_percentage': 0,
            'specialization_files': set()
        })
        
        # Analyze all detailed commits to build file and developer metrics
        print("Analyzing file changes across all commits...")
        total_commits = len(self.analyzer.detailed_commits)
        commit_count = 0
        
        # Get current date for recency calculations
        current_date = datetime.now().replace(tzinfo=None)
        recent_threshold = current_date - timedelta(days=90)  # Last 3 months
        
        for commit_id, changes_data in self.analyzer.detailed_commits.items():
            commit_count += 1
            if commit_count % 100 == 0:
                print(f"  Processing commit {commit_count}/{total_commits} ({(commit_count/total_commits)*100:.1f}%)")
            
            # Get commit info
            commit_info = next((c for c in self.analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
                
            author_info = self.analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            # Parse commit date
            try:
                commit_date_str = commit_info.get('author', {}).get('date', '')
                if commit_date_str:
                    commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '')).replace(tzinfo=None)
                else:
                    commit_date = current_date
            except:
                commit_date = current_date
            
            developer_metrics[author_key]['total_commits'] += 1
            
            # Analyze file changes
            changes = changes_data.get('changes', [])
            for change in changes:
                item = change.get('item', {})
                change_type = change.get('changeType', '')
                path = item.get('path', '')
                
                if not path or item.get('isFolder', False):
                    continue
                
                # Skip certain file types that aren't relevant for hotspot analysis
                filename = os.path.basename(path)
                if self.analyzer.classify_file_type(filename) in ['other', 'docs']:
                    continue
                
                # Update file metrics
                file_metrics[path]['developers'].add(author_key)
                file_metrics[path]['total_commits'] += 1
                file_metrics[path]['total_changes'] += 1
                
                # Track recent activity
                if commit_date >= recent_threshold:
                    file_metrics[path]['recent_commits'] += 1
                
                # Update last modified date
                if file_metrics[path]['last_modified'] is None or commit_date > file_metrics[path]['last_modified']:
                    file_metrics[path]['last_modified'] = commit_date
                
                # Estimate changes based on change type
                if change_type in ['add', 'edit']:
                    file_metrics[path]['lines_added'] += 25  # Rough estimate
                    file_metrics[path]['file_size_estimate'] += 25
                elif change_type == 'delete':
                    file_metrics[path]['lines_deleted'] += 10  # Rough estimate
                
                # Update developer metrics
                developer_metrics[author_key]['files_owned'].add(path)
                developer_metrics[author_key]['total_file_changes'] += 1
        
        print(f"✓ Analyzed {len(file_metrics)} unique files across {total_commits} commits")
        
        # Calculate file hotspot scores and bus factor risks
        file_analysis_data = []
        
        for file_path, metrics in file_metrics.items():
            if metrics['total_commits'] == 0:
                continue
            
            filename = os.path.basename(file_path)
            file_type = self.analyzer.classify_file_type(filename)
            num_developers = len(metrics['developers'])
            
            # Calculate bus factor risk (0-5 scale)
            if num_developers == 1:
                bus_factor_risk = 5.0  # Very high risk
            elif num_developers == 2:
                bus_factor_risk = 3.5  # High risk
            elif num_developers <= 4:
                bus_factor_risk = 2.0  # Medium risk
            elif num_developers <= 7:
                bus_factor_risk = 1.0  # Low risk
            else:
                bus_factor_risk = 0.2  # Very low risk
            
            # Calculate hotspot score (combination of change frequency and recency)
            change_frequency = metrics['total_commits']
            recency_weight = metrics['recent_commits'] * 2  # Recent changes are more important
            size_factor = min(metrics['file_size_estimate'] / 100, 3.0)  # Larger files are riskier
            
            hotspot_score = (change_frequency * 0.4) + (recency_weight * 0.4) + (size_factor * 0.2)
            
            # Determine if file is critical based on multiple factors
            is_critical = (
                bus_factor_risk >= 3.0 or  # High bus factor risk
                hotspot_score >= 10.0 or   # High change activity
                file_type in ['csharp', 'sql', 'csharp_project'] or  # Core file types
                'controller' in filename.lower() or
                'service' in filename.lower() or
                'manager' in filename.lower() or
                'repository' in filename.lower()
            )
            
            # Calculate change frequency (commits per week)
            if metrics['last_modified']:
                days_since_creation = (current_date - metrics['last_modified']).days
                weeks_since_creation = max(days_since_creation / 7, 1)
                change_frequency_per_week = metrics['total_commits'] / weeks_since_creation
            else:
                change_frequency_per_week = 0
            
            file_analysis_data.append({
                'File_Path': file_path,
                'File_Name': filename,
                'File_Type': file_type,
                'Total_Commits': metrics['total_commits'],
                'Recent_Commits': metrics['recent_commits'],
                'Developers_Count': num_developers,
                'Developers_List': ', '.join(sorted(list(metrics['developers']))),
                'Lines_Added_Est': metrics['lines_added'],
                'Lines_Deleted_Est': metrics['lines_deleted'],
                'File_Size_Est': metrics['file_size_estimate'],
                'Last_Modified': metrics['last_modified'].strftime('%Y-%m-%d') if metrics['last_modified'] else 'Unknown',
                'Change_Frequency_Per_Week': round(change_frequency_per_week, 2),
                'Bus_Factor_Risk': round(bus_factor_risk, 2),
                'Hotspot_Score': round(hotspot_score, 2),
                'Is_Critical': is_critical,
                'Risk_Category': (
                    'Very High' if bus_factor_risk >= 4.0 else
                    'High' if bus_factor_risk >= 3.0 else
                    'Medium' if bus_factor_risk >= 2.0 else
                    'Low' if bus_factor_risk >= 1.0 else
                    'Very Low'
                )
            })
        
        # Calculate developer bus factor risks
        developer_analysis_data = []
        total_files = len(file_metrics)
        
        for developer, metrics in developer_metrics.items():
            files_owned = len(metrics['files_owned'])
            if files_owned == 0:
                continue
            
            ownership_percentage = (files_owned / total_files) * 100
            
            # Calculate bus factor risk for developer
            if ownership_percentage >= 50:
                dev_bus_factor_risk = 5.0  # Very high risk
            elif ownership_percentage >= 30:
                dev_bus_factor_risk = 4.0  # High risk
            elif ownership_percentage >= 20:
                dev_bus_factor_risk = 3.0  # Medium-high risk
            elif ownership_percentage >= 10:
                dev_bus_factor_risk = 2.0  # Medium risk
            elif ownership_percentage >= 5:
                dev_bus_factor_risk = 1.0  # Low risk
            else:
                dev_bus_factor_risk = 0.5  # Very low risk
            
            # Find files where this developer is the only contributor
            exclusive_files = []
            for file_path in metrics['files_owned']:
                if len(file_metrics[file_path]['developers']) == 1:
                    exclusive_files.append(os.path.basename(file_path))
            
            developer_analysis_data.append({
                'Developer': developer,
                'Files_Owned': files_owned,
                'Exclusive_Files': len(exclusive_files),
                'Exclusive_Files_List': ', '.join(exclusive_files[:5]) + ('...' if len(exclusive_files) > 5 else ''),
                'Total_Commits': metrics['total_commits'],
                'Total_File_Changes': metrics['total_file_changes'],
                'Ownership_Percentage': round(ownership_percentage, 2),
                'Bus_Factor_Risk': round(dev_bus_factor_risk, 2),
                'Risk_Level': (
                    'Critical' if dev_bus_factor_risk >= 4.0 else
                    'High' if dev_bus_factor_risk >= 3.0 else
                    'Medium' if dev_bus_factor_risk >= 2.0 else
                    'Low' if dev_bus_factor_risk >= 1.0 else
                    'Minimal'
                )
            })
        
        # Create DataFrames and save results
        df_files = pd.DataFrame(file_analysis_data)
        df_developers = pd.DataFrame(developer_analysis_data)
        
        if not df_files.empty:
            df_files = df_files.sort_values('Bus_Factor_Risk', ascending=False)
            
            print(f"\n📁 File Hotspots Analysis:")
            print(f"  Total files analyzed: {len(df_files)}")
            print(f"  Critical files: {sum(df_files['Is_Critical'])}")
            print(f"  High risk files (bus factor >= 3.0): {sum(df_files['Bus_Factor_Risk'] >= 3.0)}")
            
            # Show top 10 riskiest files
            top_files = df_files.head(10)[['File_Name', 'Bus_Factor_Risk', 'Hotspot_Score', 'Developers_Count', 'Is_Critical']]
            print("\nTop 10 Riskiest Files:")
            print(top_files.to_string(index=False))
            
            df_files.to_csv(f"{self.analyzer.data_dir}/azdo_file_hotspots_analysis.csv", index=False)
        
        if not df_developers.empty:
            df_developers = df_developers.sort_values('Bus_Factor_Risk', ascending=False)
            
            print(f"\n👥 Developer Bus Factor Analysis:")
            print(f"  Developers analyzed: {len(df_developers)}")
            print(f"  High risk developers (risk >= 3.0): {sum(df_developers['Bus_Factor_Risk'] >= 3.0)}")
            
            # Show all developers with risk details
            dev_summary = df_developers[['Developer', 'Files_Owned', 'Exclusive_Files', 'Bus_Factor_Risk', 'Risk_Level']]
            print("\nDeveloper Risk Summary:")
            print(dev_summary.to_string(index=False))
            
            df_developers.to_csv(f"{self.analyzer.data_dir}/azdo_bus_factor_analysis.csv", index=False)
        
        # Generate insights
        print(f"\n=== BUS FACTOR & HOTSPOT INSIGHTS ===")
        if not df_files.empty:
            critical_files = df_files[df_files['Is_Critical'] == True]
            single_dev_files = df_files[df_files['Developers_Count'] == 1]
            
            print(f"🚨 Risk Summary:")
            print(f"  • {len(critical_files)} critical files identified")
            print(f"  • {len(single_dev_files)} files maintained by only one developer")
            print(f"  • {sum(df_files['Bus_Factor_Risk'] >= 4.0)} files with very high bus factor risk")
            
            if not single_dev_files.empty:
                print(f"\n⚠️  Single-Developer Files (Highest Risk):")
                for _, file_row in single_dev_files.head(5).iterrows():
                    print(f"    • {file_row['File_Name']} - Developer: {file_row['Developers_List']}")
        
        if not df_developers.empty:
            high_risk_devs = df_developers[df_developers['Bus_Factor_Risk'] >= 3.0]
            if not high_risk_devs.empty:
                print(f"\n🔑 Key Person Dependencies:")
                for _, dev_row in high_risk_devs.iterrows():
                    print(f"    • {dev_row['Developer']}: {dev_row['Files_Owned']} files ({dev_row['Ownership_Percentage']:.1f}% of codebase)")
        
        return df_files, df_developers
