"""Configuration settings for the Azure PR Reviewer"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # Azure DevOps settings
    azure_organization: str = Field(
        default=os.getenv("AZURE_DEVOPS_ORG", ""),
        description="Azure DevOps organization name"
    )
    azure_pat: str = Field(
        default=os.getenv("AZURE_DEVOPS_PAT", ""),
        description="Azure DevOps Personal Access Token"
    )
    azure_user_email: Optional[str] = Field(
        default=os.getenv("AZURE_USER_EMAIL", None),
        description="Your Azure DevOps email for filtering PRs"
    )
    azure_project: Optional[str] = Field(
        default=os.getenv("AZURE_DEVOPS_PROJECT", None),
        description="Default Azure DevOps project name"
    )
    
    # Working directory settings
    working_directory: str = Field(
        default=os.getenv("WORKING_DIRECTORY", "./temp_pr_analysis"),
        description="Directory for checking out code for analysis"
    )
    auto_cleanup: bool = Field(
        default=os.getenv("AUTO_CLEANUP", "true").lower() == "true",
        description="Automatically clean up working directory after analysis"
    )
    
    # Review settings - No API key needed since we'll use Claude CLI directly
    
    # Review settings
    auto_approve_threshold: float = Field(
        default=0.9,
        description="Confidence threshold for auto-approval (0-1)"
    )
    max_files_per_review: int = Field(
        default=int(os.getenv("MAX_FILES_PER_REVIEW", "5000")),
        description="Maximum number of files to review"
    )
    max_total_size_gb: float = Field(
        default=float(os.getenv("MAX_TOTAL_SIZE_GB", "2.0")),
        description="Maximum total size in GB"
    )
    review_model: str = Field(
        default=os.getenv("REVIEW_MODEL", "claude-3-5-sonnet-20241022"),
        description="Claude model to use for reviews"
    )
    custom_review_prompt_file: Optional[str] = Field(
        default=os.getenv("CUSTOM_REVIEW_PROMPT_FILE", None),
        description="Path to custom review prompt file"
    )
    
    # MCP Server settings
    server_name: str = Field(
        default="azure-pr-reviewer",
        description="MCP server name"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }
    
    def validate_settings(self) -> bool:
        """Validate that required settings are present"""
        errors = []
        
        if not self.azure_organization:
            errors.append("AZURE_DEVOPS_ORG is required")
        if not self.azure_pat:
            errors.append("AZURE_DEVOPS_PAT is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True