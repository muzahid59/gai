import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path

# Add the src directory to the Python path to allow importing cli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai import cli

@pytest.fixture(autouse=True)
def cleanup_env_vars():
    # Store original environment variables
    original_env = {k: os.environ[k] for k in os.environ if k.startswith("GAI_")}
    yield
    # Restore original environment variables
    for k in original_env:
        os.environ[k] = original_env[k]
    for k in ["GAI_MODEL", "GAI_ENDPOINT", "GAI_PROVIDER", "GAI_API_KEY"]:
        if k not in original_env:
            if k in os.environ:
                del os.environ[k]

@patch('subprocess.run')
def test_get_staged_diff(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""
    assert cli.get_staged_diff() == "diff content"

@patch('requests.post')
def test_generate_commit_message_ollama(mock_requests_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "feat: ollama commit"}
    mock_requests_post.return_value = mock_response

    diff = "test diff"
    model = "llama3"
    endpoint = "http://localhost:11434/api"
    provider = "ollama"
    api_key = None

    message = cli.generate_commit_message(diff, model, endpoint, provider, api_key)
    assert message == "feat: ollama commit"
    mock_requests_post.assert_called_once_with(
        f"{endpoint}/generate",
        headers={},
        json={"model": model, "prompt": cli.generate_commit_message.__wrapped__.__doc__.format(diff=diff), "stream": False},
        timeout=30
    )

@patch('requests.post')
def test_generate_commit_message_openai(mock_requests_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "feat: openai commit"}}]}
    mock_requests_post.return_value = mock_response

    diff = "test diff"
    model = "gpt-4o"
    endpoint = "https://api.openai.com"
    provider = "openai"
    api_key = "test_api_key"

    message = cli.generate_commit_message(diff, model, endpoint, provider, api_key)
    assert message == "feat: openai commit"
    mock_requests_post.assert_called_once_with(
        f"{endpoint}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": cli.generate_commit_message.__wrapped__.__doc__.format(diff=diff)}],
            "max_tokens": 500,
            "temperature": 0.7
        },
        timeout=30
    )

@patch('sys.argv', ['gai', '--model', 'test_model_cli', '--endpoint', 'http://cli.endpoint', '--provider', 'ollama', '--api-key', 'cli_key'])
@patch('subprocess.run')
@patch('requests.post')
def test_main_cli_args_precedence(mock_requests_post, mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "feat: cli commit"}
    mock_requests_post.return_value = mock_response

    with patch('builtins.input', return_value='q'): # Quit to avoid interactive loop
        cli.main()

    mock_requests_post.assert_called_once_with(
        "http://cli.endpoint/generate",
        headers={},
        json={"model": "test_model_cli", "prompt": cli.generate_commit_message.__wrapped__.__doc__.format(diff="diff content"), "stream": False},
        timeout=30
    )

@patch.dict(os.environ, {
    'GAI_MODEL': 'test_model_env',
    'GAI_ENDPOINT': 'http://env.endpoint',
    'GAI_PROVIDER': 'ollama',
    'GAI_API_KEY': 'env_key'
})
@patch('sys.argv', ['gai']) # No CLI args, so env vars should be used
@patch('subprocess.run')
@patch('requests.post')
def test_main_env_vars(mock_requests_post, mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "feat: env commit"}
    mock_requests_post.return_value = mock_response

    with patch('builtins.input', return_value='q'): # Quit to avoid interactive loop
        cli.main()

    mock_requests_post.assert_called_once_with(
        "http://env.endpoint/generate",
        headers={},
        json={"model": "test_model_env", "prompt": cli.generate_commit_message.__wrapped__.__doc__.format(diff="diff content"), "stream": False},
        timeout=30
    )

@patch('sys.argv', ['gai'])
@patch('subprocess.run')
@patch('requests.post')
def test_main_defaults(mock_requests_post, mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "feat: default commit"}
    mock_requests_post.return_value = mock_response

    with patch('builtins.input', return_value='q'): # Quit to avoid interactive loop
        cli.main()

    mock_requests_post.assert_called_once_with(
        f"{cli.DEFAULT_ENDPOINT}/generate",
        headers={},
        json={"model": cli.DEFAULT_MODEL, "prompt": cli.generate_commit_message.__wrapped__.__doc__.format(diff="diff content"), "stream": False},
        timeout=30
    )

@patch('sys.argv', ['gai', '--provider', 'openai', '--api-key', 'openai_key'])
@patch('subprocess.run')
@patch('requests.post')
def test_main_openai_provider_with_api_key(mock_requests_post, mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": "feat: openai cli commit"}}]}
    mock_requests_post.return_value = mock_response

    with patch('builtins.input', return_value='q'): # Quit to avoid interactive loop
        cli.main()

    mock_requests_post.assert_called_once_with(
        f"{cli.DEFAULT_ENDPOINT}/v1/chat/completions", # Default endpoint for OpenAI
        headers={"Authorization": "Bearer openai_key"},
        json={
            "model": cli.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": cli.generate_commit_message.__wrapped__.__doc__.format(diff="diff content")}],
            "max_tokens": 500,
            "temperature": 0.7
        },
        timeout=30
    )

@patch('sys.argv', ['gai', '--provider', 'openai'])
@patch('subprocess.run')
@patch('requests.post')
def test_main_openai_provider_no_api_key_fails(mock_requests_post, mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""

    with patch('builtins.input', return_value='q'):
        with pytest.raises(SystemExit) as excinfo:
            cli.main()

    assert excinfo.value.code == 1 # Expecting SystemExit with code 1 due to missing API key
    mock_requests_post.assert_not_called()


# Add a docstring to generate_commit_message for testing purposes
# This is a workaround because the original docstring is used in the prompt
# and we need to access it for testing the prompt content.
cli.generate_commit_message.__wrapped__ = cli.generate_commit_message
cli.generate_commit_message.__wrapped__.__doc__ = (
    "Based on the following `git diff --staged` output, please generate a concise and meaningful commit message. "
    "The message MUST follow the Conventional Commits specification (e.g., 'feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:'). "
    "The subject line should be 50 characters or less. "
    "Follow the subject line with a blank line, then a more detailed body explaining the what and why of the changes. "
    "Do not include any other explanatory text, comments, or markdown formatting in your response. Just the raw commit message."
    f"\n\n---\n\n{{diff}}"
)