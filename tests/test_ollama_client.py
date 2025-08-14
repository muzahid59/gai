import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.ollama_client import OllamaProvider


@patch("requests.post")
def test_ollama_provider_generate_commit_message(mock_requests_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "feat: ollama commit"}}
    mock_requests_post.return_value = mock_response

    provider = OllamaProvider(model="llama3", endpoint="http://localhost:11434/api")
    diff = "test diff"
    message = provider.generate_commit_message(diff)

    assert message == "feat: ollama commit"

    mock_requests_post.assert_called_once()
    args, kwargs = mock_requests_post.call_args
    assert args[0] == f"{provider.endpoint}/chat"

    json_payload = kwargs["json"]
    assert json_payload["model"] == provider.model
    assert json_payload["stream"] is False
    messages = json_payload["messages"]
    assert len(messages) == 2
    system_msg = messages[0]
    user_msg = messages[1]

    # Partial assertions on system prompt
    content = system_msg["content"]
    required_fragments = [
        "You are to act as an expert author of git commit messages.",
        "**COMMIT FORMAT RULES:**",
        "Use ONLY these conventional commit keywords:",
        "**OUTPUT REQUIREMENTS:**",
        "raw commit message text",
    ]
    for frag in required_fragments:
        assert frag in content

    assert (
        user_msg["content"] == f"Generate a commit message for this git diff:\n\n{diff}"
    )
