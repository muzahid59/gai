import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path

# Add the src directory to the Python path to allow importing cli
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai import cli
from gai import utils


@pytest.fixture(autouse=True)
def cleanup_env_vars():
    # Store original environment variables
    original_env = {
        k: os.environ[k]
        for k in os.environ
        if k in ["MODEL", "CHAT_URL", "PROVIDER", "OPENAI_API_KEY", "AI_PROVIDER"]
    }
    # Clear the environment variables for the test
    for k in ["MODEL", "CHAT_URL", "PROVIDER", "OPENAI_API_KEY", "AI_PROVIDER"]:
        if k in os.environ:
            del os.environ[k]

    yield

    # Restore original environment variables
    for k in original_env:
        os.environ[k] = original_env[k]
    # Clean up any variables set during the test that were not originally present
    for k in ["MODEL", "CHAT_URL", "PROVIDER", "OPENAI_API_KEY", "AI_PROVIDER"]:
        if k in os.environ and k not in original_env:
            del os.environ[k]


@patch("subprocess.run")
def test_get_staged_diff(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""
    assert utils.get_staged_diff() == "diff content"


def test_clean_commit_message():
    # Test removing <think></think> tags
    message_with_think = """<think>
This is thinking content that should be removed.
Multiple lines of thinking.
</think>

feat(repository-check): add git repository validation

added check for git repository status"""

    expected = """feat(repository-check): add git repository validation

added check for git repository status"""

    assert utils.clean_commit_message(message_with_think) == expected

    # Test message without think tags (should remain unchanged)
    clean_message = "feat: add new feature\n\nThis is a normal commit message"
    assert utils.clean_commit_message(clean_message) == clean_message

    # Test multiple think blocks
    multiple_thinks = """<think>First think block</think>
feat: test commit
<think>Second think block</think>

This is the description"""

    expected_multiple = """feat: test commit

This is the description"""

    assert utils.clean_commit_message(multiple_thinks) == expected_multiple


# Test for Ollama provider with no model (uses default)
@patch.dict(os.environ, {}, clear=True)
@patch("gai.cli.load_dotenv")  # Prevent .env loading
@patch("gai.cli.load_config", return_value={})  # Mock empty config
@patch("gai.cli.save_config")  # Mock config saving
@patch("gai.cli.update_setting")  # Mock settings update
@patch("gai.cli.OllamaProvider")
@patch("threading.Thread")
@patch(
    "builtins.input", side_effect=["http://input.endpoint", "a"]
)  # Endpoint input, then apply
def test_main_ollama_no_model_default(
    mock_input, mock_thread, mock_OllamaProvider, mock_update_setting, mock_save_config, mock_load_config, mock_load_dotenv
):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()

    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged", "--minimal", "--unified=5"]:
            result = MagicMock()
            result.stdout = "diff content"
            result.returncode = 0
            result.stderr = ""
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OllamaProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = (
        "feat: ollama default commit"
    )

    with patch("subprocess.run", side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'ollama' but no model
        with patch.object(sys, "argv", ["gai", "--provider", "ollama"]):
            cli.main()

        # Assertions
        mock_OllamaProvider.assert_called_once_with(
            model="llama3.2", endpoint="http://localhost:11434/api"
        )
        mock_provider_instance.generate_commit_message.assert_called_once_with(
            "diff content", oneline=False
        )

        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ["git", "commit", "-m", "feat: ollama default commit"]:
                commit_call_found = True
                break
        assert commit_call_found


# Test for Ollama provider with command line model argument
@patch.dict(os.environ, {"CHAT_URL": "http://env.endpoint"}, clear=True)
@patch("gai.cli.load_config", return_value={})  # Mock empty config
@patch("gai.cli.save_config")  # Mock config saving
@patch("gai.cli.update_setting")  # Mock settings update
@patch("gai.cli.OllamaProvider")
@patch("threading.Thread")
@patch("builtins.input", return_value="a")  # Only apply choice
def test_main_ollama_with_model_cmdline(mock_input, mock_thread, mock_OllamaProvider, mock_update_setting, mock_save_config, mock_load_config):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()

    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged", "--minimal", "--unified=5"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OllamaProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = (
        "feat: ollama cmdline commit"
    )

    with patch("subprocess.run", side_effect=subprocess_side_effect) as mock_run:
        with patch.object(
            sys, "argv", ["gai", "--provider", "ollama", "deepseek-r1:8b"]
        ):
            cli.main()

        # Assertions - should use the provided model with ollama provider
        mock_OllamaProvider.assert_called_once_with(
            model="deepseek-r1:8b", endpoint="http://localhost:11434/api"
        )
        mock_provider_instance.generate_commit_message.assert_called_once_with(
            "diff content", oneline=False
        )

        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ["git", "commit", "-m", "feat: ollama cmdline commit"]:
                commit_call_found = True
                break
        assert commit_call_found


# Test for OpenAI provider with default model
@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}, clear=True)
@patch("gai.cli.load_config", return_value={})  # Mock empty config
@patch("gai.cli.save_config")  # Mock config saving
@patch("gai.cli.update_setting")  # Mock settings update
@patch("gai.cli.OpenAIProvider")
@patch("threading.Thread")
@patch("builtins.input", return_value="a")  # User chooses to apply
def test_main_openai_provider_default(mock_input, mock_thread, mock_OpenAIProvider, mock_update_setting, mock_save_config, mock_load_config):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()

    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged", "--minimal", "--unified=5"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OpenAIProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = (
        "feat: openai default commit"
    )

    with patch("subprocess.run", side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'openai' but no model
        with patch.object(sys, "argv", ["gai", "--provider", "openai"]):
            cli.main()

        # Assertions
        mock_OpenAIProvider.assert_called_once_with(model="gpt-3.5-turbo")
        mock_provider_instance.generate_commit_message.assert_called_once_with(
            "diff content", oneline=False
        )

        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ["git", "commit", "-m", "feat: openai default commit"]:
                commit_call_found = True
                break
        assert commit_call_found


# Test for OpenAI provider with specified model
@patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}, clear=True)
@patch("gai.cli.load_config", return_value={})  # Mock empty config
@patch("gai.cli.save_config")  # Mock config saving
@patch("gai.cli.update_setting")  # Mock settings update
@patch("gai.cli.OpenAIProvider")
@patch("threading.Thread")
@patch("builtins.input", return_value="a")  # User chooses to apply
def test_main_openai_provider_with_model(mock_input, mock_thread, mock_OpenAIProvider, mock_update_setting, mock_save_config, mock_load_config):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()

    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged", "--minimal", "--unified=5"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OpenAIProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = (
        "feat: openai gpt4 commit"
    )

    with patch("subprocess.run", side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'openai' and specific model
        with patch.object(sys, "argv", ["gai", "--provider", "openai", "gpt-4"]):
            cli.main()

        # Assertions
        mock_OpenAIProvider.assert_called_once_with(model="gpt-4")
        mock_provider_instance.generate_commit_message.assert_called_once_with(
            "diff content", oneline=False
        )

        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ["git", "commit", "-m", "feat: openai gpt4 commit"]:
                commit_call_found = True
                break
        assert commit_call_found


@patch("gai.cli.is_git_repository")
@patch("builtins.print")  # Capture print calls for error messages
@patch("gai.cli.load_dotenv")
@patch("gai.cli.load_config", return_value={})  # Mock empty config
@patch("gai.cli.save_config")  # Mock config saving
@patch("gai.cli.get_staged_diff", return_value="diff content")
@patch("gai.cli.OllamaProvider")
@patch("threading.Thread")
@patch("builtins.input", return_value="q")  # Quit immediately
def test_main_exits_if_not_git_repo(
    mock_input,
    mock_thread,
    mock_OllamaProvider,
    mock_get_staged_diff,
    mock_save_config,
    mock_load_config,
    mock_load_dotenv,
    mock_print,
    mock_is_git_repository,
):
    mock_is_git_repository.return_value = False
    with patch.object(sys, "argv", ["gai"]):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            cli.main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1
    mock_print.assert_called_once_with(
        "\033[31mError: Not a Git repository. Please initialize a Git repository or navigate to one.\033[0m"
    )


# Test for OpenAI provider with missing API key (interactive input)
@patch.dict(os.environ, {}, clear=True)
@patch("gai.cli.load_dotenv")  # Prevent .env loading
@patch("gai.cli.load_config", return_value={})  # Mock empty config
@patch("gai.cli.save_config")  # Mock config saving
@patch("gai.cli.update_setting")  # Mock settings update
@patch("gai.cli.OpenAIProvider")
@patch("threading.Thread")
@patch(
    "builtins.input", side_effect=["sk-test-api-key", "a"]
)  # API key input, then apply
def test_main_openai_provider_interactive_api_key(
    mock_input, mock_thread, mock_OpenAIProvider, mock_update_setting, mock_save_config, mock_load_config, mock_load_dotenv
):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()

    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged", "--minimal", "--unified=5"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OpenAIProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = (
        "feat: openai interactive commit"
    )

    with patch("subprocess.run", side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'openai'
        with patch.object(sys, "argv", ["gai", "--provider", "openai"]):
            cli.main()

        # Assertions
        mock_OpenAIProvider.assert_called_once_with(model="gpt-3.5-turbo")
        mock_provider_instance.generate_commit_message.assert_called_once_with(
            "diff content", oneline=False
        )

        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == [
                "git",
                "commit",
                "-m",
                "feat: openai interactive commit",
            ]:
                commit_call_found = True
                break
        assert commit_call_found
