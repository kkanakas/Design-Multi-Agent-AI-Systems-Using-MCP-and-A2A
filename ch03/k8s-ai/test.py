import os
import sys
from anthropic import Anthropic, AuthenticationError

# Load API key from environment only — never hardcode
api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    print('ERROR: ANTHROPIC_API_KEY environment variable not set')
    sys.exit(1)

if len(api_key) < 20 or not api_key.startswith('sk-ant-'):
    print('ERROR: ANTHROPIC_API_KEY format invalid (must start with sk-ant- and be 20+ chars)')
    sys.exit(1)

# Key validation happens at client init in SDK v0.7.0+ — catch here, not at messages.create()
try:
    client = Anthropic(api_key=api_key)  # Raises AuthenticationError immediately if key invalid
except AuthenticationError as e:
    print(f'Authentication failed: {e}')
    print('Generate a new API key from console.anthropic.com and update ANTHROPIC_API_KEY')
    sys.exit(1)

# Now messages.create() will succeed if network/model are OK
try:
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': 'Hello'}]
    )
    print(response.content[0].text)
except AuthenticationError:
    print('Key was revoked after client init — refresh ANTHROPIC_API_KEY')
except Exception as e:
    print(f'Request failed (not auth): {type(e).__name__}: {e}')