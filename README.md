# Claude Memory Context Script

A simple utility that updates Claude project instructions with context from your MCP memory service. This enables Claude to start conversations with awareness of your memory contents.

## What It Does

This script:
1. Queries your MCP memory service for recent and important memories
2. Extracts topics and content summaries
3. Formats this information into a structured context section
4. Updates your Claude project's system prompt with this memory context

## Installation

```bash
# Clone this repository
git clone https://github.com/yourusername/claude-memory-context.git
cd claude-memory-context

# Install dependencies
npm install
```

Required dependencies:
- axios
- yargs

## Usage

```bash
# Basic usage
node memory-context-script.js --anthropic-api-key your_api_key --project-id your_project_id

# With custom MCP service URL
node memory-context-script.js --anthropic-api-key your_api_key --project-id your_project_id --mcp-url http://your-mcp-service:8000

# All options
node memory-context-script.js \
  --anthropic-api-key your_api_key \
  --project-id your_project_id \
  --mcp-url http://localhost:8000 \
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
0 * * * * cd /path/to/claude-memory-context && node memory-context-script.js --anthropic-api-key your_api_key --project-id your_project_id
```

## How to Use with Claude

1. First, create a Project in Claude's web interface
2. Get your Project ID from the URL (e.g., `https://claude.ai/project/{project_id}`)
3. Get your Anthropic API key from your account settings
4. Run this script to update the project instructions
5. When you chat with Claude in this project, it will now have memory awareness

## Tips for Effective Use

1. Use the `important` tag for memories you always want available to Claude
2. Consider creating a dedicated project for memory-aware conversations
3. The script preserves other custom instructions in your project
4. Check logs to ensure updates are working correctly

## Limitations

- The Anthropic API has character limits for project instructions (~100k chars)
- Only tagged and recent memories are included for conciseness
- This script requires the Anthropic API, which is a paid service

## License

MIT