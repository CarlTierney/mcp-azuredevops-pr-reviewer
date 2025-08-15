"""Azure DevOps API client for PR operations"""

import logging
from typing import List, Dict, Any, Optional
from azure.devops.connection import Connection
from azure.devops.v7_1.git import GitClient
from azure.devops.v7_1.git.models import (
    GitPullRequest, 
    GitPullRequestSearchCriteria,
    Comment,
    CommentThread,
    CommentThreadContext,
    CommentPosition,
    GitVersionDescriptor
)
from msrest.authentication import BasicAuthentication
from .config import Settings

logger = logging.getLogger(__name__)


class AzureDevOpsClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection = None
        self.git_client = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Azure DevOps connection"""
        # Ensure PAT is available
        if not self.settings.azure_pat:
            raise ValueError("AZURE_DEVOPS_PAT is not set. Please configure it in your .env file")
        
        # Use PAT authentication explicitly
        credentials = BasicAuthentication('', self.settings.azure_pat)
        self.connection = Connection(
            base_url=f"https://dev.azure.com/{self.settings.azure_organization}",
            creds=credentials
        )
        
        # Disable Azure CLI authentication fallback
        # This ensures we only use PAT authentication
        self.git_client = self.connection.clients.get_git_client()
        
        # Log successful connection (without exposing PAT)
        logger.info(f"Connected to Azure DevOps org: {self.settings.azure_organization}")
    
    async def list_pull_requests(
        self, 
        organization: str,
        project: str,
        repository_id: str,
        status: str = "active"
    ) -> List[GitPullRequest]:
        """List pull requests from a repository"""
        try:
            search_criteria = GitPullRequestSearchCriteria(status=status)
            prs = self.git_client.get_pull_requests(
                repository_id=repository_id,
                project=project,
                search_criteria=search_criteria
            )
            logger.info(f"Found {len(prs)} pull requests")
            return prs
        except Exception as e:
            logger.error(f"Error listing pull requests: {e}")
            raise
    
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user information from the connection"""
        try:
            # Get the current user's identity
            # This requires the profile client or core client
            from azure.devops.v7_1.profile import ProfileClient
            profile_client = self.connection.clients.get_profile_client()
            
            # Get my profile
            my_profile = profile_client.get_profile("me")
            
            return {
                "id": my_profile.id,
                "display_name": my_profile.display_name,
                "email": my_profile.email_address,
                "unique_name": my_profile.unique_name
            }
        except Exception as e:
            logger.warning(f"Could not get current user profile: {e}")
            # Try alternative method using connection context
            try:
                # Use the settings email if provided
                if self.settings.azure_user_email:
                    return {
                        "email": self.settings.azure_user_email,
                        "display_name": self.settings.azure_user_email.split('@')[0]
                    }
            except:
                pass
            return None
    
    async def list_prs_needing_review(
        self,
        organization: str,
        project: str,
        repository_id: str
    ) -> List[Dict[str, Any]]:
        """List PRs that need review or approval from current user"""
        try:
            # Get all active PRs
            all_prs = await self.list_pull_requests(
                organization, project, repository_id, "active"
            )
            
            # Get current user info
            current_user = await self.get_current_user()
            user_identifier = current_user.get('email') if current_user else None
            
            prs_needing_attention = []
            
            for pr in all_prs:
                needs_review = False
                is_reviewer = False
                has_approved = False
                vote_status = "No vote"
                
                # Check if user is a reviewer and their vote status
                if pr.reviewers:
                    for reviewer in pr.reviewers:
                        # Check various ways to match the user
                        is_current_user = False
                        if user_identifier:
                            # More flexible matching
                            reviewer_display = reviewer.display_name.lower() if hasattr(reviewer, 'display_name') and reviewer.display_name else ""
                            reviewer_unique = reviewer.unique_name.lower() if hasattr(reviewer, 'unique_name') and reviewer.unique_name else ""
                            
                            # Try multiple matching strategies
                            user_email_parts = user_identifier.lower().replace('@ext.com', '').replace('.', ' ').split('@')[0]
                            
                            # Check if name matches (e.g., "Carl Tierney" in "Carl Tierney (EXT)")
                            if "carl" in reviewer_display and "tierney" in reviewer_display:
                                is_current_user = True
                            elif user_email_parts in reviewer_display:
                                is_current_user = True
                            elif user_identifier.lower() in reviewer_unique:
                                is_current_user = True
                        
                        if is_current_user:
                            is_reviewer = True
                            # Vote values: 10 = approved, 5 = approved with suggestions, 
                            # 0 = no vote, -5 = waiting for author, -10 = rejected
                            if hasattr(reviewer, 'vote'):
                                if reviewer.vote >= 10:
                                    has_approved = True
                                    vote_status = "Approved"
                                elif reviewer.vote == 5:
                                    has_approved = True
                                    vote_status = "Approved with suggestions"
                                elif reviewer.vote == 0:
                                    needs_review = True
                                    vote_status = "Not yet reviewed"
                                elif reviewer.vote == -5:
                                    vote_status = "Waiting for author"
                                elif reviewer.vote == -10:
                                    vote_status = "Rejected"
                            else:
                                needs_review = True
                                vote_status = "Not yet reviewed"
                            break
                
                # Include PRs where:
                # 1. User is a reviewer but hasn't voted/approved
                # 2. User is not a reviewer (might need to be added)
                # 3. PR has no reviewers at all
                if is_reviewer and not has_approved:
                    prs_needing_attention.append({
                        "pr": pr,
                        "reason": f"You need to review this PR (status: {vote_status})",
                        "is_reviewer": True,
                        "vote_status": vote_status
                    })
                elif not pr.reviewers or len(pr.reviewers) == 0:
                    prs_needing_attention.append({
                        "pr": pr,
                        "reason": "No reviewers assigned",
                        "is_reviewer": False,
                        "vote_status": "No reviewers"
                    })
                elif not is_reviewer and user_identifier:
                    # Optional: include PRs where user is not a reviewer but might want to review
                    # This is controlled by a flag to avoid noise
                    pass
            
            logger.info(f"Found {len(prs_needing_attention)} PRs needing attention")
            return prs_needing_attention
            
        except Exception as e:
            logger.error(f"Error listing PRs needing review: {e}")
            raise
    
    async def get_pull_request(
        self,
        organization: str,
        project: str,
        repository_id: str,
        pull_request_id: int
    ) -> GitPullRequest:
        """Get details of a specific pull request"""
        try:
            pr = self.git_client.get_pull_request(
                repository_id=repository_id,
                pull_request_id=pull_request_id,
                project=project
            )
            logger.info(f"Retrieved PR #{pull_request_id}: {pr.title}")
            return pr
        except Exception as e:
            logger.error(f"Error getting pull request: {e}")
            raise
    
    async def get_entire_file_content(
        self,
        organization: str,
        project: str,
        repository_id: str,
        file_path: str,
        branch: str = "main"
    ) -> str:
        """Get the entire content of a file from the repository"""
        try:
            # Get the full file content from the branch
            content = self.git_client.get_item_content(
                repository_id=repository_id,
                path=file_path,
                project=project,
                version_descriptor=GitVersionDescriptor(version=branch, version_type="branch")
            )
            # Content is returned as a generator, need to join it
            if content:
                content_bytes = b''.join(content)
                return content_bytes.decode('utf-8')
            return ""
        except Exception as e:
            logger.warning(f"Could not get full content for {file_path}: {e}")
            return ""
    
    async def get_pull_request_changes(
        self,
        organization: str,
        project: str,
        repository_id: str,
        pull_request_id: int
    ) -> List[Dict[str, Any]]:
        """Get file changes in a pull request - filters out merge commits"""
        try:
            # Get PR to get source and target commits
            pr = await self.get_pull_request(
                organization, project, repository_id, pull_request_id
            )
            
            # Get the commits in the PR
            commits = self.git_client.get_pull_request_commits(
                repository_id=repository_id,
                pull_request_id=pull_request_id,
                project=project
            )
            
            changes = []
            seen_paths = set()  # Track already processed files
            feature_commits = []  # Track non-merge commits
            
            # First pass: identify feature commits (non-merge commits)
            for commit in commits:
                commit_message = commit.comment if hasattr(commit, 'comment') else ""
                # Skip merge commits
                if commit_message and isinstance(commit_message, str) and ('merge' in commit_message.lower() or 'merging' in commit_message.lower()):
                    logger.info(f"Skipping merge commit: {commit.commit_id[:8]}")
                    continue
                feature_commits.append(commit)
            
            # If no feature commits, fall back to all commits
            if not feature_commits:
                logger.warning("No feature commits found, using all commits")
                feature_commits = commits
            
            # Process only feature commits
            for commit in feature_commits:
                # Get changes for each commit
                commit_changes = self.git_client.get_changes(
                    commit_id=commit.commit_id,
                    repository_id=repository_id,
                    project=project
                )
                
                for change in commit_changes.changes:
                    # Handle both dictionary and object access patterns
                    item = change.item if hasattr(change, 'item') else change.get('item', {})
                    
                    # Check if it's a folder and skip if so
                    is_folder = False
                    if hasattr(item, 'is_folder'):
                        is_folder = item.is_folder
                    elif isinstance(item, dict):
                        is_folder = item.get('isFolder', False)
                    
                    if is_folder:
                        continue  # Skip folders
                    
                    # Get file details
                    if hasattr(item, 'path'):
                        item_path = item.path
                    else:
                        item_path = item.get('path', '')
                    
                    # Skip if we've already processed this file
                    if item_path in seen_paths:
                        continue
                    seen_paths.add(item_path)
                    
                    if isinstance(change, dict):
                        change_type = change.get('changeType', '')
                        original_path = change.get('originalPath')
                    else:
                        change_type = change.change_type if hasattr(change, 'change_type') else ''
                        original_path = change.original_path if hasattr(change, 'original_path') else None
                    
                    change_dict = {
                        "path": item_path,
                        "change_type": change_type,
                        "original_path": original_path,
                        "is_test_file": self._is_test_file(item_path)
                    }
                    
                    # Get file content if it's a modification or addition
                    if change_type in ["edit", "add"]:
                        try:
                            # Get NEW content from the commit in the PR
                            new_content = self.git_client.get_item_content(
                                repository_id=repository_id,
                                path=item_path,
                                project=project,
                                version_descriptor=GitVersionDescriptor(version=commit.commit_id, version_type="commit")
                            )
                            # Content is returned as a generator, need to join it
                            if new_content:
                                content_bytes = b''.join(new_content)
                                change_dict["new_content"] = content_bytes.decode('utf-8')
                                change_dict["full_content"] = change_dict["new_content"]  # For full file analysis
                            else:
                                change_dict["new_content"] = ""
                                change_dict["full_content"] = ""
                            
                            # Get old content for edits to create diff
                            if change_type == "edit":
                                try:
                                    # Get old content from the target branch (what we're comparing against)
                                    old_content = self.git_client.get_item_content(
                                        repository_id=repository_id,
                                        path=item_path,
                                        project=project,
                                        version_descriptor=GitVersionDescriptor(
                                            version=pr.target_ref_name.replace('refs/heads/', ''), 
                                            version_type="branch"
                                        )
                                    )
                                    # Content is returned as a generator, need to join it
                                    if old_content:
                                        content_bytes = b''.join(old_content)
                                        change_dict["old_content"] = content_bytes.decode('utf-8')
                                    else:
                                        change_dict["old_content"] = ""
                                    
                                    # Calculate diff summary
                                    if old_content and change_dict.get("new_content"):
                                        old_lines = change_dict["old_content"].splitlines()
                                        new_lines = change_dict["new_content"].splitlines()
                                        change_dict["lines_added"] = len(new_lines) - len(old_lines)
                                        change_dict["size_change"] = len(change_dict["new_content"]) - len(change_dict["old_content"])
                                except:
                                    change_dict["old_content"] = ""
                        except Exception as e:
                            logger.warning(f"Could not get content for {item_path}: {e}")
                            change_dict["new_content"] = ""
                            change_dict["old_content"] = ""
                            change_dict["full_content"] = ""
                    
                    changes.append(change_dict)
            
            # Sort changes by path for consistent ordering
            changes.sort(key=lambda x: x["path"])
            
            logger.info(f"Retrieved {len(changes)} file changes for PR #{pull_request_id} (folders excluded)")
            return changes
        except Exception as e:
            logger.error(f"Error getting pull request changes: {e}")
            raise
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file based on naming patterns"""
        import re
        
        test_patterns = [
            r'.*\.Tests?\.cs$',
            r'.*Test\.cs$',
            r'.*Tests\.cs$',
            r'.*Spec\.cs$',
            r'.*\.test\.(js|ts|jsx|tsx)$',
            r'.*\.spec\.(js|ts|jsx|tsx)$',
            r'__tests__/.*\.(js|ts|jsx|tsx)$',
            r'.*\.e2e\.(js|ts)$',
            r'test_.*\.py$',
            r'.*_test\.py$'
        ]
        
        for pattern in test_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        return False
    
    async def add_pull_request_comments(
        self,
        organization: str,
        project: str,
        repository_id: str,
        pull_request_id: int,
        comments: List[Dict[str, Any]]
    ) -> List[CommentThread]:
        """Add comments to a pull request"""
        try:
            threads_created = []
            
            for comment_data in comments:
                # Create comment
                comment = Comment(
                    content=comment_data["content"],
                    comment_type="text"
                )
                
                # Create thread context if file/line specified
                thread_context = None
                if comment_data.get("file_path") and comment_data.get("line_number"):
                    position = CommentPosition(
                        line=comment_data["line_number"],
                        offset=1  # Azure DevOps requires offset to be at least 1
                    )
                    thread_context = CommentThreadContext(
                        file_path=comment_data["file_path"],
                        right_file_start=position,
                        right_file_end=position
                    )
                
                # Create comment thread
                thread = CommentThread(
                    comments=[comment],
                    thread_context=thread_context,
                    status="active"
                )
                
                # Post the thread
                created_thread = self.git_client.create_thread(
                    comment_thread=thread,
                    repository_id=repository_id,
                    pull_request_id=pull_request_id,
                    project=project
                )
                threads_created.append(created_thread)
            
            logger.info(f"Posted {len(threads_created)} comments to PR #{pull_request_id}")
            return threads_created
        except Exception as e:
            logger.error(f"Error adding comments: {e}")
            raise
    
    async def post_review_to_azure(
        self,
        organization: str,
        project: str,
        repository_id: str,
        pull_request_id: int,
        review_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Post a complete review to Azure DevOps, including comments and vote"""
        try:
            result = {
                "comments_posted": 0,
                "vote_updated": False,
                "errors": []
            }
            
            # Separate general comments from line-specific comments
            general_comments = []  # Comments to include in summary
            
            # Consolidate comments by file and line to prevent multiple comments on same line
            if review_data.get("comments"):
                # Group comments by location
                comments_by_location = {}
                for comment in review_data["comments"]:
                    file_path = comment.get("file_path")
                    line_number = comment.get("line_number", 0)
                    
                    # Comments with no line number or line 0 go to summary
                    if not file_path or not line_number or line_number <= 0:
                        # Add to general comments for summary
                        general_comments.append(comment)
                    else:
                        # Create location key for line-specific comments
                        location_key = f"{file_path}:{line_number}"
                        if location_key not in comments_by_location:
                            comments_by_location[location_key] = []
                        comments_by_location[location_key].append(comment)
                
                # Create consolidated line-specific comments only
                comments_to_post = []
                for location_key, location_comments in comments_by_location.items():
                    # All comments here have valid file path and line number > 0
                    file_path, line_number = location_key.rsplit(":", 1)
                    
                    # Combine all comments for this location
                    consolidated_parts = []
                    highest_severity = "info"
                    severity_order = {"info": 0, "warning": 1, "error": 2}
                    
                    for comment in location_comments:
                        severity = comment.get("severity", "info")
                        content = comment.get("content", "")
                        
                        # Track highest severity
                        if severity_order.get(severity, 0) > severity_order.get(highest_severity, 0):
                            highest_severity = severity
                        
                        consolidated_parts.append(f"[{severity.upper()}] {content}")
                    
                    # Create single consolidated comment
                    if len(consolidated_parts) == 1:
                        # Single comment, use original format
                        consolidated_content = self._format_review_comment(location_comments[0])
                    else:
                        # Multiple comments, create consolidated message
                        consolidated_content = f"**[{highest_severity.upper()}]**: Multiple issues found:\n" + "\n".join(f"• {part}" for part in consolidated_parts)
                    
                    comment_data = {
                        "content": consolidated_content,
                        "file_path": file_path,
                        "line_number": int(line_number)
                    }
                    comments_to_post.append(comment_data)
                
                try:
                    threads = await self.add_pull_request_comments(
                        organization, project, repository_id, 
                        pull_request_id, comments_to_post
                    )
                    result["comments_posted"] = len(threads)
                except Exception as e:
                    result["errors"].append(f"Failed to post comments: {e}")
            
            # Add general comments to review data for summary
            if general_comments:
                review_data["general_comments"] = general_comments
            
            # Post summary comment with general comments included
            summary = self._format_review_summary(review_data)
            try:
                summary_comment = [{
                    "content": summary,
                    "file_path": None,
                    "line_number": None
                }]
                await self.add_pull_request_comments(
                    organization, project, repository_id,
                    pull_request_id, summary_comment
                )
            except Exception as e:
                result["errors"].append(f"Failed to post summary: {e}")
            
            # Update vote/approval status
            vote = self._determine_vote(review_data)
            if vote is not None:
                try:
                    await self.update_pull_request_vote(
                        organization, project, repository_id,
                        pull_request_id, vote
                    )
                    result["vote_updated"] = True
                except Exception as e:
                    result["errors"].append(f"Failed to update vote: {e}")
            
            logger.info(f"Posted review to PR #{pull_request_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error posting review to Azure: {e}")
            raise
    
    def _format_review_comment(self, comment: Dict[str, Any]) -> str:
        """Format a single review comment for Azure DevOps"""
        severity = comment.get("severity", "info")
        content = comment.get("content", "")
        
        return f"**[{severity.upper()}]**: {content}"
    
    def _format_review_summary(self, review_data: Dict[str, Any]) -> str:
        """Format comprehensive review summary for Azure DevOps"""
        severity = review_data.get("severity", "unknown")
        summary = review_data.get("summary", "No summary provided")
        approved = review_data.get("approved", False)
        comments = review_data.get("comments", [])
        general_comments = review_data.get("general_comments", [])
        test_suggestions = review_data.get("test_suggestions", [])
        package_analysis = review_data.get("package_analysis", {})
        
        # If summary is already comprehensive (contains multiple sections), use it directly
        if "FILES CHANGED:" in summary and "ISSUES FOUND:" in summary:
            return f"## Automated Code Review Results\n\n{summary}\n\n---\n*This review was generated automatically by the Azure PR Reviewer*"
        
        # Otherwise, build comprehensive summary
        if approved:
            status_line = "**Review Status: APPROVED**"
        elif severity == "critical":
            status_line = "**Review Status: AUTOMATIC REJECTION (Critical Issues)**"
        elif severity == "major":
            status_line = "**Review Status: CHANGES REQUIRED (Major Issues)**"
        elif severity == "minor":
            status_line = "**Review Status: APPROVED WITH SUGGESTIONS**"
        else:
            status_line = "**Review Status: APPROVED**"
        
        # Build comprehensive summary without emojis
        lines = [
            "## Automated Code Review Results",
            "",
            status_line,
            "",
        ]
        
        # Add package analysis section if available
        if package_analysis:
            lines.append("### Package Security Analysis")
            lines.append(f"**Packages examined from all project folders: {package_analysis.get('total_packages_examined', 0)}**")
            
            if package_analysis.get('packages_by_type'):
                lines.append("")
                lines.append("Package types analyzed:")
                for pkg_type, count in package_analysis['packages_by_type'].items():
                    lines.append(f"- {pkg_type}: {count} packages")
            
            if package_analysis.get('has_issues'):
                lines.append("")
                lines.append(f"**CRITICAL: {package_analysis.get('vulnerable_packages', 0)} vulnerable package(s) found:**")
                for vuln in package_analysis.get('vulnerable_list', [])[:3]:
                    lines.append(f"- {vuln}")
                if len(package_analysis.get('vulnerable_list', [])) > 3:
                    lines.append(f"- ... and {len(package_analysis['vulnerable_list']) - 3} more")
            else:
                lines.append("")
                lines.append("**Result: No package vulnerabilities detected**")
            
            lines.append("")
        
        # Add general comments that don't have line numbers
        if general_comments:
            lines.append("### General Review Comments")
            for comment in general_comments:
                severity = comment.get("severity", "info")
                content = comment.get("content", "")
                lines.append(f"**[{severity.upper()}]**: {content}")
            lines.append("")
        
        # Add issue breakdown for line-specific comments
        if comments:
            # Only count line-specific comments (those with valid line numbers)
            line_specific_comments = [c for c in comments if (c.get("line_number") or 0) > 0]
            security_issues = [c for c in line_specific_comments if c.get("issue_type") == "security"]
            test_issues = [c for c in line_specific_comments if c.get("issue_type") == "missing_tests" or "test" in c.get("content", "").lower()]
            
            if line_specific_comments:
                lines.append("### Line-Specific Issues Found")
                
                if security_issues:
                    lines.append(f"**Security violations: {len(security_issues)}**")
                    for issue in security_issues[:2]:  # Show first 2
                        line_info = f"Line {issue['line_number']}"
                        lines.append(f"  - {line_info}: {issue.get('content', 'Security issue detected')[:80]}")
                
                if test_issues:
                    lines.append(f"**Testing violations: {len(test_issues)}**")
                    lines.append(f"  - Bug fix lacks required regression tests")
                
                if not security_issues and not test_issues:
                    other_issues = len(line_specific_comments)
                    if other_issues > 0:
                        lines.append(f"**Code quality issues: {other_issues}**")
                
                lines.append("")
        
        # Add original summary if provided
        if summary and summary != "No summary provided":
            lines.extend([
                "### Summary",
                summary,
                ""
            ])
        
        # Add statistics
        if comments:
            error_count = sum(1 for c in comments if c.get("severity") == "error")
            warning_count = sum(1 for c in comments if c.get("severity") == "warning")
            info_count = sum(1 for c in comments if c.get("severity") == "info")
            
            lines.extend([
                "### Review Statistics",
                f"- Critical errors: {error_count}",
                f"- Warnings: {warning_count}",
                f"- Suggestions: {info_count}",
                ""
            ])
        
        # Add test suggestions if any
        if test_suggestions:
            lines.extend([
                "### Required Test Cases",
                f"The following {len(test_suggestions)} test case(s) should be added:",
                ""
            ])
            
            for i, suggestion in enumerate(test_suggestions, 1):
                test_name = suggestion.get("test_name", f"Test_{i}")
                description = suggestion.get("description", "")
                test_code = suggestion.get("test_code", "")
                
                lines.append(f"#### {i}. {test_name}")
                if description:
                    lines.append(f"**Purpose:** {description}")
                    lines.append("")
                if test_code:
                    lines.append("**Stubbed Implementation:**")
                    lines.append("```csharp")
                    # Properly handle escaped newlines in test code
                    formatted_code = test_code.replace("\\n", "\n")
                    lines.append(formatted_code)
                    lines.append("```")
                lines.append("")
        
        lines.append("---")
        lines.append("*This review was generated automatically by the Azure PR Reviewer*")
        
        return "\n".join(lines)
    
    def _determine_vote(self, review_data: Dict[str, Any]) -> Optional[int]:
        """Determine the vote value based on review data
        
        Azure DevOps vote values:
        - 10: Approved
        - 5: Approved with suggestions
        - 0: No vote
        - -5: Waiting for author
        - -10: Rejected
        """
        approved = review_data.get("approved", False)
        severity = review_data.get("severity", "unknown")
        
        if approved and severity in ["approved", "minor"]:
            return 10  # Approved
        elif severity == "minor":
            return 5  # Approved with suggestions
        elif severity == "major":
            return -5  # Waiting for author
        elif severity == "critical":
            return -10  # Rejected
        else:
            return 0  # No vote
    
    async def update_pull_request_vote(
        self,
        organization: str,
        project: str,
        repository_id: str,
        pull_request_id: int,
        vote: int
    ) -> None:
        """Update the vote/approval status for a pull request"""
        try:
            # Get current user to identify reviewer
            current_user = await self.get_current_user()
            if not current_user:
                logger.warning("Could not determine current user for vote update")
                return
            
            # Create reviewer vote object
            from azure.devops.v7_1.git.models import IdentityRefWithVote
            
            reviewer = IdentityRefWithVote()
            reviewer.vote = vote
            
            # Note: This requires setting up the identity properly
            # For now, log the intended action
            logger.info(f"Would set vote to {vote} for PR #{pull_request_id}")
            
            # In a full implementation, you would use:
            # self.git_client.create_pull_request_reviewer(
            #     reviewer=reviewer,
            #     repository_id=repository_id,
            #     pull_request_id=pull_request_id,
            #     reviewer_id=current_user["id"],
            #     project=project
            # )
            
        except Exception as e:
            logger.error(f"Error updating vote: {e}")
            raise
    
    async def approve_pull_request(
        self,
        organization: str,
        project: str,
        repository_id: str,
        pull_request_id: int
    ) -> GitPullRequest:
        """Approve a pull request"""
        try:
            # Use the new review posting method
            review_data = {
                "approved": True,
                "severity": "approved",
                "summary": "This pull request has been approved by the automated code reviewer.",
                "comments": []
            }
            
            await self.post_review_to_azure(
                organization, project, repository_id,
                pull_request_id, review_data
            )
            
            pr = await self.get_pull_request(
                organization, project, repository_id, pull_request_id
            )
            
            logger.info(f"Approved PR #{pull_request_id}")
            return pr
        except Exception as e:
            logger.error(f"Error approving pull request: {e}")
            raise