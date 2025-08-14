"""
Team Collaboration Patterns Analyzer
Analyzes how developers work together, including co-authorship, PR reviews, and file overlap
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
import itertools


class CollaborationAnalyzer:
    """Analyzes team collaboration patterns and developer interactions"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        
    def analyze_team_collaboration_patterns(self):
        """Analyze comprehensive team collaboration patterns"""
        print("\n[TEAM] Analyzing Team Collaboration Patterns...")
        
        collaboration_data = []
        
        # 1. Analyze file overlap (developers working on same files)
        file_overlap = self._analyze_file_overlap()
        
        # 2. Analyze temporal collaboration (developers working in same time periods)
        temporal_collab = self._analyze_temporal_collaboration()
        
        # 3. Analyze PR collaboration (reviews, comments)
        pr_collab = self._analyze_pr_collaboration()
        
        # 4. Analyze knowledge domains (developers working on similar file types)
        domain_collab = self._analyze_domain_collaboration()
        
        # 5. Calculate collaboration scores for each developer pair
        all_developers = self._get_all_developers()
        
        for dev1, dev2 in itertools.combinations(all_developers, 2):
            collaboration_score = 0
            details = []
            
            # File overlap score
            file_key = f"{dev1}_{dev2}" if f"{dev1}_{dev2}" in file_overlap else f"{dev2}_{dev1}"
            if file_key in file_overlap:
                overlap_data = file_overlap[file_key]
                collaboration_score += overlap_data['score']
                details.append(f"Shared {overlap_data['shared_files']} files")
            
            # Temporal collaboration score
            temp_key = f"{dev1}_{dev2}" if f"{dev1}_{dev2}" in temporal_collab else f"{dev2}_{dev1}"
            if temp_key in temporal_collab:
                temp_data = temporal_collab[temp_key]
                collaboration_score += temp_data['score']
                details.append(f"{temp_data['overlapping_days']} days overlap")
            
            # PR collaboration score
            pr_key = f"{dev1}_{dev2}" if f"{dev1}_{dev2}" in pr_collab else f"{dev2}_{dev1}"
            if pr_key in pr_collab:
                pr_data = pr_collab[pr_key]
                collaboration_score += pr_data['score']
                if pr_data['reviews'] > 0:
                    details.append(f"{pr_data['reviews']} PR reviews")
            
            # Domain collaboration score
            domain_key = f"{dev1}_{dev2}" if f"{dev1}_{dev2}" in domain_collab else f"{dev2}_{dev1}"
            if domain_key in domain_collab:
                domain_data = domain_collab[domain_key]
                collaboration_score += domain_data['score']
                details.append(f"{len(domain_data['shared_domains'])} shared domains")
            
            if collaboration_score > 0:
                collaboration_data.append({
                    'Developer_1': dev1,
                    'Developer_2': dev2,
                    'Collaboration_Score': round(collaboration_score, 2),
                    'File_Overlap_Score': file_overlap.get(file_key, {}).get('score', 0),
                    'Temporal_Score': temporal_collab.get(temp_key, {}).get('score', 0),
                    'PR_Collaboration_Score': pr_collab.get(pr_key, {}).get('score', 0),
                    'Domain_Overlap_Score': domain_collab.get(domain_key, {}).get('score', 0),
                    'Shared_Files': file_overlap.get(file_key, {}).get('shared_files', 0),
                    'Overlapping_Days': temporal_collab.get(temp_key, {}).get('overlapping_days', 0),
                    'PR_Reviews': pr_collab.get(pr_key, {}).get('reviews', 0),
                    'Shared_Domains': len(domain_collab.get(domain_key, {}).get('shared_domains', [])),
                    'Collaboration_Type': self._categorize_collaboration(
                        file_overlap.get(file_key, {}).get('score', 0),
                        temporal_collab.get(temp_key, {}).get('score', 0),
                        pr_collab.get(pr_key, {}).get('score', 0),
                        domain_collab.get(domain_key, {}).get('score', 0)
                    ),
                    'Details': '; '.join(details) if details else 'No direct collaboration'
                })
        
        # Add solo developer metrics
        for developer in all_developers:
            solo_score = self._calculate_solo_work_score(developer)
            collaboration_data.append({
                'Developer_1': developer,
                'Developer_2': 'SOLO',
                'Collaboration_Score': 0,
                'File_Overlap_Score': 0,
                'Temporal_Score': 0,
                'PR_Collaboration_Score': 0,
                'Domain_Overlap_Score': 0,
                'Shared_Files': 0,
                'Overlapping_Days': 0,
                'PR_Reviews': 0,
                'Shared_Domains': 0,
                'Collaboration_Type': 'Solo Work',
                'Details': f"Solo work score: {solo_score:.1f}"
            })
        
        # Convert to DataFrame and sort by collaboration score
        df_collaboration = pd.DataFrame(collaboration_data)
        df_collaboration = df_collaboration.sort_values('Collaboration_Score', ascending=False)
        
        # Save to CSV
        output_file = f"{self.analyzer.data_dir}/azdo_team_collaboration_patterns.csv"
        df_collaboration.to_csv(output_file, index=False)
        print(f"[OK] Team collaboration patterns saved to: {output_file}")
        
        # Print summary
        self._print_collaboration_summary(df_collaboration)
        
        return df_collaboration
    
    def _analyze_file_overlap(self):
        """Analyze which developers work on the same files"""
        file_overlap = {}
        
        if not self.analyzer.detailed_commits:
            return file_overlap
        
        # Build developer-file mapping
        dev_files = defaultdict(set)
        for commit in self.analyzer.detailed_commits:
            developer = commit.get('author', {}).get('name', 'Unknown')
            if 'changes' in commit:
                for change in commit['changes']:
                    if 'item' in change and 'path' in change['item']:
                        dev_files[developer].add(change['item']['path'])
        
        # Calculate overlap between developer pairs
        developers = list(dev_files.keys())
        for dev1, dev2 in itertools.combinations(developers, 2):
            shared_files = dev_files[dev1].intersection(dev_files[dev2])
            if shared_files:
                total_files = len(dev_files[dev1].union(dev_files[dev2]))
                overlap_ratio = len(shared_files) / total_files if total_files > 0 else 0
                
                file_overlap[f"{dev1}_{dev2}"] = {
                    'shared_files': len(shared_files),
                    'total_files': total_files,
                    'overlap_ratio': overlap_ratio,
                    'score': min(overlap_ratio * 30, 30)  # Max 30 points for file overlap
                }
        
        return file_overlap
    
    def _analyze_temporal_collaboration(self):
        """Analyze developers working in similar time periods"""
        temporal_collab = {}
        
        if not self.analyzer.commits:
            return temporal_collab
        
        # Build developer-date mapping
        dev_dates = defaultdict(set)
        for commit in self.analyzer.commits:
            developer = commit.get('author', {}).get('name', 'Unknown')
            commit_date = commit.get('author', {}).get('date', '')
            if commit_date:
                try:
                    date_obj = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                    dev_dates[developer].add(date_obj.date())
                except:
                    pass
        
        # Calculate temporal overlap
        developers = list(dev_dates.keys())
        for dev1, dev2 in itertools.combinations(developers, 2):
            overlapping_days = dev_dates[dev1].intersection(dev_dates[dev2])
            if overlapping_days:
                total_days = len(dev_dates[dev1].union(dev_dates[dev2]))
                overlap_ratio = len(overlapping_days) / total_days if total_days > 0 else 0
                
                temporal_collab[f"{dev1}_{dev2}"] = {
                    'overlapping_days': len(overlapping_days),
                    'total_days': total_days,
                    'overlap_ratio': overlap_ratio,
                    'score': min(overlap_ratio * 20, 20)  # Max 20 points for temporal overlap
                }
        
        return temporal_collab
    
    def _analyze_pr_collaboration(self):
        """Analyze PR reviews and interactions"""
        pr_collab = {}
        
        if not self.analyzer.pull_requests:
            return pr_collab
        
        for pr in self.analyzer.pull_requests:
            creator = pr.get('createdBy', {}).get('displayName', 'Unknown')
            
            # Check for reviewers
            if 'reviewers' in pr:
                for reviewer in pr['reviewers']:
                    reviewer_name = reviewer.get('displayName', 'Unknown')
                    if reviewer_name != creator:
                        key = f"{creator}_{reviewer_name}"
                        if key not in pr_collab:
                            pr_collab[key] = {'reviews': 0, 'comments': 0, 'score': 0}
                        pr_collab[key]['reviews'] += 1
                        pr_collab[key]['score'] = min(pr_collab[key]['reviews'] * 5, 25)  # Max 25 points
        
        return pr_collab
    
    def _analyze_domain_collaboration(self):
        """Analyze developers working on similar file types/domains"""
        domain_collab = {}
        
        if not self.analyzer.detailed_commits:
            return domain_collab
        
        # Build developer-domain mapping
        dev_domains = defaultdict(set)
        for commit in self.analyzer.detailed_commits:
            developer = commit.get('author', {}).get('name', 'Unknown')
            if 'changes' in commit:
                for change in commit['changes']:
                    if 'item' in change and 'path' in change['item']:
                        file_path = change['item']['path']
                        # Extract file extension as domain
                        if '.' in file_path:
                            ext = file_path.split('.')[-1].lower()
                            domain = self._map_extension_to_domain(ext)
                            dev_domains[developer].add(domain)
        
        # Calculate domain overlap
        developers = list(dev_domains.keys())
        for dev1, dev2 in itertools.combinations(developers, 2):
            shared_domains = dev_domains[dev1].intersection(dev_domains[dev2])
            if shared_domains:
                total_domains = len(dev_domains[dev1].union(dev_domains[dev2]))
                overlap_ratio = len(shared_domains) / total_domains if total_domains > 0 else 0
                
                domain_collab[f"{dev1}_{dev2}"] = {
                    'shared_domains': list(shared_domains),
                    'total_domains': total_domains,
                    'overlap_ratio': overlap_ratio,
                    'score': min(overlap_ratio * 25, 25)  # Max 25 points for domain overlap
                }
        
        return domain_collab
    
    def _map_extension_to_domain(self, ext):
        """Map file extensions to technology domains"""
        domain_mapping = {
            'Backend': ['py', 'java', 'cs', 'go', 'rb', 'php', 'scala', 'kt'],
            'Frontend': ['js', 'jsx', 'ts', 'tsx', 'html', 'css', 'scss', 'vue'],
            'Database': ['sql', 'ddl', 'dml', 'pgsql', 'mysql'],
            'Configuration': ['json', 'xml', 'yaml', 'yml', 'toml', 'ini', 'conf'],
            'Documentation': ['md', 'rst', 'txt', 'doc', 'docx'],
            'Testing': ['test', 'spec', 'tests'],
            'DevOps': ['dockerfile', 'sh', 'bash', 'ps1', 'jenkinsfile'],
            'Data': ['csv', 'parquet', 'avro', 'jsonl']
        }
        
        for domain, extensions in domain_mapping.items():
            if ext in extensions or any(ext.endswith(e) for e in extensions):
                return domain
        
        return f"Other-{ext}"
    
    def _get_all_developers(self):
        """Get list of all unique developers"""
        developers = set()
        
        if self.analyzer.commits:
            for commit in self.analyzer.commits:
                dev = commit.get('author', {}).get('name', 'Unknown')
                if dev != 'Unknown':
                    developers.add(dev)
        
        return list(developers)
    
    def _categorize_collaboration(self, file_score, temporal_score, pr_score, domain_score):
        """Categorize the type of collaboration"""
        scores = {
            'Code Collaboration': file_score,
            'Temporal Alignment': temporal_score,
            'Review Partnership': pr_score,
            'Domain Expertise': domain_score
        }
        
        if sum(scores.values()) == 0:
            return 'No Collaboration'
        
        # Find dominant collaboration type
        dominant = max(scores, key=scores.get)
        
        # Check for strong collaboration (multiple high scores)
        high_scores = sum(1 for s in scores.values() if s > 10)
        if high_scores >= 3:
            return 'Strong Partnership'
        elif high_scores >= 2:
            return 'Active Collaboration'
        else:
            return dominant
    
    def _calculate_solo_work_score(self, developer):
        """Calculate how much a developer works independently"""
        solo_score = 0
        
        # Count files only this developer has touched
        if self.analyzer.detailed_commits:
            dev_files = defaultdict(set)
            for commit in self.analyzer.detailed_commits:
                dev = commit.get('author', {}).get('name', 'Unknown')
                if 'changes' in commit:
                    for change in commit['changes']:
                        if 'item' in change and 'path' in change['item']:
                            dev_files[change['item']['path']].add(dev)
            
            solo_files = sum(1 for devs in dev_files.values() if len(devs) == 1 and developer in devs)
            solo_score = min(solo_files * 2, 100)  # Cap at 100
        
        return solo_score
    
    def _print_collaboration_summary(self, df_collaboration):
        """Print collaboration analysis summary"""
        print("\n[COLLABORATION] Team Collaboration Summary:")
        
        # Top collaborating pairs
        top_pairs = df_collaboration[df_collaboration['Developer_2'] != 'SOLO'].head(5)
        if not top_pairs.empty:
            print("\nTop Collaborating Pairs:")
            for _, row in top_pairs.iterrows():
                print(f"  {row['Developer_1']} <-> {row['Developer_2']}: Score {row['Collaboration_Score']:.1f}")
                print(f"    Type: {row['Collaboration_Type']}")
        
        # Collaboration statistics
        collab_only = df_collaboration[df_collaboration['Developer_2'] != 'SOLO']
        if not collab_only.empty:
            print(f"\nCollaboration Statistics:")
            print(f"  Total developer pairs: {len(collab_only)}")
            print(f"  Average collaboration score: {collab_only['Collaboration_Score'].mean():.1f}")
            print(f"  Pairs with strong partnership: {(collab_only['Collaboration_Type'] == 'Strong Partnership').sum()}")
        
        # Isolated developers (low collaboration)
        all_devs = set(df_collaboration['Developer_1'].unique())
        low_collab_devs = []
        for dev in all_devs:
            if dev != 'SOLO':
                dev_collabs = df_collaboration[
                    ((df_collaboration['Developer_1'] == dev) | 
                     (df_collaboration['Developer_2'] == dev)) &
                    (df_collaboration['Developer_2'] != 'SOLO')
                ]
                if dev_collabs['Collaboration_Score'].sum() < 10:
                    low_collab_devs.append(dev)
        
        if low_collab_devs:
            print(f"\nPotentially Isolated Developers:")
            for dev in low_collab_devs[:5]:
                print(f"  - {dev}")