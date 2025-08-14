"""
Knowledge Management Analyzer
Analyzes documentation, knowledge sharing, and code maintainability patterns
"""

import pandas as pd
import re
from collections import defaultdict
from datetime import datetime


class KnowledgeAnalyzer:
    """Analyzes knowledge management and documentation patterns"""
    
    def __init__(self, base_analyzer):
        self.analyzer = base_analyzer
        
        # Documentation-related patterns
        self.doc_patterns = {
            'readme_files': [r'readme\.md', r'readme\.txt', r'readme\.rst'],
            'documentation': [r'\.md$', r'\.rst$', r'docs/', r'documentation/'],
            'api_docs': [r'swagger', r'openapi', r'api-doc', r'apidoc'],
            'inline_docs': [r'docstring', r'javadoc', r'jsdoc', r'xmldoc'],
            'examples': [r'example', r'sample', r'demo', r'tutorial'],
            'guides': [r'guide', r'howto', r'how-to', r'walkthrough'],
            'changelog': [r'changelog', r'history', r'release', r'whatsnew'],
            'contributing': [r'contributing', r'contribute', r'development']
        }
        
        # Code quality indicators
        self.quality_patterns = {
            'tests': [r'test', r'spec', r'tests/', r'__tests__/'],
            'ci_cd': [r'\.github/workflows', r'\.gitlab-ci', r'jenkinsfile', r'azure-pipelines'],
            'linting': [r'eslint', r'pylint', r'rubocop', r'\.editorconfig'],
            'formatting': [r'prettier', r'black', r'autopep8', r'rustfmt']
        }
        
        # Knowledge sharing indicators
        self.knowledge_indicators = {
            'comments': [r'added comments', r'documented', r'added documentation', r'clarified'],
            'refactoring': [r'refactor', r'cleanup', r'reorganize', r'restructure'],
            'improvements': [r'improve', r'enhance', r'optimize', r'simplify'],
            'explanations': [r'explain', r'clarify', r'describe', r'detail']
        }
    
    def analyze_knowledge_management(self):
        """Analyze knowledge management and documentation patterns"""
        print("\n[DOCS] Analyzing Knowledge Management Patterns...")
        
        knowledge_metrics = []
        
        # 1. Analyze documentation coverage
        doc_coverage = self._analyze_documentation_coverage()
        
        # 2. Analyze commit messages for knowledge sharing
        knowledge_commits = self._analyze_knowledge_commits()
        
        # 3. Analyze developer documentation contributions
        developer_docs = self._analyze_developer_documentation()
        
        # 4. Analyze code maintainability indicators
        maintainability = self._analyze_maintainability_indicators()
        
        # 5. Analyze knowledge distribution
        knowledge_distribution = self._analyze_knowledge_distribution()
        
        # Create comprehensive knowledge report
        knowledge_summary = {
            'Analysis_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Total_Files_Analyzed': doc_coverage['total_files'],
            'Documentation_Files': doc_coverage['doc_files'],
            'Documentation_Coverage_Percent': round(doc_coverage['coverage_percentage'], 2),
            'README_Files': doc_coverage['readme_count'],
            'API_Documentation': doc_coverage['api_docs_count'],
            'Test_Coverage_Indicator': maintainability['test_files'],
            'Knowledge_Sharing_Commits': knowledge_commits['knowledge_commits'],
            'Documentation_Contributors': len(developer_docs['doc_contributors']),
            'Knowledge_Distribution_Score': knowledge_distribution['distribution_score'],
            'Documentation_Health': self._calculate_doc_health(doc_coverage, maintainability)
        }
        
        # Detailed metrics by category
        for category, details in doc_coverage['category_details'].items():
            knowledge_metrics.append({
                'Metric_Type': 'Documentation Coverage',
                'Category': category.replace('_', ' ').title(),
                'Count': details['count'],
                'Percentage': round(details['percentage'], 2),
                'Quality_Score': details['quality_score'],
                'Details': details['description']
            })
        
        # Knowledge sharing patterns
        for pattern, count in knowledge_commits['pattern_counts'].items():
            knowledge_metrics.append({
                'Metric_Type': 'Knowledge Sharing',
                'Category': pattern.replace('_', ' ').title(),
                'Count': count,
                'Percentage': round((count / len(self.analyzer.commits) * 100) if self.analyzer.commits else 0, 2),
                'Quality_Score': self._assess_knowledge_quality(pattern, count),
                'Details': f"Found in commit messages"
            })
        
        # Developer documentation contributions
        for dev_name, dev_data in developer_docs['developer_details'].items():
            if dev_data['doc_commits'] > 0:
                knowledge_metrics.append({
                    'Metric_Type': 'Developer Documentation',
                    'Category': dev_name,
                    'Count': dev_data['doc_commits'],
                    'Percentage': round(dev_data['doc_percentage'], 2),
                    'Quality_Score': dev_data['quality_score'],
                    'Details': f"Primary focus: {dev_data['primary_focus']}"
                })
        
        # Maintainability indicators
        for indicator, value in maintainability['indicators'].items():
            knowledge_metrics.append({
                'Metric_Type': 'Maintainability',
                'Category': indicator.replace('_', ' ').title(),
                'Count': value['count'],
                'Percentage': round(value['percentage'], 2),
                'Quality_Score': value['score'],
                'Details': value['description']
            })
        
        # Knowledge distribution
        for area, score in knowledge_distribution['area_scores'].items():
            knowledge_metrics.append({
                'Metric_Type': 'Knowledge Distribution',
                'Category': area,
                'Count': score['file_count'],
                'Percentage': round(score['coverage'], 2),
                'Quality_Score': score['quality'],
                'Details': score['details']
            })
        
        # Convert to DataFrame
        df_knowledge = pd.DataFrame(knowledge_metrics)
        
        # Save knowledge analysis
        output_file = f"{self.analyzer.data_dir}/azdo_knowledge_management.csv"
        df_knowledge.to_csv(output_file, index=False)
        print(f"[OK] Knowledge management analysis saved to: {output_file}")
        
        # Save summary
        summary_file = f"{self.analyzer.data_dir}/azdo_knowledge_summary.csv"
        pd.DataFrame([knowledge_summary]).to_csv(summary_file, index=False)
        print(f"[OK] Knowledge summary saved to: {summary_file}")
        
        # Print insights
        self._print_knowledge_insights(knowledge_summary, df_knowledge)
        
        return df_knowledge
    
    def _analyze_documentation_coverage(self):
        """Analyze documentation file coverage"""
        results = {
            'total_files': 0,
            'doc_files': 0,
            'coverage_percentage': 0,
            'readme_count': 0,
            'api_docs_count': 0,
            'category_details': {}
        }
        
        if not self.analyzer.detailed_commits:
            return results
        
        all_files = set()
        doc_files_by_category = defaultdict(set)
        
        for commit in self.analyzer.detailed_commits:
            if 'changes' in commit:
                for change in commit['changes']:
                    if 'item' in change and 'path' in change['item']:
                        file_path = change['item']['path'].lower()
                        all_files.add(file_path)
                        
                        for category, patterns in self.doc_patterns.items():
                            for pattern in patterns:
                                if re.search(pattern, file_path):
                                    doc_files_by_category[category].add(file_path)
                                    
                                    if category == 'readme_files':
                                        results['readme_count'] += 1
                                    elif category == 'api_docs':
                                        results['api_docs_count'] += 1
        
        results['total_files'] = len(all_files)
        results['doc_files'] = len(set().union(*doc_files_by_category.values())) if doc_files_by_category else 0
        results['coverage_percentage'] = (results['doc_files'] / results['total_files'] * 100) if results['total_files'] > 0 else 0
        
        for category, files in doc_files_by_category.items():
            results['category_details'][category] = {
                'count': len(files),
                'percentage': (len(files) / results['total_files'] * 100) if results['total_files'] > 0 else 0,
                'quality_score': self._calculate_category_quality(category, len(files)),
                'description': self._get_category_description(category)
            }
        
        return results
    
    def _analyze_knowledge_commits(self):
        """Analyze commits for knowledge sharing patterns"""
        results = {
            'knowledge_commits': 0,
            'pattern_counts': defaultdict(int)
        }
        
        if not self.analyzer.commits:
            return results
        
        for commit in self.analyzer.commits:
            message = commit.get('comment', '').lower()
            is_knowledge_commit = False
            
            for pattern_type, patterns in self.knowledge_indicators.items():
                if any(pattern in message for pattern in patterns):
                    is_knowledge_commit = True
                    results['pattern_counts'][pattern_type] += 1
            
            if is_knowledge_commit:
                results['knowledge_commits'] += 1
        
        return results
    
    def _analyze_developer_documentation(self):
        """Analyze developer contributions to documentation"""
        results = {
            'doc_contributors': [],
            'developer_details': {}
        }
        
        developer_stats = defaultdict(lambda: {
            'total_commits': 0,
            'doc_commits': 0,
            'categories': defaultdict(int)
        })
        
        for commit in self.analyzer.commits:
            developer = commit.get('author', {}).get('name', 'Unknown')
            message = commit.get('comment', '').lower()
            
            developer_stats[developer]['total_commits'] += 1
            
            # Check if commit is documentation-related
            is_doc_commit = False
            for category, patterns in self.knowledge_indicators.items():
                if any(pattern in message for pattern in patterns):
                    is_doc_commit = True
                    developer_stats[developer]['categories'][category] += 1
            
            if is_doc_commit or 'doc' in message or 'readme' in message:
                developer_stats[developer]['doc_commits'] += 1
        
        for developer, stats in developer_stats.items():
            if stats['doc_commits'] > 0:
                doc_percentage = (stats['doc_commits'] / stats['total_commits'] * 100)
                
                if doc_percentage > 5:  # Developer with >5% documentation focus
                    results['doc_contributors'].append(developer)
                
                primary_focus = max(stats['categories'], key=stats['categories'].get) if stats['categories'] else 'General'
                
                results['developer_details'][developer] = {
                    'doc_commits': stats['doc_commits'],
                    'total_commits': stats['total_commits'],
                    'doc_percentage': doc_percentage,
                    'quality_score': min(doc_percentage * 2, 100),  # Quality score based on percentage
                    'primary_focus': primary_focus.replace('_', ' ').title()
                }
        
        return results
    
    def _analyze_maintainability_indicators(self):
        """Analyze code maintainability indicators"""
        results = {
            'test_files': 0,
            'ci_cd_files': 0,
            'indicators': {}
        }
        
        if not self.analyzer.detailed_commits:
            return results
        
        indicator_counts = defaultdict(int)
        total_files = 0
        
        for commit in self.analyzer.detailed_commits:
            if 'changes' in commit:
                for change in commit['changes']:
                    if 'item' in change and 'path' in change['item']:
                        file_path = change['item']['path'].lower()
                        total_files += 1
                        
                        for indicator_type, patterns in self.quality_patterns.items():
                            for pattern in patterns:
                                if re.search(pattern, file_path):
                                    indicator_counts[indicator_type] += 1
                                    
                                    if indicator_type == 'tests':
                                        results['test_files'] += 1
                                    elif indicator_type == 'ci_cd':
                                        results['ci_cd_files'] += 1
        
        for indicator_type, count in indicator_counts.items():
            results['indicators'][indicator_type] = {
                'count': count,
                'percentage': (count / total_files * 100) if total_files > 0 else 0,
                'score': self._calculate_maintainability_score(indicator_type, count, total_files),
                'description': self._get_indicator_description(indicator_type)
            }
        
        return results
    
    def _analyze_knowledge_distribution(self):
        """Analyze how knowledge is distributed across the codebase"""
        results = {
            'distribution_score': 0,
            'area_scores': {}
        }
        
        # Define knowledge areas
        knowledge_areas = {
            'Core Logic': ['src/', 'lib/', 'core/', 'main/'],
            'Testing': ['test/', 'tests/', 'spec/', '__tests__/'],
            'Documentation': ['docs/', 'documentation/', '.md', '.rst'],
            'Configuration': ['config/', 'settings/', '.json', '.yaml', '.yml'],
            'Build & Deploy': ['.github/', '.gitlab/', 'deploy/', 'build/']
        }
        
        area_coverage = {}
        total_score = 0
        
        if self.analyzer.detailed_commits:
            all_files = set()
            area_files = defaultdict(set)
            
            for commit in self.analyzer.detailed_commits:
                if 'changes' in commit:
                    for change in commit['changes']:
                        if 'item' in change and 'path' in change['item']:
                            file_path = change['item']['path'].lower()
                            all_files.add(file_path)
                            
                            for area, patterns in knowledge_areas.items():
                                for pattern in patterns:
                                    if pattern in file_path:
                                        area_files[area].add(file_path)
                                        break
            
            total_files = len(all_files)
            
            for area, files in area_files.items():
                coverage = (len(files) / total_files * 100) if total_files > 0 else 0
                quality = self._assess_area_quality(area, len(files), total_files)
                
                area_coverage[area] = {
                    'file_count': len(files),
                    'coverage': coverage,
                    'quality': quality,
                    'details': f"{len(files)} files in {area.lower()}"
                }
                
                total_score += quality
            
            results['area_scores'] = area_coverage
            results['distribution_score'] = round(total_score / len(knowledge_areas) if knowledge_areas else 0, 2)
        
        return results
    
    def _calculate_doc_health(self, doc_coverage, maintainability):
        """Calculate overall documentation health score"""
        score = 0
        
        # Documentation coverage (40%)
        score += min(doc_coverage['coverage_percentage'] * 0.4, 40)
        
        # README presence (20%)
        if doc_coverage['readme_count'] > 0:
            score += 20
        
        # API documentation (20%)
        if doc_coverage['api_docs_count'] > 0:
            score += 20
        
        # Test coverage indicator (20%)
        if maintainability['test_files'] > 0:
            score += 20
        
        if score >= 80:
            return 'Excellent'
        elif score >= 60:
            return 'Good'
        elif score >= 40:
            return 'Fair'
        else:
            return 'Needs Improvement'
    
    def _calculate_category_quality(self, category, count):
        """Calculate quality score for documentation category"""
        if category in ['readme_files', 'api_docs']:
            return 100 if count > 0 else 0
        elif category in ['documentation', 'guides']:
            return min(count * 10, 100)
        else:
            return min(count * 5, 100)
    
    def _assess_knowledge_quality(self, pattern, count):
        """Assess quality based on knowledge pattern"""
        if pattern in ['comments', 'explanations']:
            return min(count * 2, 100)
        elif pattern in ['refactoring', 'improvements']:
            return min(count * 3, 100)
        else:
            return min(count * 1.5, 100)
    
    def _calculate_maintainability_score(self, indicator_type, count, total_files):
        """Calculate maintainability score for indicators"""
        if total_files == 0:
            return 0
        
        percentage = (count / total_files * 100)
        
        if indicator_type == 'tests':
            return min(percentage * 2, 100)  # Tests are highly valuable
        elif indicator_type == 'ci_cd':
            return 100 if count > 0 else 0  # CI/CD presence is binary
        else:
            return min(percentage * 1.5, 100)
    
    def _assess_area_quality(self, area, file_count, total_files):
        """Assess quality of knowledge area coverage"""
        if total_files == 0:
            return 0
        
        percentage = (file_count / total_files * 100)
        
        if area == 'Documentation':
            return min(percentage * 3, 100)  # Documentation is highly valued
        elif area == 'Testing':
            return min(percentage * 2.5, 100)  # Testing is important
        else:
            return min(percentage * 2, 100)
    
    def _get_category_description(self, category):
        """Get description for documentation categories"""
        descriptions = {
            'readme_files': 'Project README files',
            'documentation': 'General documentation files',
            'api_docs': 'API documentation (Swagger/OpenAPI)',
            'inline_docs': 'Inline code documentation',
            'examples': 'Example and sample code',
            'guides': 'How-to guides and walkthroughs',
            'changelog': 'Change logs and release notes',
            'contributing': 'Contribution guidelines'
        }
        return descriptions.get(category, 'Documentation files')
    
    def _get_indicator_description(self, indicator):
        """Get description for maintainability indicators"""
        descriptions = {
            'tests': 'Test files and test suites',
            'ci_cd': 'CI/CD pipeline configuration',
            'linting': 'Code linting configuration',
            'formatting': 'Code formatting tools'
        }
        return descriptions.get(indicator, 'Quality indicator')
    
    def _print_knowledge_insights(self, summary, df_knowledge):
        """Print knowledge management insights"""
        print("\n[KNOWLEDGE] Knowledge Management Summary:")
        print(f"  Documentation files: {summary['Documentation_Files']} ({summary['Documentation_Coverage_Percent']}%)")
        print(f"  README files: {summary['README_Files']}")
        print(f"  API documentation: {summary['API_Documentation']}")
        print(f"  Knowledge sharing commits: {summary['Knowledge_Sharing_Commits']}")
        print(f"  Documentation contributors: {summary['Documentation_Contributors']}")
        print(f"  Documentation health: {summary['Documentation_Health']}")
        
        if not df_knowledge.empty:
            top_categories = df_knowledge.nlargest(5, 'Quality_Score')
            if not top_categories.empty:
                print("\n[TOP] Highest Quality Areas:")
                for _, row in top_categories.iterrows():
                    print(f"  - {row['Category']}: Score {row['Quality_Score']:.0f}/100")
        
        print(f"\n[SCORE] Knowledge Distribution Score: {summary['Knowledge_Distribution_Score']}/100")