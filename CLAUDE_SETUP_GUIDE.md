# Claude Desktop Configuration Guide for Azure PR Reviewer

## Quick Setup

### 1. Prerequisites
- Python 3.8 or higher installed
- Git installed
- Azure DevOps Personal Access Token (PAT)
- Claude Desktop application

### 2. Environment Configuration

Create a `.env` file in the project root with these settings:

```env
# Azure DevOps Configuration
AZURE_DEVOPS_ORG=your-organization-name
AZURE_DEVOPS_PROJECT=your-project-name
AZURE_DEVOPS_PAT=your-personal-access-token-here

# Review Model Configuration
REVIEW_MODEL=claude-3-opus-20240229

# Working Directory Configuration (IMPORTANT)
# This directory will be used to clone repositories for analysis
# Make sure this path exists and has write permissions
WORKING_DIRECTORY=D:/temp/pr-review
AUTO_CLEANUP=true

# Review Limits
MAX_FILES_PER_REVIEW=5000
MAX_TOTAL_SIZE_GB=2

# Logging
LOG_LEVEL=INFO
```

### 3. Claude Desktop Configuration

#### For Windows Users

1. Open Claude Desktop settings
2. Navigate to MCP Servers configuration
3. Add the following configuration:

```json
{
  "mcpServers": {
    "azure-pr-reviewer": {
      "command": "python",
      "args": ["-m", "azure_pr_reviewer.server"],
      "cwd": "D:\\OpenDoors\\pr-reviewer",
      "env": {
        "PYTHONPATH": "D:\\OpenDoors\\pr-reviewer",
        "WORKING_DIRECTORY": "D:\\temp\\pr-review"
      }
    }
  }
}
```

**Important Notes:**
- Replace `D:\\OpenDoors\\pr-reviewer` with your actual installation path
- The `WORKING_DIRECTORY` must be a path where the system can create/delete folders
- Use double backslashes (`\\`) in Windows paths in JSON

#### For macOS/Linux Users

```json
{
  "mcpServers": {
    "azure-pr-reviewer": {
      "command": "python3",
      "args": ["-m", "azure_pr_reviewer.server"],
      "cwd": "/path/to/pr-reviewer",
      "env": {
        "PYTHONPATH": "/path/to/pr-reviewer",
        "WORKING_DIRECTORY": "/tmp/pr-review"
      }
    }
  }
}
```

### 4. Working Directory Setup

The working directory is crucial for the full context analyzer. It needs:

1. **Sufficient Space**: At least 5GB free space for cloning repositories
2. **Write Permissions**: The Python process must be able to create/delete folders
3. **Clean State**: The directory will be automatically cleaned before each analysis

#### Create Working Directory (Windows PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path "D:\temp\pr-review"
```

#### Create Working Directory (macOS/Linux):
```bash
mkdir -p /tmp/pr-review
```

### 5. Verify Installation

After configuration, test the setup:

1. Restart Claude Desktop
2. Check if the Azure PR Reviewer appears in available tools
3. Test with a simple command:
   ```
   List PRs in repository "YourRepo"
   ```

## Features Configuration

### Security Detection
- Automatically scans for password exposure
- Detects hardcoded credentials
- Identifies security vulnerabilities

### Package Scanning
- Set `WORKING_DIRECTORY` to enable full repository analysis
- Scans npm, NuGet, pip, Maven, Composer packages
- Checks against vulnerability databases

### Test Enforcement
- Automatically rejects bug fixes without tests
- Generates test suggestions with code stubs
- Language-specific test templates

### Full Context Analysis
- **Requires WORKING_DIRECTORY to be set**
- Clones entire repository for complete analysis
- Analyzes full files, not just diffs
- Cleans working directory before each run

## Troubleshooting

### Issue: "Working directory not found"
**Solution**: Create the directory specified in `WORKING_DIRECTORY`:
```powershell
New-Item -ItemType Directory -Force -Path "D:\temp\pr-review"
```

### Issue: "Permission denied" when cloning
**Solution**: Ensure the working directory has write permissions:
```powershell
icacls "D:\temp\pr-review" /grant Users:F
```

### Issue: "Git not found"
**Solution**: Ensure Git is installed and in PATH:
```powershell
git --version
```

### Issue: "Repository already exists"
**Solution**: The auto-cleanup should handle this, but you can manually clean:
```powershell
Remove-Item -Recurse -Force "D:\temp\pr-review\*"
```

## Advanced Configuration

### Custom Prompts
Edit files in the `prompts/` directory to customize review behavior:
- `security_focused_prompt.txt` - Security review criteria
- `test_review_prompt.txt` - Test requirement checks
- `universal_thinking_template.txt` - Deep analysis instructions

### Review Models
Available models in `.env`:
- `claude-3-opus-20240229` (recommended for thorough analysis)
- `claude-3-sonnet-20240229` (faster, less detailed)
- `claude-3-haiku-20240307` (fastest, basic analysis)

### Performance Tuning
Adjust in `.env`:
- `MAX_FILES_PER_REVIEW`: Maximum files to analyze (default: 5000)
- `MAX_TOTAL_SIZE_GB`: Maximum total size (default: 2GB)
- `AUTO_CLEANUP`: Set to `false` to keep cloned repos for debugging

## Security Best Practices

1. **Never commit the `.env` file** - It contains your PAT token
2. **Use read-only PAT tokens** when possible
3. **Regularly rotate PAT tokens**
4. **Set working directory outside of sensitive areas**
5. **Enable AUTO_CLEANUP** to remove cloned repositories

## Support

For issues or questions:
1. Check the logs in the working directory
2. Verify all environment variables are set
3. Ensure Python dependencies are installed: `pip install -r requirements.txt`
4. Test with a simple PR first before complex repositories

## Example Usage

Once configured, you can use natural language commands in Claude:

- "Review PR #1234 in MyRepo"
- "Check for security issues in PR #5678"
- "Analyze packages in repository MainApp"
- "List all open PRs needing review"

The system will automatically:
- Clone the repository to the working directory
- Analyze security vulnerabilities
- Check for missing tests
- Scan package dependencies
- Provide comprehensive feedback