# Claude Memory Context - Project Overview

This project provides tools for integrating Claude AI with memory and context management capabilities through MCP (Model Context Protocol) servers.

## Project Structure

- `memory-context-script.js` - Main CLI script for memory context operations
- `mcp-web-project-manager.py` - **Dynamic web-based project manager (Recommended)**
- `mcp-project-knowledge-server.py` - Local storage MCP server 
- `test_mcp_server.py` - Test suite for the MCP server
- `requirements.txt` - Python dependencies for MCP servers
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

### **Web-Based Project Manager Tools (`claude-web-project-manager`)**
- `list_claude_projects` - **Discover all your Claude projects automatically**
- `select_project` - **Choose which project to work with**  
- `add_project_knowledge` - **Add knowledge directly to Claude projects via web interface**
- `get_current_project` - **View currently selected project info**

### **Local Storage Tools (`claude-project-knowledge`)**
- `add_project_knowledge` - Store important project insights locally
- `update_project_instructions` - Modify project behavior guidelines
- `search_project_knowledge` - Find existing knowledge
- `get_project_overview` - View complete project status
- `update_project_context` - Track current focus/tasks
- `suggest_project_improvements` - AI-powered suggestions
- `check_project_context` - View configuration status

## Development

### Node.js CLI
- `npm install` - Install dependencies
- `npm start` - Start the memory context CLI

### Python MCP Server
- `pip install -r requirements.txt` - Install Python dependencies
- `python3 test_mcp_server.py` - Run MCP server tests

## Installation

### **Option 1: Dynamic Web-Based Project Manager (Recommended)**

1. **Install dependencies**:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. **Add to Claude Desktop**: Add this configuration to your `claude_desktop_config.json`:

```json
"claude-web-project-manager": {
    "command": "/Users/hkr/anaconda3/bin/python3",
    "args": ["/Users/hkr/Documents/GitHub/claude-memory-context/mcp-web-project-manager.py"],
    "env": {}
}
```

**Features:**
- ✅ **Dynamic project discovery** - finds all your Claude projects automatically
- ✅ **No API keys needed** - uses web interface automation  
- ✅ **Works with any project** - select from all available projects
- ✅ **Real project integration** - actually adds knowledge to Claude projects
- ✅ **Interactive workflow** - discover → select → add knowledge

### **Option 2: Local Storage Server**

```json
"claude-project-knowledge": {
    "command": "/Users/hkr/anaconda3/bin/python3",
    "args": ["/Users/hkr/Documents/GitHub/claude-memory-context/mcp-project-knowledge-server.py"],
    "env": {}
}
```

3. **Restart Claude Desktop** to activate the MCP server

## Usage Example

### **Web-Based Project Manager Workflow:**

1. **Discover projects**: `list_claude_projects`
   ```
   # Available Claude Projects (3)
   
   1. **MCP MEMORY DASHBOARD**
      - ID: `abc123`
      - URL: https://claude.ai/project/abc123
   
   2. **Robot Logger**  
      - ID: `def456`
      - URL: https://claude.ai/project/def456
   
   3. **MCP-SAP-SERVER**
      - ID: `ghi789` 
      - URL: https://claude.ai/project/ghi789
   ```

2. **Select project**: `select_project` with "MCP MEMORY DASHBOARD"
   ```
   ✅ Selected project: MCP MEMORY DASHBOARD
   🔗 URL: https://claude.ai/project/abc123
   ```

3. **Add knowledge**: `add_project_knowledge`
   ```
   ✅ Successfully added knowledge 'Performance Optimization Tips' to project MCP MEMORY DASHBOARD!
   📝 Category: technical
   🏷️ Tags: performance, optimization
   ⭐ Importance: 4/5
   🌐 Knowledge added directly to Claude project via web interface.
   ```

**Result**: Knowledge appears immediately in your actual Claude project!

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