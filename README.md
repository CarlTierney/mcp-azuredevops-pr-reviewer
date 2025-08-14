# Azure DevOps PR Reviewer MCP Server

An MCP (Model Context Protocol) server that enables Claude to review Azure DevOps pull requests with specialized, file-type-specific analysis including security vulnerability detection for package dependencies.

## Features

- **Pull Request Management**
  - List all open pull requests in Azure DevOps repositories
  - Filter PRs that need your review or approval
  - Fetch detailed PR information with file changes
  - Post review comments directly to Azure DevOps
  - Update vote/approval status on pull requests
  - Format and post comprehensive review summaries

- **Intelligent File Type Detection**
  - Automatically detects 20+ file types
  - Applies specialized review prompts for each file type
  - Supports mixed-language pull requests

- **Security Vulnerability Detection**
  - Scans package files for outdated dependencies (2+ major versions behind)
  - Checks for known CVEs in JavaScript, C#/.NET, Python, and Java packages
  - Provides actionable upgrade recommendations
  - Identifies deprecated and end-of-life packages

- **Supported File Types**
  - **Languages**: C#, JavaScript, TypeScript, Python, Java, SQL
  - **Web**: HTML, CSS, Razor views, React/JSX
  - **Configuration**: JSON, XML, YAML, .env files
  - **Package Files**: package.json, *.csproj, requirements.txt, pom.xml, build.gradle
  - **Documentation**: Markdown files
  - **Testing**: Unit tests, integration tests

## Prerequisites

- Python 3.8 or higher
- Azure DevOps account with appropriate permissions
- Claude Desktop or Claude CLI installed
- Azure DevOps Personal Access Token (PAT)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/pr-reviewer.git
cd pr-reviewer
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the sample environment file and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Azure DevOps credentials:

```env
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PAT=your-personal-access-token
AZURE_USER_EMAIL=your.email@example.com
```

### 5. Create Azure DevOps Personal Access Token

1. Navigate to `https://dev.azure.com/{your-org}/_usersSettings/tokens`
2. Click "New Token"
3. Set the following permissions:
   - **Code**: Read & Write
   - **Pull Request**: Read & Write
   - **Project and Team**: Read (optional, for project listing)
4. Copy the generated token to your `.env` file

## Configuration

### Claude Desktop Integration

Add the server to your Claude Desktop configuration:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux:** `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "azure-pr-reviewer": {
      "command": "python",
      "args": ["-m", "azure_pr_reviewer.server", "--stdio"],
      "cwd": "D:\\OpenDoors\\pr-reviewer",
      "env": {
        "PYTHONPATH": "D:\\OpenDoors\\pr-reviewer",
        "AZURE_DEVOPS_ORG": "your-organization",
        "AZURE_DEVOPS_PAT": "your-pat-token",
        "AZURE_USER_EMAIL": "your.email@example.com"
      }
    }
  }
}
```

**Important Configuration Notes:**
- The `--stdio` argument is required for proper MCP communication
- Set `PYTHONPATH` to your pr-reviewer directory to ensure modules are found
- Use your actual directory path in `cwd` (change `D:\\OpenDoors\\pr-reviewer` to your path)
- On Windows, use double backslashes (`\\`) in the JSON configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `AZURE_DEVOPS_ORG` | Yes | Your Azure DevOps organization name | - |
| `AZURE_DEVOPS_PAT` | Yes | Personal Access Token with Code and PR permissions | - |
| `AZURE_USER_EMAIL` | Yes | Email for filtering PRs needing your review | - |
| `AZURE_DEFAULT_PROJECT` | No | Default project name | - |
| `AZURE_DEFAULT_REPOSITORY` | No | Default repository name | - |
| `LOG_LEVEL` | No | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `MAX_FILES_PER_REVIEW` | No | Maximum files to review per PR | 50 |
| `MAX_DIFF_SIZE_KB` | No | Maximum diff size in KB | 500 |


## Usage

### Using with Claude Desktop

Once configured, Claude can interact with your Azure DevOps PRs:

1. **List PRs needing your review:**
   ```
   "Show me PRs that need my review in the fidem project"
   ```

2. **Get detailed PR for review:**
   ```
   "Review PR #123 from the zinnia repository"
   ```

3. **Review with vulnerability scanning:**
   ```
   "Check PR #456 for security vulnerabilities in package dependencies"
   ```

4. **Post review comments to Azure DevOps:**
   ```
   "Review PR #789 and post the feedback to Azure DevOps"
   ```

5. **Approve a pull request:**
   ```
   "Approve PR #123 if it meets our coding standards"
   ```

### Available MCP Tools

The server provides the following tools to Claude:

#### `list_prs_needing_my_review`
Lists pull requests that need your review or approval.

**Parameters:**
- `project` (required): Azure DevOps project name
- `repository` (optional): Filter by specific repository
- `max_results` (optional): Maximum number of PRs to return (default: 20)

**Returns:** List of PRs with ID, title, author, creation date, and your review status

#### `list_pull_requests`
Lists all active pull requests in a repository.

**Parameters:**
- `project` (required): Azure DevOps project name
- `repository` (required): Repository name
- `status` (optional): Filter by status (active, completed, abandoned)
- `max_results` (optional): Maximum number of PRs to return

#### `get_pr_for_review`
Fetches detailed PR information for Claude to review.

**Parameters:**
- `project` (required): Azure DevOps project name
- `repository` (required): Repository name
- `pr_id` (required): Pull request ID

**Returns:** Structured data for Claude review including:
- PR metadata (title, description, author)
- File changes with diffs
- File type analysis
- Appropriate review prompts

#### `post_review_comments`
Posts complete review results back to Azure DevOps, including comments and vote status.

**Parameters:**
- `repository_id` (required): Repository name or ID
- `pull_request_id` (required): Pull request ID
- `review_json` (required): JSON string with review results containing:
  - `approved`: boolean indicating approval status
  - `severity`: string (approved/minor/major/critical)
  - `summary`: overall review summary
  - `comments`: array of comment objects with file_path, line_number, content, and severity
- `project` (optional): Azure DevOps project name (uses env var if not provided)
- `organization` (optional): Azure DevOps organization (uses env var if not provided)

**Returns:** Status of posted comments and vote update

#### `approve_pull_request`
Approves a pull request in Azure DevOps.

**Parameters:**
- `repository_id` (required): Repository name or ID
- `pull_request_id` (required): Pull request ID
- `confirm` (required): Must be set to True to confirm the approval
- `comment` (optional): Additional approval comment
- `project` (optional): Azure DevOps project name (uses env var if not provided)
- `organization` (optional): Azure DevOps organization (uses env var if not provided)

### Command Line Testing

You can test the server directly:

```bash
# Run the server
python -m azure_pr_reviewer.server

# In another terminal, test with MCP client
python test_server.py
```

## Review Prompts

The system includes specialized review prompts for different file types:

### Security-Focused Reviews
- **Package Dependencies**: Checks for outdated packages, known CVEs, and security vulnerabilities
- **SQL Files**: SQL injection prevention, query optimization
- **Web Files**: XSS prevention, CSRF protection, secure headers

### Language-Specific Reviews
- **C#**: .NET best practices, async/await patterns, null safety
- **JavaScript/TypeScript**: ES6+ features, type safety, performance
- **Python**: PEP 8 compliance, type hints, security
- **Java**: Design patterns, thread safety, resource management

### Customizing Prompts

Review prompts are stored in the `prompts/` directory. You can customize them by editing the corresponding `.txt` files:

```
prompts/
├── default_review_prompt.txt          # Fallback for unknown file types
├── csharp_review_prompt.txt          # C# files
├── javascript_review_prompt.txt      # JavaScript files
├── python_review_prompt.txt          # Python files
├── javascript_packages_review_prompt.txt  # package.json, npm
├── csharp_packages_review_prompt.txt      # .csproj, NuGet
├── python_packages_review_prompt.txt      # requirements.txt, pip
└── java_packages_review_prompt.txt        # pom.xml, gradle
```

## Development

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=azure_pr_reviewer tests/

# Test file type detection
python test_file_detection.py

# Test package vulnerability detection
python test_package_detection.py
```

### Project Structure

```
pr-reviewer/
├── azure_pr_reviewer/
│   ├── __init__.py
│   ├── server.py              # Main MCP server
│   ├── azure_client.py        # Azure DevOps API client
│   ├── code_reviewer.py       # Review data preparation
│   ├── file_type_detector.py  # File type detection logic
│   └── config.py              # Configuration management
├── prompts/                   # Review prompt templates
│   ├── default_review_prompt.txt
│   └── [file-type]_review_prompt.txt
├── tests/                     # Unit tests
├── .env.example              # Environment variables template
├── .gitignore
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Python package configuration
└── README.md
```

### Adding New File Types

1. Add the file type to `FileType` enum in `file_type_detector.py`
2. Update `EXTENSION_MAP` or `PACKAGE_FILES` dictionaries
3. Create a new prompt file in `prompts/` directory
4. Update `get_prompt_file_for_type()` method

## Security Considerations

- **Never commit** your `.env` file with real credentials
- Store PAT tokens securely
- Rotate tokens regularly
- Use minimal required permissions for PAT
- Review security vulnerability reports before merging PRs

## Integration with Other AI Clients

### ChatGPT Integration

**Note:** ChatGPT does not natively support the MCP (Model Context Protocol). However, you can integrate this tool with ChatGPT using these approaches:

#### Option 1: API Wrapper Approach
Create a REST API wrapper around the MCP server that ChatGPT can call via Custom GPTs:

1. Create a FastAPI wrapper:
```python
# api_wrapper.py
from fastapi import FastAPI
from azure_pr_reviewer.azure_client import AzureDevOpsClient
from azure_pr_reviewer.config import Settings

app = FastAPI()

@app.get("/prs/need-review")
async def get_prs_needing_review(project: str, repository: str):
    # Call the Azure client methods
    client = AzureDevOpsClient(Settings())
    return await client.list_prs_needing_review(project, repository)

@app.post("/prs/{pr_id}/review")
async def review_pr(pr_id: int, project: str, repository: str):
    # Implement review logic
    pass
```

2. Deploy the API to a public endpoint (Azure Functions, AWS Lambda, etc.)
3. Create a Custom GPT with the API schema
4. Configure authentication for your Custom GPT

#### Option 2: GitHub Actions Integration
Use ChatGPT to generate review comments, then post via GitHub Actions:

1. Create a workflow that triggers on PR events
2. Use the OpenAI API to get reviews from GPT-4
3. Post comments back to Azure DevOps

### Google Gemini Integration

Google Gemini doesn't support MCP directly, but you can integrate using:

#### Google Cloud Functions Approach
```python
# Deploy as Google Cloud Function
import functions_framework
from azure_pr_reviewer.azure_client import AzureDevOpsClient

@functions_framework.http
def review_endpoint(request):
    """HTTP Cloud Function for Gemini integration"""
    request_json = request.get_json()
    
    if request.path == '/review':
        # Process review request
        pr_data = fetch_pr_data(request_json)
        # Use Gemini API for analysis
        review = analyze_with_gemini(pr_data)
        # Post back to Azure DevOps
        post_review(review)
    
    return {'status': 'success'}
```

### Amazon Bedrock Claude Integration

For AWS users, integrate with Bedrock's Claude model:

```python
# bedrock_integration.py
import boto3
import json
from azure_pr_reviewer.azure_client import AzureDevOpsClient

bedrock = boto3.client('bedrock-runtime')

def review_with_bedrock_claude(pr_data):
    """Use Bedrock Claude for PR review"""
    
    # Prepare the prompt
    prompt = f"Review this pull request:\n{json.dumps(pr_data)}"
    
    # Call Bedrock Claude
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps({
            'prompt': prompt,
            'max_tokens': 4000
        })
    )
    
    # Parse and return review
    return json.loads(response['body'].read())
```

### Perplexity AI Integration

Perplexity AI can be integrated through their API:

```python
# perplexity_integration.py
import requests
from azure_pr_reviewer.azure_client import AzureDevOpsClient

def review_with_perplexity(pr_data):
    """Use Perplexity AI for code review"""
    
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        'https://api.perplexity.ai/chat/completions',
        headers=headers,
        json={
            'model': 'pplx-70b-online',
            'messages': [{
                'role': 'user',
                'content': f'Review this PR: {pr_data}'
            }]
        }
    )
    
    return response.json()
```

### GitHub Copilot Integration

For GitHub Copilot users migrating to Azure DevOps:

```yaml
# .github/copilot-config.yml
version: 1
review:
  auto_review: true
  providers:
    - type: custom
      endpoint: https://your-api.com/azure-devops-review
      auth:
        type: bearer
        token: ${{ secrets.AZURE_PAT }}
```

### Generic REST API for Any AI Client

Create a universal REST API that any AI client can use:

```python
# universal_api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Azure PR Reviewer API")

class ReviewRequest(BaseModel):
    project: str
    repository: str
    pr_id: int
    ai_provider: str  # 'openai', 'anthropic', 'google', etc.
    api_key: str

@app.post("/api/v1/review")
async def review_pr(request: ReviewRequest):
    """Universal endpoint for any AI provider"""
    
    # Fetch PR data from Azure DevOps
    pr_data = await fetch_azure_pr(request.project, request.repository, request.pr_id)
    
    # Route to appropriate AI provider
    if request.ai_provider == 'openai':
        review = await review_with_openai(pr_data, request.api_key)
    elif request.ai_provider == 'anthropic':
        review = await review_with_anthropic(pr_data, request.api_key)
    elif request.ai_provider == 'google':
        review = await review_with_gemini(pr_data, request.api_key)
    else:
        raise HTTPException(status_code=400, detail="Unsupported AI provider")
    
    # Post review back to Azure DevOps
    await post_review_to_azure(review, request.project, request.repository, request.pr_id)
    
    return {"status": "success", "review": review}

@app.get("/api/v1/prs")
async def list_prs(project: str, repository: str = None):
    """List PRs needing review"""
    # Implementation here
    pass
```

### Using with LangChain

Integrate with LangChain for advanced AI workflows:

```python
# langchain_integration.py
from langchain.tools import Tool
from langchain.agents import initialize_agent
from azure_pr_reviewer.azure_client import AzureDevOpsClient

class AzurePRReviewTool(Tool):
    name = "azure_pr_review"
    description = "Review Azure DevOps pull requests"
    
    def _run(self, pr_id: str, project: str, repository: str):
        client = AzureDevOpsClient()
        pr_data = client.get_pr_for_review(project, repository, pr_id)
        return pr_data

# Create agent with the tool
tools = [AzurePRReviewTool()]
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
```

### Using with AutoGPT/AgentGPT

For autonomous agents, create a plugin:

```yaml
# azure_pr_plugin.yaml
name: azure_pr_reviewer
description: Reviews Azure DevOps PRs
version: 1.0.0
commands:
  - name: review_pr
    description: Review a pull request
    parameters:
      - name: pr_id
        type: integer
        required: true
      - name: project
        type: string
        required: true
    endpoint: http://localhost:8000/review
```

### Security Considerations for AI Integrations

1. **API Key Management**: Never expose Azure PAT tokens to client-side applications
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **Authentication**: Use OAuth2 or API keys for all public endpoints
4. **Data Privacy**: Ensure PR data is not logged or stored by third-party AI services
5. **Network Security**: Use HTTPS for all API communications

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify your PAT has correct permissions
   - Check PAT expiration date
   - Ensure `AZURE_USER_EMAIL` matches your Azure DevOps account

2. **MCP Connection Issues**
   - Restart Claude Desktop after configuration changes
   - Check Python path in claude_desktop_config.json
   - Verify all environment variables are set

3. **Review Not Working**
   - Check file size limits (MAX_DIFF_SIZE_KB)
   - Verify prompt files exist in prompts/ directory
   - Check logs for specific errors

4. **MCP Server Not Found**
   - Ensure `--stdio` argument is included in the args
   - Add `PYTHONPATH` environment variable pointing to the pr-reviewer directory
   - Verify Python is in your system PATH
   - Check that all dependencies are installed: `pip install -r requirements.txt`
   - Try using the full Python path if needed (e.g., `C:\\Python312\\python.exe`)

5. **Import Errors**
   - Ensure you're using FastMCP instead of Server from mcp.server
   - Install pydantic-settings separately: `pip install pydantic-settings`
   - Verify the working directory (cwd) is set correctly in the config

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

### Testing the MCP Server

You can test the MCP server directly:

```bash
# Test that the server starts
python -m azure_pr_reviewer.server --stdio

# Test with a simple initialization
echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"1.0.0","capabilities":{},"clientInfo":{"name":"test"}},"id":1}' | python -m azure_pr_reviewer.server --stdio
```

If the server starts without errors, it should work with Claude Desktop.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details

## Acknowledgments

- Built for use with [Claude](https://claude.ai) by Anthropic
- Uses the [MCP (Model Context Protocol)](https://github.com/anthropics/mcp) framework
- Integrates with [Azure DevOps Services](https://dev.azure.com)

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

## Roadmap

- [ ] Support for GitLab and Bitbucket
- [ ] Integration with more security scanning tools
- [ ] Custom review rules configuration
- [ ] Review metrics and analytics
- [ ] Automated PR approval workflows
- [ ] Support for more programming languages
- [ ] AI-powered code suggestions
- [ ] Integration with CI/CD pipelines