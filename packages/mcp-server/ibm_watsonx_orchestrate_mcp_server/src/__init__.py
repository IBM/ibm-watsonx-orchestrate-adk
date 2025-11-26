from .version_checker import check_version
from .agents.mcp_tools import __tools__ as agent_tools
from .tools.mcp_tools import __tools__ as tool_tools
from .toolkits.mcp_tools import __tools__ as toolkit_tools
from .knowledge_bases.mcp_tools import __tools__ as knowledge_base_tools
from .connections.mcp_tools import __tools__ as connection_tools
from .voice_configurations.mcp_tools import __tools__ as voice_configuration_tools
from .models.mcp_tools import __tools__ as model_tools
from .channels.mcp_tools import __tools__ as channel_tools
from .phone.mcp_tools import __tools__ as phone_tools

__all_tools__ = agent_tools + tool_tools + toolkit_tools + knowledge_base_tools + connection_tools + voice_configuration_tools + model_tools + channel_tools + phone_tools + [check_version]
