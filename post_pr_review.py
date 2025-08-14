#!/usr/bin/env python3
"""
Post PR Review to Azure DevOps
Posts comprehensive review comments and test recommendations to a PR
"""

import os
import sys
import json
import requests
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class PRReviewPoster:
    """Posts reviews and comments to Azure DevOps PRs"""
    
    def __init__(self, org_name: str, project_name: str, repo_name: str, pat_token: str):
        self.org_name = org_name
        self.project_name = project_name
        self.repo_name = repo_name
        self.pat_token = pat_token
        
        # Setup API access
        self.base_url = f"https://dev.azure.com/{org_name}/{project_name}/_apis"
        self.headers = {
            'Authorization': f'Basic {base64.b64encode(f":{pat_token}".encode()).decode()}',
            'Content-Type': 'application/json'
        }
    
    def post_review(self, pr_id: int, review_content: Dict[str, Any]) -> bool:
        """Post a comprehensive review to a PR"""
        
        print(f"\n[POST] Posting review to PR #{pr_id}...")
        
        # Create main review thread
        main_thread = self.create_review_thread(
            pr_id,
            review_content.get('summary', ''),
            review_content.get('decision', 'waitForAuthor')
        )
        
        if main_thread:
            print(f"[OK] Main review thread created: ID {main_thread.get('id')}")
        
        # Post test recommendations as separate thread
        if review_content.get('test_recommendations'):
            test_thread = self.create_test_recommendations_thread(
                pr_id,
                review_content['test_recommendations']
            )
            if test_thread:
                print(f"[OK] Test recommendations thread created: ID {test_thread.get('id')}")
        
        # Post code-specific comments
        if review_content.get('code_comments'):
            for comment in review_content['code_comments']:
                self.create_code_comment(pr_id, comment)
        
        # Update PR status if needed
        if review_content.get('set_status'):
            self.set_pr_status(pr_id, review_content['set_status'])
        
        return True
    
    def create_review_thread(self, pr_id: int, content: str, status: str = 'active') -> Optional[Dict]:
        """Create a main review thread"""
        
        url = f"{self.base_url}/git/repositories/{self.repo_name}/pullRequests/{pr_id}/threads?api-version=7.0"
        
        thread_data = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": content,
                    "commentType": 1  # 1 = text
                }
            ],
            "status": status  # active, byDesign, closed, fixed, pending, unknown, wontFix
        }
        
        try:
            response = requests.post(url, json=thread_data, headers=self.headers)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"[ERROR] Failed to create thread: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"[ERROR] Exception creating thread: {e}")
            return None
    
    def create_test_recommendations_thread(self, pr_id: int, test_recommendations: Dict) -> Optional[Dict]:
        """Create a thread specifically for test recommendations"""
        
        content = self.format_test_recommendations(test_recommendations)
        
        url = f"{self.base_url}/git/repositories/{self.repo_name}/pullRequests/{pr_id}/threads?api-version=7.0"
        
        thread_data = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": content,
                    "commentType": 1
                }
            ],
            "status": "active",
            "properties": {
                "Microsoft.TeamFoundation.Discussion.UniqueID": f"test-recommendations-{pr_id}"
            }
        }
        
        try:
            response = requests.post(url, json=thread_data, headers=self.headers)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"[ERROR] Failed to create test thread: {response.status_code}")
                return None
        except Exception as e:
            print(f"[ERROR] Exception creating test thread: {e}")
            return None
    
    def create_code_comment(self, pr_id: int, comment: Dict) -> Optional[Dict]:
        """Create a comment on specific code lines"""
        
        url = f"{self.base_url}/git/repositories/{self.repo_name}/pullRequests/{pr_id}/threads?api-version=7.0"
        
        thread_data = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": comment.get('content', ''),
                    "commentType": 1
                }
            ],
            "status": comment.get('status', 'active'),
            "threadContext": {
                "filePath": comment.get('file_path'),
                "rightFileStart": {
                    "line": comment.get('line_start', 1),
                    "offset": 1
                },
                "rightFileEnd": {
                    "line": comment.get('line_end', 1),
                    "offset": 1
                }
            }
        }
        
        try:
            response = requests.post(url, json=thread_data, headers=self.headers)
            if response.status_code in [200, 201]:
                print(f"[OK] Code comment added to {comment.get('file_path')} line {comment.get('line_start')}")
                return response.json()
            else:
                print(f"[ERROR] Failed to create code comment: {response.status_code}")
                return None
        except Exception as e:
            print(f"[ERROR] Exception creating code comment: {e}")
            return None
    
    def set_pr_status(self, pr_id: int, status: Dict) -> bool:
        """Set PR status (approve, reject, wait)"""
        
        url = f"{self.base_url}/git/repositories/{self.repo_name}/pullRequests/{pr_id}/statuses?api-version=7.0"
        
        status_data = {
            "state": status.get('state', 'pending'),  # succeeded, failed, pending
            "description": status.get('description', ''),
            "targetUrl": status.get('url', ''),
            "context": {
                "genre": "continuous-integration",
                "name": "code-analyzer/review"
            }
        }
        
        try:
            response = requests.post(url, json=status_data, headers=self.headers)
            if response.status_code in [200, 201]:
                print(f"[OK] PR status set to: {status.get('state')}")
                return True
            else:
                print(f"[ERROR] Failed to set status: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Exception setting status: {e}")
            return False
    
    def format_test_recommendations(self, recommendations: Dict) -> str:
        """Format test recommendations for posting"""
        
        content = "## 🧪 Required Tests\n\n"
        content += f"**Priority:** {recommendations.get('priority', 'HIGH').upper()}\n"
        content += f"**Framework:** {recommendations.get('framework', 'NUnit/xUnit')}\n\n"
        
        # Unit tests
        unit_tests = recommendations.get('unit_tests', [])
        if unit_tests:
            content += "### Unit Tests (Required)\n"
            for i, test in enumerate(unit_tests[:5], 1):  # Limit to 5 for readability
                content += f"{i}. **{test.get('test_name', '')}**\n"
                content += f"   - {test.get('description', '')}\n"
            if len(unit_tests) > 5:
                content += f"\n_...and {len(unit_tests) - 5} more unit tests_\n"
            content += "\n"
        
        # Integration tests
        integration_tests = recommendations.get('integration_tests', [])
        if integration_tests:
            content += "### Integration Tests\n"
            for test in integration_tests[:3]:
                content += f"- **{test.get('test_name', '')}**: {test.get('description', '')}\n"
            content += "\n"
        
        # Security tests
        security_tests = recommendations.get('security_tests', [])
        if security_tests:
            content += "### 🔒 Security Tests\n"
            for test in security_tests:
                content += f"- **{test.get('test_name', '')}**: {test.get('description', '')}\n"
            content += "\n"
        
        content += "---\n"
        content += "_Review generated by Azure DevOps Code Analyzer v0.1.0_"
        
        return content
    
    def post_vote(self, pr_id: int, vote: int, comment: str = "") -> bool:
        """Post a vote on the PR (-10 reject, -5 wait, 0 none, 5 approved with suggestions, 10 approved)"""
        
        # Get current user ID
        user_url = f"https://dev.azure.com/{self.org_name}/_apis/connectiondata?api-version=7.0"
        user_response = requests.get(user_url, headers=self.headers)
        
        if user_response.status_code != 200:
            print("[ERROR] Could not get user ID")
            return False
        
        user_id = user_response.json().get('authenticatedUser', {}).get('id')
        
        # Post the vote
        url = f"{self.base_url}/git/repositories/{self.repo_name}/pullRequests/{pr_id}/reviewers/{user_id}?api-version=7.0"
        
        vote_data = {
            "vote": vote
        }
        
        try:
            response = requests.put(url, json=vote_data, headers=self.headers)
            if response.status_code in [200, 201]:
                vote_text = {
                    -10: "Rejected",
                    -5: "Waiting for author",
                    0: "No vote",
                    5: "Approved with suggestions",
                    10: "Approved"
                }.get(vote, "Unknown")
                print(f"[OK] Vote posted: {vote_text}")
                return True
            else:
                print(f"[ERROR] Failed to post vote: {response.status_code}")
                return False
        except Exception as e:
            print(f"[ERROR] Exception posting vote: {e}")
            return False


def create_pr_1364_review() -> Dict[str, Any]:
    """Create the review content for PR 1364"""
    
    return {
        "summary": """## Code Review Summary

### ✅ Improvements
- Well-structured refactoring of `ProcessInvite` method
- Better separation of concerns with `DeleteInvite` and `UpsertInvite`
- Improved variable naming (`i` → `invite`)

### ❌ Critical Issues
1. **No test coverage** - This PR modifies critical deletion logic without any tests
2. **Missing error handling** - New methods lack try-catch blocks
3. **Security TODO** remains unaddressed

### 📋 Requirements Before Approval
- [ ] Add minimum 8 unit tests
- [ ] Add 4 integration tests
- [ ] Add error handling
- [ ] Document new methods

**Decision: Changes requested - tests required before merge**

See test recommendations thread for specific test cases needed.""",
        
        "decision": "waitForAuthor",
        
        "test_recommendations": {
            "priority": "CRITICAL",
            "framework": "NUnit/xUnit",
            "unit_tests": [
                {
                    "test_name": "Test_DeleteInvite_Success",
                    "description": "Verify complete deletion including cache and Woppy"
                },
                {
                    "test_name": "Test_DeleteInvite_WithAnswers",
                    "description": "Ensure cascade deletion of question answers"
                },
                {
                    "test_name": "Test_DeleteInvite_NonExistent",
                    "description": "Handle non-existent invites gracefully"
                },
                {
                    "test_name": "Test_UpsertInvite_CreateNew",
                    "description": "Test new invite creation"
                },
                {
                    "test_name": "Test_UpsertInvite_UpdateExisting",
                    "description": "Verify update logic"
                }
            ],
            "integration_tests": [
                {
                    "test_name": "Test_DeleteInvite_WoppyIntegration",
                    "description": "Verify Woppy service notification"
                },
                {
                    "test_name": "Test_ProcessInvite_EndToEnd",
                    "description": "Complete workflow testing"
                }
            ],
            "security_tests": [
                {
                    "test_name": "Test_DeleteInvite_Authorization",
                    "description": "Verify permission checks"
                },
                {
                    "test_name": "Test_ProcessInvite_AuditTrail",
                    "description": "Ensure audit logging"
                }
            ]
        },
        
        "code_comments": [
            {
                "file_path": "/ZinniaInternal.Businesslogic/WWL/Questionnaires.cs",
                "line_start": 1279,
                "line_end": 1287,
                "content": "⚠️ **Missing error handling**: The new `DeleteInvite` and `UpsertInvite` methods should be wrapped in try-catch blocks to handle potential exceptions from cache operations and external service calls.",
                "status": "active"
            },
            {
                "file_path": "/ZinniaInternal.Businesslogic/WWL/Questionnaires.cs",
                "line_start": 131,
                "line_end": 131,
                "content": "🔒 **Security Issue**: This TODO comment indicates a security risk in the `RevealPassword` method. This should be addressed as part of this PR or tracked separately.",
                "status": "active"
            }
        ],
        
        "set_status": {
            "state": "pending",
            "description": "Tests required before merge",
            "url": ""
        }
    }


def main():
    """Main function to test posting review to PR"""
    
    # Load configuration
    org_name = os.getenv('AZDO_ORG', '')
    project_name = os.getenv('AZDO_PROJECT', '')
    repo_name = os.getenv('AZDO_REPO', '')
    pat_token = os.getenv('AZDO_PAT', '')
    
    if not all([org_name, project_name, repo_name, pat_token]):
        print("[ERROR] Missing Azure DevOps configuration!")
        return 1
    
    print("="*70)
    print("TESTING PR REVIEW POSTING")
    print("="*70)
    print(f"Organization: {org_name}")
    print(f"Project: {project_name}")
    print(f"Repository: {repo_name}")
    print(f"PR: #1364")
    print()
    
    # Create reviewer
    reviewer = PRReviewPoster(org_name, project_name, repo_name, pat_token)
    
    # Create review content
    review_content = create_pr_1364_review()
    
    # Post the review
    success = reviewer.post_review(1364, review_content)
    
    if success:
        print("\n[SUCCESS] Review posted successfully!")
        
        # Also post a vote
        reviewer.post_vote(1364, -5, "Changes requested - tests required")
        
        print("\n" + "="*70)
        print("REVIEW POSTED TO PR #1364")
        print("="*70)
        print("✓ Main review thread created")
        print("✓ Test recommendations posted")
        print("✓ Code comments added")
        print("✓ Vote: Waiting for author")
        print("\nView the PR at:")
        print(f"https://dev.azure.com/{org_name}/{project_name}/_git/{repo_name}/pullrequest/1364")
    else:
        print("\n[FAILED] Could not post review")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())