#!/usr/bin/env python
"""Standalone Azure PR Reviewer MCP Server - works like simple_test.py"""

import sys
import os

# Add the current directory to Python path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import FastMCP
from azure_pr_reviewer.azure_client import AzureDevOpsClient
from azure_pr_reviewer.code_reviewer import CodeReviewer
from azure_pr_reviewer.config import Settings

# Create the MCP server directly (like simple_test.py does)
mcp = FastMCP("azure-pr-reviewer")

# Initialize components
settings = Settings()
settings.validate_settings()
azure_client = AzureDevOpsClient(settings)
code_reviewer = CodeReviewer(settings)

@mcp.tool()
async def list_prs_needing_my_review(project: str, repository: str = None, max_results: int = 20) -> str:
    """List pull requests that need your review or approval"""
    try:
        result = await azure_client.list_prs_needing_review(
            settings.azure_devops_org,
            project,
            repository
        )
        
        if not result:
            return "No PRs found that need your review."
        
        output = []
        for pr in result[:max_results]:
            output.append(f"PR #{pr.get('pullRequestId')}: {pr.get('title')}")
            output.append(f"  Author: {pr.get('createdBy', {}).get('displayName', 'Unknown')}")
            output.append(f"  Repository: {pr.get('repository', {}).get('name', 'Unknown')}")
            output.append("")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error listing PRs: {str(e)}"

@mcp.tool()
async def list_pull_requests(project: str, repository: str, status: str = "active", max_results: int = 20) -> str:
    """List all pull requests in a repository"""
    try:
        result = await azure_client.list_pull_requests(
            settings.azure_devops_org,
            project,
            repository,
            status
        )
        
        if not result:
            return f"No {status} PRs found in {project}/{repository}."
        
        output = []
        for pr in result[:max_results]:
            output.append(f"PR #{pr.get('pullRequestId')}: {pr.get('title')}")
            output.append(f"  Status: {pr.get('status')}")
            output.append(f"  Author: {pr.get('createdBy', {}).get('displayName', 'Unknown')}")
            output.append("")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error listing PRs: {str(e)}"

@mcp.tool()
async def get_pr_for_review(project: str, repository: str, pr_id: int) -> str:
    """Get a pull request ready for Claude to review"""
    try:
        # Get PR details
        pr = await azure_client.get_pull_request(
            settings.azure_devops_org,
            project,
            repository,
            pr_id
        )
        
        if not pr:
            return f"PR #{pr_id} not found."
        
        # Get PR changes
        changes = await azure_client.get_pull_request_changes(
            settings.azure_devops_org,
            project,
            repository,
            pr_id
        )
        
        # Prepare review data
        review_data = code_reviewer.prepare_review_data(pr, changes)
        
        output = []
        output.append(f"PR #{pr_id}: {pr.get('title', 'Untitled')}")
        output.append(f"Author: {pr.get('createdBy', {}).get('displayName', 'Unknown')}")
        output.append(f"Description: {pr.get('description', 'No description')}")
        output.append("")
        output.append("Files Changed:")
        
        for change in changes[:10]:  # Limit to first 10 files for preview
            output.append(f"  - {change.get('path', 'Unknown path')}")
        
        if len(changes) > 10:
            output.append(f"  ... and {len(changes) - 10} more files")
        
        output.append("")
        output.append("Ready for review. Use the review data to analyze the changes.")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error getting PR: {str(e)}"

@mcp.tool()
async def post_review_comments(
    repository: str, 
    pr_id: int, 
    review_json: str, 
    project: str = None,
    organization: str = None
) -> str:
    """Post complete review results to Azure DevOps including comments and vote
    
    Args:
        repository: Repository name
        pr_id: Pull request ID
        review_json: JSON string with review results containing:
            - approved: boolean
            - severity: string (approved/minor/major/critical)
            - summary: string
            - comments: array of comment objects
        project: Project name (optional, uses settings if not provided)
        organization: Organization name (optional, uses settings if not provided)
    """
    try:
        import json
        
        # Use provided or default values
        org = organization or settings.azure_organization
        proj = project or settings.azure_project
        
        # Parse the review JSON
        review_data = json.loads(review_json)
        parsed_review = code_reviewer.parse_review_response(review_data)
        
        # Use the integrated posting method
        result = await azure_client.post_review_to_azure(
            org, proj, repository, pr_id, parsed_review
        )
        
        return json.dumps({
            "status": "success" if not result["errors"] else "partial_success",
            "pr_id": pr_id,
            "comments_posted": result["comments_posted"],
            "vote_updated": result["vote_updated"],
            "review_status": parsed_review["severity"],
            "approved": parsed_review["approved"],
            "errors": result["errors"]
        }, indent=2)
        
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON format in review_json parameter: {e}"
    except Exception as e:
        return f"Error posting review: {str(e)}"

@mcp.tool()
async def approve_pull_request(
    repository: str,
    pr_id: int,
    confirm: bool = False,
    comment: str = None,
    project: str = None,
    organization: str = None
) -> str:
    """Approve a pull request in Azure DevOps
    
    IMPORTANT: This action will approve the PR on your behalf.
    
    Args:
        repository: Repository name
        pr_id: Pull request ID
        confirm: Must be set to True to confirm the approval
        comment: Optional approval comment
        project: Project name (optional)
        organization: Organization name (optional)
    """
    try:
        if not confirm:
            return (
                f"⚠️ APPROVAL CONFIRMATION REQUIRED ⚠️\n\n"
                f"You are about to approve PR #{pr_id} in {repository}.\n"
                f"To confirm, set confirm=True"
            )
        
        org = organization or settings.azure_organization
        proj = project or settings.azure_project
        
        await azure_client.approve_pull_request(org, proj, repository, pr_id)
        
        if comment:
            # Add additional comment
            await azure_client.add_pull_request_comments(
                org, proj, repository, pr_id, 
                [{"content": f"✅ **PR Approved**\n\n{comment}", "file_path": None, "line_number": None}]
            )
        
        return f"Successfully approved PR #{pr_id} in {repository}"
        
    except Exception as e:
        return f"Error approving PR: {str(e)}"

if __name__ == "__main__":
    # Run the server directly (like simple_test.py)
    mcp.run()