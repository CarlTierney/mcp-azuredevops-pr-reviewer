#!/usr/bin/env python3
"""
Code Quality Analysis Module
"""

import pandas as pd
import statistics
import os
from collections import defaultdict
from ..utils.file_classifier import FileClassifier

class CodeQualityAnalyzer:
    def __init__(self, base_analyzer):
        self.base_analyzer = base_analyzer
        self.file_classifier = FileClassifier()
    
    def analyze_code_quality_metrics(self):
        """Enhanced code quality analysis for C#/SQL environments"""
        print("\n=== C#/SQL CODE QUALITY ANALYSIS ===")
        
        developer_metrics = defaultdict(lambda: {
            'total_files_changed': 0,
            'file_types': defaultdict(int),
            'avg_complexity': [],
            'test_coverage_changes': 0,
            'documentation_changes': 0,
            'large_file_changes': 0,
            'small_focused_changes': 0,
            'files_per_commit': [],
            'csharp_specific': {
                'controller_changes': 0,
                'service_changes': 0,
                'model_changes': 0,
                'config_changes': 0,
                'test_changes': 0,
                'architecture_impact_high': 0,
                'web_changes': 0
            },
            'sql_specific': {
                'stored_procedure_changes': 0,
                'view_changes': 0,
                'function_changes': 0,
                'migration_changes': 0,
                'trigger_changes': 0,
                'query_changes': 0
            }
        })
        
        # Analyze detailed commits with file changes
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
                
            developer_metrics[author_key]['files_per_commit'].append(len(changes))
            
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
                
                # Track C# and SQL specific patterns
                self._track_file_patterns(developer_metrics[author_key], filename, file_type)
        
        # Convert to DataFrame with C#/SQL specific metrics
        quality_data = []
        for author_key, metrics in developer_metrics.items():
            if metrics['total_files_changed'] == 0:
                continue
                
            avg_files_per_commit = statistics.mean(metrics['files_per_commit']) if metrics['files_per_commit'] else 0
            
            # Calculate C#/SQL specific quality scores
            focus_score = (metrics['small_focused_changes'] / max(1, metrics['total_files_changed'])) * 100
            test_score = (metrics['test_coverage_changes'] / max(1, metrics['total_files_changed'])) * 100
            docs_score = (metrics['documentation_changes'] / max(1, metrics['total_files_changed'])) * 100
            
            # C# expertise score
            csharp_files = (metrics['file_types']['csharp'] + metrics['file_types']['test_csharp'] + 
                          metrics['file_types']['web_dotnet'])
            csharp_expertise = (csharp_files / max(1, metrics['total_files_changed'])) * 100
            
            # SQL expertise score  
            sql_files = metrics['file_types']['sql'] + metrics['file_types']['sql_server']
            sql_expertise = (sql_files / max(1, metrics['total_files_changed'])) * 100
            
            # Architecture impact score
            architecture_impact = metrics['csharp_specific']['architecture_impact_high']
            architecture_score = (architecture_impact / max(1, metrics['total_files_changed'])) * 100
            
            # Primary specialization
            if csharp_files > sql_files:
                specialization = f"C# Developer ({csharp_expertise:.0f}%)"
            elif sql_files > 0:
                specialization = f"SQL Developer ({sql_expertise:.0f}%)"
            else:
                specialization = "Full Stack"
                
            quality_data.append({
                'Developer': author_key,
                'Total_Files_Changed': metrics['total_files_changed'],
                'Avg_Files_Per_Commit': round(avg_files_per_commit, 1),
                'Focus_Score': round(focus_score, 1),
                'Test_Coverage_Score': round(test_score, 1),
                'Documentation_Score': round(docs_score, 1),
                'CSharp_Expertise': round(csharp_expertise, 1),
                'SQL_Expertise': round(sql_expertise, 1),
                'Architecture_Impact_Score': round(architecture_score, 1),
                'Specialization': specialization,
                'Language_Diversity': len(metrics['file_types']),
                'Large_Changes': metrics['large_file_changes'],
                'Controller_Changes': metrics['csharp_specific']['controller_changes'],
                'Service_Changes': metrics['csharp_specific']['service_changes'],
                'SQL_Procedures': metrics['sql_specific']['stored_procedure_changes'],
                'SQL_Views': metrics['sql_specific']['view_changes']
            })
        
        df_code_quality = pd.DataFrame(quality_data)
        if not df_code_quality.empty:
            df_code_quality = df_code_quality.sort_values('Total_Files_Changed', ascending=False)
            
            print(df_code_quality.to_string(index=False))
            df_code_quality.to_csv(f"{self.base_analyzer.data_dir}/azdo_csharp_sql_quality_metrics.csv", index=False)
        
        return df_code_quality
    
    def _track_file_patterns(self, metrics, filename, file_type):
        """Track C# and SQL specific patterns"""
        filename_lower = filename.lower()
        
        # C# patterns
        if file_type in ['csharp', 'test_csharp', 'web_dotnet', 'csharp_project', 'dotnet_config']:
            if 'controller' in filename_lower:
                metrics['csharp_specific']['controller_changes'] += 1
            elif any(pattern in filename_lower for pattern in ['service', 'manager', 'handler']):
                metrics['csharp_specific']['service_changes'] += 1
            elif any(pattern in filename_lower for pattern in ['model', 'dto', 'entity', 'viewmodel']):
                metrics['csharp_specific']['model_changes'] += 1
            elif file_type in ['csharp_project', 'dotnet_config']:
                metrics['csharp_specific']['config_changes'] += 1
                metrics['csharp_specific']['architecture_impact_high'] += 1
            elif file_type == 'test_csharp':
                metrics['csharp_specific']['test_changes'] += 1
                metrics['test_coverage_changes'] += 1
            elif file_type == 'web_dotnet':
                metrics['csharp_specific']['web_changes'] += 1
        
        # SQL patterns
        elif file_type in ['sql', 'sql_server']:
            if any(pattern in filename_lower for pattern in ['procedure', 'proc', 'sp_']):
                metrics['sql_specific']['stored_procedure_changes'] += 1
            elif any(pattern in filename_lower for pattern in ['view', 'vw_']):
                metrics['sql_specific']['view_changes'] += 1
            elif any(pattern in filename_lower for pattern in ['function', 'fn_', 'func']):
                metrics['sql_specific']['function_changes'] += 1
            elif 'migration' in filename_lower:
                metrics['sql_specific']['migration_changes'] += 1
            elif any(pattern in filename_lower for pattern in ['trigger', 'trg_']):
                metrics['sql_specific']['trigger_changes'] += 1
            else:
                metrics['sql_specific']['query_changes'] += 1
        
        # Documentation
        elif file_type == 'docs':
            metrics['documentation_changes'] += 1
        
        # Estimate change size
        if file_type in ['csharp_project', 'dotnet_config']:
            metrics['small_focused_changes'] += 1  # Config changes usually small
        elif 'migration' in filename_lower:
            metrics['large_file_changes'] += 1  # Migrations tend to be large
        else:
            metrics['small_focused_changes'] += 1  # Default to focused
