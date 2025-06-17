#!/usr/bin/env python3
"""
Main Azure DevOps analyzer that orchestrates all analysis components
"""

import os
import json
import glob
import sys
from datetime import datetime

# Add the parent directory to sys.path to enable imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.base_analyzer import BaseAnalyzer
from analyzers.data_collector import DataCollector
from analyzers.developer_analyzer import DeveloperAnalyzer
from analyzers.quality_analyzer import QualityAnalyzer
from analyzers.hotspot_analyzer import HotspotAnalyzer
from analyzers.language_analyzer import LanguageAnalyzer
from analyzers.contribution_analyzer import ContributionAnalyzer

class AzureDevOpsAnalyzer(BaseAnalyzer):
    def __init__(self, org_name, project_name, repo_name, pat_token, data_dir="./azdo_analytics", 
                 date_from=None, date_to=None):
        super().__init__(org_name, project_name, repo_name, pat_token, data_dir, date_from, date_to)
        
        # Initialize analyzer components
        self.data_collector = DataCollector(self)
        self.developer_analyzer = DeveloperAnalyzer(self)
        self.quality_analyzer = QualityAnalyzer(self)
        self.hotspot_analyzer = HotspotAnalyzer(self)
        self.language_analyzer = LanguageAnalyzer(self)
        self.contribution_analyzer = ContributionAnalyzer(self)
        
        print(f"✓ Configured for Azure DevOps analysis")
        print(f"  Organization: {org_name}")
        print(f"  Project: {project_name}")
        print(f"  Repository: {repo_name}")
        print(f"  Date Filter: {self.date_from_dt.strftime('%Y-%m-%d')} to {self.date_to_dt.strftime('%Y-%m-%d')}")

    def collect_all_data(self):
        """Collect all data from Azure DevOps APIs"""
        return self.data_collector.collect_all_data()

    def load_collected_data(self):
        """Load collected data alias for backward compatibility"""
        return self.data_collector.load_collected_data()

    def load_data(self):
        """Load collected data"""
        return self.data_collector.load_collected_data()

    def analyze_repository_basic_stats(self):
        """Analyze basic repository statistics"""
        print("\n=== BASIC REPOSITORY STATISTICS ===")
        
        if not self.commits:
            print("No commit data available")
            return
        
        # Basic statistics
        total_commits = len(self.commits)
        total_detailed_commits = len(self.detailed_commits)
        
        # Developer count
        developers = set()
        for commit in self.commits:
            author_info = self.get_author_info(commit.get('author', {}))
            developers.add(author_info['unique_name'])
        
        print(f"📊 Repository Overview:")
        print(f"  • Total commits: {total_commits:,}")
        print(f"  • Detailed commits analyzed: {total_detailed_commits:,}")
        print(f"  • Active developers: {len(developers)}")
        print(f"  • Date range: {self.date_from_dt.strftime('%Y-%m-%d')} to {self.date_to_dt.strftime('%Y-%m-%d')}")
        
        if self.pull_requests:
            print(f"  • Pull requests: {len(self.pull_requests)}")

    def analyze_developer_activity(self):
        """Analyze developer activity patterns"""
        return self.developer_analyzer.analyze_developer_activity()

    def analyze_pull_requests(self):
        """Analyze pull request patterns"""
        return self.developer_analyzer.analyze_pull_request_metrics()

    def analyze_pull_request_metrics(self):
        """Alias for backward compatibility"""
        return self.analyze_pull_requests()

    def analyze_enhanced_quality_metrics(self):
        """Enhanced quality metrics analysis by calendar month"""
        return self.quality_analyzer.analyze_enhanced_quality_metrics()

    def analyze_commit_timing(self):
        """Analyze comprehensive contribution metrics with timing patterns"""
        return self.contribution_analyzer.analyze_commit_timing()

    def analyze_language_complexity_distribution(self):
        """Analyze complexity distribution across ALL files in repository"""
        return self.language_analyzer.analyze_language_complexity_distribution()

    def analyze_bus_factor_and_hotspots(self):
        """Analyze bus factor and hotspots for ALL repository files"""
        return self.hotspot_analyzer.analyze_bus_factor_and_hotspots()

    def analyze_advanced_developer_contributions(self):
        """Analyze advanced developer contributions with real metrics"""
        return self.contribution_analyzer.analyze_advanced_developer_contributions()

    def analyze_security_insights(self):
        """Analyze security-related patterns in commits"""
        print("\n=== SECURITY ANALYSIS ===")
        print("Security analysis not implemented in this version")

    def analyze_knowledge_management(self):
        """Analyze knowledge management patterns"""
        print("\n=== KNOWLEDGE MANAGEMENT ANALYSIS ===")
        print("Knowledge management analysis not implemented in this version")

    def run_complete_analysis(self):
        """Run complete analysis workflow with all metrics and insights"""
        print("🚀 Starting Complete Azure DevOps Repository Analysis")
        print("=" * 60)
        
        try:
            # Step 1: Collect all data from Azure DevOps
            print("\n📊 STEP 1: Data Collection")
            repo_id = self.collect_all_data()
            
            # Step 2: Load and validate collected data
            print("\n📂 STEP 2: Data Loading & Validation")
            self.load_collected_data()
            
            if not self.commits:
                print("❌ No commits data found. Cannot proceed with analysis.")
                return False
            
            print(f"✅ Loaded {len(self.commits)} commits and {len(self.detailed_commits)} detailed commits")
            
            # Step 3: Run all analysis modules
            print("\n🔍 STEP 3: Running Analysis Modules")
            
            # Basic repository analysis
            print("\n📈 Running basic repository analysis...")
            self.analyze_repository_basic_stats()
            
            # Developer activity analysis
            print("\n👥 Running developer activity analysis...")
            self.analyze_developer_activity()
            
            # Pull request analysis
            print("\n🔀 Running pull request analysis...")
            self.analyze_pull_requests()
            
            # Contribution metrics (enhanced timing + quality)
            print("\n⏰ Running contribution metrics analysis...")
            self.analyze_commit_timing()
            
            # Language complexity distribution
            print("\n🌐 Running language complexity analysis...")
            self.analyze_language_complexity_distribution()
            
            # Bus factor and hotspots analysis
            print("\n🔥 Running bus factor & hotspots analysis...")
            self.analyze_bus_factor_and_hotspots()
            
            # Enhanced quality metrics by month
            print("\n📅 Running monthly quality metrics analysis...")
            self.analyze_enhanced_quality_metrics()
            
            # Advanced developer contributions
            print("\n🏆 Running advanced developer contributions analysis...")
            self.analyze_advanced_developer_contributions()
            
            # Security analysis
            print("\n🔒 Running security analysis...")
            self.analyze_security_insights()
            
            # Knowledge management analysis
            print("\n📚 Running knowledge management analysis...")
            self.analyze_knowledge_management()
            
            # Step 4: Generate comprehensive summary
            print("\n📋 STEP 4: Generating Comprehensive Summary")
            self.generate_analysis_summary()
            
            print("\n✅ COMPLETE ANALYSIS FINISHED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📁 Results saved in: {self.data_dir}")
            print("\n📊 Generated Reports:")
            
            # List all generated CSV files
            csv_files = glob.glob(f"{self.data_dir}/*.csv")
            for csv_file in sorted(csv_files):
                filename = os.path.basename(csv_file)
                print(f"  • {filename}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_analysis_summary(self):
        """Generate a comprehensive analysis summary"""
        print("\n📊 Generating comprehensive analysis summary...")
        
        try:
            summary_data = {
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'repository_info': {
                    'total_commits': len(self.commits),
                    'detailed_commits': len(self.detailed_commits),
                    'date_range': f"{self.date_from} to {self.date_to}",
                    'organization': self.org_name,
                    'project': self.project_name,
                    'repository': self.repo_name
                }
            }
            
            # Try to gather key metrics from generated files
            try:
                import pandas as pd
                
                # Developer metrics
                contrib_file = f"{self.data_dir}/azdo_contribution_metrics.csv"
                if os.path.exists(contrib_file):
                    df_contrib = pd.read_csv(contrib_file)
                    summary_data['developer_metrics'] = {
                        'total_developers': len(df_contrib),
                        'top_contributor': df_contrib.iloc[0]['Developer'] if not df_contrib.empty else 'Unknown',
                        'avg_contribution_score': round(df_contrib['Overall_Contribution_Score'].mean(), 1) if 'Overall_Contribution_Score' in df_contrib.columns else 0
                    }
                
                # Language complexity
                lang_file = f"{self.data_dir}/azdo_language_complexity.csv"
                if os.path.exists(lang_file):
                    df_lang = pd.read_csv(lang_file)
                    summary_data['language_metrics'] = {
                        'languages_analyzed': len(df_lang),
                        'total_files': df_lang['Unique_Files'].sum() if 'Unique_Files' in df_lang.columns else 0,
                        'highest_risk_language': df_lang.iloc[0]['Language_Type'] if not df_lang.empty else 'Unknown'
                    }
                
                # Bus factor analysis
                hotspot_file = f"{self.data_dir}/azdo_file_hotspots_analysis.csv"
                if os.path.exists(hotspot_file):
                    df_hotspots = pd.read_csv(hotspot_file)
                    summary_data['risk_metrics'] = {
                        'files_analyzed': len(df_hotspots),
                        'critical_files': df_hotspots['Is_Critical'].sum() if 'Is_Critical' in df_hotspots.columns else 0,
                        'high_risk_files': (df_hotspots['Bus_Factor_Risk'] >= 3.0).sum() if 'Bus_Factor_Risk' in df_hotspots.columns else 0
                    }
                
            except Exception as e:
                print(f"Warning: Could not gather summary metrics: {e}")
            
            # Save summary
            summary_file = f"{self.data_dir}/analysis_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2, default=str)
            
            print(f"✅ Analysis summary saved to: {summary_file}")
            
            # Print key insights
            print(f"\n🎯 KEY INSIGHTS:")
            if 'developer_metrics' in summary_data:
                dev_metrics = summary_data['developer_metrics']
                print(f"  • {dev_metrics['total_developers']} developers analyzed")
                print(f"  • Top contributor: {dev_metrics['top_contributor']}")
                print(f"  • Average contribution score: {dev_metrics['avg_contribution_score']}/100")
            
            if 'language_metrics' in summary_data:
                lang_metrics = summary_data['language_metrics']
                print(f"  • {lang_metrics['languages_analyzed']} programming languages")
                print(f"  • {lang_metrics['total_files']} unique files analyzed")
                print(f"  • Highest complexity risk: {lang_metrics['highest_risk_language']}")
            
            if 'risk_metrics' in summary_data:
                risk_metrics = summary_data['risk_metrics']
                print(f"  • {risk_metrics['critical_files']} critical files identified")
                print(f"  • {risk_metrics['high_risk_files']} high bus factor risk files")
        
        except Exception as e:
            print(f"Warning: Could not generate analysis summary: {e}")
