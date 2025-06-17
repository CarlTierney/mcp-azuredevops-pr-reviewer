"""
Language Complexity Analysis Module
"""

import os
import pandas as pd
import numpy as np
import sys
from collections import defaultdict

# Ensure we can import from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class LanguageAnalyzer:
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer

    def analyze_language_complexity_distribution(self):
        """Analyze complexity distribution across ALL files in repository"""
        print("\n=== COMPREHENSIVE LANGUAGE COMPLEXITY DISTRIBUTION ANALYSIS ===")
        
        language_metrics = defaultdict(lambda: {
            'files_analyzed': 0,
            'total_loc': 0,
            'total_complexity': 0,
            'complexity_samples': [],
            'avg_file_size': [],
            'developers_contributing': set(),
            'commits_involving_language': 0,
            'high_complexity_files': 0,
            'low_complexity_files': 0,
            'medium_complexity_files': 0,
            'unique_files': set()
        })
        
        # Get repository ID for content analysis
        try:
            repo_id = self.analyzer.get_repository_id()
        except Exception as e:
            print(f"Warning: Could not get repository ID: {e}")
            repo_id = None
        
        print(f"Analyzing ALL detailed commits for comprehensive language complexity...")
        
        # Analyze ALL detailed commits for language-specific metrics
        total_commits = len(self.analyzer.detailed_commits)
        commit_count = 0
        total_files_processed = 0
        
        for commit_id, changes_data in self.analyzer.detailed_commits.items():
            commit_count += 1
            if commit_count % 100 == 0:
                print(f"  Processing commit {commit_count}/{total_commits} ({(commit_count/total_commits)*100:.1f}%)")
            
            commit_info = next((c for c in self.analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
                
            author_info = self.analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            changes = changes_data.get('changes', [])
            for change in changes:
                item = change.get('item', {})
                change_type = change.get('changeType', '')
                path = item.get('path', '')
                
                if not path or item.get('isFolder', False) or change_type == 'delete':
                    continue
                    
                filename = os.path.basename(path)
                file_type = self.analyzer.classify_file_type(filename)
                
                # Skip non-code files
                if file_type in ['other', 'docs']:
                    continue
                
                # Track unique files per language
                language_metrics[file_type]['unique_files'].add(path)
                language_metrics[file_type]['files_analyzed'] += 1
                language_metrics[file_type]['developers_contributing'].add(author_key)
                language_metrics[file_type]['commits_involving_language'] += 1
                
                # Fetch and analyze file content for complexity
                if repo_id:
                    content = self.analyzer.fetch_file_content(repo_id, commit_id, path)
                    if content:
                        file_analysis = self.analyzer.analyze_file_contents(content)
                        complexity = self.analyzer.calculate_cyclomatic_complexity(content, filename)
                        
                        language_metrics[file_type]['total_loc'] += file_analysis['loc']
                        language_metrics[file_type]['avg_file_size'].append(file_analysis['loc'])
                        
                        if complexity > 1:  # Valid complexity measurement
                            language_metrics[file_type]['total_complexity'] += complexity
                            language_metrics[file_type]['complexity_samples'].append(complexity)
                            
                            # Classify complexity level (more granular)
                            if complexity < 5:
                                language_metrics[file_type]['low_complexity_files'] += 1
                            elif complexity < 15:
                                language_metrics[file_type]['medium_complexity_files'] += 1
                            else:
                                language_metrics[file_type]['high_complexity_files'] += 1
                        
                        total_files_processed += 1
        
        print(f"✓ Completed comprehensive analysis:")
        print(f"  - {total_files_processed} file versions processed")
        print(f"  - {sum(len(metrics['unique_files']) for metrics in language_metrics.values())} unique files analyzed")
        
        # Generate comprehensive language complexity report
        complexity_data = []
        for file_type, metrics in language_metrics.items():
            if metrics['files_analyzed'] == 0:
                continue
            
            unique_file_count = len(metrics['unique_files'])
            
            # Calculate comprehensive averages
            avg_complexity = (sum(metrics['complexity_samples']) / len(metrics['complexity_samples'])) if metrics['complexity_samples'] else 0
            avg_file_size = (sum(metrics['avg_file_size']) / len(metrics['avg_file_size'])) if metrics['avg_file_size'] else 0
            complexity_std = np.std(metrics['complexity_samples']) if len(metrics['complexity_samples']) > 1 else 0
            max_complexity = max(metrics['complexity_samples']) if metrics['complexity_samples'] else 0
            min_complexity = min(metrics['complexity_samples']) if metrics['complexity_samples'] else 0
            
            # Calculate complexity distribution percentages
            total_complexity_files = (metrics['low_complexity_files'] + 
                                    metrics['medium_complexity_files'] + 
                                    metrics['high_complexity_files'])
            
            low_complexity_pct = (metrics['low_complexity_files'] / max(1, total_complexity_files)) * 100
            medium_complexity_pct = (metrics['medium_complexity_files'] / max(1, total_complexity_files)) * 100
            high_complexity_pct = (metrics['high_complexity_files'] / max(1, total_complexity_files)) * 100
            
            # Calculate risk score based on multiple factors
            size_risk = min(avg_file_size / 500, 2.0)  # Files over 500 lines are riskier
            complexity_risk = avg_complexity / 10  # Higher complexity = higher risk
            distribution_risk = high_complexity_pct / 100  # More high-complexity files = higher risk
            
            overall_risk_score = (complexity_risk + size_risk + distribution_risk) * 10
            
            complexity_data.append({
                'Language_Type': file_type,
                'Unique_Files': unique_file_count,
                'Total_File_Versions': metrics['files_analyzed'],
                'Total_LOC': metrics['total_loc'],
                'Avg_File_Size': round(avg_file_size, 1),
                'Max_File_Size': max(metrics['avg_file_size']) if metrics['avg_file_size'] else 0,
                'Developers_Contributing': len(metrics['developers_contributing']),
                'Commits_Involving_Language': metrics['commits_involving_language'],
                'Avg_Complexity': round(avg_complexity, 2),
                'Min_Complexity': round(min_complexity, 2),
                'Max_Complexity': round(max_complexity, 2),
                'Complexity_Std_Dev': round(complexity_std, 2),
                'Low_Complexity_Files': metrics['low_complexity_files'],
                'Medium_Complexity_Files': metrics['medium_complexity_files'],
                'High_Complexity_Files': metrics['high_complexity_files'],
                'Low_Complexity_Pct': round(low_complexity_pct, 1),
                'Medium_Complexity_Pct': round(medium_complexity_pct, 1),
                'High_Complexity_Pct': round(high_complexity_pct, 1),
                'Complexity_Risk_Score': round(overall_risk_score, 2),
                'Size_Risk_Factor': round(size_risk, 2),
                'Distribution_Risk_Factor': round(distribution_risk, 2)
            })
        
        df_language_complexity = pd.DataFrame(complexity_data)
        if not df_language_complexity.empty:
            df_language_complexity = df_language_complexity.sort_values('Complexity_Risk_Score', ascending=False)
            
            print(f"\n📈 Comprehensive Language Complexity Analysis Results:")
            print(f"  File types analyzed: {len(df_language_complexity)}")
            print(f"  Total unique files: {sum(df_language_complexity['Unique_Files'])}")
            print(f"  Total file versions processed: {sum(df_language_complexity['Total_File_Versions'])}")
            print(f"  Total lines of code: {sum(df_language_complexity['Total_LOC']):,}")
            
            print(df_language_complexity[['Language_Type', 'Unique_Files', 'Total_LOC', 'Avg_Complexity', 'Complexity_Risk_Score']].to_string(index=False))
            df_language_complexity.to_csv(f"{self.analyzer.data_dir}/azdo_language_complexity.csv", index=False)
            
            # Generate detailed language-specific insights
            print(f"\n=== COMPREHENSIVE LANGUAGE INSIGHTS ===")
            if not df_language_complexity.empty:
                highest_risk = df_language_complexity.iloc[0]
                print(f"🔥 Highest complexity risk: {highest_risk['Language_Type']}")
                print(f"   • Risk Score: {highest_risk['Complexity_Risk_Score']}")
                print(f"   • Unique files: {highest_risk['Unique_Files']}")
                print(f"   • Average complexity: {highest_risk['Avg_Complexity']}")
                print(f"   • High complexity files: {highest_risk['High_Complexity_Files']} ({highest_risk['High_Complexity_Pct']:.1f}%)")
                print(f"   • Total LOC: {highest_risk['Total_LOC']:,}")
                
                if len(df_language_complexity) > 1:
                    most_stable = df_language_complexity.iloc[-1]
                    print(f"✅ Most stable language: {most_stable['Language_Type']}")
                    print(f"   • Risk Score: {most_stable['Complexity_Risk_Score']}")
                    print(f"   • Unique files: {most_stable['Unique_Files']}")
                    print(f"   • Average complexity: {most_stable['Avg_Complexity']}")
        else:
            print("No language complexity data found")
        
        return df_language_complexity
