from typing import Any

from task.tools.deployment.base_agent_tool import BaseAgentTool


class WebSearchAgentTool(BaseAgentTool):

    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean

    @property
    def name(self) -> str:
        return "web_search_agent_tool"

    @property
    def description(self) -> str:
        return "Web Search Agent that performs online searches to retrieve up-to-date information from the web. Equipped with web search capabilities to find relevant information based on user queries."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The query or instruction to send to the Web Search Agent."
                },
                "propagate_history": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Whether to include previous conversation history between the current agent and Web Search Agent. This provides context for the Web Search Agent, allowing it to reference past interactions."
                        "When `true`, the Web Search Agent will have access to prior exchanges for context continuity. "
                        "When `false`, each call starts fresh without historical context. "
                        )
                },
            },
            "required": [
                "prompt"
            ]
        }

    @property
    def deployment_name(self) -> str:
        return "web-search-agent"
