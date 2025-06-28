# Claude Memory Context Script

A simple utility that updates Claude project instructions with context from your MCP memory service. This enables Claude to start conversations with awareness of your memory contents.

# 🚧 Work in Progress 🚧

This project is actively under development.  
Features may change, break, or improve rapidly!  
Stay tuned for updates — contributions and feedback are welcome!

## Prerequisites

**Important**: This utility requires:
1. An active [MCP Memory Service](https://github.com/doobidoo/mcp-memory-service) installation
2. An Anthropic API key with access to Claude's project API endpoints
3. Node.js installed on your system

The MCP Memory Service must be properly set up and running before this utility can function. This script does not install or configure the memory service itself—it only connects to an existing installation.

## What It Does

This script:
1. Queries your MCP memory service for recent and important memories
2. Extracts topics and content summaries
3. Formats this information into a structured context section
4. Updates your Claude project's system prompt with this memory context

## Installation

```bash
# Clone this repository
git clone https://github.com/doobidoo/claude-memory-context.git
cd claude-memory-context

# Install dependencies
npm install
```

Required dependencies:
- axios
- yargs

## Setting Up Claude Project Instructions

Before running the script, you need to set up your Claude project with special markers that the script will use to insert memory context:

1. Create a new project in Claude's web interface
2. In the project settings, find the system prompt/custom instructions section
3. Add the following markers where you want the memory context to appear:

```
<!-- MEMORY CONTEXT START -->
You have a searchable memory.
<!-- MEMORY CONTEXT END -->
```

For example, your complete project instructions might look like:

```
# Project Instructions

You are my personal assistant. Please be concise and helpful in your responses.

<!-- MEMORY CONTEXT START -->
You have a searchable memory.
<!-- MEMORY CONTEXT END -->

Remember to always check your facts and be transparent about what you know and don't know.
```

The script will replace everything between these markers with the memory context. Anything outside the markers will remain unchanged.

See [docs/claude-project-template.md](docs/claude-project-template.md) for more detailed examples and best practices.

## Usage

This utility supports three modes of operation to accommodate different MCP Memory Service setups:

### Auto Mode (Default and Recommended)

The simplest way to use this utility - it automatically detects your Claude Desktop configuration:

```bash
# Automatic detection (recommended for Claude Desktop users)
node memory-context-script.js --anthropic-api-key your_api_key --project-id your_project_id
```

In auto mode, the script:
1. Searches for Claude Desktop configuration in your system
2. Extracts MCP Memory Service paths and settings
3. Falls back to HTTP mode if no configuration is found

This works best for Claude Desktop users as it requires minimal configuration.

### HTTP Mode

Use this mode if your MCP Memory Service is running as a web service (e.g., via Docker, standalone server, or Cloudflare Worker).

```bash
# Explicitly use HTTP mode
node memory-context-script.js \
  --mode http \
  --anthropic-api-key your_api_key \
  --project-id your_project_id \
  --mcp-url http://your-mcp-service:8000
```

### CLI Mode

Use this mode if you want to explicitly specify the paths to your MCP Memory Service (instead of auto-detection).

```bash
# Explicitly use CLI mode
node memory-context-script.js \
  --mode cli \
  --anthropic-api-key your_api_key \
  --project-id your_project_id \
  --mcp-memory-dir "/path/to/mcp-memory-service" \
  --chroma-db-path "/path/to/chroma_db" \
  --backups-path "/path/to/backups"
```

For Windows users:
```bash
node memory-context-script.js ^
  --mode cli ^
  --anthropic-api-key your_api_key ^
  --project-id your_project_id ^
  --mcp-memory-dir "C:\REPOSITORIES\mcp-memory-service" ^
  --chroma-db-path "C:\Users\YourUsername\AppData\Local\mcp-memory\chroma_db" ^
  --backups-path "C:\Users\YourUsername\AppData\Local\mcp-memory\backups"
```

This mode uses the same setup as specified in your Claude Desktop settings JSON:
```json
{
  "memory": {
    "command": "uv",
    "args": [
      "--directory",
      "your_mcp_memory_service_directory",
      "run",
      "memory"
    ],
    "env": {
      "MCP_MEMORY_CHROMA_PATH": "your_chroma_db_path",
      "MCP_MEMORY_BACKUPS_PATH": "your_backups_path"
    }
  }
}
```

Note: If your Claude Desktop uses `npx` instead of `uv`, add `--cli-command npx` to the command.

### All Options

```bash
node memory-context-script.js \
  --anthropic-api-key your_api_key \
  --project-id your_project_id \
  --mode auto|http|cli \
  --mcp-url http://localhost:8000 \
  --mcp-memory-dir "/path/to/mcp-memory-service" \
  --chroma-db-path "/path/to/chroma_db" \
  --backups-path "/path/to/backups" \
  --cli-command uv|npx \
  --max-recent-memories 5 \
  --max-important-memories 3 \
  --memory-prefix "You have a searchable memory. "
```

## Setting Up Automated Updates

You can use cron to run this script periodically:

```bash
# Open crontab editor
crontab -e

# Add a line to run every hour (adjust path as needed)
# For auto mode (recommended):
0 * * * * cd /path/to/claude-memory-context && node memory-context-script.js --anthropic-api-key your_api_key --project-id your_project_id
```

For Windows users, you can use Task Scheduler instead of cron.

## How to Use with Claude

1. First, create a Project in Claude's web interface
2. Get your Project ID from the URL (e.g., `https://claude.ai/project/{project_id}`)
3. Get your Anthropic API key from your account settings
4. Add the memory context markers to your project instructions (see above)
5. Run this script to update the project instructions
6. When you chat with Claude in this project, it will now have memory awareness

The memory context section will look something like this after the script runs:

```
<!-- MEMORY CONTEXT START -->
You have a searchable memory. 

Recent topics you remember include: programming, python, machine learning, data analysis, meeting notes.

Important long-term memories include:
- Project deadline for TechCorp is May 15th, 2025. Deliverables include API integration and dashboard...
- My daughter's birthday is June 12. She wants a science kit and books about space...
- Monthly team meeting agenda template: 1. Project updates 2. Roadblocks 3. Next sprint planning...

If the user mentions any of these topics or needs additional information, you can help them retrieve more from their memory by suggesting they ask about specific topics or use the memory search functions.
<!-- MEMORY CONTEXT END -->
```

## Auto-Detection Details

The auto-detection feature searches for Claude Desktop configuration in common application data directories:

- **Windows**: `%APPDATA%\Claude\settings.json` or similar
- **macOS**: `~/Library/Application Support/Claude/settings.json` or similar 
- **Linux**: `~/.config/Claude/settings.json` or similar

From this configuration, it extracts:
- The MCP Memory Service directory path
- The ChromaDB data path
- The backups path
- The CLI command (uv or npx)

If the configuration is found and parsed successfully, the script will automatically use CLI mode with these settings. If not, it falls back to HTTP mode.

## Tips for Effective Use

1. Use the `important` tag for memories you always want available to Claude
2. Consider creating a dedicated project for memory-aware conversations
3. The script preserves other custom instructions in your project
4. Check logs to ensure updates are working correctly
5. Place the memory context markers near the beginning of your instructions for best results
6. For Claude Desktop users, the auto-detection mode should work without additional configuration

## Limitations

- The Anthropic API has character limits for project instructions (~100k chars)
- Only tagged and recent memories are included for conciseness
- This script requires the Anthropic API, which is a paid service
- Requires a running MCP Memory Service instance with populated memories
- Auto-detection may not work with non-standard Claude Desktop installations

## Complete System Setup

For a full memory-aware Claude setup, you'll need:

1. **MCP Memory Service**: Install and configure the [MCP Memory Service](https://github.com/doobidoo/mcp-memory-service) first
2. **Claude API Access**: Sign up for [Anthropic's API](https://www.anthropic.com/api) to get an API key
3. **This Utility**: Install this script to bridge the two systems together

## License

MIT
