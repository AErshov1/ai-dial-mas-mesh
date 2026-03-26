from typing import Any

from task.tools.deployment.base_agent_tool import BaseAgentTool


class CalculationsAgentTool(BaseAgentTool):
    # Provide implementations of deployment_name (in core config), name, description and parameters.
    # Don't forget to mark them as @property
    # Parameters:
    #   - prompt: string. Required.
    #   - propagate_history: boolean

    @property
    def deployment_name(self) -> str:
        return "calculations-agent"
