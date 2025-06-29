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
        
    async def detect_current_project_context(self) -> Optional[ClaudeProject]:
        """Dynamically detect current project context using multiple methods with timeout handling"""
        print("🔍 Detecting current project context dynamically...", file=sys.stderr)
        
        detection_results = []
        
        # Method 1: Environment Variables (fast)
        try:
            env_result = self._detect_from_environment()
            if env_result:
                detection_results.append(("environment", env_result, 5))
                print(f"📧 Environment detection: {env_result['name']}", file=sys.stderr)
                # Return immediately if we have a high-confidence result
                return ClaudeProject(
                    id=env_result['id'],
                    name=env_result['name'],
                    url=f"https://claude.ai/project/{env_result['id']}"
                )
        except Exception as e:
            print(f"Environment detection failed: {e}", file=sys.stderr)
            
        # Method 2: Database Analysis (fast)
        try:
            db_result = self._detect_from_database()
            if db_result:
                detection_results.append(("database", db_result, 4))
                print(f"💾 Database detection: {db_result['name']}", file=sys.stderr)
                # Return immediately if we have a good result
                return ClaudeProject(
                    id=db_result['id'],
                    name=db_result['name'],
                    url=f"https://claude.ai/project/{db_result['id']}"
                )
        except Exception as e:
            print(f"Database detection failed: {e}", file=sys.stderr)
            
        # Method 3: Process Analysis (fast)
        try:
            process_result = self._detect_from_processes()
            if process_result:
                detection_results.append(("process", process_result, 3))
                print(f"⚙️ Process detection: {process_result['name']}", file=sys.stderr)
                # Return immediately if we have a result
                return ClaudeProject(
                    id=process_result['id'],
                    name=process_result['name'],
                    url=f"https://claude.ai/project/{process_result['id']}"
                )
        except Exception as e:
            print(f"Process detection failed: {e}", file=sys.stderr)
        
        # Method 4: Browser Detection (slow, with timeout)
        try:
            print("🌐 Attempting browser detection with timeout...", file=sys.stderr)
            browser_result = await asyncio.wait_for(
                self._detect_from_browser(), 
                timeout=10.0  # 10 second timeout
            )
            if browser_result:
                detection_results.append(("browser", browser_result, 5))
                print(f"🌐 Browser detection: {browser_result['name']}", file=sys.stderr)
                return ClaudeProject(
                    id=browser_result['id'],
                    name=browser_result['name'],
                    url=f"https://claude.ai/project/{browser_result['id']}"
                )
        except asyncio.TimeoutError:
            print("⏰ Browser detection timed out (10s), skipping...", file=sys.stderr)
        except Exception as e:
            print(f"Browser detection failed: {e}", file=sys.stderr)
        
        print("❌ No project context detected from any method", file=sys.stderr)
        return None
    
    def _detect_from_environment(self) -> Optional[Dict]:
        """Detect project from environment variables"""
        try:
            project_id = os.environ.get('CLAUDE_PROJECT_ID')
            project_name = os.environ.get('CLAUDE_PROJECT_NAME')
            
            if project_id:
                return {
                    'id': project_id,
                    'name': project_name or f"Project {project_id[:8]}"
                }
        except Exception as e:
            print(f"Environment detection failed: {e}", file=sys.stderr)
        return None
    
    async def _detect_from_browser(self) -> Optional[Dict]:
        """Detect project from active browser tabs"""
        try:
            # Skip browser detection if browser isn't already initialized to avoid slow startup
            if not self.browser:
                print("🚫 Browser not initialized, skipping browser detection to avoid timeout", file=sys.stderr)
                return None
                
            # Get all pages/tabs with timeout
            try:
                pages = self.browser.pages
                
                for page in pages:
                    try:
                        # Quick URL check first
                        url = page.url
                        if 'claude.ai/project/' in url:
                            project_id = url.split('/project/')[-1].split('/')[0]
                            
                            # Try to get project name from page title with timeout
                            try:
                                title = await asyncio.wait_for(page.title(), timeout=2.0)
                                project_name = title if title and 'Claude' not in title else f"Project {project_id[:8]}"
                            except (asyncio.TimeoutError, Exception):
                                project_name = f"Project {project_id[:8]}"
                            
                            return {
                                'id': project_id,
                                'name': project_name
                            }
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"Error accessing browser pages: {e}", file=sys.stderr)
                    
        except Exception as e:
            print(f"Browser detection failed: {e}", file=sys.stderr)
        return None
    
    def _detect_from_database(self) -> Optional[Dict]:
        """Detect project from Claude Desktop's database"""
        try:
            import sqlite3
            db_path = os.path.expanduser("~/Library/Application Support/Claude/claudeSQLite.db")
            
            if not os.path.exists(db_path):
                return None
                
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Look for recent project-related activity
                cursor.execute("""
                    SELECT title, content, created_at FROM notes 
                    WHERE title LIKE '%project%' OR content LIKE '%project%'
                    ORDER BY created_at DESC LIMIT 5
                """)
                
                for title, content, created_at in cursor.fetchall():
                    # Extract project ID from content if available
                    import re
                    project_matches = re.findall(r'project/([a-f0-9-]{36})', content)
                    if project_matches:
                        project_id = project_matches[0]
                        return {
                            'id': project_id,
                            'name': title or f"Project {project_id[:8]}"
                        }
                        
        except Exception as e:
            print(f"Database detection failed: {e}", file=sys.stderr)
        return None
    
    def _detect_from_processes(self) -> Optional[Dict]:
        """Detect project from running processes"""
        try:
            import subprocess
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            
            # Look for Claude processes with project information
            for line in result.stdout.split('\n'):
                if 'Claude' in line and 'project' in line.lower():
                    # Try to extract project ID from command line
                    import re
                    project_matches = re.findall(r'project/([a-f0-9-]{36})', line)
                    if project_matches:
                        project_id = project_matches[0]
                        return {
                            'id': project_id,
                            'name': f"Project {project_id[:8]}"
                        }
                        
        except Exception as e:
            print(f"Process detection failed: {e}", file=sys.stderr)
        return None
        
    async def init_browser(self):
        """Initialize browser for web automation"""
        try:
            playwright = await async_playwright().start()
            # Use persistent context to maintain login state
            user_data_dir = os.path.expanduser("~/Library/Application Support/Claude/playwright-data")
            
            print(f"🔧 Using browser data directory: {user_data_dir}", file=sys.stderr)
            
            self.browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,  # Show browser window
                viewport={'width': 1280, 'height': 720},
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            self.page = await self.browser.new_page()
            
            # Set a proper user agent
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            print("🌐 Loading Claude web interface...", file=sys.stderr)
            await self.page.goto("https://claude.ai", wait_until='networkidle')
            
            print("✅ Browser initialized successfully", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
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
    
    async def access_current_project(self, project_id: str) -> bool:
        """Access a specific project directly by ID"""
        try:
            if not self.page:
                if not await self.init_browser():
                    return False
            
            # Go directly to the project
            project_url = f"https://claude.ai/project/{project_id}"
            print(f"🎯 Accessing project directly: {project_url}", file=sys.stderr)
            
            await self.page.goto(project_url, wait_until='networkidle')
            await self.page.wait_for_timeout(3000)  # Wait for page to load
            
            # Check if we can access the project
            current_url = self.page.url
            print(f"📍 Current URL: {current_url}", file=sys.stderr)
            
            if project_id in current_url:
                print("✅ Successfully accessed project!", file=sys.stderr)
                
                # Try to get project name from the page
                project_name = "Current Project"
                try:
                    # Look for project title elements
                    title_selectors = [
                        'h1', '[data-testid="project-title"]', '.project-title', 
                        'title', '[class*="title"]'
                    ]
                    
                    for selector in title_selectors:
                        elements = await self.page.locator(selector).all()
                        for element in elements:
                            text = await element.text_content()
                            if text and len(text.strip()) > 2 and len(text) < 100:
                                project_name = text.strip()
                                break
                        if project_name != "Current Project":
                            break
                    
                except Exception:
                    pass
                
                self.current_project = ClaudeProject(
                    id=project_id,
                    name=project_name,
                    url=project_url
                )
                
                print(f"🎉 Project set: {project_name} (ID: {project_id})", file=sys.stderr)
                return True
            else:
                print(f"❌ Could not access project. Current URL: {current_url}", file=sys.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Failed to access project: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False
    
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
            description="Add new knowledge to a Claude project via web interface automation. Automatically detects current project if none is selected.",
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
        ),
        Tool(
            name="detect_current_project_context",
            description="Dynamically detect the current Claude Desktop project context using multiple detection methods. No project ID needed - automatically finds your active project.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="access_current_project",
            description="Access a specific Claude Desktop project by ID. Use detect_current_project_context for automatic detection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "Project ID to access"}
                },
                "required": ["project_id"]
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
    
    elif name == "detect_current_project_context":
        detected_project = await web_manager.detect_current_project_context()
        
        if detected_project:
            web_manager.current_project = detected_project
            return [TextContent(
                type="text",
                text=f"✅ Successfully detected current project context!\n\n**{detected_project.name}**\n- ID: `{detected_project.id}`\n- URL: {detected_project.url}\n\n🎯 This project is now selected for adding knowledge. You can use `add_project_knowledge` to add knowledge directly to this project!"
            )]
        else:
            return [TextContent(
                type="text",
                text="❌ Could not detect current project context.\n\n**Troubleshooting:**\n1. Make sure you have a Claude project open in your browser\n2. Check that Claude Desktop is running\n3. Try using `list_claude_projects` to see available projects\n4. You can manually select a project with `select_project`"
            )]
    
    elif name == "add_project_knowledge":
        # Auto-detect current project if none is selected
        if not web_manager.current_project:
            print("🔍 No project selected, attempting auto-detection...", file=sys.stderr)
            detected_project = await web_manager.detect_current_project_context()
            
            if detected_project:
                web_manager.current_project = detected_project
                print(f"✅ Auto-detected project: {detected_project.name}", file=sys.stderr)
            else:
                return [TextContent(
                    type="text",
                    text="❌ No project selected and could not auto-detect current project.\n\n**Please try one of these options:**\n1. Use `detect_current_project_context` to auto-detect your current project\n2. Use `list_claude_projects` and `select_project` to manually choose a project\n3. Make sure you have a Claude project open in your browser"
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
    
    elif name == "access_current_project":
        project_id = arguments["project_id"]
        
        print(f"🎯 Attempting to access project: {project_id}", file=sys.stderr)
        success = await web_manager.access_current_project(project_id)
        
        if success:
            project = web_manager.current_project
            return [TextContent(
                type="text",
                text=f"✅ Successfully connected to project!\n\n**{project.name}**\n- ID: `{project.id}`\n- URL: {project.url}\n\n🎉 You can now use `add_project_knowledge` to add knowledge directly to this project!\n\n**Browser window should be visible** - you may need to log in to Claude if prompted."
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Could not access project {project_id}.\n\n**Troubleshooting:**\n1. Check if a browser window opened - you may need to log in to Claude\n2. Make sure the project ID is correct: {project_id}\n3. Verify you have access to this project\n4. Try running this command again after logging in\n5. Use `detect_current_project_context` for automatic detection"
            )]
    
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