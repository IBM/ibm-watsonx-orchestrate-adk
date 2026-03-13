/**
 * Welcome Tool Module
 *
 * Contains the welcome tool that is automatically invoked when a thread begins
 * to greet the customer and authenticate them with a PIN
 */

import { z } from 'zod';
import {
  getCustomerProfileByPhone,
  verifyCustomerPin,
} from './customerDatabase';
import { setGlobalVariable } from './globalStore';

/**
 * Welcome customer tool definition
 *
 * This is a welcome tool that is automatically invoked when a thread begins.
 * It retrieves the customer's telephone number from context, looks up their
 * profile, greets them by name, and requests PIN authentication.
 */
export const welcomeCustomerTool = {
  name: 'welcome_customer',
  config: {
    title: 'Welcome Customer',
    description: 'Welcome the customer and authenticate them with their PIN',
    inputSchema: {},
    _meta: {
      welcomeTool: true, // Designate as welcome tool for automatic invocation
      ui: {
        visibility: ['app'], // 🔒 Hidden from model - only callable by system
      },
    },
  },
  handler: async (args: any, extra: any) => {
    console.error('[WELCOME] Received args:', JSON.stringify(args, null, 2));
    console.error('[WELCOME] Received extra:', JSON.stringify(extra, null, 2));

    const _meta = extra?._meta;

    // Extract telephone number from customer context
    const telephoneNumber =
      _meta?.['com.ibm.orchestrate/context']?.telephoneNumber;

    console.error('[WELCOME] Extracted telephoneNumber:', telephoneNumber);

    // Look up customer profile by telephone number
    const customerProfile = telephoneNumber
      ? getCustomerProfileByPhone(telephoneNumber)
      : null;

    // If we can't find telephone number or customer profile, transfer to agent
    if (!telephoneNumber || !customerProfile) {
      const res = {
        content: [
          {
            type: 'text',
            text: 'Welcome! I was unable to find your account. Let me connect you with an agent who can assist you.',
            annotations: {
              audience: ['user'],
            },
          },
        ],
        _meta: {
          'com.ibm.orchestrate/extensions': {
            connect_to_agent: {
              message_to_human_agent:
                'Customer account could not be found. Authentication failed.',
              agent_available: 'Please wait while I connect you to an agent.',
              agent_unavailable: "I'm sorry, but no agents are online at the moment. Please try again later.",
            },
          },
        },
      };
      return res;
    }

    // Greet the customer by name and request PIN
    // Note: customerId is NOT stored yet - only after successful PIN verification
    return {
      content: [
        {
          type: 'text',
          text: `Hello ${customerProfile.firstName} ${customerProfile.lastName}! Welcome to CustomerCare Banking.`,
          annotations: { audience: ['user'] },
        },
      ],
      _meta: {
        'com.ibm.orchestrate/widget': {
          type: 'number',
          collection_type: 'integer',
          title: 'For your security, please enter your 4-digit PIN. You can speak it or use the keypad, then press #.',
          min_number: 0,
          max_number: 9999,
          min_digits: 4,
          max_digits: 4,
          on_event: {
            tool: 'verify_customer_pin',
            parameters: {},
            map_input_to: 'pin',
          },
        },
      },
    };
  },
};

/**
 * Verify customer PIN tool definition
 *
 * Verifies the PIN entered by the customer during the welcome flow.
 * This tool should have visibility: ["app"] to prevent the model
 * from calling it directly.
 */
export const verifyCustomerPinTool = {
  name: 'verify_customer_pin',
  config: {
    title: 'Verify Customer PIN',
    description: 'Verify the PIN entered by the customer',
    inputSchema: {
      pin: z.string().describe('PIN entered by the customer'),
    },
    visibility: ['app'],
  },
  handler: async (
    {
      pin,
    }: {
      pin: string;
    },
    extra: any,
  ) => {
    // Extract telephone number from context
    const telephoneNumber =
      extra?._meta?.['com.ibm.orchestrate/context']?.telephoneNumber;
    const threadId = extra?._meta?.['com.ibm.orchestrate/systemcontext']?.thread_id;

    // Verify PIN using telephone number
    const isValid = telephoneNumber && verifyCustomerPin(telephoneNumber, pin);

    if (isValid && telephoneNumber) {
      // Look up customer profile to get customerId
      const customerProfile = getCustomerProfileByPhone(telephoneNumber);

      // Store customer ID in global store ONLY after successful PIN verification
      if (threadId && customerProfile) {
        setGlobalVariable(threadId, 'customerId', customerProfile.customerId);
      }


      return {
        content: [
          {
            type: 'text',
            text: 'Thank you! Your PIN has been verified. How can I assist you today?',
            annotations: { audience: ['user'] },
          },
        ],
        _meta: {
          // Signal all MCP servers to refresh their tool/resources lists for this thread
          // since the user is now authenticated and new tools/resources may be available
          refreshThreadCapabilities: threadId,
        },
      };
    } else {
      // Incorrect PIN - allow re-entry (user can ask to speak with agent if needed) - the model would call the request_agent_handoff tool
      return {
        content: [
          {
            type: 'text',
            text: "I'm sorry, but the PIN you entered is incorrect. Please try again, or you can ask to speak with an agent if you need assistance.",
            annotations: { audience: ['user'] },
          },
        ],
        _meta: {
          'com.ibm.orchestrate/widget': {
            type: 'number',
            collection_type: 'integer',
            title: 'Please enter your 4-digit PIN. You can speak it or use the keypad, then press #.',
            min_number: 0,
            max_number: 9999,
            min_digits: 4,
            max_digits: 4,
            on_event: {
              tool: 'verify_customer_pin',
              parameters: {},
              map_input_to: 'pin',
            },
          },
        },
      };
    }
  },
};

/**
 * Export all welcome tools
 */
export const welcomeTools = [welcomeCustomerTool, verifyCustomerPinTool];
