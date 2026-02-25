#!/usr/bin/env node

/**
 * MCP Client Demo - Widget Scenario
 *
 * Interactive demo for:
 * 1. Account selection (from) - single-choice widget
 * 2. Account selection (to) - single-choice widget
 * 3. Date selection - date-picker widget
 * 4. Confirmation - confirmation widget
 *
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import * as readline from 'readline';
import logger from '../logger';

// Global variables for context
let SYSTEM_CONTEXT: Record<string, any> = {};
let OTHER_CONTEXT: Record<string, any> = {};

interface WidgetResponse {
  _meta?: {
    refreshThreadCapabilities?: string;
    'com.ibm.orchestrate/widget'?: {
      responseType: string;
      title?: string;
      description?: string;
      text?: string;
      options?: Array<{
        value: string;
        label: string;
        description?: string;
      }>;
      onChange?: {
        toolName: string;
        parameters: Record<string, any>;
        mapSelectionTo: string;
      };
      minDate?: string;
      maxDate?: string;
      minDigits?: number;
      maxDigits?: number;
      confirmationText?: string;
      onConfirm?: {
        tool: string;
        parameters: Record<string, any>;
      };
      onCancel?: {
        tool: string;
        parameters: Record<string, any>;
      };
    };
  };
}

/**
 * Demo client for widget-based money transfer flow
 */
class WidgetDemoClient {
  private client: Client;
  private transport: StreamableHTTPClientTransport;
  private verbose: boolean;
  private threadId: string;
  private rl: readline.Interface;

  constructor(private serverUrl: string, verbose: boolean = false) {
    this.verbose = verbose;
    this.threadId = `thread_${Date.now()}`; // Generate a unique thread ID
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
    this.transport = new StreamableHTTPClientTransport(
      new URL(this.serverUrl),
      {
        fetch: async (url, init) => {
          if (this.verbose) {
            console.log('[CLIENT] Fetch request:', {
              url: url.toString(),
              method: init?.method,
              headers: init?.headers,
              body: init?.body ? JSON.parse(init.body as string) : null,
            });
          }
          const response = await fetch(url, init);
          const responseText = await response.text();
          if (this.verbose) {
            console.log('[CLIENT] Fetch response:', {
              status: response.status,
              headers: Object.fromEntries(response.headers.entries()),
              body: responseText,
            });
          }
          // Return a new response with the same data
          return new Response(responseText, {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers,
          });
        },
      },
    );

    this.client = new Client(
      {
        name: 'widget-demo-client',
        version: '1.0.0',
      },
      {
        capabilities: {},
      },
    );
  }

  /**
   * Initialize the MCP connection
   */
  async connect(): Promise<void> {
    console.log('\n[CONNECT] Connecting to MCP server...');
    console.log(`[CONNECT] Server URL: ${this.serverUrl}`);
    console.log(`[CONNECT] System Context:`, SYSTEM_CONTEXT);
    console.log(`[CONNECT] Other Context:`, OTHER_CONTEXT);
    console.log(`[CONNECT] Thread ID: ${this.threadId}`);
    
    await this.client.connect(this.transport);
    console.log('[CONNECT] Connected successfully!');
  }

  /**
   * List available tools
   */
  async listTools(): Promise<void> {
    console.log('\n[TOOLS] Listing available tools...');
    const response = await this.client.listTools({
      _meta: {
        'com.ibm.orchestrate/systemcontext': {
          thread_id: this.threadId,
          ...SYSTEM_CONTEXT,
        },
        'com.ibm.orchestrate/context': OTHER_CONTEXT,
      },
    });
    
    console.log(`\n[TOOLS] Found ${response.tools.length} tools:`);
    response.tools.forEach(tool => {
      console.log(`  - ${tool.name}: ${tool.description}`);
    });
  }

  /**
   * List available resources
   */
  async listResources(): Promise<void> {
    logger.info('\n[RESOURCES] Listing available resources...');
    const response = await this.client.listResources({
        _meta: {
          'com.ibm.orchestrate/systemcontext': {
            thread_id: this.threadId,
            ...SYSTEM_CONTEXT,
          },
          'com.ibm.orchestrate/context': OTHER_CONTEXT,
        },
      });
      
      logger.info(`\n[RESOURCES] Found ${response.resources.length} resources:`);
      response.resources.forEach((resource: any) => {
        logger.info(`  - ${resource.name} (${resource.uri})`);
        if (resource.description) {
          logger.info(`    ${resource.description}`);
        }
      });
  }

  /**
   * Read a resource
   */
  async readResource(uri: string): Promise<void> {
    console.log(`\n[RESOURCE] Reading resource: ${uri}`);
    const response = await this.client.readResource({
      uri,
      _meta: {
        'com.ibm.orchestrate/systemcontext': {
          thread_id: this.threadId,
          ...SYSTEM_CONTEXT,
        },
        'com.ibm.orchestrate/context': OTHER_CONTEXT,
      },
    });
    
    response.contents.forEach((content: any) => {
      if ('text' in content) {
        console.log(`\n${content.text}`);
      }
    });
  }

  /**
   * Call a tool and handle widget response
   */
  async callTool(
    toolName: string,
    args: Record<string, any>,
  ): Promise<WidgetResponse> {
    console.log(`\n[TOOL] Calling tool: ${toolName}`);
    if (this.verbose) {
      console.log(`[TOOL] Arguments:`, JSON.stringify(args, null, 2));
    }

    // Pass _meta at the params level (sibling to arguments, not inside it)
    const response = await this.client.callTool({
      name: toolName,
      arguments: args,
      _meta: {
        'com.ibm.orchestrate/systemcontext': {
          thread_id: this.threadId,
          ...SYSTEM_CONTEXT,
        },
        'com.ibm.orchestrate/context': OTHER_CONTEXT,
      },
    });

    // Always log response structure for debugging
    console.log(`[TOOL] Response:`, JSON.stringify(response, null, 2));

    return response as WidgetResponse;
  }

  /**
   * Display widget information
   */
  displayWidget(response: WidgetResponse): void {
    const widget = response._meta?.['com.ibm.orchestrate/widget'];
    
    if (!widget) {
      console.log('\n[WIDGET] No widget in response');
      return;
    }

    console.log('\n[WIDGET] Widget Response:');
    console.log(`[WIDGET] Type: ${widget.responseType}`);

    switch (widget.responseType) {
      case 'single-choice':
        console.log(`[WIDGET] Title: ${widget.title}`);
        console.log(`[WIDGET] Description: ${widget.description}`);
        console.log(`\n[WIDGET] Options:`);
        widget.options?.forEach((opt, idx) => {
          console.log(`  ${idx + 1}. ${opt.label}`);
          if (opt.description) {
            console.log(`     ${opt.description}`);
          }
        });
        console.log(`\n[WIDGET] On selection, will call: ${widget.onChange?.toolName}`);
        console.log(`[WIDGET] Map selection to parameter: ${widget.onChange?.mapSelectionTo}`);
        break;

      case 'date-picker':
        console.log(`[WIDGET] Title: ${widget.title}`);
        console.log(`[WIDGET] Description: ${widget.description}`);
        console.log(`[WIDGET] Date range: ${widget.minDate} to ${widget.maxDate}`);
        console.log(`\n[WIDGET] On selection, will call: ${widget.onChange?.toolName}`);
        console.log(`[WIDGET] Map selection to parameter: ${widget.onChange?.mapSelectionTo}`);
        break;

      case 'numeric':
        console.log(`[WIDGET] Text: ${widget.text || widget.description}`);
        if (widget.minDigits !== undefined || widget.maxDigits !== undefined) {
          console.log(`[WIDGET] Digits: ${widget.minDigits || 'any'} to ${widget.maxDigits || 'any'}`);
        }
        console.log(`\n[WIDGET] On input, will call: ${widget.onChange?.toolName}`);
        console.log(`[WIDGET] Map input to parameter: ${widget.onChange?.mapSelectionTo}`);
        break;

      case 'confirmation':
        console.log(`\n${widget.confirmationText}`);
        console.log(`\n[WIDGET] On Confirm: Call ${widget.onConfirm?.tool}`);
        console.log(`[WIDGET] On Cancel: Call ${widget.onCancel?.tool}`);
        break;

      default:
        console.log(`[WIDGET] Unknown widget type: ${widget.responseType}`);
    }
  }

  /**
   * Prompt user for input with a question and hint
   */
  async promptUser(question: string, hint: string): Promise<string> {
    return new Promise((resolve) => {
      console.log(`\n${question}`);
      console.log(`Hint: ${hint}`);
      this.rl.question('> ', (answer: string) => {
        resolve(answer.trim());
      });
    });
  }

  /**
   * Get user selection from a single-choice widget
   */
  async getUserSelection(
    response: WidgetResponse,
  ): Promise<{ toolName: string; args: Record<string, any> } | null> {
    const widget = response._meta?.['com.ibm.orchestrate/widget'];
    
    if (!widget || widget.responseType !== 'single-choice') {
      return null;
    }

    const optionsText = widget.options?.map((opt, idx) =>
      `  ${idx + 1}. ${opt.label} (value: ${opt.value})${opt.description ? '\n     ' + opt.description : ''}`
    ).join('\n') || '';
    
    const hint = `Enter the value you want to select (e.g., ${widget.options?.[0]?.value || 'value'})`;
    
    const selectedValue = await this.promptUser(
      `\n[USER INPUT REQUIRED] ${widget.title}\n${widget.description}\n\nOptions:\n${optionsText}`,
      hint
    );

    console.log(`\n[USER] Selected value: ${selectedValue}`);

    const toolName = widget.onChange!.toolName;
    const args = {
      ...widget.onChange!.parameters,
      [widget.onChange!.mapSelectionTo]: selectedValue,
    };

    return { toolName, args };
  }

  /**
   * Get user date selection from a date-picker widget
   */
  async getUserDateSelection(
    response: WidgetResponse,
  ): Promise<{ toolName: string; args: Record<string, any> } | null> {
    const widget = response._meta?.['com.ibm.orchestrate/widget'];
    
    if (!widget || widget.responseType !== 'date-picker') {
      return null;
    }

    const hint = `Enter a date (e.g., ${widget.minDate || '2026-01-15'})`;
    
    const date = await this.promptUser(
      `\n[USER INPUT REQUIRED] ${widget.title}\n${widget.description}\nDate range: ${widget.minDate} to ${widget.maxDate}`,
      hint
    );

    console.log(`\n[USER] Selected date: ${date}`);

    const toolName = widget.onChange!.toolName;
    const args = {
      ...widget.onChange!.parameters,
      [widget.onChange!.mapSelectionTo]: date,
    };

    return { toolName, args };
  }
  /**
   * Get user numeric input from a numeric widget
   */
  async getUserNumericInput(
    response: WidgetResponse,
  ): Promise<{ toolName: string; args: Record<string, any> } | null> {
    const widget = response._meta?.['com.ibm.orchestrate/widget'];
    
    if (!widget || widget.responseType !== 'numeric') {
      return null;
    }

    const digitInfo = widget.minDigits !== undefined || widget.maxDigits !== undefined
      ? ` (${widget.minDigits || 'any'}-${widget.maxDigits || 'any'} digits)`
      : '';
    const hint = `Enter numeric value${digitInfo}`;
    
    const input = await this.promptUser(
      `\n[USER INPUT REQUIRED] ${widget.text || widget.description || 'Enter numeric input'}`,
      hint
    );

    console.log(`\n[USER] Entered: ${input}`);

    const toolName = widget.onChange!.toolName;
    const args = {
      ...widget.onChange!.parameters,
      [widget.onChange!.mapSelectionTo]: input,
    };

    return { toolName, args };
  }


  /**
   * Get user confirmation action
   */
  async getUserConfirmation(
    response: WidgetResponse,
  ): Promise<{ toolName: string; args: Record<string, any> } | null> {
    const widget = response._meta?.['com.ibm.orchestrate/widget'];
    
    if (!widget || widget.responseType !== 'confirmation') {
      return null;
    }

    const hint = `Type 'confirm' or 'cancel'`;
    
    const input = await this.promptUser(
      `\n[USER INPUT REQUIRED] ${widget.confirmationText}`,
      hint
    );

    const confirm = input.toLowerCase() === 'confirm';
    const action = confirm ? 'Confirm' : 'Cancel';
    console.log(`\n[USER] Action: ${action}`);

    const toolCall = confirm ? widget.onConfirm : widget.onCancel;
    if (!toolCall) {
      return null;
    }

    return {
      toolName: toolCall.tool,
      args: toolCall.parameters,
    };
  }

  /**
   * Display final result
   */
  displayResult(response: any): void {
    console.log('\n[RESULT] Final Result:');
    
    if (response.content) {
      response.content.forEach((item: any) => {
        if (item.type === 'text') {
          console.log(`\n${item.text}`);
          if (item.annotations?.audience) {
            console.log(`[RESULT] (Audience: ${item.annotations.audience.join(', ')})`);
          }
        }
      });
    }
  }

  /**
   * Close the connection
   */
  async close(): Promise<void> {
    console.log('\n[CLOSE] Closing connection...');
    this.rl.close();
    await this.client.close();
    console.log('[CLOSE] Connection closed');
  }
}

/**
 * Process widget response and get next action from user
 */
async function processWidget(
  client: WidgetDemoClient,
  response: WidgetResponse,
): Promise<{ toolName: string; args: Record<string, any> } | null> {
  const widget = response._meta?.['com.ibm.orchestrate/widget'];
  
  if (!widget) {
    return null;
  }

  client.displayWidget(response);

  switch (widget.responseType) {
    case 'single-choice':
      return await client['getUserSelection'](response);
    
    case 'date-picker':
      return await client['getUserDateSelection'](response);
    
    case 'numeric':
      return await client['getUserNumericInput'](response);
    
    case 'confirmation':
      return await client['getUserConfirmation'](response);
    
    default:
      console.log(`[WIDGET] Unknown widget type: ${widget.responseType}`);
      return null;
  }
}

/**
 * Display available tools and prompt user to select one
 */
async function selectTool(
  client: WidgetDemoClient,
  tools: Array<{ name: string; description?: string; inputSchema?: any }>,
): Promise<{ toolName: string; args: Record<string, any> } | null> {
  console.log('\n===============================================================');
  console.log('  Available Tools');
  console.log('===============================================================');
  
  tools.forEach((tool, idx) => {
    console.log(`\n${idx + 1}. ${tool.name}`);
    if (tool.description) {
      console.log(`   ${tool.description}`);
    }
  });

  const toolName = await client['promptUser'](
    '\n[USER INPUT REQUIRED] Enter the tool name you want to call',
    `e.g., ${tools[0]?.name || 'tool_name'}`
  );

  const selectedTool = tools.find(t => t.name === toolName);
  if (!selectedTool) {
    console.log(`[ERROR] Tool '${toolName}' not found`);
    return null;
  }

  // Parse input schema to get required parameters
  const args: Record<string, any> = {};
  if (selectedTool.inputSchema?.properties) {
    const properties = selectedTool.inputSchema.properties;
    const required = selectedTool.inputSchema.required || [];

    for (const [paramName, paramSchema] of Object.entries(properties)) {
      const schema = paramSchema as any;
      const isRequired = required.includes(paramName);
      const prompt = `Enter value for '${paramName}'${isRequired ? ' (required)' : ' (optional)'}`;
      const hint = schema.description || `Type: ${schema.type || 'any'}`;
      
      const value = await client['promptUser'](prompt, hint);
      
      if (value || isRequired) {
        // Try to parse based on type
        if (schema.type === 'number' || schema.type === 'integer') {
          args[paramName] = Number(value);
        } else if (schema.type === 'boolean') {
          args[paramName] = value.toLowerCase() === 'true';
        } else if (schema.type === 'object' || schema.type === 'array') {
          try {
            args[paramName] = JSON.parse(value);
          } catch {
            args[paramName] = value;
          }
        } else {
          args[paramName] = value;
        }
      }
    }
  }

  return { toolName, args };
}

/**
 * Run the generic widget demo
 */
async function runWidgetDemo() {
  console.log('===============================================================');
  console.log('  MCP Generic Widget Client');
  console.log('===============================================================');
  console.log('\nThis client works with any MCP server that supports widgets.');
  console.log('It will list available tools and let you execute them interactively.\n');

  const serverUrl = process.env.MCP_SERVER_URL || 'http://localhost:3004/mcp';
  const verbose = process.env.VERBOSE === 'true';

  // Create readline interface for user inputs
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const promptInput = (question: string): Promise<string> => {
    return new Promise((resolve) => {
      rl.question(question, (answer: string) => {
        resolve(answer.trim());
      });
    });
  };

  // Helper function to parse comma-separated key=value pairs
  const parseContext = (input: string): Record<string, any> => {
    const context: Record<string, any> = {};
    if (!input.trim()) return context;
    
    const pairs = input.split(',').map(p => p.trim());
    for (const pair of pairs) {
      const [key, ...valueParts] = pair.split('=');
      if (key && valueParts.length > 0) {
        const value = valueParts.join('=').trim();
        // Try to parse as JSON, otherwise use as string
        try {
          context[key.trim()] = JSON.parse(value);
        } catch {
          context[key.trim()] = value;
        }
      }
    }
    return context;
  };

  // Get context inputs
  console.log('\n[SETUP] Context Configuration');
  console.log('---------------------------------------------------------------');
  console.log('Enter context as comma-separated key=value pairs');
  console.log('Example:locale=en-US');
  console.log('Note: thread_id is automatically added to system context');
  console.log('---------------------------------------------------------------\n');

  const systemContextInput = await promptInput(
    'Enter System Context (com.ibm.orchestrate/systemcontext) or press Enter to skip:\n> '
  );
  SYSTEM_CONTEXT = parseContext(systemContextInput);

  const otherContextInput = await promptInput(
    'Enter Other Context (com.ibm.orchestrate/context) or press Enter to skip:\n> '
  );
  OTHER_CONTEXT = parseContext(otherContextInput);
  
  rl.close();

  console.log('\n[SETUP] Configuration Summary:');
  console.log('---------------------------------------------------------------');
  console.log('System Context:', JSON.stringify(SYSTEM_CONTEXT, null, 2));
  console.log('Other Context:', JSON.stringify(OTHER_CONTEXT, null, 2));
  console.log('---------------------------------------------------------------\n');

  const client = new WidgetDemoClient(serverUrl, verbose);

  try {
    // Connect and list initial tools
    await client.connect();
    
    const toolsResponse = await client['client'].listTools({
      _meta: {
        'com.ibm.orchestrate/systemcontext': {
          thread_id: client['threadId'],
          ...SYSTEM_CONTEXT,
        },
        'com.ibm.orchestrate/context': OTHER_CONTEXT,
      },
    });
    let availableTools = toolsResponse.tools;

    // Main interaction loop
    while (true) {
      console.log('\n===============================================================');
      console.log('  Main Menu');
      console.log('===============================================================');
      console.log('\n1. List available tools');
      console.log('2. List available resources');
      console.log('3. Read a resource');
      console.log('4. Call a tool');
      console.log('5. Exit');

      const choice = await client['promptUser'](
        '\n[USER INPUT REQUIRED] Select an option',
        'Enter 1, 2, 3, 4, or 5'
      );

      if (choice === '5') {
        console.log('\n[EXIT] Exiting...');
        break;
      }

      switch (choice) {
        case '1':
          // List tools
          await client.listTools();
          availableTools = (await client['client'].listTools({
            _meta: {
              'com.ibm.orchestrate/systemcontext': {
                thread_id: client['threadId'],
                ...SYSTEM_CONTEXT,
              },
              'com.ibm.orchestrate/context': OTHER_CONTEXT,
            },
          })).tools;
          break;

        case '2':
          // List resources
          await client.listResources();
          break;

        case '3':
          // Read resource
          const uri = await client['promptUser'](
            '\n[USER INPUT REQUIRED] Enter resource URI',
            'e.g., banking://accounts/available'
          );
          try {
            await client.readResource(uri);
          } catch (error: any) {
            console.log(`[ERROR] Failed to read resource: ${error.message}`);
          }
          break;

        case '4':
          // Call a tool
          const toolCall = await selectTool(client, availableTools);
          if (!toolCall) {
            console.log('[ERROR] No tool selected or invalid tool');
            break;
          }

          // Execute the tool and handle any widget responses
          let currentCall: { toolName: string; args: Record<string, any> } | null = toolCall;
          let stepCount = 0;

          while (currentCall) {
            stepCount++;
            console.log(`\n[STEP ${stepCount}] Calling tool: ${currentCall.toolName}`);
            console.log('---------------------------------------------------------------');

            const response = await client.callTool(currentCall.toolName, currentCall.args);

            // Check if response indicates tools should be refreshed
            if (response._meta?.refreshThreadCapabilities) {
              console.log(`\n[REFRESH] Refreshing tools for thread: ${response._meta.refreshThreadCapabilities}`);
              availableTools = (await client['client'].listTools({
                _meta: {
                  'com.ibm.orchestrate/systemcontext': {
                    thread_id: client['threadId'],
                    ...SYSTEM_CONTEXT,
                  },
                  'com.ibm.orchestrate/context': OTHER_CONTEXT,
                },
              })).tools;
              console.log(`[REFRESH] Tools list updated (${availableTools.length} tools available)`);
            }

            // Check if response contains a widget with next steps
            const widget = response._meta?.['com.ibm.orchestrate/widget'];
            
            if (widget && (widget.onChange || widget.onConfirm || widget.onCancel)) {
              // Widget has next steps - process it
              currentCall = await processWidget(client, response);
            } else {
              // No widget or no next steps - display result and stop
              client.displayResult(response);
              console.log('\n[COMPLETE] Tool execution finished (no more steps)');
              currentCall = null;
            }
          }

          // Refresh tools list after execution (in case authentication changed available tools)
          availableTools = (await client['client'].listTools({
            _meta: {
              'com.ibm.orchestrate/systemcontext': {
                thread_id: client['threadId'],
                ...SYSTEM_CONTEXT,
              },
              'com.ibm.orchestrate/context': OTHER_CONTEXT,
            },
          })).tools;
          break;

        default:
          console.log('[ERROR] Invalid choice. Please select 1, 2, 3, 4, or 5.');
      }
    }

    console.log('\n===============================================================');
    console.log('  Session Complete!');
    console.log('===============================================================');

  } catch (error) {
    logger.error('\n[ERROR] Error during session:', error);
    throw error;
  } finally {
    await client.close();
  }
}

// Main execution
if (require.main === module) {
  (async () => {
    try {
      await runWidgetDemo();
      
      console.log('\n\n[SUCCESS] Demo completed successfully!\n');
      process.exit(0);
    } catch (error) {
      logger.error('\n[FAILED] Demo failed:', error);
      process.exit(1);
    }
  })();
}

export { WidgetDemoClient, runWidgetDemo };