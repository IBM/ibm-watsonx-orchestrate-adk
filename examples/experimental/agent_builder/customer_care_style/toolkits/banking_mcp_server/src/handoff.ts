/**
 * Agent Handoff Tools Module
 *
 * Contains tool definitions for transferring customers to human agents
 */

import { z } from 'zod';

/**
 * Request agent handoff tool definition
 *
 * Presents the user with options to either request a callback or
 * connect to an agent in real-time. Uses a single-choice widget
 * to gather the user's preference.
 */
export const requestAgentHandoffTool = {
  name: 'request_agent_handoff',
  config: {
    title: 'Request Agent Handoff',
    description:
      'Initiate a handoff to a human agent. Presents options for callback or real-time connection.',
    inputSchema: {
      reason: z
        .string()
        .optional()
        .describe('Optional reason for the handoff request'),
    },
    // outputSchema: {},
  },
  handler: async (
    {
      customerId,
      reason,
    }: {
      customerId?: string;
      reason?: string;
    },
    extra: any,
  ) => {
    const customerContext = customerId
      ? ` Customer ID: ${customerId}.`
      : ' Customer not yet authenticated.';
    const contextMessage = reason
      ? `User requested agent assistance. Reason: ${reason}.${customerContext}`
      : `User requested to speak with an agent.${customerContext}`;

    return {
      content: [
        {
          type: 'text',
          text: "I'd be happy to connect you with one of our agents. How would you like to proceed?",
          annotations: { audience: ['user'] },
        },
      ],
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'options',
          title: 'Choose Connection Type',
          description: 'Select how you would like to connect with an agent:',
          options: [
            {
              value: 'realtime',
              label: 'Connect Now',
            },
            {
              value: 'callback',
              label: 'Request Callback',
            },
          ],
          on_event: {
            tool: 'process_agent_handoff_choice',
            parameters: {
              contextMessage,
            },
            map_input_to: 'handoffType',
          },
        },
      },
    };
  },
};

/**
 * Process agent handoff choice tool definition
 *
 * Handles the user's selection from the handoff options.
 * For real-time handoff, issues the connect_to_agent response type.
 * For callback, confirms the callback request.
 *
 * This tool should have visibility: ["app"] to prevent the model
 * from calling it directly.
 */
export const processAgentHandoffChoiceTool = {
  name: 'process_agent_handoff_choice',
  config: {
    title: 'Process Agent Handoff Choice',
    description:
      'Process the user selection for agent handoff type (real-time or callback)',
    inputSchema: {
      handoffType: z
        .enum(['realtime', 'callback'])
        .describe('Type of handoff selected by the user'),
      contextMessage: z
        .string()
        .describe('Context message to pass to the human agent'),
    },
    _meta: {
      ui: {
        visibility: ['app'],
      },
    },
  },
  handler: async (
    {
      customerId,
      handoffType,
      contextMessage,
    }: {
      customerId?: string;
      handoffType: 'realtime' | 'callback';
      contextMessage: string;
    },
    extra: any,
  ) => {
    if (handoffType === 'realtime') {
      // Issue the connect_to_agent response type for real-time handoff
      return {
        content: [
          {
            type: 'text',
            text: 'Connecting you to an agent...',
            annotations: { audience: ['user'] },
          },
        ],
        _meta: {
          'com.ibm.orchestrate/extensions': {
            connect_to_agent: {
              message_to_human_agent: contextMessage,
              agent_available: 'Please wait while I connect you to an agent.',
              agent_unavailable:
                "I'm sorry, but no agents are online at the moment. Please try again later or request a callback.",
            },
          },
        },
      };
    } else {
      // Handle callback request
      // In a real implementation, this would create a callback ticket/request
      return {
        content: [
          {
            type: 'text',
            text: "Thank you! I've submitted your callback request. One of our agents will contact you within the next business day. You'll receive a confirmation email shortly with the details.",
            annotations: { audience: ['user'] },
          },
        ],
      };
    }
  },
};

/**
 * Export all handoff tools
 */
export const handoffTools = [
  requestAgentHandoffTool,
  processAgentHandoffChoiceTool,
];
