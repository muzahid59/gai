import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path

# Add the src directory to the Python path to allow importing openai_client
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.openai_client import OpenAIProvider

@patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
@patch('openai.ChatCompletion.create')
def test_openai_provider_generate_commit_message(mock_openai_create):
    mock_response = MagicMock()
    mock_response.choices[0].message = {'content': 'feat: openai commit'}
    mock_openai_create.return_value = mock_response

    provider = OpenAIProvider()
    diff = "test diff"
    message = provider.generate_commit_message(diff);

    assert message == "feat: openai commit"

    system_prompt = (
        "You are the best git assistant whose aim is to generate a git commit message."
        "IT MUST BE written in English, be concise, be lowercase, relevant and straight to the point."
        "IT MUST FOLLOW conventional commits specifications and the following template:"
        "<type>[optional scope]: <short description>"
        "Where <type> MUST BE ONE OF: fix, feat, build, chore, ci, docs, style, refactor, perf, test"
        "Where <type> MUST NOT BE: add, update, delete etc."
        "A commit that has a footer BREAKING CHANGE:, or appends a ! after the type, introduces a breaking API change."
        "DO NOT ADD UNDER ANY CIRCUMSTANCES: explanation about the commit, details such as file, changes, hash or the conventional commits specs."
        "Here is the git diff:"
    )
    user_prompt = f"---\n\nGIT DIFF:\n{diff}"

    mock_openai_create.assert_called_once_with(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        stream=False
    )
