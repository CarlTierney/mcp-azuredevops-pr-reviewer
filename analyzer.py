"""
Standalone Azure DevOps Repository Analytics Analyzer
Main entry point - imports from refactored modules
"""

# Import warnings configuration
import pandas as pd
import warnings
import os
import sys

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# Add the current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

warnings.filterwarnings("ignore", category=pd.errors.SettingWithCopyWarning)

# Import from refactored modules
try:
    from core.main_analyzer import AzureDevOpsAnalyzer
    print("[OK] Using refactored modular analyzer")
except ImportError as e:
    print(f"[ERROR] Failed to import refactored modules: {e}")
    print("Please ensure all analyzer modules are in place.")
    sys.exit(1)

# Export for backward compatibility
__all__ = ['AzureDevOpsAnalyzer']