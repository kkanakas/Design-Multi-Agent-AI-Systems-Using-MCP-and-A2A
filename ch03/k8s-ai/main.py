import json
import os

import sh
import anthropic

client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
model_name = "claude-sonnet-4-6"
system_prompt = "You are a Kubernetes expert ready to help"
tools = [{
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


def send(messages: list[dict]) -> str:
    response = client.messages.create(
        model=model_name,
        max_tokens=8096,
        system=system_prompt,
        messages=messages,
        tools=tools,
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
                cmd = block.input["cmd"].split()
                result = sh.kubectl(cmd)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})
        return send(messages)

    return text_content.strip()


def main():
    print("☸️ Interactive Kubernetes Chat. Type 'exit' to quit.\n" + "-" * 52)
    messages = []
    while (user_input := input("👤 You: ")).lower() != "exit":
        messages.append({"role": "user", "content": user_input})
        response = send(messages)
        messages.append({"role": "assistant", "content": response})
        print(f"🤖 AI: {response}\n----------")


if __name__ == "__main__":
    main()
