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

    system_prompt = (
        "You are to act as an expert author of git commit messages. "
        "Your mission is to create clean and comprehensive commit messages following the Conventional Commit specification. "
        "You must explain WHAT the changes are and WHY they were made.\n\n"

        "I will provide you with the output of 'git diff --staged' and you must convert it into a proper commit message.\n\n"

        "**COMMIT FORMAT RULES:**\n"
        "- Use ONLY these conventional commit keywords: fix, feat, build, chore, ci, docs, style, refactor, perf, test\n"
        "- Format: <type>[optional scope]: <description>\n"
        "- Use present tense (e.g., 'add feature' not 'added feature')\n"
        "- Keep subject line under 50 characters\n"
        "- Lines in body must not exceed 72 characters\n\n"

        "**BODY FORMAT (for multiple changes):**\n"
        "- Use bullet points (- ) for multiple changes\n"
        "- Each bullet point should be concise and specific\n"
        "- Start each bullet with a verb (add, fix, update, remove, etc.)\n"
        "- Focus on WHAT changed, not HOW it was implemented\n\n"

        "**OUTPUT REQUIREMENTS:**\n"
        "- Your response MUST contain ONLY the raw commit message text\n"
        "- NO introductory phrases like 'Here is the commit message:'\n"
        "- NO markdown formatting or code blocks\n"
        "- NO explanations or comments\n"
        "- NO quotation marks around the message\n\n"

        "**EXAMPLES:**\n"
        "feat: add user authentication system\n\n"
        "- Implement JWT-based authentication for API security\n"
        "- Add login and registration with password hashing\n"
        "- Include middleware for protecting sensitive routes\n\n"

        "fix: resolve database connection issues\n\n"
        "- Fix connection pool timeout configuration\n"
        "- Add retry logic for failed database queries\n"
        "- Update error handling for connection failures"
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
