import redis
import time
import json
from dotenv import load_dotenv
import os

from typing import (
    AsyncIterator, Union
)

from ..types import (
    FlowEventType, TaskEventType, FlowEvent, FlowContext
)

class StreamConsumer:
    def __init__(self, instance_id: str):
        
        load_dotenv()
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = os.getenv("REDIS_PORT", 6379)
        self.redis_db = os.getenv("REDIS_DB", 0)
        self.redis = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db)
        self.instance_id = instance_id
        self.stream_name = f"tempus:{self.instance_id}"
        self.last_processed_id = 0
        

    async def consume(self) -> AsyncIterator[FlowEvent]:
        
        while True:
            try:
                # XREAD command: Read new messages from the stream
                messages = self.redis.xread({self.stream_name: self.last_processed_id}, block=5000, count=10)

                for stream, events in messages:
                    for event_id, event_data in events:
                        self.last_processed_id = event_id  # Update the last read event ID
                        flow_event = deserialize_flow_event(event_data)
                        yield flow_event

            except Exception as e:
                print(f"Error occurred: {e}")
                time.sleep(5)  # Wait for 5 seconds before retrying

            time.sleep(1)  # Sleep for 1 second before checking for new messages

def deserialize_flow_event(byte_data: bytes) -> FlowEvent:
    """Deserialize byte data into a FlowEvent object."""
    # Decode the byte data
    decoded_data = byte_data[b'data'].decode('utf-8') if b'data' in byte_data else None
    if not decoded_data:
        decoded_data = byte_data[b'message'].decode('utf-8') if b'message' in byte_data else None
    
    if not decoded_data:
        raise ValueError("No data in received event.")

    # Parse the JSON string into a dictionary
    parsed_data = json.loads(decoded_data)
    
    # Deserialize into FlowEvent using Pydantic's parsing
    flow_event = FlowEvent(
        kind=get_event_type(parsed_data["kind"]),
        context=FlowContext(**parsed_data["context"]) if "context" in parsed_data and parsed_data["context"] != {} else None,
        error=json.loads(parsed_data["error"]) if "error" in parsed_data and parsed_data["error"] != {} and len(parsed_data["error"]) > 0 else None,
    )
    
    return flow_event

def get_event_type(selected_event_type: str) -> Union[FlowEventType, TaskEventType]:
    """Selects the right event type from the corresponding enumerator"""
    eventKind = selected_event_type.upper()
    if eventKind in FlowEventType.__members__:
        return FlowEventType(selected_event_type)
    elif eventKind in TaskEventType.__members__:
        return TaskEventType(selected_event_type)
    else:
        raise ValueError(f"Invalid event type: {eventKind}")
