"""Core kubectl functionality for k8s-ai."""

import json
import os
from typing import Dict, List, Any, Optional

import sh
import anthropic


class KubectlExecutor:
    """Handles kubectl command execution and Anthropic integration."""

    def __init__(self, context: Optional[str] = None):
        """Initialize kubectl executor with optional context."""
        self.context = context
        self.client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
        self.model_name = "claude-sonnet-4-6"
        self.system_prompt = "You are a Kubernetes expert ready to help"
        self.tools = [{
            "name": "kubectl",
            "description": "execute a kubectl command against the current k8s cluster",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": (
                            "the kubectl command to execute (without kubectl, just "
                            "the arguments). For example, 'get pods'"
                        ),
                    },
                },
                "required": ["cmd"],
            },
        }]

    def execute_kubectl(self, cmd: str) -> str:
        """Execute a kubectl command and return the result."""
        cmd_parts = cmd.split()
        if self.context:
            cmd_parts = ['--context', self.context] + cmd_parts

        try:
            result = sh.kubectl(cmd_parts)
            return str(result)
        except sh.ErrorReturnCode as e:
            return f"Error: {e.stderr.decode() if e.stderr else str(e)}"

    def send_message(self, messages: List[Dict[str, Any]]) -> str:
        """Send messages to Anthropic and handle tool calls."""
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=8096,
            system=self.system_prompt,
            messages=messages,
            tools=self.tools,
        )

        text_content = ""
        tool_use_blocks = []
        for block in response.content:
            if block.type == "text":
                text_content = block.text
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        if tool_use_blocks:
            assistant_content = []
            if text_content:
                assistant_content.append({"type": "text", "text": text_content})
            for block in tool_use_blocks:
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results = []
            for block in tool_use_blocks:
                if block.name == "kubectl":
                    cmd = block.input["cmd"]
                    result = self.execute_kubectl(cmd)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            return self.send_message(messages)

        return text_content.strip()
