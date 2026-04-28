#!/usr/bin/env python3

"""Minimal test to debug MAKDO agent creation."""

import os
import sys
sys.path.insert(0, '/Users/gigi/git/ai-six/py')

from ai_six.agent.config import Config
from ai_six.agent.agent import Agent

def test_minimal_agent():
    """Test minimal agent creation."""
    print("🧪 Testing minimal AI-6 agent creation...")

    # Create minimal config
    config = Config(
        name="Test Agent",
        description="Test agent",
        default_model_id="claude-sonnet-4-6",
        tools_dirs=["/Users/gigi/git/ai-six/py/ai_six/tools"],
        mcp_tools_dirs=["/Users/gigi/git/ai-six/py/ai_six/mcp_tools"],
        memory_dir="data/memory",
        provider_config={
            "anthropic": {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "default_model": "claude-sonnet-4-6"
            }
        }
    )

    print(f"✅ Config created: {config.name}")
    print(f"Anthropic API key set: {'Yes' if config.provider_config.get('anthropic', {}).get('api_key') else 'No'}")

    # Test agent creation
    try:
        agent = Agent(config)
        print(f"✅ Agent created successfully!")
        print(f"LLM providers: {len(agent.llm_providers)}")
        return True
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False

if __name__ == "__main__":
    test_minimal_agent()