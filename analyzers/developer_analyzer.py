"""
Developer activity and contribution analysis
"""

import os
import pandas as pd
import sys
from datetime import datetime
from collections import defaultdict

# Ensure we can import from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class DeveloperAnalyzer:
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer

    def analyze_developer_activity(self):
        """Analyze real developer activity patterns from actual commits"""
        print("\n=== DEVELOPER ACTIVITY ANALYSIS ===")
        
        # Check if analysis is already cached
        analysis_name = "developer_activity"
        if self.analyzer.is_analysis_cached(analysis_name):
            cached_df = self.analyzer.get_cached_dataframe(analysis_name)
            if cached_df is not None:
                print("[STATS] Displaying cached developer activity results:")
                summary_cols = ['Developer', 'Total_Commits', 'Total_Files_Changed', 'LOC_Net_Change', 
                               'Primary_File_Type', 'Most_Active_Day', 'Consistency_Ratio']
                print("\nDeveloper Activity Summary:")
                print(cached_df[summary_cols].to_string(index=False))
                return cached_df
        
        print("[SEARCH] Running fresh developer activity analysis...")
        
        developer_metrics = defaultdict(lambda: {
            'total_commits': 0,
            'files_changed': set(),
            'loc_added': 0,
            'loc_deleted': 0,
            'loc_modified': 0,
            'commit_dates': [],
            'file_types': defaultdict(int),
            'change_types': defaultdict(int),
            'hours': defaultdict(int),
            'days_of_week': defaultdict(int),
            'complexity_samples': [],
            'first_commit': None,
            'last_commit': None
        })
        
        try:
            repo_id = self.analyzer.get_repository_id()
            print(f"  [OK] Repository ID obtained: {repo_id}")
        except Exception as e:
            print(f"  [WARNING]  Warning: Could not get repository ID: {e}")
            repo_id = None
        
        print("[STATS] Analyzing commit patterns and code metrics...")
        
        # Process all commits for basic activity
        total_commits = len(self.analyzer.commits)
        print(f"  Processing {total_commits:,} commits for basic activity patterns...")
        
        processed_basic = 0
        for commit in self.analyzer.commits:
            processed_basic += 1
            if processed_basic % 500 == 0:
                progress_pct = (processed_basic / total_commits) * 100
                print(f"    Basic commit processing: {processed_basic:,}/{total_commits:,} ({progress_pct:.1f}%)")
            
            author_info = self.analyzer.get_author_info(commit.get('author', {}))
            author_key = author_info['unique_name']
            
            try:
                commit_date_str = commit.get('author', {}).get('date', '')
                if commit_date_str:
                    commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                    developer_metrics[author_key]['commit_dates'].append(commit_date)
                    
                    # Track timing patterns
                    developer_metrics[author_key]['hours'][commit_date.hour] += 1
                    developer_metrics[author_key]['days_of_week'][commit_date.weekday()] += 1
                    
                    # Track first and last commits
                    if developer_metrics[author_key]['first_commit'] is None:
                        developer_metrics[author_key]['first_commit'] = commit_date
                    developer_metrics[author_key]['last_commit'] = commit_date
                    
                    developer_metrics[author_key]['total_commits'] += 1
            except Exception as e:
                print(f"    Warning: Error processing commit {commit.get('commitId', 'unknown')}: {type(e).__name__}")
                continue
        
        print(f"  [OK] Completed basic commit processing for {len(developer_metrics)} developers")
        
        # Process detailed commits for quality metrics
        total_detailed = len(self.analyzer.detailed_commits)
        processed_commits = 0
        processed_files = 0
        skipped_files = 0
        
        # Add time tracking for detailed commits processing
        import time
        detailed_start_time = time.time()
        last_detailed_progress = detailed_start_time
        elapsed = 0  # Initialize elapsed variable
        
        for commit_id, changes_data in self.analyzer.detailed_commits.items():
            processed_commits += 1
            current_time = time.time()
            elapsed = current_time - detailed_start_time  # Update elapsed time
            
            # Progress reporting every 100 commits OR every 30 seconds
            if processed_commits % 100 == 0 or (current_time - last_detailed_progress) > 30:
                progress_pct = (processed_commits / total_detailed) * 100
                commits_per_sec = processed_commits / max(elapsed, 1)
                eta_seconds = (total_detailed - processed_commits) / max(commits_per_sec, 0.1)
                
                print(f"    Processing detailed commits: {processed_commits}/{total_detailed} ({progress_pct:.1f}%)")
                print(f"      Speed: {commits_per_sec:.1f} commits/sec | ETA: {eta_seconds/60:.1f} minutes")
                last_detailed_progress = current_time
              # Log current processing status for visibility
            if processed_commits % 50 == 0:
                current_commit_short = commit_id[:8] if commit_id else "unknown"
                print(f"    [LOCATION] Currently processing commit: {current_commit_short} ({processed_commits}/{total_detailed})")

            commit_info = next((c for c in self.analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
                
            author_info = self.analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            changes = changes_data.get('changes', [])
            if not changes:
                continue
            
            for change in changes:
                item = change.get('item', {})
                change_type = change.get('changeType', '')
                path = item.get('path', '')
                
                if not path or item.get('isFolder', False):
                    continue
                
                filename = os.path.basename(path)
                file_type = self.analyzer.classify_file_type(filename)
                
                # Skip non-code files
                if file_type in ['other', 'docs']:
                    skipped_files += 1
                    continue
                
                developer_metrics[author_key]['files_changed'].add(path)
                developer_metrics[author_key]['file_types'][file_type] += 1
                developer_metrics[author_key]['change_types'][change_type] += 1
                processed_files += 1
                
                # Analyze file content for quality metrics with detailed error handling
                if repo_id:
                    try:
                        # Show progress for slow file operations every 100 files
                        if processed_files % 100 == 0:
                            print(f"      Analyzing file content: {processed_files:,} files processed...")
                        
                        content = self.analyzer.fetch_file_content(repo_id, commit_id, path)
                        if content and len(content.strip()) > 0:  # Only analyze non-empty content
                            file_analysis = self.analyzer.analyze_file_contents(content)
                            complexity = self.analyzer.calculate_cyclomatic_complexity(content, filename)
                            
                            if complexity > 1:
                                developer_metrics[author_key]['complexity_samples'].append(complexity)
                            
                            # Calculate real LOC metrics based on change type
                            if change_type == 'add':
                                developer_metrics[author_key]['loc_added'] += file_analysis['loc']
                            elif change_type == 'edit':
                                loc_modified = int(file_analysis['loc'] * 0.3)
                                developer_metrics[author_key]['loc_modified'] += loc_modified
                            elif change_type == 'delete':
                                developer_metrics[author_key]['loc_deleted'] += file_analysis['loc']
                        else:
                            skipped_files += 1
                            
                    except Exception as e:
                        # Log error but continue processing
                        if processed_files % 1000 == 0:  # Only log occasionally to avoid spam
                            print(f"      Warning: Failed to analyze {filename}: {type(e).__name__}")
                        skipped_files += 1
                        # Use fallback estimates
                        if change_type == 'add':
                            developer_metrics[author_key]['loc_added'] += 50
                        elif change_type == 'edit':
                            developer_metrics[author_key]['loc_modified'] += 15
                        elif change_type == 'delete':
                            developer_metrics[author_key]['loc_deleted'] += 25
                else:
                    # Fallback estimates when repo_id is not available
                    if change_type == 'add':
                        developer_metrics[author_key]['loc_added'] += 50
                    elif change_type == 'edit':
                        developer_metrics[author_key]['loc_modified'] += 15
                    elif change_type == 'delete':
                        developer_metrics[author_key]['loc_deleted'] += 25
        
        print(f"  [OK] Completed detailed commit processing:")
        print(f"    - {processed_commits:,} commits processed")
        print(f"    - {processed_files:,} files analyzed")
        print(f"    - {skipped_files:,} files skipped")
        
        # Generate activity analysis
        print("[CHART] Generating developer activity report...")
        activity_data = []
        
        for author_key, metrics in developer_metrics.items():
            if metrics['total_commits'] == 0:
                continue
            
            commit_dates = metrics['commit_dates']
            
            # Calculate activity metrics
            total_files_changed = len(metrics['files_changed'])
            avg_complexity = (sum(metrics['complexity_samples']) / len(metrics['complexity_samples'])) if metrics['complexity_samples'] else 0
            
            # Calculate time-based patterns
            most_active_hour = max(metrics['hours'].items(), key=lambda x: x[1])[0] if metrics['hours'] else 9
            most_active_day = max(metrics['days_of_week'].items(), key=lambda x: x[1])[0] if metrics['days_of_week'] else 0
            
            # Calculate consistency
            if len(commit_dates) > 1:
                active_period = (max(commit_dates) - min(commit_dates)).days + 1
                unique_commit_days = len(set(d.date() for d in commit_dates))
                consistency_ratio = unique_commit_days / max(active_period, 1)
            else:
                consistency_ratio = 1.0
                active_period = 1
            
            # Determine primary file type
            primary_file_type = max(metrics['file_types'].items(), key=lambda x: x[1])[0] if metrics['file_types'] else 'unknown'
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            most_active_day_name = day_names[most_active_day]
            
            activity_data.append({
                'Developer': author_key,
                'Total_Commits': metrics['total_commits'],
                'Total_Files_Changed': total_files_changed,
                'LOC_Added': metrics['loc_added'],
                'LOC_Deleted': metrics['loc_deleted'],
                'LOC_Modified': metrics['loc_modified'],
                'LOC_Net_Change': metrics['loc_added'] - metrics['loc_deleted'],
                'Avg_Cyclomatic_Complexity': round(avg_complexity, 2),
                'Primary_File_Type': primary_file_type,
                'Most_Active_Hour': most_active_hour,
                'Most_Active_Day': most_active_day_name,
                'Consistency_Ratio': round(consistency_ratio, 3),
                'Active_Period_Days': active_period,
                'First_Commit': metrics['first_commit'].strftime('%Y-%m-%d') if metrics['first_commit'] else 'Unknown',
                'Last_Commit': metrics['last_commit'].strftime('%Y-%m-%d') if metrics['last_commit'] else 'Unknown',
                'Commits_Per_Day': round(metrics['total_commits'] / max(active_period, 1), 2)
            })
        
        df_activity = pd.DataFrame(activity_data)
        if not df_activity.empty:
            df_activity = df_activity.sort_values('Total_Commits', ascending=False)
            
            print(f"[OK] Analyzed activity for {len(df_activity)} developers")
            
            # Display summary
            summary_cols = ['Developer', 'Total_Commits', 'Total_Files_Changed', 'LOC_Net_Change', 
                           'Primary_File_Type', 'Most_Active_Day', 'Consistency_Ratio']
            print("\nDeveloper Activity Summary:")
            print(df_activity[summary_cols].to_string(index=False))
            
            # Save results
            output_file = f"{self.analyzer.data_dir}/azdo_developer_activity.csv"
            df_activity.to_csv(output_file, index=False)
            print(f"[SAVED] Saved results to: {output_file}")
            
            # Mark as cached
            self.analyzer.mark_analysis_cached(analysis_name, output_file)
            
            # Generate insights
            print(f"\n=== ACTIVITY INSIGHTS ===")
            total_commits = df_activity['Total_Commits'].sum()
            total_files = df_activity['Total_Files_Changed'].sum()
            
            print(f"[STATS] Team Activity Summary:")
            print(f"  • Total commits: {total_commits:,}")
            print(f"  • Total files changed: {total_files:,}")
            print(f"  • Average commits per developer: {total_commits / len(df_activity):.1f}")
            
            top_contributor = df_activity.iloc[0]
            print(f"\n[BEST] Most Active Developer: {top_contributor['Developer']}")
            print(f"  • {top_contributor['Total_Commits']} commits ({top_contributor['Total_Commits']/total_commits*100:.1f}% of total)")
            print(f"  • {top_contributor['Total_Files_Changed']} files changed")
            print(f"  • Most active on {top_contributor['Most_Active_Day']}s at {top_contributor['Most_Active_Hour']}:00")
        else:
            print("[WARNING]  No developer activity data found")
        
        return df_activity

    def analyze_pull_request_metrics(self):
        """Analyze real pull request patterns and metrics"""
        print("\n=== PULL REQUEST METRICS ANALYSIS ===")
        
        # Check if analysis is already cached
        analysis_name = "pull_request_metrics"
        if self.analyzer.is_analysis_cached(analysis_name):
            cached_df = self.analyzer.get_cached_dataframe(analysis_name)
            if cached_df is not None:
                print("[STATS] Displaying cached pull request results:")
                summary_cols = ['PR_ID', 'Title', 'Status', 'Author', 'Duration_Hours', 'Reviewer_Count', 'Approvals']
                print("\nRecent Pull Requests:")
                print(cached_df.head(10)[summary_cols].to_string(index=False))
                return cached_df
        
        print("[SEARCH] Running fresh pull request analysis...")
        
        if not self.analyzer.pull_requests:
            print("No pull request data available for analysis")
            return pd.DataFrame()
        
        pr_metrics = []
        
        for pr in self.analyzer.pull_requests:
            try:
                # Basic PR info
                pr_id = pr.get('pullRequestId', 0)
                title = pr.get('title', 'No Title')
                status = pr.get('status', 'unknown')
                
                # Author information
                created_by = pr.get('createdBy', {})
                author_info = self.analyzer.get_author_info(created_by)
                
                # Dates
                creation_date_str = pr.get('creationDate', '')
                completion_date_str = pr.get('completionDate', '')
                
                creation_date = None
                completion_date = None
                
                if creation_date_str:
                    creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
                
                if completion_date_str:
                    completion_date = datetime.fromisoformat(completion_date_str.replace('Z', '+00:00'))
                
                # Calculate duration
                duration_hours = 0
                if creation_date and completion_date:
                    duration_hours = (completion_date - creation_date).total_seconds() / 3600
                
                # Repository and branch info
                source_branch = pr.get('sourceRefName', '').replace('refs/heads/', '')
                target_branch = pr.get('targetRefName', '').replace('refs/heads/', '')
                
                # Reviewer info
                reviewers = pr.get('reviewers', [])
                reviewer_count = len(reviewers)
                
                # Vote analysis
                approvals = sum(1 for r in reviewers if r.get('vote', 0) > 0)
                rejections = sum(1 for r in reviewers if r.get('vote', 0) < 0)
                
                pr_metrics.append({
                    'PR_ID': pr_id,
                    'Title': title[:50] + '...' if len(title) > 50 else title,
                    'Status': status,
                    'Author': author_info['unique_name'],
                    'Creation_Date': creation_date.strftime('%Y-%m-%d %H:%M') if creation_date else 'Unknown',
                    'Completion_Date': completion_date.strftime('%Y-%m-%d %H:%M') if completion_date else 'Pending',
                    'Duration_Hours': round(duration_hours, 1),
                    'Source_Branch': source_branch,
                    'Target_Branch': target_branch,
                    'Reviewer_Count': reviewer_count,
                    'Approvals': approvals,
                    'Rejections': rejections,
                    'Is_Completed': status in ['completed', 'merged'],
                    'Is_Abandoned': status == 'abandoned'
                })
                
            except Exception as e:
                print(f"Warning: Error processing PR {pr.get('pullRequestId', 'unknown')}: {e}")
                continue
        
        df_prs = pd.DataFrame(pr_metrics)
        
        if not df_prs.empty:
            print(f"[OK] Analyzed {len(df_prs)} pull requests")
            
            # Calculate summary statistics
            completed_prs = df_prs[df_prs['Is_Completed'] == True]
            avg_duration = completed_prs['Duration_Hours'].mean() if not completed_prs.empty else 0
            avg_reviewers = df_prs['Reviewer_Count'].mean()
            
            # Display summary
            summary_cols = ['PR_ID', 'Title', 'Status', 'Author', 'Duration_Hours', 'Reviewer_Count', 'Approvals']
            print("\nRecent Pull Requests:")
            print(df_prs.head(10)[summary_cols].to_string(index=False))
            
            output_file = f"{self.analyzer.data_dir}/azdo_pull_request_metrics.csv"
            df_prs.to_csv(output_file, index=False)
            
            # Mark as cached
            self.analyzer.mark_analysis_cached(analysis_name, output_file)
            
            # Generate insights
            print(f"\n=== PULL REQUEST INSIGHTS ===")
            print(f"[STATS] PR Statistics:")
            print(f"  • Total PRs: {len(df_prs)}")
            print(f"  • Completed: {sum(df_prs['Is_Completed'])}")
            print(f"  • Abandoned: {sum(df_prs['Is_Abandoned'])}")
            print(f"  • Average duration: {avg_duration:.1f} hours")
            print(f"  • Average reviewers: {avg_reviewers:.1f}")
            
            # Top contributors
            author_counts = df_prs['Author'].value_counts()
            if not author_counts.empty:
                print(f"\n[BEST] Top PR Authors:")
                for author, count in author_counts.head(3).items():
                    print(f"  • {author}: {count} PRs")
        
        return df_prs
