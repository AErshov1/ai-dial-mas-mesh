from typing import Any

from task.tools.deployment.base_agent_tool import BaseAgentTool


class CalculationsAgentTool(BaseAgentTool):
    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean

    @property
    def name(self) -> str:
        return "calc_agent_tool"

    @property
    def description(self) -> str:
        return "Calculations Agent that performs mathematical calculations. Capable to make plotly graphics and chart bars. Equipped with: Python Code Interpreter and Simple calculator."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The query or instruction to send to the Calculations Agent."
                },
                "propagate_history": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Whether to include previous conversation history between the current agent and Calculations Agent. This provides context for the Calculations Agent, allowing it to reference past interactions."
                        "When `true`, the Calculations Agent will have access to prior exchanges for context continuity. "
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
        return "calculations-agent"
