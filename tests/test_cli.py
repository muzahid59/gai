import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path to allow importing cli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai import cli

@pytest.fixture(autouse=True)
def cleanup_env_vars():
    # Store original environment variables
    original_env = {k: os.environ[k] for k in os.environ if k in ["MODEL", "CHAT_URL"]}
    # Clear the environment variables for the test
    for k in ["MODEL", "CHAT_URL"]:
        if k in os.environ:
            del os.environ[k]

    yield

    # Restore original environment variables
    for k in original_env:
        os.environ[k] = original_env[k]
    # Clean up any variables set during the test that were not originally present
    for k in ["MODEL", "CHAT_URL"]:
        if k in os.environ and k not in original_env:
            del os.environ[k]

@patch('subprocess.run')
def test_get_staged_diff(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""
    assert cli.get_staged_diff() == "diff content"

@patch('requests.post')
def test_generate_commit_message(mock_requests_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "feat: ollama commit"}}
    mock_requests_post.return_value = mock_response

    diff = "test diff"
    model = "llama3"
    endpoint = "http://localhost:11434/api"

    message = cli.generate_commit_message(diff, model, endpoint)
    assert message == "feat: ollama commit"

    system_prompt = (
        "You are an expert programmer tasked with writing a Git commit message. "
        "Based on the following `git diff --staged` output, generate a commit message that follows the Conventional Commits specification. "
        "The commit message must have a subject line of 50 characters or less, followed by a blank line, and then a more detailed explanatory body. "
        "Do not include any introductory phrases, comments, or markdown formatting like ```. Your entire response should be only the raw commit message text."
        "\n\nHere is an example of the desired format:\n"
        "feat: add user authentication\n\n"
        "Implement JWT-based authentication for the API.\n"
        "Add login and registration endpoints.\n"
        "Protect sensitive routes with an authentication middleware."
    )
    user_prompt = f"---\n\nGIT DIFF:\n{diff}"

    mock_requests_post.assert_called_once_with(
        f"{endpoint}/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        },
        timeout=60
    )

@patch.dict(os.environ, {}, clear=True)
@patch('gai.cli.load_dotenv')
@patch('threading.Thread')
@patch('requests.post')
@patch('builtins.input', side_effect=['test_model_input', 'http://input.endpoint', 'a'])
def test_main_interactive_input(mock_input, mock_requests_post, mock_thread, mock_load_dotenv):
    # Mock subprocess calls
    mock_subprocess_run = MagicMock()
    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged"]:
            result = MagicMock()
            result.stdout = "diff content"
            result.returncode = 0
            result.stderr = ""
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        else:
            return MagicMock()
    
    with patch('subprocess.run', side_effect=subprocess_side_effect) as mock_run:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "feat: interactive commit"}}
        mock_requests_post.return_value = mock_response

        cli.main()

        assert mock_input.call_count == 3
        
        system_prompt = (
            "You are an expert programmer tasked with writing a Git commit message. "
            "Based on the following `git diff --staged` output, generate a commit message that follows the Conventional Commits specification. "
            "The commit message must have a subject line of 50 characters or less, followed by a blank line, and then a more detailed explanatory body. "
            "Do not include any introductory phrases, comments, or markdown formatting like ```. Your entire response should be only the raw commit message text."
            "\n\nHere is an example of the desired format:\n"
            "feat: add user authentication\n\n"
            "Implement JWT-based authentication for the API.\n"
            "Add login and registration endpoints.\n"
            "Protect sensitive routes with an authentication middleware."
        )
        user_prompt = f"---\n\nGIT DIFF:\ndiff content"

        mock_requests_post.assert_called_once_with(
            "http://input.endpoint/chat",
            json={
                "model": "test_model_input",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            },
            timeout=60
        )
        
        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ['git', 'commit', '-m', 'feat: interactive commit']:
                commit_call_found = True
                break
        assert commit_call_found

@patch.dict(os.environ, {
    'MODEL': 'test_model_env',
    'CHAT_URL': 'http://env.endpoint'
})
@patch('gai.cli.load_dotenv')
@patch('threading.Thread')
@patch('requests.post')
@patch('builtins.input', return_value='q')
def test_main_env_vars_precedence(mock_input, mock_requests_post, mock_thread, mock_load_dotenv):
    with patch('subprocess.run') as mock_subprocess_run:
        mock_subprocess_run.return_value.stdout = "diff content"
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stderr = ""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "feat: env commit"}}
        mock_requests_post.return_value = mock_response

        cli.main()

        system_prompt = (
            "You are an expert programmer tasked with writing a Git commit message. "
            "Based on the following `git diff --staged` output, generate a commit message that follows the Conventional Commits specification. "
            "The commit message must have a subject line of 50 characters or less, followed by a blank line, and then a more detailed explanatory body. "
            "Do not include any introductory phrases, comments, or markdown formatting like ```. Your entire response should be only the raw commit message text."
            "\n\nHere is an example of the desired format:\n"
            "feat: add user authentication\n\n"
            "Implement JWT-based authentication for the API.\n"
            "Add login and registration endpoints.\n"
            "Protect sensitive routes with an authentication middleware."
        )
        user_prompt = f"---\n\nGIT DIFF:\ndiff content"

        mock_requests_post.assert_called_once_with(
            "http://env.endpoint/chat",
            json={
                "model": "test_model_env",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            },
            timeout=60
        )

