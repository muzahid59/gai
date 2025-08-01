import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.ollama_client import OllamaProvider

@patch('requests.post')
def test_ollama_provider_generate_commit_message(mock_requests_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "feat: ollama commit"}}
    mock_requests_post.return_value = mock_response

    provider = OllamaProvider(model="llama3", endpoint="http://localhost:11434/api")
    diff = "test diff"
    message = provider.generate_commit_message(diff)

    assert message == "feat: ollama commit"

    system_prompt=(
        "You are the best git assistant whose aim is to generate a git commit message."
        "IT MUST BE written in English, be concise, be lowercase, relevant and straight to the point."
        "IT MUST FOLLOW conventional commits specifications and the following template:"
        "<type>[optional scope]: <short description>"
       
        "[optional body]"
        
        "Where <type> MUST BE ONE OF: fix, feat, build, chore, ci, docs, style, refactor, perf, test"
        "Where <type> MUST NOT BE: add, update, delete etc."
        "A commit that has a footer BREAKING CHANGE:, or appends a ! after the type, introduces a breaking API change."
        "DO NOT ADD UNDER ANY CIRCUMSTANCES: explanation about the commit, details such as file, changes, hash or the conventional commits specs."
        "Here is the git diff:"
    )
    user_prompt = f"---\n\nGIT DIFF:\n{diff}"

    mock_requests_post.assert_called_once_with(
        f"{provider.endpoint}/chat",
        json={
            "model": provider.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        },
        timeout=60
    )
