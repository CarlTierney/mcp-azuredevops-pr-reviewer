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
            print(f"  [OK] Repository ID obtained: {repo_id}")
        except Exception as e:
            print(f"  [WARNING]  Warning: Could not get repository ID: {e}")
            repo_id = None
        
        total_commits = len(self.analyzer.detailed_commits)
        if total_commits == 0:
            print("  [WARNING]  No detailed commits available for language analysis")
            return pd.DataFrame()
        
        print(f"[SEARCH] Analyzing {total_commits:,} detailed commits for language complexity...")
        
        # Analyze detailed commits with aggressive progress reporting
        commit_count = 0
        total_files_processed = 0
        skipped_files = 0
        error_files = 0
        timeout_files = 0
        
        # Add time tracking
        import time
        start_time = time.time()
        last_progress_time = start_time
        elapsed = 0  # Initialize elapsed variable
        
        for commit_id, changes_data in self.analyzer.detailed_commits.items():
            commit_count += 1
            current_time = time.time()
            elapsed = current_time - start_time  # Update elapsed time each iteration
            
            # Progress reporting every 25 commits OR every 30 seconds
            if commit_count % 25 == 0 or (current_time - last_progress_time) > 30:
                progress_pct = (commit_count / total_commits) * 100
                commits_per_sec = commit_count / max(elapsed, 1)
                eta_seconds = (total_commits - commit_count) / max(commits_per_sec, 0.1)
                
                print(f"    Language analysis: {commit_count:,}/{total_commits:,} ({progress_pct:.1f}%)")
                print(f"      Files: {total_files_processed:,} processed | {skipped_files:,} skipped | {error_files:,} errors | {timeout_files:,} timeouts")
                print(f"      Speed: {commits_per_sec:.1f} commits/sec | ETA: {eta_seconds/60:.1f} minutes")
                last_progress_time = current_time
            
            # Log current processing status for visibility
            if commit_count % 50 == 0:
                current_commit_short = commit_id[:8] if commit_id else "unknown"
                print(f"    [LOCATION] Currently processing commit: {current_commit_short} ({commit_count}/{total_commits})")
            
            commit_info = next((c for c in self.analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
                
            author_info = self.analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            changes = changes_data.get('changes', [])
            if not changes:
                continue
            
            # Process all changes without artificial limits for comprehensive analysis
            if len(changes) > 500:
                print(f"      Large commit detected ({len(changes)} changes), processing all changes...")
            
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
                    skipped_files += 1
                    continue
                
                # Track unique files per language
                language_metrics[file_type]['unique_files'].add(path)
                language_metrics[file_type]['files_analyzed'] += 1
                language_metrics[file_type]['developers_contributing'].add(author_key)
                language_metrics[file_type]['commits_involving_language'] += 1
                
                # Fetch and analyze file content with timeout protection
                if repo_id:
                    try:
                        # Timeout for individual file analysis
                        file_start_time = time.time()
                        
                        content = self.analyzer.fetch_file_content(repo_id, commit_id, path)
                        if content and len(content.strip()) > 0:
                            # Check if file fetch took too long
                            if time.time() - file_start_time > 10:  # 10 second timeout per file
                                timeout_files += 1
                                print(f"        Timeout fetching {filename}, skipping...")
                                continue
                            
                            file_analysis = self.analyzer.analyze_file_contents(content)
                            complexity = self.analyzer.calculate_cyclomatic_complexity(content, filename)
                            
                            language_metrics[file_type]['total_loc'] += file_analysis['loc']
                            language_metrics[file_type]['avg_file_size'].append(file_analysis['loc'])
                            
                            if complexity > 1:  # Valid complexity measurement
                                language_metrics[file_type]['total_complexity'] += complexity
                                language_metrics[file_type]['complexity_samples'].append(complexity)
                                
                                # Classify complexity level
                                if complexity < 5:
                                    language_metrics[file_type]['low_complexity_files'] += 1
                                elif complexity < 15:
                                    language_metrics[file_type]['medium_complexity_files'] += 1
                                else:
                                    language_metrics[file_type]['high_complexity_files'] += 1
                            
                            total_files_processed += 1
                        else:
                            skipped_files += 1
                            
                    except Exception as e:
                        error_files += 1
                        # Only log errors occasionally to avoid spam
                        if error_files % 100 == 0:
                            print(f"        Warning: Failed to analyze {filename}: {type(e).__name__}")
                        continue
                else:
                    skipped_files += 1
            
            # Emergency brake - if too many errors, stop
            if error_files > 1000:
                print(f"    [WARNING]  Too many errors ({error_files}), stopping analysis...")
                break
        
        analysis_time = time.time() - start_time
        print(f"  [OK] Completed language analysis in {analysis_time/60:.1f} minutes:")
        print(f"    - {commit_count:,}/{total_commits:,} commits processed")
        print(f"    - {total_files_processed:,} files analyzed successfully")
        print(f"    - {skipped_files:,} files skipped")
        print(f"    - {error_files:,} files had errors")
        print(f"    - {timeout_files:,} files timed out")
        print(f"    - {sum(len(metrics['unique_files']) for metrics in language_metrics.values())} unique files found")
        
        # Generate report only if we have meaningful data
        if total_files_processed == 0:
            print("  [WARNING]  No files were successfully analyzed")
            return pd.DataFrame()
        
        # Generate comprehensive language complexity report
        print("[STATS] Generating language complexity report...")
        complexity_data = []
        
        for file_type, metrics in language_metrics.items():
            if metrics['files_analyzed'] == 0:
                continue
            
            unique_file_count = len(metrics['unique_files'])
            
            # Calculate comprehensive averages (with safety checks)
            avg_complexity = (sum(metrics['complexity_samples']) / len(metrics['complexity_samples'])) if metrics['complexity_samples'] else 0
            avg_file_size = (sum(metrics['avg_file_size']) / len(metrics['avg_file_size'])) if metrics['avg_file_size'] else 0
            complexity_std = np.std(metrics['complexity_samples']) if len(metrics['complexity_samples']) > 1 else 0
            max_complexity = max(metrics['complexity_samples']) if metrics['complexity_samples'] else 0
            min_complexity = min(metrics['complexity_samples']) if metrics['complexity_samples'] else 0
            
            # Calculate complexity distribution percentages
            total_complexity_files = (metrics['low_complexity_files'] + 
                                    metrics['medium_complexity_files'] + 
                                    metrics['high_complexity_files'])
            
            if total_complexity_files > 0:
                low_complexity_pct = (metrics['low_complexity_files'] / total_complexity_files) * 100
                medium_complexity_pct = (metrics['medium_complexity_files'] / total_complexity_files) * 100
                high_complexity_pct = (metrics['high_complexity_files'] / total_complexity_files) * 100
            else:
                low_complexity_pct = medium_complexity_pct = high_complexity_pct = 0
            
            # Calculate risk score based on multiple factors
            size_risk = min(avg_file_size / 500, 2.0) if avg_file_size > 0 else 0
            complexity_risk = avg_complexity / 10 if avg_complexity > 0 else 0
            distribution_risk = high_complexity_pct / 100 if high_complexity_pct > 0 else 0
            
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
            
            print(f"\n[CHART] Language Complexity Analysis Results:")
            print(f"  File types analyzed: {len(df_language_complexity)}")
            print(f"  Total unique files: {sum(df_language_complexity['Unique_Files'])}")
            print(f"  Total file versions processed: {sum(df_language_complexity['Total_File_Versions'])}")
            print(f"  Total lines of code: {sum(df_language_complexity['Total_LOC']):,}")
            
            # Show only key columns to avoid overwhelming output
            display_cols = ['Language_Type', 'Unique_Files', 'Total_LOC', 'Avg_Complexity', 'Complexity_Risk_Score']
            print("\nTop Language Types by Complexity Risk:")
            print(df_language_complexity[display_cols].head(10).to_string(index=False))
            
            output_file = f"{self.analyzer.data_dir}/azdo_language_complexity.csv"
            df_language_complexity.to_csv(output_file, index=False)
            print(f"[SAVED] Saved language complexity analysis to: {output_file}")
            
            # Generate insights
            print(f"\n=== LANGUAGE INSIGHTS ===")
            if not df_language_complexity.empty:
                highest_risk = df_language_complexity.iloc[0]
                print(f"[HIGH RISK] Highest complexity risk: {highest_risk['Language_Type']}")
                print(f"   • Risk Score: {highest_risk['Complexity_Risk_Score']}")
                print(f"   • Unique files: {highest_risk['Unique_Files']}")
                print(f"   • Average complexity: {highest_risk['Avg_Complexity']}")
                
                if len(df_language_complexity) > 1:
                    most_stable = df_language_complexity.iloc[-1]
                    print(f"[OK] Most stable language: {most_stable['Language_Type']}")
                    print(f"   • Risk Score: {most_stable['Complexity_Risk_Score']}")
        else:
            print("[WARNING]  No language complexity data could be generated")
        
        return df_language_complexity
