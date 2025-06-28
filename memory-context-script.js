#!/usr/bin/env node

// memory-context-script.js - Updates Claude project instructions with context from your MCP memory service

const axios = require('axios');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('=== Starting Memory Context Update ===');

// Custom function to find Claude Desktop config specific to this user's system
function findClaudeDesktopConfig() {
  // Check the specific file path mentioned by the user
  const specificPath = path.join(os.homedir(), 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
  
  if (fs.existsSync(specificPath)) {
    console.log(`Found Claude Desktop configuration at ${specificPath}`);
    return { configPath: specificPath, configExists: true };
  }
  
  // Fall back to general search logic
  let configPath = '';
  let configExists = false;
  
  try {
    const homeDir = os.homedir();
    let appDataPath = '';
    
    // Determine OS-specific application data directory
    if (process.platform === 'win32') {
      // Windows
      appDataPath = path.join(homeDir, 'AppData', 'Roaming', 'Claude');
    } else if (process.platform === 'darwin') {
      // macOS
      appDataPath = path.join(homeDir, 'Library', 'Application Support', 'Claude');
    } else if (process.platform === 'linux') {
      // Linux
      appDataPath = path.join(homeDir, '.config', 'Claude');
    }
    
    // Check for various possible config file names
    const possibleNames = [
      'claude_desktop_config.json',
      'settings.json', 
      'config.json', 
      'preferences.json'
    ];
    
    for (const name of possibleNames) {
      const tryPath = path.join(appDataPath, name);
      if (fs.existsSync(tryPath)) {
        configPath = tryPath;
        configExists = true;
        console.log(`Found configuration file: ${tryPath}`);
        break;
      }
    }
  } catch (error) {
    console.warn('Error detecting Claude Desktop configuration:', error.message);
  }
  
  if (!configExists) {
    console.warn('Could not find Claude Desktop configuration file');
  }
  
  return { configPath, configExists };
}

// Parse Claude Desktop configuration to extract MCP memory service settings
// Parse Claude Desktop configuration to extract MCP memory service settings
function parseClaudeDesktopConfig(configPath) {
  try {
    console.log(`Reading config file: ${configPath}`);
    const configContent = fs.readFileSync(configPath, 'utf8');
    console.log(`Config file content length: ${configContent.length} characters`);
    
    const config = JSON.parse(configContent);
    
    // Log the structure to help debug
    console.log('Top level config keys:', Object.keys(config));
    
    // Look for memory service in mcpServers section
    const mcpServers = config.mcpServers || {};
    console.log('Available MCP servers:', Object.keys(mcpServers));
    
    // Look for a server that might be the memory service
    let memoryServer = null;
    
    // First try to find a server with "memory" in the name
    for (const [serverName, serverConfig] of Object.entries(mcpServers)) {
      if (serverName.toLowerCase().includes('memory')) {
        console.log(`Found memory server by name: ${serverName}`);
        memoryServer = { name: serverName, config: serverConfig };
        break;
      }
    }
    
    // If no memory server found by name, try to examine each server's args
    if (!memoryServer) {
      for (const [serverName, serverConfig] of Object.entries(mcpServers)) {
        if (Array.isArray(serverConfig.args) && 
            (serverConfig.args.includes('memory') || 
             serverConfig.args.some(arg => arg && arg.includes && arg.includes('memory')))) {
          console.log(`Found likely memory server: ${serverName}`);
          memoryServer = { name: serverName, config: serverConfig };
          break;
        }
      }
    }
    
    if (!memoryServer) {
      console.log('Could not identify memory service in mcpServers configuration');
      return { found: false };
    }
    
    console.log('Memory server configuration:', JSON.stringify(memoryServer.config, null, 2));
    
    // Extract memory service settings
    let mcpMemoryDir = '';
    
    // Look for directory in args
    if (Array.isArray(memoryServer.config.args)) {
      // Print all args for debugging
      console.log('Server args:', memoryServer.config.args);
      
      // Look for --directory argument
      const dirIndex = memoryServer.config.args.indexOf('--directory');
      if (dirIndex !== -1 && dirIndex + 1 < memoryServer.config.args.length) {
        mcpMemoryDir = memoryServer.config.args[dirIndex + 1];
      }
      
      // If no --directory found, look for a path that might be the memory service
      if (!mcpMemoryDir) {
        for (const arg of memoryServer.config.args) {
          if (typeof arg === 'string' && 
              (arg.includes('memory-service') || arg.includes('mcp-memory'))) {
            mcpMemoryDir = arg;
            break;
          }
        }
      }
    }
    
    // Get environment variables
    const env = memoryServer.config.env || {};
    const chromaDbPath = env.MCP_MEMORY_CHROMA_PATH || '';
    const backupsPath = env.MCP_MEMORY_BACKUPS_PATH || '';
    const cliCommand = memoryServer.config.command || 'uv';
    
    console.log('Extracted configuration:');
    console.log(`- MCP Memory Directory: ${mcpMemoryDir}`);
    console.log(`- ChromaDB Path: ${chromaDbPath}`);
    console.log(`- Backups Path: ${backupsPath}`);
    console.log(`- CLI Command: ${cliCommand}`);
    
    return {
      found: !!(mcpMemoryDir && chromaDbPath),
      mcpMemoryDir,
      chromaDbPath,
      backupsPath,
      cliCommand
    };
  } catch (error) {
    console.warn('Error parsing Claude Desktop configuration:', error.message);
    if (error instanceof SyntaxError) {
      console.warn('JSON parsing error - the config file might not be valid JSON');
    }
    return { found: false };
  }
}

// Auto-detect Claude Desktop configuration and MCP memory settings
function autoDetectClaudeDesktopSettings() {
  const { configPath, configExists } = findClaudeDesktopConfig();
  
  if (configExists) {
    console.log(`Found Claude Desktop configuration at ${configPath}`);
    const settings = parseClaudeDesktopConfig(configPath);
    
    if (settings.found) {
      console.log('Successfully detected MCP memory service settings');
      return settings;
    } else {
      console.warn('Found Claude Desktop configuration, but could not detect MCP memory service settings');
    }
  } else {
    console.warn('Could not find Claude Desktop configuration');
  }
  
  return { found: false };
}

// Parse command line arguments
const argv = yargs(hideBin(process.argv))
  .option('anthropic-api-key', {
    type: 'string',
    description: 'Your Anthropic API key',
    demandOption: true
  })
  .option('project-id', {
    type: 'string', 
    description: 'Claude Project ID',
    demandOption: true
  })
  .option('mode', {
    type: 'string',
    description: 'Mode to interact with MCP service: "http", "cli", or "auto"',
    choices: ['http', 'cli', 'auto'],
    default: 'auto'
  })
  // Options for HTTP mode
  .option('mcp-url', {
    type: 'string',
    description: 'MCP memory service URL (for HTTP mode)',
    default: 'http://localhost:8000'
  })
  // Options for CLI mode
  .option('mcp-memory-dir', {
    type: 'string',
    description: 'Path to MCP Memory Service directory (for CLI mode)',
    default: process.env.MCP_MEMORY_DIR || ''
  })
  .option('chroma-db-path', {
    type: 'string',
    description: 'Path to ChromaDB data directory (for CLI mode)',
    default: process.env.MCP_MEMORY_CHROMA_PATH || ''
  })
  .option('backups-path', {
    type: 'string',
    description: 'Path to backups directory (for CLI mode)',
    default: process.env.MCP_MEMORY_BACKUPS_PATH || ''
  })
  .option('cli-command', {
    type: 'string',
    description: 'Command to run MCP service (uv or npx)',
    default: 'uv'
  })
  // Common options
  .option('max-recent-memories', {
    type: 'number',
    description: 'Maximum number of recent memories to include',
    default: 5
  })
  .option('max-important-memories', {
    type: 'number',
    description: 'Maximum number of important memories to include',
    default: 3
  })
  .option('memory-prefix', {
    type: 'string',
    description: 'Template prefix to use for memory context',
    default: 'You have a searchable memory. '
  })
  .help()
  .argv;

// If mode is 'auto', try to auto-detect Claude Desktop settings
let actualMode = argv.mode;
let cliOptions = {};

if (argv.mode === 'auto') {
  const detectedSettings = autoDetectClaudeDesktopSettings();
  
  if (detectedSettings.found) {
    actualMode = 'cli';
    
    // Override CLI options with detected settings
    argv.mcpMemoryDir = detectedSettings.mcpMemoryDir;
    argv.chromaDbPath = detectedSettings.chromaDbPath;
    argv.backupsPath = detectedSettings.backupsPath;
    argv.cliCommand = detectedSettings.cliCommand;
    
    console.log('Automatically using CLI mode with detected settings');
  } else {
    actualMode = 'http';
    console.log('Could not detect Claude Desktop settings, falling back to HTTP mode');
  }
}

// Function to query memories from MCP service via HTTP
async function getMemorySummaryHttp() {
  try {
    console.log(`Querying MCP service at: ${argv.mcpUrl}`);
    
    // Get recent memories (last 48 hours)
    const recentResponse = await axios.post(`${argv.mcpUrl}/mcp`, {
      tool: 'memory',
      action: 'recall_memory',
      input: {
        query: 'recall what was stored in the last 48 hours',
        n_results: argv.maxRecentMemories
      }
    });
    
    // Get important memories (tagged as important)
    const importantResponse = await axios.post(`${argv.mcpUrl}/mcp`, {
      tool: 'memory',
      action: 'search_by_tag',
      input: {
        tags: ['important']
      }
    });

    // Extract memories from responses
    const recentMemories = recentResponse.data.result || [];
    let importantMemories = importantResponse.data.result || [];
    
    // Limit important memories to specified max
    importantMemories = importantMemories.slice(0, argv.maxImportantMemories);
    
    return {
      recentMemories,
      importantMemories
    };
  } catch (error) {
    console.error('Error querying MCP memory service:');
    console.error(`Status: ${error.response?.status}`);
    console.error(`Status Text: ${error.response?.statusText}`);
    console.error(`Error Details: ${error.response?.data}`);
    console.error(`Request URL: ${error.config?.url}`);
    console.error(`Request Method: ${error.config?.method}`);
    return { recentMemories: [], importantMemories: [] };
  }
}

// Function to query memories from MCP service via CLI
async function getMemorySummaryCli() {
  try {
    console.log(`Getting memories via CLI from ${argv.mcpMemoryDir}...`);
    
    // First, start the memory service as a server on a temporary port
    const tempPort = 8765;
    console.log(`Starting memory service on port ${tempPort}...`);
    
    // Set up environment variables
    const env = {
      ...process.env,
      MCP_MEMORY_CHROMA_PATH: argv.chromaDbPath,
      MCP_MEMORY_BACKUPS_PATH: argv.backupsPath
    };
    
    // Start the server in the background
    const serverProcess = require('child_process').spawn(
      argv.cliCommand,
      [
        '--directory', argv.mcpMemoryDir,
        'run', 'memory', 'server',
        '--port', tempPort.toString()
      ],
      { 
        env,
        detached: true,
        stdio: 'ignore'
      }
    );
    
    // Wait for server to start
    console.log('Waiting for server to start...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Now query the server using HTTP
    console.log(`Querying memory service at http://localhost:${tempPort}...`);
    
    // Get recent memories (last 48 hours)
    const recentResponse = await axios.post(`http://localhost:${tempPort}/mcp`, {
      tool: 'memory',
      action: 'recall_memory',
      input: {
        query: 'recall what was stored in the last 48 hours',
        n_results: argv.maxRecentMemories
      }
    });
    
    // Get important memories (tagged as important)
    const importantResponse = await axios.post(`http://localhost:${tempPort}/mcp`, {
      tool: 'memory',
      action: 'search_by_tag',
      input: {
        tags: ['important']
      }
    });
    
    // Kill the server process
    if (serverProcess.pid) {
      process.kill(-serverProcess.pid);
    }
    
    // Extract memories from responses
    const recentMemories = recentResponse.data.result || [];
    let importantMemories = importantResponse.data.result || [];
    
    // Limit important memories to specified max
    importantMemories = importantMemories.slice(0, argv.maxImportantMemories);
    
    return {
      recentMemories,
      importantMemories
    };
  } catch (error) {
    console.error('Error executing MCP memory service via CLI:', error.message);
    return { recentMemories: [], importantMemories: [] };
  }
}

// Choose the appropriate method based on mode
async function getMemorySummary() {
  console.log(`Running in ${actualMode.toUpperCase()} mode`);
  
  if (actualMode === 'http') {
    return getMemorySummaryHttp();
  } else if (actualMode === 'cli') {
    return getMemorySummaryCli();
  } else {
    // Auto mode - try CLI first, then fall back to HTTP if it fails
    try {
      return await getMemorySummaryCli();
    } catch (error) {
      console.log('CLI mode failed, falling back to HTTP mode');
      return getMemorySummaryHttp();
    }
  }
}

// Format memories into instruction text
function formatMemoryContext(memorySummary) {
  const { recentMemories, importantMemories } = memorySummary;
  
  // Extract topics from memories
  const recentTopics = [...new Set(
    recentMemories
      .flatMap(memory => memory.metadata?.tags || [])
      .filter(Boolean)
  )].slice(0, 10);
  
  let contextText = argv.memoryPrefix;
  
  // Recent topics section
  if (recentTopics.length > 0) {
    contextText += `\n\nRecent topics you remember include: ${recentTopics.join(', ')}.`;
  }
  
  // Important memories section
  if (importantMemories.length > 0) {
    contextText += '\n\nImportant long-term memories include:';
    importantMemories.forEach(memory => {
      // Truncate content if too long
      const content = memory.content?.length > 100 
        ? memory.content.substring(0, 100) + '...' 
        : (memory.content || 'No content');
      
      contextText += `\n- ${content}`;
    });
  }
  
  // Instructions for using memory
  contextText += '\n\nIf the user mentions any of these topics or needs additional information, ' +
                'you can help them retrieve more from their memory by suggesting they ask about ' +
                'specific topics or use the memory search functions.';
  
  return contextText;
}

// Update Claude project instructions 
async function updateProjectInstructions(memoryContext) {
  try {
    console.log(`Updating project ${argv.projectId} with Anthropic API...`);
    
    // Try different API endpoints
    const possibleEndpoints = [
      `https://api.anthropic.com/v1/projects/${argv.projectId}`,
      `https://api.anthropic.com/v1/human/projects/${argv.projectId}`,
      `https://api.anthropic.com/v1/users/me/projects/${argv.projectId}`,
      `https://api.anthropic.com/v1/claude-beta/projects/${argv.projectId}`
    ];
    
    let project = null;
    let usedEndpoint = '';
    
    // Try to get project details from different endpoints
    for (const endpoint of possibleEndpoints) {
      try {
        console.log(`Trying to get project from: ${endpoint}`);
        const response = await axios.get(endpoint, {
          headers: {
            'x-api-key': argv.anthropicApiKey,
            'anthropic-version': '2023-06-01'
          }
        });
        
        if (response.status === 200 && response.data) {
          project = response.data;
          usedEndpoint = endpoint;
          console.log(`Successfully retrieved project details from ${endpoint}`);
          break;
        }
      } catch (error) {
        console.log(`Endpoint ${endpoint} failed: ${error.message}`);
      }
    }
    
    if (!project) {
      throw new Error('Could not retrieve project details from any endpoint');
    }
    
    // Update memory section in system prompt
    // Keep other sections intact
    let systemPrompt = project.system_prompt || '';
    
    // Replace or add memory section
    const memorySection = /<!-- MEMORY CONTEXT START -->[\s\S]*?<!-- MEMORY CONTEXT END -->/;
    const newMemorySection = `<!-- MEMORY CONTEXT START -->\n${memoryContext}\n<!-- MEMORY CONTEXT END -->`;
    
    if (memorySection.test(systemPrompt)) {
      systemPrompt = systemPrompt.replace(memorySection, newMemorySection);
      console.log('Replaced existing memory context section');
    } else {
      systemPrompt += `\n\n${newMemorySection}`;
      console.log('Added new memory context section');
    }
    
    // Update project with new system prompt using the same endpoint that worked
    console.log('Sending updated project instructions...');
    await axios.patch(
      usedEndpoint,
      {
        system_prompt: systemPrompt
      },
      {
        headers: {
          'x-api-key': argv.anthropicApiKey,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json'
        }
      }
    );
    
    console.log('Successfully updated project instructions with memory context');
    return true;
  } catch (error) {
    console.error('Error updating project instructions:', error.message);
    if (error.response) {
      console.error('API response:', error.response.data);
    }
    return false;
  }
}

// Instead of updateProjectInstructions, create a function to save the context to a file
async function saveMemoryContextToFile(memoryContext) {
  try {
    // Format the complete memory context with markers
    const formattedContext = `<!-- MEMORY CONTEXT START -->\n${memoryContext}\n<!-- MEMORY CONTEXT END -->`;
    
    // Save to a file
    const outputPath = path.join(process.cwd(), 'memory-context.txt');
    fs.writeFileSync(outputPath, formattedContext, 'utf8');
    
    console.log(`Memory context saved to: ${outputPath}`);
    console.log('\nYou can now copy this content into your Claude project instructions at:');
    console.log(`https://claude.ai/project/${argv.projectId}`);
    
    // Also print to console for convenience
    console.log('\n--- MEMORY CONTEXT ---');
    console.log(formattedContext);
    console.log('--- END MEMORY CONTEXT ---');
    
    return true;
  } catch (error) {
    console.error('Error saving memory context:', error.message);
    return false;
  }
}

// Main function
async function main() {
  try {
    const memorySummary = await getMemorySummary();
    
    console.log('Formatting memory context...');
    const memoryContext = formatMemoryContext(memorySummary);
    
    const success = await saveMemoryContextToFile(memoryContext);
    
    if (success) {
      console.log('✅ Memory context generated successfully');
      process.exit(0);
    } else {
      console.error('❌ Failed to generate memory context');
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Script execution failed:');
    console.error(error.message);
    console.error(`\nThe Path: ${__filename}`);
    process.exit(1);
  }
}

// Run the script
main();