import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path

# Add the src directory to the Python path to allow importing openai_client
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.openai_client import OpenAIProvider

@patch.dict(os.environ, {"OPEN_AI_API_KEY": "test_api_key"})
@patch('gai.openai_client.OpenAI')
def test_openai_provider_generate_commit_message(mock_openai_class):
    # Mock the OpenAI client instance
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Mock the response structure for the new API
    mock_response = MagicMock()
    mock_response.choices[0].message.content = 'feat: openai commit'
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAIProvider()
    diff = "test diff"
    message = provider.generate_commit_message(diff)

    assert message == "feat: openai commit"

    # Capture the actual call instead of asserting full prompt equality
    mock_client.chat.completions.create.assert_called_once()
    _, kwargs = mock_client.chat.completions.create.call_args

    assert kwargs['model'] == provider.model
    assert kwargs['stream'] is False

    messages = kwargs['messages']
    assert isinstance(messages, list) and len(messages) == 2
    system_msg = messages[0]
    user_msg = messages[1]

    assert system_msg['role'] == 'system'
    content = system_msg['content']
    # Key fragments that must be present (prompt may evolve slightly)
    required_fragments = [
        "You are to act as an expert author of git commit messages.",
        "**COMMIT FORMAT RULES:**",
        "Use ONLY these conventional commit keywords:",
        "**OUTPUT REQUIREMENTS:**",
        "raw commit message text"
    ]
    for frag in required_fragments:
        assert frag in content

    assert user_msg['role'] == 'user'
    assert user_msg['content'] == f"Generate a commit message for this git diff:\n\n{diff}"