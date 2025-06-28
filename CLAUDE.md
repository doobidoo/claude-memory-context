# Claude Memory Context - Project Overview

This project provides tools for integrating Claude AI with memory and context management capabilities through MCP (Model Context Protocol) servers.

## Project Structure

- `memory-context-script.js` - Main CLI script for memory context operations
- `mcp-project-knowledge-server.py` - MCP server for Claude project knowledge management
- `test_mcp_server.py` - Test suite for the MCP server
- `requirements.txt` - Python dependencies for MCP server
- `package.json` - Node.js project configuration and dependencies
- `docs/claude-project-template.md` - Template documentation for Claude projects

## Key Components

### Memory Context CLI
- Memory context management
- Integration with MCP Memory Service
- Claude AI project bridging

### MCP Project Knowledge Server
- Autonomous project knowledge management
- Dynamic instruction updates
- Context tracking and suggestions
- SQLite-based knowledge storage

## MCP Server Tools

The `claude-project-knowledge` MCP server provides:
- `add_project_knowledge` - Store important project insights
- `update_project_instructions` - Modify project behavior guidelines
- `search_project_knowledge` - Find existing knowledge
- `get_project_overview` - View complete project status
- `update_project_context` - Track current focus/tasks
- `suggest_project_improvements` - AI-powered suggestions

## Development

### Node.js CLI
- `npm install` - Install dependencies
- `npm start` - Start the memory context CLI

### Python MCP Server
- `pip install -r requirements.txt` - Install Python dependencies
- `python3 test_mcp_server.py` - Run MCP server tests

## Installation

1. **Add to Claude Desktop**: Add this configuration to your `claude_desktop_config.json`:

```json
"claude-project-knowledge": {
    "command": "/Users/hkr/anaconda3/bin/python3",
    "args": ["/path/to/mcp-project-knowledge-server.py"],
    "env": {}
}
```

2. **Restart Claude Desktop** to activate the MCP server

## Testing

Run the comprehensive test suite:
```bash
python3 test_mcp_server.py
```

This verifies:
- Database operations
- Knowledge management
- Project instructions
- Context tracking
- MCP protocol integration