# Agent Handoff Pattern

## Overview

This pattern demonstrates how to implement a user-controlled agent handoff flow that gives customers the choice between real-time connection to a human agent or scheduling a callback. The pattern uses a two-step flow with a single-choice widget to gather user preference, then conditionally issues the `connect_to_agent` response type for real-time handoffs.

## Problems This Pattern Solves

### **Providing Flexible Agent Connection Options**

When a customer requests to speak with a human agent, the system should:

- Give the user control over how they connect (immediate vs. scheduled)
- Respect the user's time and availability preferences
- Handle agent availability gracefully
- Provide clear messaging about what will happen next

The Agent Handoff Pattern addresses these issues by presenting clear options and handling each path appropriately.

### **Context Preservation for Human Agents**

When transferring to a human agent, context is critical:

The pattern allows you to:

- Pass contextual messages to human agents
- Include the reason for handoff
- Maintain conversation continuity
- Provide agents with the information they need to help effectively

## Implementation Walkthrough

Below we walk through the agent handoff implementation that demonstrates this pattern.

### Two-Step Handoff Flow

The Agent Handoff Pattern uses a two-step flow with two corresponding tools. One tool is visible to the model, and one is hidden to prevent the model from bypassing user choice:

1. **Request Step**: Presents options for real-time or callback connection
2. **Process Step**: Handles the user's choice and initiates the appropriate handoff

**File:** [`src/handoff.ts`](../src/handoff.ts)

### Step 1: Request Agent Handoff

The request tool presents a single-choice widget with connection options:

```typescript
// Step 1: Present handoff options to user
export const requestAgentHandoffTool = {
  name: 'request_agent_handoff',
  config: {
    title: 'Request Agent Handoff',
    description: 'Initiate handoff to human agent',
    inputSchema: {
      reason: z.string().optional()
    }
  },
  handler: async ({ reason }: { reason?: string }, extra: any) => {
    const contextMessage = reason
      ? `User requested assistance. Reason: ${reason}`
      : 'User requested to speak with an agent';
    
    return {
      content: [{
        type: 'text',
        text: "How would you like to connect with an agent?",
        annotations: { audience: ['user'] }
      }],
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'options_selector',
          title: 'Choose Connection Type',
          options: [
            { value: 'realtime', label: 'Connect Now' },
            { value: 'callback', label: 'Request Callback' }
          ],
          on_event: {
            tool: 'process_agent_handoff_choice',
            parameters: { contextMessage },
            map_input_to: 'handoffType'
          }
        }
      }
    };
  }
};
```

**Key aspects:**

1. **Optional Context**: The `reason` parameter allows the model to pass context about why handoff is needed
2. **Context Passing**: The `contextMessage` is passed to the next tool via widget parameters
3. **User Choice**: Widget presents clear options for real-time or callback connection
4. **Two-Step Flow**: This tool is visible to the model; the next tool is hidden

### Step 2: Process User Choice

The second tool handles the user's selection and initiates the appropriate handoff type:

```typescript
// Step 2: Process user's choice (hidden from model)
export const processAgentHandoffChoiceTool = {
  name: 'process_agent_handoff_choice',
  config: {
    title: 'Process Agent Handoff Choice',
    inputSchema: {
      handoffType: z.enum(['realtime', 'callback']),
      contextMessage: z.string()
    },
    _meta: {
      ui: { visibility: ['app'] }  // 🔒 Hidden from model
    }
  },
  handler: async (
    {
      handoffType,
      contextMessage,
    }: {
      handoffType: 'realtime' | 'callback';
      contextMessage: string;
    },
    extra: any,
  ) => {
    if (handoffType === 'realtime') {
      return {
        content: [{ type: 'text', text: 'Connecting...', annotations: { audience: ['user'] } }],
        _meta: {
          'com.ibm.orchestrate/extensions': {
            connect_to_agent: {
              message_to_human_agent: contextMessage,
              agent_available: 'Please wait while I connect you to an agent.',
              agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later."
            }
          }
        }
      };
    }
    
    // Handle callback request
    return {
      content: [{
        type: 'text',
        text: 'Callback request submitted',
        annotations: { audience: ['user'] }
      }]
    };
  }
};
```

**Key aspects:**

1. **Hidden from Model**: `visibility: ['app']` prevents the model from calling this tool directly
2. **User Control**: Only the UI widget can invoke this tool based on explicit user selection
3. **Context Preservation**: The `contextMessage` is passed to the human agent
4. **connect_to_agent Response**: For real-time handoff, uses the `connect_to_agent` response type

#### Full Working Example

For the complete implementation with detailed widget configurations, agent availability handling, and error messages, see [`src/handoff.ts`](../src/handoff.ts).

### How the Handoff Flow Works

**Critical security feature**: The `visibility: ['app']` setting ensures the process tool is **hidden from the model**. This means:

- The model cannot see this tool in its available tools list
- The model cannot call this tool directly
- Only the UI widget can invoke this tool based on explicit user selection
- This ensures the user's choice is respected and cannot be overridden by the model

### The connect_to_agent Extension

When the user selects real-time connection, the tool returns the `connect_to_agent` extension:

```typescript
_meta: {
  'com.ibm.orchestrate/extensions': {
    connect_to_agent: {
      message_to_human_agent: "User requested agent assistance. Reason: Complex account issue",
      agent_available: "Please wait while I connect you to an agent.",
      agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later or request a callback."
    }
  }
}
```

**Key fields:**

- **`message_to_human_agent`**: Context passed to the human agent about why the customer is being transferred
- **`agent_available`**: Message shown to the user while connecting to an available agent
- **`agent_unavailable`**: Fallback message shown when no agents are online

### How the Handoff Flow Works

The complete handoff flow:

1. **User Request**: Customer says "I need to speak with someone" or "Connect me to an agent"
2. **Model Calls Request Tool**: The model invokes `request_agent_handoff`, optionally with a reason
3. **Widget Rendered**: The single-choice widget displays with "Connect Now" and "Request Callback" options
4. **User Selects Option**: The user explicitly chooses their preferred connection method
5. **Widget Calls Process Tool**: The widget directly invokes `process_agent_handoff_choice` with the selection
6. **Handoff Initiated**:
   - For real-time: The `connect_to_agent` extension is issued
   - For callback: A confirmation message is returned
7. **Connection Handled**: The platform handles the actual agent connection or callback scheduling

**Important**: The model never has the ability to force a specific handoff type. It can only present the options and let the user decide.

## Key Takeaways

The Agent Handoff Pattern provides essential capabilities for customer care applications that need human escalation:

- **User Choice**: Customers control how they connect with agents (immediate vs. scheduled)
- **Graceful Degradation**: Clear messaging when agents are unavailable with automatic fallback options
- **Context Preservation**: Important context is passed to human agents to ensure continuity
- **Model Cannot Force Handoff Type**: The `visibility: ['app']` setting prevents the model from bypassing user choice
- **Flexible Integration**: Works with existing agent routing and availability systems

**When to use this pattern:**

- Customer requests to speak with a human agent
- Complex issues that require human expertise
- Escalation scenarios where automated assistance is insufficient
- Situations requiring empathy or nuanced judgment
- Regulatory or compliance scenarios requiring human oversight

**Channel Adaptation:**

- **Web/Mobile**: Displays choice widget and handles connection UI
- **Voice**: Presents verbal options and transfers call appropriately
- **Chat**: Shows selection buttons and initiates an agent chat

The Agent Handoff Pattern is essential for customer care applications that need to seamlessly transition between automated and human assistance while respecting user preferences and handling availability constraints gracefully.
