import os

import uvicorn
from aidial_sdk import DIALApp
from aidial_sdk.chat_completion import ChatCompletion, Request, Response

from task.agents.content_management.content_management_app import ContentManagementApplication
from task.agents.web_search.web_search_agent import WebSearchAgent
from task.tools.base_tool import BaseTool
from task.tools.deployment.calculations_agent_tool import CalculationsAgentTool
from task.tools.deployment.content_management_agent_tool import ContentManagementAgentTool
from task.tools.mcp.mcp_client import MCPClient
from task.tools.mcp.mcp_tool import MCPTool
from task.utils.constants import DIAL_ENDPOINT, DEPLOYMENT_NAME

_DDG_MCP_URL = os.getenv('DDG_MCP_URL', "http://localhost:8051/mcp")

# 1. Create WebSearchApplication class and extend ChatCompletion
# 2. As a tools for WebSearchAgent you need to provide:
#   - MCP tools by _DDG_MCP_URL
#   - CalculationsAgentTool (MAS Mesh)
#   - ContentManagementAgentTool (MAS Mesh)
# 3. Override the chat_completion method of ChatCompletion, create Choice and call WebSearchAgent
# ---
# 4. Create DIALApp with deployment_name `web-search-agent` (the same as in the core config) and impl is instance
#    of the WebSearchApplication
# 5. Add starter with DIALApp, port is 5003 (see core config)

class WebSearchApplication(ChatCompletion):

    def __init__(self):
        self.tools: list[BaseTool] = []

    async def _create_tools(self) -> list[BaseTool]:
        tools: list[BaseTool] = [
            ContentManagementAgentTool(DIAL_ENDPOINT),
            CalculationsAgentTool(DIAL_ENDPOINT),
        ]
        mcp_tools = []
        ddg_client = await MCPClient.create(_DDG_MCP_URL)
        for tool_model in await ddg_client.get_tools():
            mcp_tools.append(
                MCPTool(
                  client=ddg_client,
                  mcp_tool_model=tool_model
                )
            )

        tools.extend(mcp_tools)
        print(f"=> WebSearchAgent Tools: {[tool.name for tool in tools]}")
        return tools

    async def chat_completion(
        self, request: Request, response: Response
    ) -> None:
      if not self.tools:
          self.tools = await self._create_tools()
      with response.create_single_choice() as choice:
        agent = WebSearchAgent(
            endpoint=DIAL_ENDPOINT,
            tools=self.tools
        )
        result = await agent.handle_request(
            deployment_name=DEPLOYMENT_NAME,
            request=request,
            choice=choice,
            response=response
        )
        print(f"=> WebSearchAgent Result: {result}")

app: DIALApp = DIALApp()
app.add_chat_completion(deployment_name="web-search-agent", impl=WebSearchApplication())

if __name__ == "__main__":
    uvicorn.run(app, port=5003, host="0.0.0.0")


