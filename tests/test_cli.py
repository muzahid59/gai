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
    original_env = {k: os.environ[k] for k in os.environ if k in ["MODEL", "CHAT_URL", "PROVIDER", "API_KEY"]}
    # Clear the environment variables for the test
    for k in ["MODEL", "CHAT_URL", "PROVIDER", "API_KEY"]:
        if k in os.environ:
            del os.environ[k]

    yield

    # Restore original environment variables
    for k in original_env:
        os.environ[k] = original_env[k]
    # Clean up any variables set during the test that were not originally present
    for k in ["MODEL", "CHAT_URL", "PROVIDER", "API_KEY"]:
        if k in os.environ and k not in original_env:
            del os.environ[k]

@patch('subprocess.run')
def test_get_staged_diff(mock_subprocess_run):
    mock_subprocess_run.return_value.stdout = "diff content"
    mock_subprocess_run.return_value.returncode = 0
    mock_subprocess_run.return_value.stderr = ""
    assert cli.get_staged_diff() == "diff content"

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
    
    assert cli.clean_commit_message(message_with_think) == expected
    
    # Test message without think tags (should remain unchanged)
    clean_message = "feat: add new feature\n\nThis is a normal commit message"
    assert cli.clean_commit_message(clean_message) == clean_message
    
    # Test multiple think blocks
    multiple_thinks = """<think>First think block</think>
feat: test commit
<think>Second think block</think>

This is the description"""
    
    expected_multiple = """feat: test commit

This is the description"""
    
    assert cli.clean_commit_message(multiple_thinks) == expected_multiple

# Test for Ollama provider with interactive input
@patch.dict(os.environ, {}, clear=True)
@patch('gai.cli.load_dotenv')  # Prevent .env loading
@patch('gai.cli.OllamaProvider')
@patch('threading.Thread')
@patch('builtins.input', side_effect=['test_model_input', 'http://input.endpoint', 'a'])
def test_main_ollama_interactive(mock_input, mock_thread, mock_OllamaProvider, mock_load_dotenv):
    # Mock subprocess calls for git
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
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OllamaProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = "feat: ollama interactive commit"

    with patch('subprocess.run', side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'ollama'
        with patch.object(sys, 'argv', ['gai', '--provider', 'ollama']):
            cli.main()

        # Assertions
        mock_OllamaProvider.assert_called_once_with(model='test_model_input', endpoint='http://input.endpoint')
        mock_provider_instance.generate_commit_message.assert_called_once_with("diff content")
        
        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ['git', 'commit', '-m', 'feat: ollama interactive commit']:
                commit_call_found = True
                break
        assert commit_call_found

# Test for Ollama provider with environment variables
@patch.dict(os.environ, {
    'PROVIDER': 'ollama',
    'MODEL': 'test_model_env',
    'CHAT_URL': 'http://env.endpoint'
})
@patch('gai.cli.OllamaProvider')
@patch('threading.Thread')
@patch('builtins.input', return_value='a') # User chooses to apply
def test_main_ollama_env_vars(mock_input, mock_thread, mock_OllamaProvider):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()
    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OllamaProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = "feat: ollama env commit"

    with patch('subprocess.run', side_effect=subprocess_side_effect) as mock_run:
        with patch.object(sys, 'argv', ['gai']): # No provider arg, should default to ollama from env
            cli.main()

        # Assertions
        mock_OllamaProvider.assert_called_once_with(model='test_model_env', endpoint='http://env.endpoint')
        mock_provider_instance.generate_commit_message.assert_called_once_with("diff content")
        
        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ['git', 'commit', '-m', 'feat: ollama env commit']:
                commit_call_found = True
                break
        assert commit_call_found

# Test for OpenAI provider
@patch.dict(os.environ, {"API_KEY": "fake-key"}, clear=True)
@patch('gai.cli.OpenAIProvider')
@patch('threading.Thread')
@patch('builtins.input', return_value='a') # User chooses to apply
def test_main_openai_provider(mock_input, mock_thread, mock_OpenAIProvider):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()
    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OpenAIProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = "feat: openai commit"

    with patch('subprocess.run', side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'openai'
        with patch.object(sys, 'argv', ['gai', '--provider', 'openai']):
            cli.main()

        # Assertions
        mock_OpenAIProvider.assert_called_once()
        mock_provider_instance.generate_commit_message.assert_called_once_with("diff content")
        
        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ['git', 'commit', '-m', 'feat: openai commit']:
                commit_call_found = True
                break
        assert commit_call_found

@patch('gai.cli.is_git_repository')
@patch('builtins.print') # Capture print calls for error messages
@patch('gai.cli.load_dotenv')
@patch('gai.cli.get_staged_diff', return_value="diff content")
@patch('gai.cli.OllamaProvider')
@patch('threading.Thread')
@patch('builtins.input', return_value='q') # Quit immediately
def test_main_exits_if_not_git_repo(mock_input, mock_thread, mock_OllamaProvider, mock_get_staged_diff, mock_load_dotenv, mock_print, mock_is_git_repository):
    mock_is_git_repository.return_value = False
    with patch.object(sys, 'argv', ['gai']):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            cli.main()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1
    mock_print.assert_called_once_with("\033[31mError: Not a Git repository. Please initialize a Git repository or navigate to one.\033[0m")

# Test for OpenAI provider with missing API key (interactive input)
@patch.dict(os.environ, {}, clear=True)
@patch('gai.cli.load_dotenv')  # Prevent .env loading
@patch('gai.cli.save_api_key_to_env')
@patch('gai.cli.OpenAIProvider')
@patch('threading.Thread')
@patch('builtins.input', side_effect=['sk-test-api-key', 'a'])  # API key input, then apply
def test_main_openai_provider_interactive_api_key(mock_input, mock_thread, mock_OpenAIProvider, mock_save_api_key, mock_load_dotenv):
    # Mock subprocess calls for git
    mock_subprocess_run = MagicMock()
    def subprocess_side_effect(*args, **kwargs):
        if args[0] == ["git", "diff", "--staged"]:
            result = MagicMock()
            result.stdout = "diff content"
            return result
        elif args[0] and args[0][0] == "git" and args[0][1] == "commit":
            return MagicMock()
        return MagicMock()

    # Mock the provider
    mock_provider_instance = mock_OpenAIProvider.return_value
    mock_provider_instance.generate_commit_message.return_value = "feat: openai interactive commit"

    with patch('subprocess.run', side_effect=subprocess_side_effect) as mock_run:
        # Run main with provider 'openai'
        with patch.object(sys, 'argv', ['gai', '--provider', 'openai']):
            cli.main()

        # Assertions
        mock_save_api_key.assert_called_once_with('sk-test-api-key')
        mock_OpenAIProvider.assert_called_once()
        mock_provider_instance.generate_commit_message.assert_called_once_with("diff content")
        
        # Check that commit was called
        commit_call_found = False
        for call in mock_run.call_args_list:
            if call.args[0] == ['git', 'commit', '-m', 'feat: openai interactive commit']:
                commit_call_found = True
                break
        assert commit_call_found
