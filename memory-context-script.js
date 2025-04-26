#!/usr/bin/env node

// memory-context-script.js - Updates Claude project instructions with context from your MCP memory service
// Usage: node memory-context-script.js --anthropic-api-key YOUR_API_KEY --project-id YOUR_PROJECT_ID

const axios = require('axios');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Try to detect Claude Desktop configuration paths
function findClaudeDesktopConfig() {
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
    
    // Check for settings.json or config.json
    const possibleNames = ['settings.json', 'config.json', 'preferences.json'];
    for (const name of possibleNames) {
      const tryPath = path.join(appDataPath, name);
      if (fs.existsSync(tryPath)) {
        configPath = tryPath;
        configExists = true;
        break;
      }
    }
    
    // Additional checks for other potential locations
    if (!configExists) {
      // Try detecting Claude Beta locations
      const betaPath = path.join(appDataPath, 'Beta');
      if (fs.existsSync(betaPath)) {
        for (const name of possibleNames) {
          const tryPath = path.join(betaPath, name);
          if (fs.existsSync(tryPath)) {
            configPath = tryPath;
            configExists = true;
            break;
          }
        }
      }
    }
  } catch (error) {
    console.warn('Error detecting Claude Desktop configuration:', error.message);
  }
  
  return { configPath, configExists };
}

// Parse Claude Desktop configuration to extract MCP memory service settings
function parseClaudeDesktopConfig(configPath) {
  try {
    const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    const memoryConfig = config?.memory || config?.tools?.memory || {};
    
    // Extract memory service settings
    const mcpMemoryDir = extractPathFromArgs(memoryConfig?.args || []);
    const chromaDbPath = memoryConfig?.env?.MCP_MEMORY_CHROMA_PATH || '';
    const backupsPath = memoryConfig?.env?.MCP_MEMORY_BACKUPS_PATH || '';
    const cliCommand = memoryConfig?.command || 'uv';
    
    return {
      found: !!(mcpMemoryDir && chromaDbPath),
      mcpMemoryDir,
      chromaDbPath,
      backupsPath,
      cliCommand
    };
  } catch (error) {
    console.warn('Error parsing Claude Desktop configuration:', error.message);
    return { found: false };
  }
}

// Extract memory service directory from args array
function extractPathFromArgs(args) {
  // In the Claude Desktop config, the directory is typically specified after "--directory"
  const dirIndex = args.indexOf('--directory');
  if (dirIndex !== -1 && dirIndex + 1 < args.length) {
    return args[dirIndex + 1];
  }
  return '';
}

// Auto-detect Claude Desktop configuration and MCP memory settings
function autoDetectClaudeDesktopSettings() {
  const { configPath, configExists } = findClaudeDesktopConfig();
  
  if (configExists) {
    console.log(`Found Claude Desktop configuration at ${configPath}`);
    const settings = parseClaudeDesktopConfig(configPath);
    
    if (settings.found) {
      console.log('Successfully detected MCP memory service settings:');
      console.log(`- MCP Memory Directory: ${settings.mcpMemoryDir}`);
      console.log(`- ChromaDB Path: ${settings.chromaDbPath}`);
      console.log(`- Backups Path: ${settings.backupsPath}`);
      console.log(`- CLI Command: ${settings.cliCommand}`);
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
    description: 'Mode to interact with MCP service: "http", "cli", or "auto" (tries to auto-detect)',
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
    cliOptions = detectedSettings;
    
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

// Validate required arguments for CLI mode
if (actualMode === 'cli') {
  if (!argv.mcpMemoryDir) {
    console.error('Error: --mcp-memory-dir is required when using CLI mode');
    process.exit(1);
  }
  if (!argv.chromaDbPath) {
    console.error('Error: --chroma-db-path is required when using CLI mode');
    process.exit(1);
  }
  if (!argv.backupsPath) {
    console.error('Error: --backups-path is required when using CLI mode');
    process.exit(1);
  }
}

// Function to query memories from MCP service via HTTP
async function getMemorySummaryHttp() {
  try {
    console.log(`Getting memories via HTTP from ${argv.mcpUrl}...`);
    
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
    console.error('Error querying MCP memory service via HTTP:', error.message);
    if (error.response) {
      console.error('API response:', error.response.data);
    }
    return { recentMemories: [], importantMemories: [] };
  }
}

// Function to query memories from MCP service via CLI
async function getMemorySummaryCli() {
  try {
    console.log(`Getting memories via CLI from ${argv.mcpMemoryDir}...`);
    
    // Set up environment variables
    const env = {
      ...process.env,
      MCP_MEMORY_CHROMA_PATH: argv.chromaDbPath,
      MCP_MEMORY_BACKUPS_PATH: argv.backupsPath
    };
    
    // Make sure the paths exist
    if (!fs.existsSync(argv.mcpMemoryDir)) {
      throw new Error(`MCP Memory Service directory not found: ${argv.mcpMemoryDir}`);
    }
    if (!fs.existsSync(argv.chromaDbPath)) {
      // Create the directory if it doesn't exist
      fs.mkdirSync(argv.chromaDbPath, { recursive: true });
      console.log(`Created ChromaDB directory: ${argv.chromaDbPath}`);
    }
    if (!fs.existsSync(argv.backupsPath)) {
      // Create the directory if it doesn't exist
      fs.mkdirSync(argv.backupsPath, { recursive: true });
      console.log(`Created backups directory: ${argv.backupsPath}`);
    }
    
    // Get recent memories (last 48 hours)
    console.log('Getting recent memories...');
    const recentQuery = JSON.stringify({
      query: 'recall what was stored in the last 48 hours',
      n_results: argv.maxRecentMemories
    });
    
    const cliCmd = argv.cliCommand === 'npx' ? 'npx' : 'uv';
    const recentMemoriesCmd = execSync(
      `${cliCmd} --directory "${argv.mcpMemoryDir}" run memory recall_memory '${recentQuery}'`,
      { env, encoding: 'utf-8' }
    );
    
    // Parse the output
    let recentMemories = [];
    try {
      const recentResult = JSON.parse(recentMemoriesCmd.toString());
      recentMemories = recentResult.result || [];
    } catch (error) {
      console.error('Error parsing recent memories output:', error.message);
      console.error('Output was:', recentMemoriesCmd);
    }
    
    // Get important memories (tagged as important)
    console.log('Getting important memories...');
    const importantQuery = JSON.stringify({
      tags: ['important']
    });
    
    const importantMemoriesCmd = execSync(
      `${cliCmd} --directory "${argv.mcpMemoryDir}" run memory search_by_tag '${importantQuery}'`,
      { env, encoding: 'utf-8' }
    );
    
    // Parse the output
    let importantMemories = [];
    try {
      const importantResult = JSON.parse(importantMemoriesCmd.toString());
      importantMemories = importantResult.result || [];
      
      // Limit important memories to specified max
      importantMemories = importantMemories.slice(0, argv.maxImportantMemories);
    } catch (error) {
      console.error('Error parsing important memories output:', error.message);
      console.error('Output was:', importantMemoriesCmd);
    }
    
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
  if (actualMode === 'http') {
    return getMemorySummaryHttp();
  } else {
    return getMemorySummaryCli();
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
    
    // First, get current project details
    const getResponse = await axios.get(
      `https://api.anthropic.com/v1/projects/${argv.projectId}`,
      {
        headers: {
          'x-api-key': argv.anthropicApiKey,
          'anthropic-version': '2023-06-01'
        }
      }
    );
    
    const project = getResponse.data;
    console.log('Successfully retrieved project details');
    
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
    
    // Update project with new system prompt
    console.log('Sending updated project instructions...');
    await axios.patch(
      `https://api.anthropic.com/v1/projects/${argv.projectId}`,
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

// Main function
async function main() {
  try {
    console.log(`Running in ${actualMode.toUpperCase()} mode`);
    
    console.log('Fetching memory summary from MCP service...');
    const memorySummary = await getMemorySummary();
    
    const memoryCount = (memorySummary.recentMemories?.length || 0) + 
                       (memorySummary.importantMemories?.length || 0);
    
    console.log(`Retrieved ${memoryCount} memories in total`);
    
    console.log('Formatting memory context...');
    const memoryContext = formatMemoryContext(memorySummary);
    
    console.log('Updating Claude project instructions...');
    const success = await updateProjectInstructions(memoryContext);
    
    if (success) {
      console.log('Memory context successfully injected into Claude project instructions');
      process.exit(0);
    } else {
      console.error('Failed to update Claude project instructions');
      process.exit(1);
    }
  } catch (error) {
    console.error('Error in memory context script:', error.message);
    process.exit(1);
  }
}

// Run the script
main();