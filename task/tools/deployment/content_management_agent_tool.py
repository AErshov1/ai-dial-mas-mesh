from typing import Any

from task.tools.deployment.base_agent_tool import BaseAgentTool


class ContentManagementAgentTool(BaseAgentTool):

    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean

    @property
    def name(self) -> str:
        return "content_management_agent_tool"

    @property
    def description(self) -> str:
        return "Content Management Agent that manages content and capable to extract and search content from various file types. Equipped with capabilities to files content extractor and RAG search (supports PDF, TXT, CSV files)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The query or instruction to send to the Content Management Agent."
                },
                "propagate_history": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Whether to include previous conversation history between the current agent and Content Management Agent. This provides context for the Content Management Agent, allowing it to reference past interactions."
                        "When `true`, the Content Management Agent will have access to prior exchanges for context continuity. "
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
        return "content-management-agent"
