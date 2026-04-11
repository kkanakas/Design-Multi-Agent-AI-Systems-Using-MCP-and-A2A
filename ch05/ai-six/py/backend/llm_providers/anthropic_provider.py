import json
from typing import Iterator

import anthropic

from backend.object_model import LLMProvider, ToolCall, Usage, Tool, AssistantMessage, Message


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-6"):
        self.default_model = default_model
        self.client = anthropic.Anthropic(api_key=api_key)

    @staticmethod
    def _tool2dict(tool: Tool) -> dict:
        """Convert the tool to a dictionary format for Anthropic API."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": {
                "type": "object",
                "required": list(tool.required),
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description
                    } for param in tool.parameters
                },
            }
        }

    @staticmethod
    def _messages_to_anthropic(messages: list[Message]) -> tuple[str, list[dict]]:
        """Convert Message objects to Anthropic API format.

        Returns:
            A tuple of (system_prompt, anthropic_messages).
            System messages are extracted and concatenated into system_prompt.
            Tool result messages are converted to user messages with tool_result content.
        """
        system_parts = []
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "user":
                anthropic_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    content = []
                    if msg.content:
                        content.append({"type": "text", "text": msg.content})
                    for tc in msg.tool_calls:
                        try:
                            input_data = json.loads(tc.arguments) if tc.arguments else {}
                        except (json.JSONDecodeError, TypeError):
                            input_data = {}
                        content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": input_data,
                        })
                    anthropic_messages.append({"role": "assistant", "content": content})
                else:
                    anthropic_messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                    })
            elif msg.role == "tool":
                # Anthropic expects tool results as user messages with tool_result blocks.
                # Consecutive tool results can be grouped in a single user message.
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": msg.content,
                }
                if (
                    anthropic_messages
                    and anthropic_messages[-1]["role"] == "user"
                    and isinstance(anthropic_messages[-1]["content"], list)
                    and anthropic_messages[-1]["content"]
                    and anthropic_messages[-1]["content"][0].get("type") == "tool_result"
                ):
                    anthropic_messages[-1]["content"].append(tool_result)
                else:
                    anthropic_messages.append({"role": "user", "content": [tool_result]})

        system_prompt = "\n\n".join(system_parts)
        return system_prompt, anthropic_messages

    def send(self, messages: list[Message], tool_dict: dict[str, Tool], model: str | None = None) -> AssistantMessage:
        """Send messages to the Anthropic API and return a complete response."""
        if not messages:
            raise ValueError("At least one message is required to send to the LLM.")

        if model is None:
            model = self.default_model

        tool_data = [self._tool2dict(tool) for tool in tool_dict.values()]
        system_prompt, anthropic_messages = self._messages_to_anthropic(messages)

        kwargs: dict = dict(
            model=model,
            max_tokens=8096,
            messages=anthropic_messages,
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        if tool_data:
            kwargs["tools"] = tool_data

        response = self.client.messages.create(**kwargs)

        text_content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_content = block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=json.dumps(block.input),
                    required=list(tool_dict[block.name].required) if block.name in tool_dict else [],
                ))

        return AssistantMessage(
            content=text_content,
            tool_calls=tool_calls if tool_calls else None,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )

    def stream(self, messages: list[Message], tool_dict: dict[str, Tool], model: str | None = None) -> Iterator[AssistantMessage]:
        """Stream messages from the Anthropic API, yielding partial responses."""
        if model is None:
            model = self.default_model

        tool_data = [self._tool2dict(tool) for tool in tool_dict.values()]
        system_prompt, anthropic_messages = self._messages_to_anthropic(messages)

        kwargs: dict = dict(
            model=model,
            max_tokens=8096,
            messages=anthropic_messages,
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        if tool_data:
            kwargs["tools"] = tool_data

        content = ""
        input_tokens = 0
        output_tokens = 0

        with self.client.messages.stream(**kwargs) as stream:
            for text_chunk in stream.text_stream:
                content += text_chunk
                yield AssistantMessage(
                    content=content,
                    tool_calls=None,
                    usage=None,
                )

            final_message = stream.get_final_message()

        # Extract tool calls from the completed response
        tool_calls = []
        for block in final_message.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=json.dumps(block.input),
                    required=list(tool_dict[block.name].required) if block.name in tool_dict else [],
                ))

        if hasattr(final_message, "usage"):
            input_tokens = final_message.usage.input_tokens
            output_tokens = final_message.usage.output_tokens

        yield AssistantMessage(
            content=content,
            tool_calls=tool_calls if tool_calls else None,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )

    @property
    def models(self) -> list[str]:
        return [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ]
