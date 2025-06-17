#!/usr/bin/env python3
"""
Enhanced Code Quality Analysis Module
"""

import pandas as pd
import numpy as np
import os
from collections import defaultdict
from ..utils.file_classifier import FileClassifier, ContentAnalyzer

class EnhancedQualityAnalyzer:
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
        self.file_classifier = FileClassifier()
        self.content_analyzer = ContentAnalyzer()
    
    def analyze_enhanced_code_quality(self):
        """Analyze code quality with advanced metrics including cyclomatic complexity"""
        print("\n=== ENHANCED CODE QUALITY METRICS ===")
        
        # Track metrics by developer
        developer_metrics = defaultdict(lambda: {
            'total_files_changed': 0,
            'file_types': defaultdict(int),
            'total_complexity': 0,
            'complexity_samples': 0,
            'loc_added': 0,
            'loc_deleted': 0,
            'non_whitespace_loc_added': 0,
            'non_whitespace_loc_deleted': 0,
            'small_changes': 0,  # <10 LOC
            'medium_changes': 0,  # 10-100 LOC
            'large_changes': 0,  # >100 LOC
            'low_complexity_changes': 0,  # <5 complexity
            'medium_complexity_changes': 0,  # 5-10 complexity
            'high_complexity_changes': 0,  # >10 complexity
            'test_coverage_changes': 0,
            'code_to_test_ratio': [],
            'complexity_by_language': defaultdict(list)
        })
        
        # Get repository ID
        try:
            repo_id = self.base_analyzer.get_repository_id()
        except Exception as e:
            print(f"Error getting repository ID: {e}")
            return None
        
        # Analyze detailed commits
        for commit_id, changes_data in self.base_analyzer.detailed_commits.items():
            # Find the corresponding commit to get author info
            commit_info = next((c for c in self.base_analyzer.commits if c.get('commitId') == commit_id), None)
            if not commit_info:
                continue
                
            author_info = self.base_analyzer.get_author_info(commit_info.get('author', {}))
            author_key = author_info['unique_name']
            
            changes = changes_data.get('changes', [])
            if not changes:
                continue
            
            # Track metrics for this commit
            commit_metrics = {
                'code_files': 0,
                'test_files': 0,
                'code_loc': 0,
                'test_loc': 0
            }
            
            for change in changes:
                item = change.get('item', {})
                change_type = change.get('changeType', '')
                
                if change_type == 'delete':
                    continue
                    
                path = item.get('path', '')
                if not path:
                    continue
                    
                filename = os.path.basename(path)
                file_type = self.file_classifier.classify_file_type(filename)
                
                developer_metrics[author_key]['file_types'][file_type] += 1
                developer_metrics[author_key]['total_files_changed'] += 1
                
                # Fetch file content
                content = self.base_analyzer.fetch_file_content(repo_id, commit_id, path)
                if not content:
                    continue
                
                # Analyze complexity and LOC
                complexity = self.content_analyzer.calculate_cyclomatic_complexity(content, filename)
                file_metrics = self.content_analyzer.analyze_file_contents(content)
                
                # Track complexity metrics
                if complexity > 1:  # Only count if meaningful complexity was calculated
                    developer_metrics[author_key]['total_complexity'] += complexity
                    developer_metrics[author_key]['complexity_samples'] += 1
                    developer_metrics[author_key]['complexity_by_language'][file_type].append(complexity)
                    
                    # Classify complexity
                    if complexity < 5:
                        developer_metrics[author_key]['low_complexity_changes'] += 1
                    elif complexity < 10:
                        developer_metrics[author_key]['medium_complexity_changes'] += 1
                    else:
                        developer_metrics[author_key]['high_complexity_changes'] += 1
                
                # Track LOC metrics
                loc = file_metrics['loc']
                sloc = file_metrics['sloc']  # Source lines (non-whitespace)
                
                developer_metrics[author_key]['loc_added'] += loc
                developer_metrics[author_key]['non_whitespace_loc_added'] += sloc
                
                # Classify change size
                if loc < 10:
                    developer_metrics[author_key]['small_changes'] += 1
                elif loc < 100:
                    developer_metrics[author_key]['medium_changes'] += 1
                else:
                    developer_metrics[author_key]['large_changes'] += 1
                
                # Track test coverage metrics
                is_test = any(test_indicator in filename.lower() for test_indicator in ['test', 'tests', 'spec', 'specs', 'unittest'])
                if is_test:
                    developer_metrics[author_key]['test_coverage_changes'] += 1
                    commit_metrics['test_files'] += 1
                    commit_metrics['test_loc'] += sloc
                else:
                    commit_metrics['code_files'] += 1
                    commit_metrics['code_loc'] += sloc
            
            # Calculate code-to-test ratio for this commit (if both types present)
            if commit_metrics['test_loc'] > 0 and commit_metrics['code_loc'] > 0:
                code_test_ratio = commit_metrics['code_loc'] / commit_metrics['test_loc']
                developer_metrics[author_key]['code_to_test_ratio'].append(code_test_ratio)
        
        # Convert metrics to DataFrame
        quality_data = []
        for author_key, metrics in developer_metrics.items():
            if metrics['total_files_changed'] == 0:
                continue
                
            # Calculate average complexity
            avg_complexity = (metrics['total_complexity'] / metrics['complexity_samples']) if metrics['complexity_samples'] > 0 else 0
            
            # Calculate code-to-test ratio
            avg_code_test_ratio = (sum(metrics['code_to_test_ratio']) / len(metrics['code_to_test_ratio'])) if metrics['code_to_test_ratio'] else 0
            
            # Calculate complexity by language
            complexity_by_language = {lang: round(sum(complexities) / len(complexities), 2) 
                                     for lang, complexities in metrics['complexity_by_language'].items() 
                                     if complexities}
            
            # Calculate non-whitespace ratio
            non_whitespace_ratio = metrics['non_whitespace_loc_added'] / max(1, metrics['loc_added'])
            
            quality_data.append({
                'Developer': author_key,
                'Total_Files_Changed': metrics['total_files_changed'],
                'LOC_Added': metrics['loc_added'],
                'Non_Whitespace_LOC': metrics['non_whitespace_loc_added'],
                'Non_Whitespace_Ratio': round(non_whitespace_ratio, 2),
                'Avg_Cyclomatic_Complexity': round(avg_complexity, 2),
                'Small_Changes': metrics['small_changes'],
                'Medium_Changes': metrics['medium_changes'],
                'Large_Changes': metrics['large_changes'],
                'Low_Complexity': metrics['low_complexity_changes'],
                'Medium_Complexity': metrics['medium_complexity_changes'],
                'High_Complexity': metrics['high_complexity_changes'],
                'Test_Changes': metrics['test_coverage_changes'],
                'Code_Test_Ratio': round(avg_code_test_ratio, 2),
                'Highest_Complexity_Lang': max(complexity_by_language.items(), key=lambda x: x[1])[0] if complexity_by_language else 'N/A',
                'Highest_Complexity_Value': max(complexity_by_language.values()) if complexity_by_language else 0
            })
        
        df_enhanced_quality = pd.DataFrame(quality_data)
        if not df_enhanced_quality.empty:
            df_enhanced_quality = df_enhanced_quality.sort_values('Total_Files_Changed', ascending=False)
            
            print(df_enhanced_quality.to_string(index=False))
            df_enhanced_quality.to_csv(f"{self.base_analyzer.data_dir}/azdo_enhanced_quality_metrics.csv", index=False)
        
        return df_enhanced_quality
