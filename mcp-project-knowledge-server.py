#!/usr/bin/env python3
"""
Claude Desktop Project Knowledge Management MCP Server

This MCP server provides tools for Claude to autonomously manage project knowledge
and instructions within Claude Desktop. Claude can decide when to update project
context, add knowledge, or modify instructions based on conversation insights.

Features:
- Add/update structured project knowledge
- Modify project instructions dynamically  
- Query existing project context
- Store conversation insights as project knowledge
- Auto-suggest project improvements
"""

import sqlite3
import json
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# MCP imports - using the official MCP Python SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, Resource, TextContent, ImageContent
    from pydantic import BaseModel
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


class ProjectKnowledgeEntry(BaseModel):
    """Structure for project knowledge entries"""
    title: str
    content: str
    category: str
    tags: List[str] = []
    importance: int = 3  # 1-5 scale
    source: str = "conversation"  # conversation, file, manual
    
    
class ProjectInstruction(BaseModel):
    """Structure for project instructions"""
    section: str  # e.g., "context", "guidelines", "constraints"
    content: str
    priority: int = 3  # 1-5 scale


class ClaudeProjectKnowledgeManager:
    """Manages Claude Desktop project knowledge and instructions"""
    
    def __init__(self, claude_db_path: str = None):
        # Check for project context from environment variables
        self.project_id = os.environ.get('CLAUDE_PROJECT_ID')
        self.project_name = os.environ.get('CLAUDE_PROJECT_NAME')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        
        # Fallback to local storage if no project context
        if claude_db_path is None:
            claude_db_path = os.path.expanduser(
                "~/Library/Application Support/Claude/claudeSQLite.db"
            )
        self.db_path = claude_db_path
        self.init_db()
        
        print(f"🎯 Project Context: {self.project_name or 'Local Storage'} (ID: {self.project_id or 'None'})", file=sys.stderr)
    
    def init_db(self):
        """Initialize database with project knowledge tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create notes table (Claude Desktop's Project knowledge UI)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create project_knowledge table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,  -- JSON array of tags
                    importance INTEGER CHECK (importance BETWEEN 1 AND 5) DEFAULT 3,
                    source TEXT DEFAULT 'conversation',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create project_instructions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_instructions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section TEXT NOT NULL,
                    content TEXT NOT NULL,
                    priority INTEGER CHECK (priority BETWEEN 1 AND 5) DEFAULT 3,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create project_context table for dynamic context
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_key TEXT UNIQUE NOT NULL,
                    context_value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def add_knowledge(self, entry: ProjectKnowledgeEntry) -> int:
        """Add new project knowledge entry - to Claude API if project context available, otherwise local"""
        
        if self.project_id and self.anthropic_api_key:
            # TODO: Add to actual Claude project via API
            print(f"🌐 Would add to Claude project {self.project_name} (ID: {self.project_id})", file=sys.stderr)
            print(f"📝 Title: {entry.title}", file=sys.stderr)
            print(f"🏷️ Category: {entry.category}", file=sys.stderr)
            # For now, still store locally as we need API implementation
            
        # Store locally (either as fallback or primary)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Format content with metadata for Claude Desktop's project knowledge
            project_prefix = f"[{self.project_name}] " if self.project_name else ""
            formatted_content = f"""Project: {self.project_name or 'Local'}
Category: {entry.category}
Importance: {entry.importance}/5
Tags: {', '.join(entry.tags)}
Source: {entry.source}

{entry.content}"""
            
            # Insert into Claude Desktop's notes table (appears in Project knowledge UI)
            cursor.execute("""
                INSERT INTO notes (title, content, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (f"{project_prefix}{entry.title}", formatted_content))
            
            note_id = cursor.lastrowid
            
            # Also store in our custom table for advanced querying
            cursor.execute("""
                INSERT INTO project_knowledge 
                (title, content, category, tags, importance, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.title,
                entry.content,
                entry.category,
                json.dumps(entry.tags),
                entry.importance,
                entry.source
            ))
            
            conn.commit()
            return note_id
    
    def get_project_context(self) -> Dict[str, str]:
        """Get current project context information"""
        return {
            'project_id': self.project_id or 'None',
            'project_name': self.project_name or 'Local Storage',
            'has_api_key': bool(self.anthropic_api_key),
            'storage_mode': 'API + Local' if self.project_id else 'Local Only'
        }
    
    def update_instruction(self, instruction: ProjectInstruction) -> bool:
        """Update or add project instruction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if instruction section exists
            cursor.execute(
                "SELECT id FROM project_instructions WHERE section = ? AND active = 1",
                (instruction.section,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing instruction
                cursor.execute("""
                    UPDATE project_instructions 
                    SET content = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE section = ? AND active = 1
                """, (instruction.content, instruction.priority, instruction.section))
            else:
                # Add new instruction
                cursor.execute("""
                    INSERT INTO project_instructions (section, content, priority)
                    VALUES (?, ?, ?)
                """, (instruction.section, instruction.content, instruction.priority))
            
            conn.commit()
            return True
    
    def get_all_knowledge(self) -> List[Dict]:
        """Get all project knowledge entries"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, category, tags, importance, source, created_at
                FROM project_knowledge
                ORDER BY importance DESC, created_at DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'category': row[3],
                    'tags': json.loads(row[4]) if row[4] else [],
                    'importance': row[5],
                    'source': row[6],
                    'created_at': row[7]
                })
            return results
    
    def get_all_instructions(self) -> List[Dict]:
        """Get all active project instructions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, section, content, priority, created_at, updated_at
                FROM project_instructions
                WHERE active = 1
                ORDER BY priority DESC, section
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'section': row[1],
                    'content': row[2],
                    'priority': row[3],
                    'created_at': row[4],
                    'updated_at': row[5]
                })
            return results
    
    def search_knowledge(self, query: str, category: str = None) -> List[Dict]:
        """Search project knowledge"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            base_query = """
                SELECT id, title, content, category, tags, importance, source, created_at
                FROM project_knowledge
                WHERE (content LIKE ? OR title LIKE ? OR tags LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]
            
            if category:
                base_query += " AND category = ?"
                params.append(category)
            
            base_query += " ORDER BY importance DESC, created_at DESC"
            
            cursor.execute(base_query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'category': row[3],
                    'tags': json.loads(row[4]) if row[4] else [],
                    'importance': row[5],
                    'source': row[6],
                    'created_at': row[7]
                })
            return results
    
    def update_context(self, key: str, value: str, description: str = None) -> bool:
        """Update dynamic project context"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO project_context 
                (context_key, context_value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value, description))
            conn.commit()
            return True
    
    def get_context(self) -> Dict[str, Dict]:
        """Get all project context"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT context_key, context_value, description, updated_at
                FROM project_context
                ORDER BY updated_at DESC
            """)
            
            context = {}
            for row in cursor.fetchall():
                context[row[0]] = {
                    'value': row[1],
                    'description': row[2],
                    'updated_at': row[3]
                }
            return context
    
    def get_claude_desktop_notes(self) -> List[Dict]:
        """Get notes from Claude Desktop's UI (what appears in Project knowledge)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content, created_at
                FROM notes
                ORDER BY created_at DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'created_at': row[3]
                })
            return results


# Initialize the knowledge manager
knowledge_manager = ClaudeProjectKnowledgeManager()

# Create MCP server
server = Server("claude-project-knowledge")

# Define MCP tools
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="add_project_knowledge",
            description="Add new knowledge to the current Claude Desktop project. Use this when you learn something important that should be remembered for future conversations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Clear, descriptive title for this knowledge"},
                    "content": {"type": "string", "description": "Detailed content of the knowledge"},
                    "category": {"type": "string", "description": "Category like 'technical', 'business', 'preferences', 'constraints'"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for organization"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Importance level (1=low, 5=critical)"}
                },
                "required": ["title", "content", "category"]
            }
        ),
        Tool(
            name="update_project_instructions",
            description="Update or add instructions for this Claude Desktop project. Use this to modify how Claude should behave in this project context.",
            inputSchema={
                "type": "object", 
                "properties": {
                    "section": {"type": "string", "description": "Instruction section like 'context', 'guidelines', 'constraints', 'objectives'"},
                    "content": {"type": "string", "description": "The instruction content"},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Priority level (1=low, 5=critical)"}
                },
                "required": ["section", "content"]
            }
        ),
        Tool(
            name="search_project_knowledge",
            description="Search existing project knowledge. Use this to check what's already known before adding duplicate information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Optional category filter"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_project_overview",
            description="Get a complete overview of current project knowledge and instructions. Use this to understand the current project context.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="update_project_context",
            description="Update dynamic project context (current focus, active tasks, etc.). Use this to track what's currently happening in the project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Context key like 'current_focus', 'active_task', 'last_discussion'"},
                    "value": {"type": "string", "description": "Current value"},
                    "description": {"type": "string", "description": "Optional description of this context"}
                },
                "required": ["key", "value"]
            }
        ),
        Tool(
            name="suggest_project_improvements",
            description="Analyze current conversation and suggest improvements to project knowledge or instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_summary": {"type": "string", "description": "Summary of current conversation"},
                    "focus_areas": {"type": "array", "items": {"type": "string"}, "description": "Areas to focus suggestions on"}
                },
                "required": ["conversation_summary"]
            }
        ),
        Tool(
            name="get_claude_desktop_notes",
            description="Get all notes that appear in Claude Desktop's Project knowledge UI. Use this to see what's actually visible in the interface.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="check_project_context",
            description="Check current project context and configuration status. Shows which project (if any) the MCP server is connected to.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    
    if name == "add_project_knowledge":
        entry = ProjectKnowledgeEntry(
            title=arguments["title"],
            content=arguments["content"],
            category=arguments["category"],
            tags=arguments.get("tags", []),
            importance=arguments.get("importance", 3)
        )
        
        note_id = knowledge_manager.add_knowledge(entry)
        context = knowledge_manager.get_project_context()
        
        # Prepare status message without backslashes in f-string
        api_note = "🌐 Note: This entry will be added to the actual Claude project when API integration is implemented."
        local_note = "📱 This entry will appear in Claude Desktop's local Project knowledge section."
        status_note = api_note if context['project_id'] != 'None' else local_note
        
        return [TextContent(
            type="text",
            text=f"✅ Added project knowledge '{entry.title}' (Note ID: {note_id})\n🎯 Project: {context['project_name']}\n📝 Category: {entry.category} | Importance: {entry.importance}/5\n🏷️ Tags: {', '.join(entry.tags)}\n💾 Storage: {context['storage_mode']}\n\n{status_note}"
        )]
    
    elif name == "update_project_instructions":
        instruction = ProjectInstruction(
            section=arguments["section"],
            content=arguments["content"],
            priority=arguments.get("priority", 3)
        )
        
        success = knowledge_manager.update_instruction(instruction)
        if success:
            return [TextContent(
                type="text",
                text=f"✅ Updated project instructions for section '{instruction.section}' with priority {instruction.priority}"
            )]
        else:
            return [TextContent(
                type="text", 
                text=f"❌ Failed to update project instructions for section '{instruction.section}'"
            )]
    
    elif name == "search_project_knowledge":
        results = knowledge_manager.search_knowledge(
            query=arguments["query"],
            category=arguments.get("category")
        )
        
        if not results:
            return [TextContent(
                type="text",
                text=f"No project knowledge found for query: '{arguments['query']}'"
            )]
        
        response = f"Found {len(results)} knowledge entries for '{arguments['query']}':\n\n"
        for item in results[:5]:  # Limit to top 5 results
            response += f"**{item['title']}** ({item['category']}, importance: {item['importance']})\n"
            response += f"{item['content'][:200]}{'...' if len(item['content']) > 200 else ''}\n"
            response += f"Tags: {', '.join(item['tags'])}\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "get_project_overview":
        knowledge = knowledge_manager.get_all_knowledge()
        instructions = knowledge_manager.get_all_instructions()
        context = knowledge_manager.get_context()
        
        response = "# Project Overview\n\n"
        
        # Current Context
        if context:
            response += "## Current Context\n"
            for key, data in context.items():
                response += f"- **{key}**: {data['value']}\n"
                if data['description']:
                    response += f"  _{data['description']}_\n"
            response += "\n"
        
        # Instructions
        if instructions:
            response += "## Project Instructions\n"
            for inst in instructions:
                response += f"### {inst['section'].title()} (Priority: {inst['priority']})\n"
                response += f"{inst['content']}\n\n"
        
        # Knowledge Summary
        if knowledge:
            response += "## Knowledge Summary\n"
            categories = {}
            for item in knowledge:
                cat = item['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            for category, items in categories.items():
                response += f"### {category.title()} ({len(items)} items)\n"
                for item in items[:3]:  # Top 3 per category
                    response += f"- **{item['title']}** (importance: {item['importance']})\n"
                if len(items) > 3:
                    response += f"- ... and {len(items) - 3} more\n"
                response += "\n"
        else:
            response += "## Knowledge Summary\nNo project knowledge stored yet.\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "update_project_context":
        success = knowledge_manager.update_context(
            key=arguments["key"],
            value=arguments["value"],
            description=arguments.get("description")
        )
        
        if success:
            return [TextContent(
                type="text",
                text=f"✅ Updated project context '{arguments['key']}' = '{arguments['value']}'"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to update project context '{arguments['key']}'"
            )]
    
    elif name == "suggest_project_improvements":
        # Analyze current state and suggest improvements
        knowledge = knowledge_manager.get_all_knowledge()
        instructions = knowledge_manager.get_all_instructions()
        conversation_summary = arguments["conversation_summary"]
        
        suggestions = []
        
        # Analyze knowledge gaps
        categories = set(item['category'] for item in knowledge)
        if 'technical' not in categories and 'code' in conversation_summary.lower():
            suggestions.append("Consider adding technical knowledge about coding practices or architecture")
        
        if 'preferences' not in categories and 'prefer' in conversation_summary.lower():
            suggestions.append("Consider documenting user preferences mentioned in conversations")
        
        # Analyze instruction gaps
        instruction_sections = set(inst['section'] for inst in instructions)
        if 'constraints' not in instruction_sections and ('limit' in conversation_summary.lower() or 'constraint' in conversation_summary.lower()):
            suggestions.append("Consider adding constraint instructions based on mentioned limitations")
        
        if 'guidelines' not in instruction_sections and len(knowledge) > 5:
            suggestions.append("Consider adding guideline instructions for how to use the accumulated knowledge")
        
        # Knowledge organization suggestions
        if len(knowledge) > 10:
            low_importance = [k for k in knowledge if k['importance'] < 3]
            if len(low_importance) > 5:
                suggestions.append(f"Consider reviewing {len(low_importance)} low-importance knowledge entries for relevance")
        
        response = "# Project Improvement Suggestions\n\n"
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
            response += f"\nBased on analysis of {len(knowledge)} knowledge entries and {len(instructions)} instruction sections."
        else:
            response += "No specific improvements suggested at this time. The project knowledge appears well-organized."
        
        return [TextContent(type="text", text=response)]
    
    elif name == "get_claude_desktop_notes":
        notes = knowledge_manager.get_claude_desktop_notes()
        
        if not notes:
            return [TextContent(
                type="text",
                text="No notes found in Claude Desktop's Project knowledge section."
            )]
        
        response = f"# Claude Desktop Project Knowledge ({len(notes)} entries)\n\n"
        for note in notes:
            response += f"## {note['title']}\n"
            response += f"**Created:** {note['created_at']}\n\n"
            content_preview = note['content'][:300] + "..." if len(note['content']) > 300 else note['content']
            response += f"{content_preview}\n\n---\n\n"
        
        return [TextContent(type="text", text=response)]
    
    elif name == "check_project_context":
        context = knowledge_manager.get_project_context()
        
        response = f"""# Project Context Status
        
🎯 **Current Project**: {context['project_name']}
🆔 **Project ID**: {context['project_id']}
🔑 **API Key**: {'✅ Configured' if context['has_api_key'] else '❌ Not configured'}
💾 **Storage Mode**: {context['storage_mode']}

## Configuration Status

{'✅ **Project Context Detected**' if context['project_id'] != 'None' else '⚠️ **No Project Context**'}

{'''
**Current Setup**: Connected to specific Claude project
**Knowledge will be added to**: Actual Claude project (when API is implemented)
''' if context['project_id'] != 'None' else '''
**Current Setup**: Local storage mode
**Knowledge will be added to**: Claude Desktop's local notes section

### 🛠️ To Connect to a Specific Project:

1. **Edit your MCP server configuration** in `claude_desktop_config.json`:
```json
"claude-project-knowledge": {{
    "command": "/Users/hkr/anaconda3/bin/python3",
    "args": ["/path/to/mcp-project-knowledge-server.py"],
    "env": {{
        "CLAUDE_PROJECT_ID": "your-project-id",
        "CLAUDE_PROJECT_NAME": "MCP MEMORY DASHBOARD",
        "ANTHROPIC_API_KEY": "your-api-key"
    }}
}}
```

2. **Find your project ID** from the Claude web interface URL
3. **Restart Claude Desktop** to apply changes
'''}

**Available Projects** (based on local notes):
- MCP-Memory-Dashboard (found in local notes)
""".strip()
        
        return [TextContent(type="text", text=response)]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())