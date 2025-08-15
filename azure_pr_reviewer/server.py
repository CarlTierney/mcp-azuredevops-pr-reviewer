"""MCP server for Azure DevOps PR reviews using Claude CLI"""

import asyncio
import logging
import json
from typing import Any, Dict, List, Optional
from mcp.server import FastMCP
from mcp.types import TextContent, Tool
from pydantic import BaseModel

from .azure_client import AzureDevOpsClient
from .code_reviewer import CodeReviewer
from .config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzurePRReviewerServer:
    def __init__(self):
        self.server = FastMCP("azure-pr-reviewer")
        self.settings = Settings()
        self.settings.validate_settings()
        self.azure_client = AzureDevOpsClient(self.settings)
        self.code_reviewer = CodeReviewer(self.settings)
        self._last_review = None  # Store last review for confirmation workflow
        self._setup_tools()
        
    def _setup_tools(self):
        """Register MCP tools"""
        
        @self.server.tool()
        async def list_prs_needing_my_review(
            repository_id: str,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """List pull requests that need your review or approval
            
            This tool filters PRs to show only those that:
            - You are assigned as a reviewer but haven't approved yet
            - Have no reviewers assigned
            - Are waiting for your vote/approval
            
            Args:
                repository_id: Repository name or ID
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                List of PRs needing your attention with status details
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                prs_needing_review = await self.azure_client.list_prs_needing_review(
                    org, proj, repository_id
                )
                
                pr_list = []
                for pr_info in prs_needing_review:
                    pr = pr_info["pr"]
                    pr_list.append({
                        "id": pr.pull_request_id,
                        "title": pr.title,
                        "author": pr.created_by.display_name if pr.created_by else "Unknown",
                        "creation_date": pr.creation_date.isoformat() if pr.creation_date else "Unknown",
                        "source_branch": pr.source_ref_name.replace("refs/heads/", ""),
                        "target_branch": pr.target_ref_name.replace("refs/heads/", ""),
                        "reason": pr_info["reason"],
                        "your_status": pr_info["vote_status"],
                        "is_reviewer": pr_info["is_reviewer"]
                    })
                
                return json.dumps({
                    "status": "success",
                    "count": len(pr_list),
                    "message": f"Found {len(pr_list)} PR(s) needing your review",
                    "pull_requests": pr_list
                }, indent=2)
            except Exception as e:
                logger.error(f"Error listing PRs needing review: {e}")
                return f"Error listing pull requests needing review: {str(e)}"
        
        @self.server.tool()
        async def list_pull_requests(
            repository_id: str,
            status: str = "active",
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """List pull requests from Azure DevOps repository
            
            Args:
                repository_id: Repository name or ID
                status: PR status (active/completed/abandoned)
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                List of pull requests with details
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                prs = await self.azure_client.list_pull_requests(
                    org, proj, repository_id, status
                )
                
                pr_list = []
                for pr in prs:
                    pr_list.append({
                        "id": pr.pull_request_id,
                        "title": pr.title,
                        "description": pr.description,
                        "status": pr.status,
                        "created_by": pr.created_by.display_name if pr.created_by else "Unknown",
                        "creation_date": pr.creation_date.isoformat() if pr.creation_date else "Unknown",
                        "source_branch": pr.source_ref_name,
                        "target_branch": pr.target_ref_name
                    })
                
                return json.dumps({
                    "status": "success",
                    "count": len(pr_list),
                    "pull_requests": pr_list
                }, indent=2)
            except Exception as e:
                logger.error(f"Error listing PRs: {e}")
                return f"Error listing pull requests: {str(e)}"
        
        @self.server.tool()
        async def get_pull_request(
            repository_id: str,
            pull_request_id: int,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Get details of a specific pull request
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                Detailed PR information
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                pr = await self.azure_client.get_pull_request(
                    org, proj, repository_id, pull_request_id
                )
                
                pr_details = {
                    "id": pr.pull_request_id,
                    "title": pr.title,
                    "description": pr.description,
                    "status": pr.status,
                    "created_by": pr.created_by.display_name if pr.created_by else "Unknown",
                    "creation_date": pr.creation_date.isoformat() if pr.creation_date else "Unknown",
                    "source_branch": pr.source_ref_name,
                    "target_branch": pr.target_ref_name,
                    "merge_status": pr.merge_status if hasattr(pr, 'merge_status') else None,
                    "reviewers": [r.display_name for r in pr.reviewers] if pr.reviewers else []
                }
                
                return json.dumps({
                    "status": "success",
                    "pull_request": pr_details
                }, indent=2)
            except Exception as e:
                logger.error(f"Error getting PR: {e}")
                return f"Error getting pull request: {str(e)}"
        
        @self.server.tool()
        async def get_pr_for_review(
            repository_id: str,
            pull_request_id: int,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Get pull request changes formatted for Claude CLI review
            
            This tool fetches PR details and changes, then returns them in a format
            ready for Claude to review. Use this to prepare a PR for code review.
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                PR details and changes ready for review
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                logger.info(f"Fetching PR {pull_request_id} for review")
                
                # Get PR details
                pr = await self.azure_client.get_pull_request(
                    org, proj, repository_id, pull_request_id
                )
                
                # Get PR changes
                changes = await self.azure_client.get_pull_request_changes(
                    org, proj, repository_id, pull_request_id
                )
                
                # Prepare review data
                review_data = self.code_reviewer.prepare_review_data(pr, changes)
                
                # Get review instructions
                instructions = self.code_reviewer.get_review_instructions()
                
                # Include package analysis in response
                package_analysis = review_data.pr_details.get("package_analysis", {})
                
                # Include security analysis results
                security_issues = self.code_reviewer.security_issues
                security_analysis = {
                    "issues_found": len(security_issues),
                    "issues": security_issues,
                    "has_critical_issues": len(security_issues) > 0
                }
                
                return json.dumps({
                    "status": "success",
                    "pr_id": pull_request_id,
                    "review_instructions": instructions,
                    "pr_details": review_data.pr_details,
                    "review_context": review_data.review_prompt,
                    "file_count": len(changes),
                    "file_types": review_data.file_type_summary,
                    "package_analysis": package_analysis,
                    "security_analysis": security_analysis,
                    "message": f"PR data prepared with file-type specific review prompts, package analysis, and security scanning. {len(security_issues)} security issue(s) detected."
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Error preparing PR for review: {e}")
                return f"Error preparing pull request for review: {str(e)}"
        
        @self.server.tool()
        async def preview_review(
            review_json: str,
            store_for_posting: bool = True
        ) -> str:
            """Preview the review before posting to Azure DevOps
            
            This tool shows you what the review will look like before posting.
            After previewing, you can use confirm_and_post_review to post it.
            
            Args:
                review_json: JSON string with review results
                store_for_posting: If True, stores the review for later posting (default: True)
            
            Returns:
                Formatted preview of the review that will be posted
            """
            try:
                # Parse the review JSON
                review_data = json.loads(review_json)
                parsed_review = self.code_reviewer.parse_review_response(review_data)
                
                # Store the review if requested and we have context
                if store_for_posting and self._last_review:
                    self._last_review["review_data"] = parsed_review
                
                # Get PR info from stored context
                pr_info = ""
                if self._last_review:
                    pr_info = f"PR #{self._last_review['pull_request_id']} in {self._last_review['repository_id']}"
                else:
                    pr_info = "Review Preview"
                
                # Format the preview
                preview_lines = [
                    "=" * 60,
                    "REVIEW PREVIEW - NOT POSTED YET",
                    "=" * 60,
                    "",
                    pr_info,
                    f"Status: {'APPROVED' if parsed_review['approved'] else 'CHANGES REQUIRED'}",
                    f"Severity: {parsed_review['severity'].upper()}",
                    "",
                    "--- SUMMARY ---",
                    self.azure_client._format_review_summary(parsed_review),
                    "",
                    "--- LINE COMMENTS ---"
                ]
                
                # Separate general and line-specific comments
                general_comments = []
                comments_by_location = {}
                
                for comment in parsed_review.get("comments", []):
                    file_path = comment.get("file_path")
                    line_num = comment.get("line_number", 0)
                    
                    # Comments with no line number or line 0 are general
                    if not file_path or not line_num or line_num <= 0:
                        general_comments.append(comment)
                    else:
                        location_key = f"{file_path}:{line_num}"
                        if location_key not in comments_by_location:
                            comments_by_location[location_key] = []
                        comments_by_location[location_key].append(comment)
                
                # Show general comments
                if general_comments:
                    preview_lines.append("\n--- GENERAL COMMENTS (will be in summary) ---")
                    for comment in general_comments:
                        severity = comment.get("severity", "info")
                        content = comment.get("content", "")
                        preview_lines.append(f"  [{severity.upper()}] {content}")
                
                # Show line-specific comments
                if comments_by_location:
                    for location, location_comments in sorted(comments_by_location.items()):
                        file_path, line_num = location.rsplit(":", 1)
                        preview_lines.append(f"\n{file_path} (Line {line_num}):")
                        # Consolidate multiple comments on same line
                        consolidated_content = "; ".join([c["content"] for c in location_comments])
                        severity = max([c.get("severity", "info") for c in location_comments])
                        preview_lines.append(f"  [{severity.upper()}] {consolidated_content}")
                else:
                    preview_lines.append("No line-specific comments")
                
                # Show test suggestions
                test_suggestions = parsed_review.get("test_suggestions", [])
                if test_suggestions:
                    preview_lines.extend([
                        "",
                        "--- TEST SUGGESTIONS ---",
                        f"{len(test_suggestions)} test(s) will be suggested:"
                    ])
                    for suggestion in test_suggestions:
                        preview_lines.append(f"  • {suggestion.get('test_name', 'Unknown')}: {suggestion.get('description', '')}")
                
                preview_lines.extend([
                    "",
                    "=" * 60,
                ])
                
                if store_for_posting and self._last_review:
                    preview_lines.extend([
                        "REVIEW STORED - Ready to post",
                        "",
                        "To post this review to Azure DevOps:",
                        "  confirm_and_post_review(confirm=True)",
                        "",
                        "To modify the review:",
                        "  1. Update your review JSON",
                        "  2. Call preview_review again with the new JSON"
                    ])
                else:
                    preview_lines.extend([
                        "To store and post this review:",
                        "  1. First use review_and_confirm to prepare the PR",
                        "  2. Then call preview_review with your review JSON",
                        "  3. Finally use confirm_and_post_review(confirm=True)"
                    ])
                
                return "\n".join(preview_lines)
                
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON format - {e}"
            except Exception as e:
                logger.error(f"Error generating preview: {e}")
                return f"Error generating preview: {str(e)}"
        
        @self.server.tool()
        async def review_and_confirm(
            repository_id: str,
            pull_request_id: int,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Review a PR and show results for confirmation before posting
            
            This tool performs a complete review of the PR and shows you the results.
            After reviewing, you can choose to post the comments or make modifications.
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                The review results with instructions for posting
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                logger.info(f"Performing review of PR {pull_request_id}")
                
                # Get PR details
                pr = await self.azure_client.get_pull_request(
                    org, proj, repository_id, pull_request_id
                )
                
                # Get PR changes
                changes = await self.azure_client.get_pull_request_changes(
                    org, proj, repository_id, pull_request_id
                )
                
                # Prepare review data
                review_data = self.code_reviewer.prepare_review_data(pr, changes)
                
                # Store the review data for later use
                self._last_review = {
                    "repository_id": repository_id,
                    "pull_request_id": pull_request_id,
                    "project": proj,
                    "organization": org,
                    "pr_details": review_data.pr_details,
                    "review_prompt": review_data.review_prompt,
                    "file_count": len(changes),
                    "file_types": review_data.file_type_summary,
                    "package_analysis": review_data.pr_details.get("package_analysis", {})
                }
                
                # Format the response
                response_lines = [
                    "=" * 60,
                    f"REVIEW PREPARED FOR PR #{pull_request_id}",
                    "=" * 60,
                    "",
                    f"Repository: {repository_id}",
                    f"Project: {proj}",
                    f"Title: {pr.title}",
                    f"Author: {pr.created_by.display_name if pr.created_by else 'Unknown'}",
                    f"Source: {pr.source_ref_name.replace('refs/heads/', '')}",
                    f"Target: {pr.target_ref_name.replace('refs/heads/', '')}",
                    "",
                    "FILES CHANGED:",
                    f"  Total files: {len(changes)}",
                    f"  File types: {', '.join(review_data.file_type_summary.keys())}",
                    "",
                    "PACKAGE ANALYSIS:",
                ]
                
                pkg_analysis = review_data.pr_details.get("package_analysis", {})
                if pkg_analysis:
                    response_lines.append(f"  Packages examined: {pkg_analysis.get('total_packages_examined', 0)}")
                    if pkg_analysis.get('has_issues'):
                        response_lines.append(f"  VULNERABILITIES FOUND: {pkg_analysis.get('vulnerable_packages', 0)}")
                        for vuln in pkg_analysis.get('vulnerable_list', [])[:3]:
                            response_lines.append(f"    - {vuln}")
                    else:
                        response_lines.append("  No vulnerabilities detected")
                else:
                    response_lines.append("  No packages found in this PR")
                
                # Add security analysis
                security_issues = self.code_reviewer.security_issues
                response_lines.extend([
                    "",
                    "SECURITY ANALYSIS:",
                    f"  Security issues detected: {len(security_issues)}"
                ])
                
                if security_issues:
                    response_lines.append("  CRITICAL SECURITY ISSUES FOUND:")
                    for issue in security_issues[:5]:  # Show first 5
                        file_path = issue.get('file_path', 'Unknown')
                        line_num = issue.get('line_number', 0)
                        content = issue.get('content', '')[:60] + "..." if len(issue.get('content', '')) > 60 else issue.get('content', '')
                        response_lines.append(f"    - {file_path}:{line_num} - {content}")
                    if len(security_issues) > 5:
                        response_lines.append(f"    - ... and {len(security_issues) - 5} more issues")
                else:
                    response_lines.append("  No security issues detected")
                
                response_lines.extend([
                    "",
                    "=" * 60,
                    "REVIEW DATA PREPARED",
                    "=" * 60,
                    "",
                    "The PR is ready for review. Claude will now analyze the code.",
                    "",
                    "To proceed with the review:",
                    "1. Claude will analyze the code based on the prepared data",
                    "2. You'll see a preview of the review comments",
                    "3. You can then choose to post or modify the review",
                    "",
                    "The review will check for:",
                    "- Code quality and best practices",
                    "- Security vulnerabilities",
                    "- Performance issues",
                    "- Missing tests",
                    "- Package vulnerabilities",
                    "",
                    "Review prompt contains " + str(len(review_data.review_prompt)) + " characters of context.",
                    "",
                    "Please review the PR and provide your analysis in JSON format."
                ])
                
                return "\n".join(response_lines)
                
            except Exception as e:
                logger.error(f"Error performing review: {e}")
                return f"Error performing review: {str(e)}"
        
        @self.server.tool()
        async def post_review_comments(
            repository_id: str,
            pull_request_id: int,
            review_json: str,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Post review comments from Claude's analysis to Azure DevOps
            
            After Claude reviews a PR, use this tool to post the comments back to Azure DevOps.
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number
                review_json: JSON string with review results containing:
                    - approved: boolean
                    - severity: string (approved/minor/major/critical)
                    - summary: string
                    - comments: array of comment objects
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                Status of posted comments
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                # Parse the review JSON
                review_data = json.loads(review_json)
                parsed_review = self.code_reviewer.parse_review_response(review_data)
                
                # Add package analysis to the review if available
                if self.code_reviewer.package_analysis:
                    parsed_review["package_analysis"] = self.code_reviewer.package_analysis
                
                # Use the new integrated posting method
                result = await self.azure_client.post_review_to_azure(
                    org, proj, repository_id, pull_request_id,
                    parsed_review
                )
                
                # Log results
                if result["errors"]:
                    logger.warning(f"Some errors occurred during posting: {result['errors']}")
                
                return json.dumps({
                    "status": "success" if not result["errors"] else "partial_success",
                    "pr_id": pull_request_id,
                    "comments_posted": result["comments_posted"],
                    "vote_updated": result["vote_updated"],
                    "review_status": parsed_review["severity"],
                    "approved": parsed_review["approved"],
                    "errors": result["errors"]
                }, indent=2)
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing review JSON: {e}")
                return f"Error: Invalid JSON format in review_json parameter"
            except Exception as e:
                logger.error(f"Error posting review comments: {e}")
                return f"Error posting review comments: {str(e)}"
        
        @self.server.tool()
        async def add_pr_comment(
            repository_id: str,
            pull_request_id: int,
            comment: str,
            file_path: Optional[str] = None,
            line_number: Optional[int] = None,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Add a single comment to a pull request
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number
                comment: Comment text
                file_path: Optional file path for inline comment
                line_number: Optional line number for inline comment
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                Success/failure status
            """
            try:
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                comment_data = {
                    "content": comment,
                    "file_path": file_path,
                    "line_number": line_number
                }
                
                result = await self.azure_client.add_pull_request_comments(
                    org, proj, repository_id, pull_request_id,
                    [comment_data]
                )
                
                return f"Comment added to PR #{pull_request_id}"
            except Exception as e:
                logger.error(f"Error adding comment: {e}")
                return f"Error adding comment: {str(e)}"
        
        @self.server.tool()
        async def confirm_and_post_review(
            confirm: bool = False
        ) -> str:
            """Confirm and post the last review to Azure DevOps
            
            After reviewing with review_and_confirm and seeing the preview,
            use this tool to post the review to Azure DevOps.
            
            Args:
                confirm: Must be set to True to confirm posting the review
            
            Returns:
                Status of the posted review
            """
            try:
                if not confirm:
                    return (
                        "⚠️ CONFIRMATION REQUIRED ⚠️\n\n"
                        "You are about to post the review to Azure DevOps.\n"
                        "This will add comments to the PR that are visible to all reviewers.\n\n"
                        "To confirm, call this tool again with confirm=True:\n"
                        "confirm_and_post_review(confirm=True)"
                    )
                
                if not self._last_review:
                    return (
                        "Error: No review prepared.\n"
                        "Please use 'review_and_confirm' first to prepare a review,\n"
                        "then use 'preview_review' to see what will be posted,\n"
                        "and finally use this tool to post the review."
                    )
                
                # Get the stored review data
                review_data = self._last_review.get("review_data")
                if not review_data:
                    return "Error: Review data is missing. Please prepare a new review."
                
                # Store values before clearing
                pr_id = self._last_review["pull_request_id"]
                
                # Post the review
                result = await self.azure_client.post_review_to_azure(
                    self._last_review["organization"],
                    self._last_review["project"],
                    self._last_review["repository_id"],
                    self._last_review["pull_request_id"],
                    review_data
                )
                
                # Clear the stored review
                self._last_review = None
                
                # Format response
                response_lines = [
                    "=" * 60,
                    "REVIEW POSTED SUCCESSFULLY",
                    "=" * 60,
                    "",
                    f"PR #{pr_id} has been reviewed.",
                    f"Comments posted: {result['comments_posted']}",
                    f"Vote updated: {'Yes' if result['vote_updated'] else 'No'}",
                ]
                
                if result.get("errors"):
                    response_lines.extend([
                        "",
                        "⚠️ Some issues occurred:",
                    ])
                    for error in result["errors"]:
                        response_lines.append(f"  - {error}")
                else:
                    response_lines.extend([
                        "",
                        "✅ All review comments posted successfully.",
                        "",
                        "The review is now visible in Azure DevOps."
                    ])
                
                return "\n".join(response_lines)
                
            except Exception as e:
                logger.error(f"Error posting review: {e}")
                return f"Error posting review: {str(e)}"
        
        @self.server.tool()
        async def approve_pull_request(
            repository_id: str,
            pull_request_id: int,
            confirm: bool = False,
            comment: Optional[str] = None,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Approve a pull request in Azure DevOps
            
            IMPORTANT: This action will approve the PR on your behalf. Please review carefully before approving.
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number to approve
                confirm: Must be set to True to confirm the approval action
                comment: Optional approval comment to add
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                Confirmation of approval or error message
            """
            try:
                # Require explicit confirmation
                if not confirm:
                    return (
                        "⚠️ APPROVAL CONFIRMATION REQUIRED ⚠️\n\n"
                        f"You are about to approve PR #{pull_request_id} in {repository_id}.\n"
                        "This action will mark the PR as approved on your behalf.\n\n"
                        "To confirm this action, please set the 'confirm' parameter to True.\n"
                        "Example: approve_pull_request(project='...', repository_id='...', "
                        f"pull_request_id={pull_request_id}, confirm=True)"
                    )
                
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                # First, get the PR details to show what's being approved
                pr = await self.azure_client.get_pull_request(
                    org, proj, repository_id, pull_request_id
                )
                
                # Call the approve function
                await self.azure_client.approve_pull_request(
                    org, proj, repository_id, pull_request_id
                )
                
                # Add custom approval comment if provided
                if comment:
                    comment_data = {
                        "content": f"✅ **PR Approved**\n\n{comment}",
                        "file_path": None,
                        "line_number": None
                    }
                    await self.azure_client.add_pull_request_comments(
                        org, proj, repository_id, pull_request_id,
                        [comment_data]
                    )
                
                return (
                    f"✅ Successfully approved PR #{pull_request_id}: {pr.title}\n"
                    f"Author: {pr.created_by.display_name if pr.created_by else 'Unknown'}\n"
                    f"Target Branch: {pr.target_ref_name.replace('refs/heads/', '')}\n"
                    + (f"\nComment added: {comment}" if comment else "")
                )
                
            except Exception as e:
                logger.error(f"Error approving PR: {e}")
                return f"Error approving PR #{pull_request_id}: {str(e)}"
        
        @self.server.tool()
        async def reject_pull_request(
            repository_id: str,
            pull_request_id: int,
            reason: str,
            confirm: bool = False,
            require_changes: bool = True,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Reject a pull request in Azure DevOps
            
            IMPORTANT: This action will reject the PR and require changes. Use with caution.
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number to reject
                reason: Reason for rejection (will be posted as a comment)
                confirm: Must be set to True to confirm the rejection
                require_changes: If True, sets vote to "Rejected" (-10), if False sets to "Wait for author" (-5)
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                Confirmation of rejection or error message
            """
            try:
                # Require explicit confirmation
                if not confirm:
                    return (
                        "⚠️ REJECTION CONFIRMATION REQUIRED ⚠️\n\n"
                        f"You are about to REJECT PR #{pull_request_id} in {repository_id}.\n"
                        "This action will:\n"
                        "  - Mark the PR as requiring changes\n"
                        "  - Post your rejection reason as a comment\n"
                        "  - Notify the author that changes are needed\n\n"
                        "To confirm this action, set 'confirm=True'\n"
                        f"Example: reject_pull_request(repository_id='{repository_id}', "
                        f"pull_request_id={pull_request_id}, reason='...', confirm=True)"
                    )
                
                # Validate reason
                if not reason or len(reason.strip()) < 10:
                    return "Error: Please provide a detailed reason for rejection (at least 10 characters)"
                
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured. Set AZURE_DEVOPS_ORG environment variable."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified. Provide project parameter or set AZURE_DEVOPS_PROJECT environment variable."
                
                # Get PR details
                pr = await self.azure_client.get_pull_request(
                    org, proj, repository_id, pull_request_id
                )
                
                # Create rejection review data
                review_data = {
                    "approved": False,
                    "severity": "critical" if require_changes else "major",
                    "summary": f"PR REJECTED: {reason}",
                    "comments": []
                }
                
                # Post the rejection review
                result = await self.azure_client.post_review_to_azure(
                    org, proj, repository_id, pull_request_id, review_data
                )
                
                # Add rejection comment
                rejection_comment = {
                    "content": (
                        f"## ❌ PR Rejected\n\n"
                        f"**Reason:** {reason}\n\n"
                        f"**Status:** {'Changes Required' if require_changes else 'Waiting for Author'}\n\n"
                        f"Please address the issues mentioned above and update the PR.\n\n"
                        f"---\n"
                        f"*Rejected by Azure PR Reviewer v2.0.0*\n"
                        f"*Timestamp: {self.azure_client._get_timestamp()}*"
                    ),
                    "file_path": None,
                    "line_number": None
                }
                
                await self.azure_client.add_pull_request_comments(
                    org, proj, repository_id, pull_request_id,
                    [rejection_comment]
                )
                
                return (
                    f"❌ PR #{pull_request_id} has been REJECTED\n\n"
                    f"**PR Title:** {pr.title}\n"
                    f"**Author:** {pr.created_by.display_name if pr.created_by else 'Unknown'}\n"
                    f"**Reason:** {reason}\n"
                    f"**Vote Status:** {'Rejected (-10)' if require_changes else 'Wait for Author (-5)'}\n\n"
                    f"The author has been notified and must address the issues before the PR can be approved."
                )
                
            except Exception as e:
                logger.error(f"Error rejecting PR: {e}")
                return f"Error rejecting PR #{pull_request_id}: {str(e)}"
        
        @self.server.tool()
        async def set_pr_vote(
            repository_id: str,
            pull_request_id: int,
            vote: str,
            comment: Optional[str] = None,
            project: Optional[str] = None,
            organization: Optional[str] = None
        ) -> str:
            """Set your vote on a pull request
            
            Args:
                repository_id: Repository name or ID
                pull_request_id: PR number
                vote: Vote value - one of: 'approve', 'approve_with_suggestions', 'no_vote', 'wait_for_author', 'reject'
                comment: Optional comment to add with the vote
                project: Project name (uses env var if not provided)
                organization: Azure DevOps organization name (uses env var if not provided)
            
            Returns:
                Confirmation of vote update
            """
            try:
                # Map vote strings to Azure DevOps vote values
                vote_map = {
                    'approve': 10,
                    'approve_with_suggestions': 5,
                    'no_vote': 0,
                    'wait_for_author': -5,
                    'reject': -10
                }
                
                if vote not in vote_map:
                    return f"Error: Invalid vote '{vote}'. Must be one of: {', '.join(vote_map.keys())}"
                
                vote_value = vote_map[vote]
                
                # Use environment variables if not provided
                org = organization or self.settings.azure_organization
                if not org:
                    return "Error: Azure DevOps organization not configured."
                
                proj = project or self.settings.azure_project
                if not proj:
                    return "Error: Azure DevOps project not specified."
                
                # Update the vote
                await self.azure_client.update_pull_request_vote(
                    org, proj, repository_id, pull_request_id, vote_value
                )
                
                # Add comment if provided
                if comment:
                    vote_comment = {
                        "content": (
                            f"**Vote Updated: {vote.replace('_', ' ').title()}**\n\n"
                            f"{comment}\n\n"
                            f"---\n"
                            f"*Azure PR Reviewer v2.0.0*"
                        ),
                        "file_path": None,
                        "line_number": None
                    }
                    await self.azure_client.add_pull_request_comments(
                        org, proj, repository_id, pull_request_id,
                        [vote_comment]
                    )
                
                return (
                    f"✅ Vote updated successfully\n"
                    f"PR #{pull_request_id}: {vote.replace('_', ' ').title()}\n"
                    f"Vote value: {vote_value}"
                    + (f"\nComment added: {comment}" if comment else "")
                )
                
            except Exception as e:
                logger.error(f"Error setting vote: {e}")
                return f"Error setting vote: {str(e)}"
    
    def run(self):
        """Run the MCP server"""
        logger.info("Starting Azure PR Reviewer MCP Server")
        self.server.run()


def main():
    """Main entry point"""
    import sys
    
    # Check if running with stdio transport
    if "--stdio" in sys.argv or len(sys.argv) == 1:
        server = AzurePRReviewerServer()
        server.run()
    else:
        print("Azure DevOps PR Reviewer MCP Server")
        print("Usage: python -m azure_pr_reviewer.server [--stdio]")
        print("\nThis server should be run through an MCP client like Claude Code.")
        print("\nAvailable tools:")
        print("  - list_prs_needing_my_review: List PRs that need your review/approval")
        print("  - list_pull_requests: List all PRs in a repository")
        print("  - get_pull_request: Get details of a specific PR")
        print("  - get_pr_for_review: Prepare PR data for Claude CLI review")
        print("  - post_review_comments: Post Claude's review back to Azure DevOps")
        print("  - add_pr_comment: Add a single comment to a PR")


if __name__ == "__main__":
    main()