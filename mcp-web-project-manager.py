#!/usr/bin/env python3
"""
Claude Web Project Manager - Dynamic MCP Server

This MCP server uses browser automation to interact with Claude's web interface,
providing dynamic project detection, selection, and knowledge management.

Features:
- List all available Claude projects
- Detect current project context
- Add knowledge to any project via web interface
- No API keys required - uses web automation
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, Resource, TextContent, ImageContent
    from pydantic import BaseModel
except ImportError:
    print("Error: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Browser automation imports
try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Error: Playwright not installed. Run: pip install playwright", file=sys.stderr)
    print("Then run: playwright install", file=sys.stderr)
    sys.exit(1)


class ClaudeProject(BaseModel):
    """Structure for Claude project information"""
    id: str
    name: str
    url: str
    last_accessed: Optional[str] = None
    knowledge_count: Optional[int] = None


class ProjectKnowledgeEntry(BaseModel):
    """Structure for project knowledge entries"""
    title: str
    content: str
    category: str = "general"
    tags: List[str] = []
    importance: int = 3  # 1-5 scale


class ClaudeWebProjectManager:
    """Manages Claude projects via web interface automation"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_project: Optional[ClaudeProject] = None
        self.available_projects: List[ClaudeProject] = []
        
    async def init_browser(self):
        """Initialize browser for web automation"""
        try:
            playwright = await async_playwright().start()
            # Use persistent context to maintain login state
            user_data_dir = os.path.expanduser("~/Library/Application Support/Claude/browser-data")
            
            self.browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,  # Show browser window so user can log in if needed
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            self.page = await self.browser.new_page()
            await self.page.goto("https://claude.ai")
            
            print("🌐 Browser initialized for Claude web interface", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}", file=sys.stderr)
            return False
    
    async def detect_login_status(self) -> bool:
        """Check if user is logged into Claude"""
        try:
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            
            # Wait a bit more for dynamic content
            await self.page.wait_for_timeout(3000)
            
            # Check URL first
            current_url = self.page.url
            print(f"🌐 Current URL: {current_url}", file=sys.stderr)
            
            if 'login' in current_url or 'auth' in current_url:
                print("⚠️ On login page - please log in to Claude in the browser window", file=sys.stderr)
                return False
            
            # Check for various login/logout indicators
            login_selectors = [
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'a:has-text("Log in")',
                'a:has-text("Sign in")',
                '[data-testid="login-button"]'
            ]
            
            for selector in login_selectors:
                if await self.page.locator(selector).count() > 0:
                    print("⚠️ Login button found - please log in to Claude in the browser window", file=sys.stderr)
                    return False
            
            # Check for user menu or profile indicators
            user_selectors = [
                '[data-testid="user-menu"]',
                'button[aria-label*="user" i]',
                'button[aria-label*="profile" i]',
                '.user-menu',
                '.profile-menu'
            ]
            
            for selector in user_selectors:
                if await self.page.locator(selector).count() > 0:
                    print("✅ User menu found - logged in successfully", file=sys.stderr)
                    return True
            
            # Check if we can access a protected page
            if 'claude.ai' in current_url and 'login' not in current_url:
                print("✅ On Claude.ai and not on login page - assuming logged in", file=sys.stderr)
                return True
                
            print("⚠️ Could not determine login status - check browser window", file=sys.stderr)
            return False
            
        except Exception as e:
            print(f"⚠️ Could not determine login status: {e}", file=sys.stderr)
            return False
    
    async def list_projects(self) -> List[ClaudeProject]:
        """Discover all available Claude projects"""
        try:
            if not await self.init_browser():
                return []
            
            if not await self.detect_login_status():
                print("❌ Not logged into Claude. A browser window should have opened.", file=sys.stderr)
                print("📋 Instructions:", file=sys.stderr)
                print("   1. Look for the Chrome/Chromium browser window that opened", file=sys.stderr)
                print("   2. Log in to Claude in that browser window", file=sys.stderr)
                print("   3. Try this command again after logging in", file=sys.stderr)
                print("   4. The browser window will stay open to maintain your session", file=sys.stderr)
                return []
            
            # Navigate to projects page
            await self.page.goto("https://claude.ai/projects")
            await self.page.wait_for_load_state('networkidle')
            
            projects = []
            
            # Look for project cards/links
            project_selectors = [
                '[data-testid="project-card"]',
                '.project-item',
                'a[href*="/project/"]',
                '[class*="project"]'
            ]
            
            for selector in project_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        try:
                            # Extract project information
                            text = await element.text_content()
                            href = await element.get_attribute('href')
                            
                            if href and '/project/' in href:
                                project_id = href.split('/project/')[-1].split('/')[0]
                                project_name = text.strip() if text else f"Project {project_id[:8]}"
                                
                                project = ClaudeProject(
                                    id=project_id,
                                    name=project_name,
                                    url=f"https://claude.ai/project/{project_id}"
                                )
                                
                                if project not in projects:
                                    projects.append(project)
                                    
                        except Exception:
                            continue
                            
                except Exception:
                    continue
            
            # Fallback: scan page text for project URLs
            if not projects:
                page_content = await self.page.content()
                import re
                project_urls = re.findall(r'https://claude\.ai/project/([a-zA-Z0-9-]+)', page_content)
                
                for project_id in set(project_urls):
                    projects.append(ClaudeProject(
                        id=project_id,
                        name=f"Project {project_id[:8]}",
                        url=f"https://claude.ai/project/{project_id}"
                    ))
            
            self.available_projects = projects
            print(f"🔍 Found {len(projects)} Claude projects", file=sys.stderr)
            
            return projects
            
        except Exception as e:
            print(f"❌ Failed to list projects: {e}", file=sys.stderr)
            return []
    
    async def select_project(self, project_id: str) -> bool:
        """Select and navigate to a specific project"""
        try:
            # Find project in available projects
            project = None
            for p in self.available_projects:
                if p.id == project_id or p.name == project_id:
                    project = p
                    break
            
            if not project:
                print(f"❌ Project not found: {project_id}", file=sys.stderr)
                return False
            
            # Navigate to project
            await self.page.goto(project.url)
            await self.page.wait_for_load_state('networkidle')
            
            self.current_project = project
            print(f"✅ Selected project: {project.name}", file=sys.stderr)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to select project: {e}", file=sys.stderr)
            return False
    
    async def add_knowledge_to_project(self, entry: ProjectKnowledgeEntry) -> bool:
        """Add knowledge entry to current project via web interface"""
        try:
            if not self.current_project:
                print("❌ No project selected", file=sys.stderr)
                return False
            
            # Navigate to project knowledge section
            knowledge_url = f"{self.current_project.url}/knowledge"
            await self.page.goto(knowledge_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Look for "Add knowledge" or similar button
            add_buttons = [
                'button:has-text("Add knowledge")',
                'button:has-text("Add")',
                'button:has-text("New")',
                '[data-testid="add-knowledge"]',
                '.add-knowledge-button'
            ]
            
            clicked = False
            for selector in add_buttons:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        clicked = True
                        break
                except Exception:
                    continue
            
            if not clicked:
                print("❌ Could not find 'Add knowledge' button", file=sys.stderr)
                return False
            
            # Wait for form to appear
            await self.page.wait_for_timeout(2000)
            
            # Fill in knowledge entry
            # Try different field selectors
            title_selectors = ['input[name="title"]', '[placeholder*="title" i]', 'input[type="text"]:first']
            content_selectors = ['textarea[name="content"]', '[placeholder*="content" i]', 'textarea:first']
            
            # Fill title
            for selector in title_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.fill(selector, entry.title)
                        break
                except Exception:
                    continue
            
            # Fill content
            formatted_content = f"""Category: {entry.category}
Tags: {', '.join(entry.tags)}
Importance: {entry.importance}/5

{entry.content}"""
            
            for selector in content_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.fill(selector, formatted_content)
                        break
                except Exception:
                    continue
            
            # Submit form
            submit_selectors = [
                'button:has-text("Save")',
                'button:has-text("Add")',
                'button:has-text("Submit")',
                'button[type="submit"]'
            ]
            
            for selector in submit_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.click(selector)
                        break
                except Exception:
                    continue
            
            # Wait for save to complete
            await self.page.wait_for_timeout(3000)
            
            print(f"✅ Added knowledge '{entry.title}' to project {self.current_project.name}", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Failed to add knowledge: {e}", file=sys.stderr)
            return False
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass


# Initialize the web project manager
web_manager = ClaudeWebProjectManager()

# Create MCP server
server = Server("claude-web-project-manager")

# Define MCP tools
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="list_claude_projects",
            description="Discover and list all available Claude projects by browsing the web interface. No authentication needed - uses browser automation.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="select_project",
            description="Select a specific Claude project to work with. Use project ID or name from list_claude_projects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID or name to select"}
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="add_project_knowledge",
            description="Add new knowledge to the currently selected Claude project via web interface automation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Clear, descriptive title for this knowledge"},
                    "content": {"type": "string", "description": "Detailed content of the knowledge"},
                    "category": {"type": "string", "description": "Category like 'technical', 'business', 'preferences'", "default": "general"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for organization"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Importance level (1=low, 5=critical)", "default": 3}
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="get_current_project",
            description="Get information about the currently selected project.",
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
    
    if name == "list_claude_projects":
        projects = await web_manager.list_projects()
        
        if not projects:
            return [TextContent(
                type="text",
                text="❌ No Claude projects found. Make sure you're logged into Claude in your browser."
            )]
        
        response = f"# Available Claude Projects ({len(projects)})\n\n"
        for i, project in enumerate(projects, 1):
            response += f"{i}. **{project.name}**\n"
            response += f"   - ID: `{project.id}`\n"
            response += f"   - URL: {project.url}\n\n"
        
        response += "Use `select_project` with the project ID or name to work with a specific project."
        
        return [TextContent(type="text", text=response)]
    
    elif name == "select_project":
        project_id = arguments["project_id"]
        success = await web_manager.select_project(project_id)
        
        if success:
            return [TextContent(
                type="text",
                text=f"✅ Selected project: {web_manager.current_project.name}\n🔗 URL: {web_manager.current_project.url}\n\nYou can now add knowledge to this project using `add_project_knowledge`."
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to select project '{project_id}'. Use `list_claude_projects` to see available projects."
            )]
    
    elif name == "add_project_knowledge":
        if not web_manager.current_project:
            return [TextContent(
                type="text",
                text="❌ No project selected. Use `select_project` first to choose a project."
            )]
        
        entry = ProjectKnowledgeEntry(
            title=arguments["title"],
            content=arguments["content"],
            category=arguments.get("category", "general"),
            tags=arguments.get("tags", []),
            importance=arguments.get("importance", 3)
        )
        
        success = await web_manager.add_knowledge_to_project(entry)
        
        if success:
            return [TextContent(
                type="text",
                text=f"✅ Successfully added knowledge '{entry.title}' to project {web_manager.current_project.name}!\n\n📝 Category: {entry.category}\n🏷️ Tags: {', '.join(entry.tags)}\n⭐ Importance: {entry.importance}/5\n\n🌐 Knowledge added directly to Claude project via web interface."
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Failed to add knowledge to project {web_manager.current_project.name}. The web interface may have changed or there might be access issues."
            )]
    
    elif name == "get_current_project":
        if not web_manager.current_project:
            return [TextContent(
                type="text",
                text="❌ No project currently selected. Use `list_claude_projects` and `select_project` to choose a project."
            )]
        
        project = web_manager.current_project
        response = f"# Current Project\n\n**{project.name}**\n- ID: `{project.id}`\n- URL: {project.url}\n\nReady to add knowledge to this project!"
        
        return [TextContent(type="text", text=response)]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def main():
    """Main entry point for the MCP server"""
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    finally:
        await web_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())