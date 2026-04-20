from __future__ import annotations

import json
import os
from typing import Annotated, Any, TypedDict, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import RunnableConfig
from langchain_ibm import ChatWatsonx

from ibm_watsonx_orchestrate_sdk import Client


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def list_hotels(city: str) -> str:
    """
    List hotels for a given city.
    
    Args:
        city: The city name to search hotels for
        
    Returns:
        JSON string containing list of 50 hotels
    """
    hotels = []
    hotel_chains = ["Marriott", "Hilton", "Hyatt", "InterContinental", "Radisson", 
                    "Sheraton", "Westin", "Holiday Inn", "Crowne Plaza", "Best Western"]
    hotel_types = ["Hotel", "Resort", "Suites", "Inn", "Grand Hotel"]
    
    for i in range(1, 51):
        chain = hotel_chains[i % len(hotel_chains)]
        hotel_type = hotel_types[i % len(hotel_types)]
        
        hotel = {
            "id": f"hotel_{i}",
            "name": f"{chain} {hotel_type} {city}",
            "city": city,
            "rating": round(3.5 + (i % 15) / 10, 1),
            "price_per_night": 100 + (i * 10) % 300,
            "amenities": ["WiFi", "Pool", "Gym", "Restaurant"][:((i % 4) + 1)],
            "available_rooms": (i * 3) % 50 + 1
        }
        hotels.append(hotel)
    
    return json.dumps({"city": city, "hotels": hotels, "total_count": len(hotels)}, indent=2)


def create_agent(config: RunnableConfig):
    """
    Hotel List Agent with Context Compression.
    
    This agent demonstrates:
    1. ReAct loop with tool calling (list_hotels)
    2. ChatWatsonx for LLM interactions
    3. Token counting with count_tokens_approximately
    4. Context compression when tokens exceed 2500
    5. Replacing old messages with summarized content
    """
    configurable = config.get("configurable", {})
    execution_context = configurable.get("execution_context", {}) or {}

    # runs on Client initialization
    client = Client(execution_context=execution_context)

    # runs elsewhere Client initialization
    # client = Client(
    #     api_key='',
    #     instance_url='',
    #     iam_url="https://iam.platform.test.saas.ibm.com"  # Required for staging environments
    # )
    
    # Initialize ChatWatsonx for LLM calls
    # Get model configuration from execution context or use defaults
    credentials = config.get("configurable", {}).get("credentials", {})
    
    llm = ChatWatsonx(
        #model_id="mistralai/mistral-medium-2505",                         
        model_id="openai/gpt-oss-120b", # LLM
        url="https://us-south.ml.cloud.ibm.com", # your region endpoint
        space_id=credentials.get("wxai_space_id", os.getenv("WXAI_SPACE_ID")), # Space ID
        apikey=credentials.get("wxai_apikey", os.getenv("WXAI_API_KEY")), # IAM API Key
        streaming=True
    )
    
    # Context compression configuration
    TOKEN_THRESHOLD = 6000  # Compress when tokens exceed this
    MESSAGES_TO_KEEP_RECENT = 4  # Keep the most recent N messages uncompressed
    
    # Define available tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_hotels",
                "description": "List hotels for a given city. Returns a list of 50 hotels with details like name, rating, price, and amenities.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city name to search hotels for"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    ]
    
    def _convert_to_dict_messages(messages: list[BaseMessage]) -> list[dict]:
        """
        Convert LangChain messages to dictionary format for SDK.
        
        Handles:
        - Regular messages (user, assistant, system)
        - Tool calls (AI messages with tool_calls)
        - Tool responses (ToolMessage)
        - Empty content (passes None instead of empty string)
        """
        dict_messages = []
        for msg in messages:
            msg_type = getattr(msg, "type", "")
            content = getattr(msg, "content", "")
            
            # Handle empty content - pass None instead of empty string
            if content == "":
                content = None
            
            if msg_type == "human":
                dict_messages.append({"role": "user", "content": content})
            
            elif msg_type == "ai":
                # Check if this is a tool call message
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls and len(tool_calls) > 0:
                    # AI message with tool calls - content may be None
                    msg_dict = {"role": "assistant", "content": content}
                    # Add tool_calls if present
                    msg_dict["tool_calls"] = tool_calls
                    dict_messages.append(msg_dict)
                else:
                    # Regular AI message
                    dict_messages.append({"role": "assistant", "content": content})
            
            elif msg_type == "tool":
                # Tool response message
                tool_call_id = getattr(msg, "tool_call_id", None)
                msg_dict = {"role": "tool", "content": content}
                if tool_call_id:
                    msg_dict["tool_call_id"] = tool_call_id
                dict_messages.append(msg_dict)
            
            elif msg_type == "system":
                dict_messages.append({"role": "system", "content": content})
        
        return dict_messages
    
    def _should_compress(messages: list[BaseMessage]) -> bool:
        """Determine if we should compress based on token count."""
        token_count = count_tokens_approximately(messages)
        if token_count > TOKEN_THRESHOLD:
            print(f"🗜️  Context compression required: {token_count} tokens exceeds threshold of {TOKEN_THRESHOLD}")
            return True
        else:
            print('Compression not required')
            print(f"🗜️  Token count: {token_count}")
        return False
    
    def _compress_history(messages: list[BaseMessage]) -> list[BaseMessage]:
        """
        Compress older messages while keeping recent ones.
        
        This function REPLACES the older messages with a compressed summary.
        
        Process:
        1. Split messages into "old" (to compress) and "recent" (to keep)
        2. Call client.context.summarize() to compress old messages
        3. Replace old messages with a single HumanMessage containing the summary
        4. Return [compressed_summary] + recent_messages
        
        Returns a new message list with:
        - A HumanMessage containing the compressed summary of old messages
        - The most recent N messages (uncompressed)
        
        Example:
        - Input: [msg1, msg2, msg3, msg4, msg5, msg6] (6 messages)
        - With MESSAGES_TO_KEEP_RECENT=2
        - Output: [compressed_summary_of_msg1-4, msg5, msg6] (3 messages)
        """
        if len(messages) <= MESSAGES_TO_KEEP_RECENT:
            return messages
        
        # Split messages into old (to compress) and recent (to keep)
        messages_to_compress = messages[:-MESSAGES_TO_KEEP_RECENT]
        recent_messages = messages[-MESSAGES_TO_KEEP_RECENT:]
        
        # Convert to dict format for SDK
        dict_messages = _convert_to_dict_messages(messages_to_compress)
        
        try:
            # Use SDK's context compression (similar to runs_elsewhere_example.py)
            compressed_response = client.context.summarize(messages=dict_messages)
            
            # Create a HumanMessage with the compressed context
            # This REPLACES all the old messages with a single summary message
            compressed_summary = HumanMessage(
                content=f"[Compressed conversation history - {len(messages_to_compress)} messages]: {compressed_response.summary}"
            )
            
            # Return compressed summary + recent messages
            return [compressed_summary] + recent_messages
            
        except Exception as e:
            # If compression fails, fall back to keeping all messages
            return messages
    
    def _parse_tool_call(ai_message: AIMessage) -> tuple[str, dict] | None:
        """Parse tool call from AI message."""
        # Check if message has tool_calls attribute
        tool_calls = getattr(ai_message, "tool_calls", None)
        if tool_calls and len(tool_calls) > 0:
            tool_call = tool_calls[0]
            return tool_call.get("name"), tool_call.get("args", {})
        
        # Fallback: parse from content if it looks like a tool call
        content = getattr(ai_message, "content", "")
        if "list_hotels" in content.lower():
            # Simple parsing - in production, use proper JSON parsing
            import re
            city_match = re.search(r'city["\s:]+(["\']?)([^"\'}\n]+)\1', content, re.IGNORECASE)
            if city_match:
                city = city_match.group(2).strip()
                return "list_hotels", {"city": city}
        
        return None
    
    def agent_node(state: AgentState):
        """Main agent node that handles the ReAct loop."""
        messages = state.get("messages", [])
        
        # Check if we should compress the conversation history
        if _should_compress(messages):
            compressed_messages = _compress_history(messages)
            # Log the compression result
            new_token_count = count_tokens_approximately(compressed_messages)
            print(f"   → Compressed to {new_token_count} tokens ({len(compressed_messages)} messages)")
            messages = compressed_messages

        
        # Get the latest user message
        latest_message = messages[-1] if messages else None
        
        if not latest_message or getattr(latest_message, "type", "") != "human":
            return {"messages": [AIMessage(content="I'm ready to help you find hotels. Which city are you interested in?")]}
        
        user_query = getattr(latest_message, "content", "")
        
        # Create system prompt for the agent
        system_prompt = """You are a helpful hotel booking assistant. You can:
1. Chat with users about their travel plans
2. List hotels for any city using the list_hotels tool

When a user asks about hotels in a city, use the list_hotels tool to get the information.
For general conversation, respond naturally and helpfully."""
        
        # Prepare messages for LLM
        llm_messages = [SystemMessage(content=system_prompt)] + messages
        
        try:
            # Bind tools to LLM and invoke
            llm_with_tools = llm.bind_tools(tools)
            response = llm_with_tools.invoke(llm_messages)
            
            # Check if LLM wants to call a tool
            tool_call_info = _parse_tool_call(response)
            
            if tool_call_info:
                tool_name, tool_args = tool_call_info
                
                if tool_name == "list_hotels":
                    city = tool_args.get("city", "")
                    
                    # Execute the tool
                    tool_result = list_hotels(city)
                    
                    # Parse the result to create a user-friendly response
                    try:
                        hotel_data = json.loads(tool_result)
                        hotel_count = hotel_data.get("total_count", 0)
                        hotels = hotel_data.get("hotels", [])
                        
                        # Create a summary of top hotels
                        top_hotels = hotels[:5]
                        summary = f"I found {hotel_count} hotels in {city}. Here are the top 5:\n\n"
                        
                        for i, hotel in enumerate(top_hotels, 1):
                            summary += f"{i}. {hotel['name']}\n"
                            summary += f"   Rating: {hotel['rating']}/5.0\n"
                            summary += f"   Price: ${hotel['price_per_night']}/night\n"
                            summary += f"   Amenities: {', '.join(hotel['amenities'])}\n\n"
                        
                        summary += f"Would you like more details about any of these hotels?"
                        
                        # Return both the tool call and the response
                        return {
                            "messages": [
                                response,  # AI message with tool call
                                ToolMessage(content=tool_result, tool_call_id="list_hotels_1"),
                                AIMessage(content=summary)
                            ]
                        }
                    except json.JSONDecodeError:
                        return {"messages": [AIMessage(content=f"I found hotels in {city}, but had trouble parsing the results. Please try again.")]}
            
            # No tool call - just return the LLM response
            return {"messages": [response]}
            
        except Exception as e:
            print(f"❌ Error in agent_node: {e}")
            import traceback
            traceback.print_exc()
            return {"messages": [AIMessage(content=f"I encountered an error: {str(e)}. Please try again.")]}
    
    # Build the graph
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    
    return builder.compile()


def main():
    """
    Main function for local testing.
    
    This allows you to test the agent locally without deploying to watsonx Orchestrate.
    Set environment variables for credentials before running.
    """
    import os
    
    print("\n" + "="*80)
    print("HOTEL LIST AGENT - LOCAL TEST")
    print("="*80 + "\n")
    
    # Create mock execution context
    config = RunnableConfig(
        configurable={
            "execution_context": {
                "model_config": {
                    "model_id": "ibm/granite-13b-chat-v2",
                    "url": "https://us-south.ml.cloud.ibm.com",
                    "project_id":  ""
                }
            }
        }
    )
    
    # Create the agent
    print("Creating agent...")
    agent = create_agent(config)
    print("✓ Agent created successfully\n")
    
    # Test conversation
    test_messages = [
        "Hi! I'm planning a trip to Paris. Can you help me find hotels?",
        "What about hotels in London?",
        "I'm also interested in hotels in New York.",
        "Tell me about hotels in Tokyo.",
        "What hotels are available in Sydney?",
    ]
    
    state = {"messages": []}
    
    for i, user_input in enumerate(test_messages, 1):
        print(f"User: {user_input}")
        
        # Add user message
        state["messages"].append(HumanMessage(content=user_input))
        
        
        try:
            # Invoke agent
            result = agent.invoke(state, config)
            
            # Update state
            if result and "messages" in result:
                state["messages"] = result["messages"]
                
                # Get agent's response
                last_msg = state["messages"][-1]
                response = getattr(last_msg, "content", "")
                
                # Print response (truncated for readability)
                print(f"\nAgent: {response[:300]}...")
                if len(response) > 300:
                    print(f"       (response truncated, full length: {len(response)} chars)")                            
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            break


if __name__ == "__main__":
    main()



