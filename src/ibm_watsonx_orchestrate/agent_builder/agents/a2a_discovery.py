import requests
import logging
from typing import Optional
from urllib.parse import urljoin
from .a2a_types import AgentCard

logger = logging.getLogger(__name__)


class A2ADiscoveryService:
    """Client for discovering A2A agents from well-known URIs."""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the A2A discovery client.
        
        Args:
            timeout: Request timeout in seconds (default: 30)
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WatsonX-Orchestrate-A2A-Discovery/1.0',
            'Accept': 'application/json'
        })
    
    def discover_from_wellknown(
        self,
        base_url: str,
        endpoint: str = ".well-known/agent-card.json"
    ) -> AgentCard:
        """
        Discover an A2A agent from a well-known URI.
        
        Args:
            base_url: Base URL of the agent (e.g., "https://example.com")
            endpoint: Well-known endpoint path (default: ".well-known/agent-card.json")
            
        Returns:
            AgentCard object parsed from the response
            
        Raises:
            requests.RequestException: If the request fails
            ValueError: If the response cannot be parsed as an AgentCard
        """
        # Ensure base_url ends with /
        if not base_url.endswith('/'):
            base_url += '/'
        
        # Construct full URL
        full_url = urljoin(base_url, endpoint)
                
        try:
            # Fetch the agent card
            response = self.session.get(
                full_url,
                timeout=self.timeout
            )
            response.raise_for_status()
            card_data = response.json()
            # Validate and create AgentCard
            agent_card = AgentCard(**card_data)
            
            return agent_card
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch agent card from {full_url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse agent card from {full_url}: {str(e)}")
            raise ValueError(f"Invalid agent card format: {str(e)}")
    
    def discover_and_convert(
        self,
        base_url: str,
        endpoint: str = ".well-known/agent-card.json",
        agent_name: Optional[str] = None,
        app_id: Optional[str] = None
    ) -> dict:
        """
        Discover an A2A agent and convert it to WxO external agent format.
        
        Args:
            base_url: Base URL of the agent
            endpoint: Well-known endpoint path
            agent_name: Override agent name (optional)
            app_id: Connection app_id for authentication (optional)
            
        Returns:
            Dictionary in WxO external agent YAML format
        """
        # Discover the agent card (no auth needed for discovery)
        agent_card = self.discover_from_wellknown(base_url, endpoint)
        
        # Convert to WxO format
        wxo_spec = agent_card.convert_to_wxo_external_agent_dict(
            agent_name=agent_name,
            app_id=app_id
        )
        
        return wxo_spec
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

