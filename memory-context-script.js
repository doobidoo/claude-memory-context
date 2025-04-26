#!/usr/bin/env node

// memory-context-script.js - Updates Claude project instructions with memory context
// Usage: node memory-context-script.js --anthropic-api-key YOUR_API_KEY --project-id YOUR_PROJECT_ID

const axios = require('axios');
const yargs = require('yargs/yargs');
const { hideBin } = require('yargs/helpers');

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
  .option('mcp-url', {
    type: 'string',
    description: 'MCP memory service URL',
    default: 'http://localhost:8000'
  })
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

// Function to query memories from MCP service
async function getMemorySummary() {
  try {
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
    console.error('Error querying MCP memory service:', error.message);
    return { recentMemories: [], importantMemories: [] };
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
      const content = memory.content.length > 100 
        ? memory.content.substring(0, 100) + '...' 
        : memory.content;
      
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
    
    // Update memory section in system prompt
    // Keep other sections intact
    let systemPrompt = project.system_prompt || '';
    
    // Replace or add memory section
    const memorySection = /<!-- MEMORY CONTEXT START -->[\s\S]*?<!-- MEMORY CONTEXT END -->/;
    const newMemorySection = `<!-- MEMORY CONTEXT START -->\n${memoryContext}\n<!-- MEMORY CONTEXT END -->`;
    
    if (memorySection.test(systemPrompt)) {
      systemPrompt = systemPrompt.replace(memorySection, newMemorySection);
    } else {
      systemPrompt += `\n\n${newMemorySection}`;
    }
    
    // Update project with new system prompt
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
  } catch (error) {
    console.error('Error updating project instructions:', error.message);
    if (error.response) {
      console.error('API response:', error.response.data);
    }
  }
}

// Main function
async function main() {
  try {
    console.log('Fetching memory summary from MCP service...');
    const memorySummary = await getMemorySummary();
    
    console.log('Formatting memory context...');
    const memoryContext = formatMemoryContext(memorySummary);
    
    console.log('Updating Claude project instructions...');
    await updateProjectInstructions(memoryContext);
    
    console.log('Memory context successfully injected into Claude project instructions');
  } catch (error) {
    console.error('Error in memory context script:', error.message);
    process.exit(1);
  }
}

// Run the script
main();