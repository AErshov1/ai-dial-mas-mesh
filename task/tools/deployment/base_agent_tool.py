import json
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any

from aidial_client import AsyncDial
from aidial_sdk.chat_completion import Message, Role, CustomContent, Stage, Attachment
from pydantic import StrictStr

from task.tools.base_tool import BaseTool
from task.tools.models import ToolCallParams
from task.utils.stage import StageProcessor

_AGENT_DEPLOYMENT = "agent_deployment"
_AGENT_MESSAGES = "agent_messages"

class BaseAgentTool(BaseTool, ABC):

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    @property
    @abstractmethod
    def deployment_name(self) -> str:
        pass

    async def _execute(self, tool_call_params: ToolCallParams) -> str | Message:
        # 1. All the agents that will used as tools will have two parameters in request:
        #   - `prompt` (the request to agent)
        #   - `propagate_history`, boolean whether we need to propagate the history of communication with called agent
        # 2. Use AsyncDial (api_version='2025-01-01-preview'), call the agent with steaming option.
        #    Here, actually, you can find one of the most powerful features of DIAL - Unified protocol. All the
        #    applications that provide `/chat/completions` endpoint and following Unified protocol - can `communicate`
        #    between each other though Unified protocol (that is OpenAI compatible), in other words, applications can
        #    `communicate` between each other like they communication with OpenAI models (Unified protocol is OpenAI compatible).
        #    The second powerful feature is that the application that makes the call provides with whole context and
        #    responsible to manage this context. So, like we calling the model and provide it with the whole history in
        #    the same way we are working with applications, the application that makes a call provide the conversation history.
        #    ⚠️ To provide proper message history you need to implement the `_prepare_messages` method!
        #    ⚠️ Don't forget to include as extra_headers `x-conversation-id`!
        # 3. Prepare:
        #   - `content` variable, here we will collect the streamed content
        #   - `custom_content: CustomContent` variable, here we will collect variable CustomContent from agent response
        #   - `stages_map: dict[int, Stage]` variable, here will be persisted propagated stages
        # 4. Iterate through chunks and:
        #   - Stream content to the Stage (from tool_call_params) for this tool call
        #   - For custom_content:
        #       - set `state` from response CustomContent to the `custom_content`
        #       - in attachments are found propagate them to choice
        #       - Optional:
        #           Stages propagation: convert response CustomContent to dict and if stages are present:
        #           - each Stage has it is `index`, it will be returned in each chunk. If stage by such index is present
        #             in `stages_map` then you need to propagate content, otherwise you need to create stage
        #           - propagate stage name from response to propagated stage name, the same story for `content` and `attachments`
        #           - if response stage has `status = completed` - we need to close such stage
        # 5. Ensure that stages are closed (just iterate through them and close safely with StageProcessor)
        # 6. Return Tool message
        #    ⚠️ Remember, tool message must have tool call id, also don't forget to add `custom_content` since we need
        #       to save properly tool history to choice state later
        arguments = json.loads(tool_call_params.tool_call.function.arguments)
        print(f"{'='*80}\nDEPLOYMENT TOOL CALL: {self.name}\n\n{arguments}\n{'='*80}")

        dial_client = AsyncDial(base_url=self.endpoint, api_key=tool_call_params.api_key, api_version='2025-01-01-preview')
        chunks = await dial_client.chat.completions.create(
            messages=self._prepare_messages(arguments, tool_call_params.messages),
            deployment_name=self.deployment_name,
            extra_headers={
                'x-conversation-id': tool_call_params.conversation_id,
            },
            extra_body={
                "custom_fields": {
                    "configuration": {**arguments}
                }
            },
            stream=True,
        )
        content = ''
        result_custom_content = CustomContent(attachments=[])
        stages: dict[int, Stage] = {}
        stage = tool_call_params.stage
        choice = tool_call_params.choice
        async for chunk in chunks:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    stage.append_content(delta.content)
                    content += delta.content
                if custom_content := delta.custom_content:
                    print("Agent Custom Content:", custom_content)
                    if custom_content.attachments:
                        result_custom_content.attachments.extend(custom_content.attachments)

                    if custom_content.state:
                        if not result_custom_content.state:
                          result_custom_content.state = custom_content.state
                        else:
                          print(f"[WARNING] Agent: multiple states in custom content!\nPrevious state: {result_custom_content.state}\nNew state: {custom_content.state}")

                    agent_stages: dict[str, Any] = custom_content.dict(exclude_none=True).get("stages")
                    if agent_stages:
                        for stg in agent_stages:
                            idx = stg["index"]
                            opened_stg = stages.get(idx)
                            if not opened_stg:
                                opened_stg = StageProcessor.open_stage(choice, stg.get("name"))
                                stages[idx] = opened_stg

                            if stg_content := stg.get("content"):
                                opened_stg.append_content(stg_content)
                            elif stg_attachments := stg.get("attachments"):
                                for stg_attachment in stg_attachments:
                                    opened_stg.add_attachment(Attachment(**stg_attachment))

        for stg in stages.values():
            StageProcessor.close_stage_safely(stg)
        for attachment in result_custom_content.attachments:
            choice.add_attachment(
                Attachment(**attachment.dict(exclude_none=True))
            )

        choice.set_state(
            {
                _AGENT_DEPLOYMENT: True,
                _AGENT_MESSAGES: result_custom_content.state,
            }
        )
        return Message(
            role=Role.TOOL,
            content=StrictStr(content),
            custom_content=result_custom_content,
            tool_call_id=StrictStr(tool_call_params.tool_call.id)
        )


    def _prepare_messages(self, arguments: Any, messages: list[Message]) -> list[dict[str, Any]]:
        # In here we will manage the context for the agent that we are going to call.
        # We support two modes:
        #   - One-shot: only one user message to the Agent with prompt
        #   - Propagate whole Per-To-Per history between this Agent and the Agent that we are calling
        # ---
        # 1. Get: `prompt` and `propagate_history` params from tool call
        # 2. Prepare empty `messages` array, here we will collect history with Per-To-Per communication between this
        #    agent and the agent that we are colling
        # 3. Collect the proper history, iterate through messages and:
        #   - In Assistant messages presented the state with tool_call_history, we need to properly unpack it. If message
        #   from assistant and in custom content present state and in this state present history for this `self.name`
        #   (self.name is the key in state to get tool_call_history from the agent that we are going to call), then
        #   firstly add to `messages` user message that is going before the assistant message and then add assistant
        #   message. For assistant message you need to make a deepcopy and refactor the state for copied message, instead
        #   of the whole state you need to get from the state value by `self.name`
        # 4. Lastly, add the user message with `prompt` and don't forget about the custom_content
        prompt = arguments["prompt"]
        propagate_history = bool(arguments.get("propagate_history", False))

        history: list[dict[str, Any]] = []
        if propagate_history:
            for idx in range(len(messages)):
                msg = messages[idx]
                if msg.role == Role.ASSISTANT:
                    if msg.custom_content and msg.custom_content.state:
                        msg_state = msg.custom_content.state
                        if msg_state.get(self.name):
                            copied_msg = deepcopy(msg)
                            copied_msg.custom_content.state = msg_state.get(self.name)  # TODO: Check what is the trick here
                            history.append(messages[idx - 1].dict(exclude_none=True))
                            history.append(copied_msg.dict(exclude_none=True))

        print(f"History for agent {self.name}:", history)

        custom_content = messages[-1].custom_content
        history.append(
            {
                "role": "user",
                "content": prompt,
                "custom_content": custom_content.dict(exclude_none=True) if custom_content else None,
            }
        )
        return history
