import argparse
import sys
import os
import threading
from dotenv import load_dotenv
from typing import Tuple  # added for Python 3.8 compatibility

from gai.provider import Provider
from gai.ollama_client import OllamaProvider
from gai.openai_client import OpenAIProvider
import json
from pathlib import Path
from gai.utils import (
    is_git_repository,
    get_staged_diff,
    commit,
    edit_message,
    spinner_animation,
    clean_commit_message,
)

# Configuration
DEFAULT_ENDPOINT = "http://localhost:11434/api"
DEFAULT_PROVIDER = "ollama"

# Config file path
CONFIG_DIR = Path.home() / ".config" / "gai-commit"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    """Load configuration from config file."""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config):
    """Save configuration to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except IOError:
        print("Warning: Could not save configuration.")


def update_setting(setting_type, provider_name=None, value=None):
    """Update a setting in the config file.

    Args:
        setting_type: Type of setting (provider, model, api_key)
        provider_name: Provider name (required for model settings)
        value: Value to store
    """
    config = load_config()

    if setting_type == "provider" and value:
        config["provider"] = value
    elif setting_type == "model" and provider_name and value:
        if "models" not in config:
            config["models"] = {}
        config["models"][provider_name] = value
    elif setting_type == "api_key" and provider_name and value:
        if "api_keys" not in config:
            config["api_keys"] = {}
        config["api_keys"][provider_name] = value

    save_config(config)


def setup_provider(provider_name: str, model: str) -> Provider:
    """Setup and return the appropriate provider."""
    from gai.ollama_client import DEFAULT_OLLAMA_MODEL
    from gai.openai_client import DEFAULT_OPENAI_MODEL

    # Load saved config
    config = load_config()

    # Determine provider (in priority order)
    if provider_name:
        # 1. Command line argument (highest priority)
        provider_name = provider_name.lower()
    else:
        # 2. Environment variable
        env_provider = os.getenv("AI_PROVIDER")
        if env_provider:
            provider_name = env_provider.lower()
        else:
            # 3. Config file
            provider_name = config.get("provider", DEFAULT_PROVIDER).lower()

    # Save provider choice and set environment variable
    update_setting("provider", value=provider_name)
    os.environ["AI_PROVIDER"] = provider_name

    # Get saved models and API keys from config
    saved_models = config.get("models", {})
    saved_api_keys = config.get("api_keys", {})

    if provider_name == "ollama":
        # Determine model to use (in priority order)
        model_to_use = model or saved_models.get(provider_name) or DEFAULT_OLLAMA_MODEL
        endpoint_to_use = DEFAULT_ENDPOINT

        # Save model choice if specified on command line
        if model:
            update_setting("model", provider_name=provider_name, value=model_to_use)

        return OllamaProvider(model=model_to_use, endpoint=endpoint_to_use)

    elif provider_name == "openai":
        # Determine API key (in priority order)
        api_key = os.getenv("OPENAI_API_KEY") or saved_api_keys.get(provider_name)

        # If no API key is found, prompt the user
        if not api_key:
            api_key = input("Enter your OpenAI API key: ").strip()
            if not api_key:
                print("OpenAI API key is required for the OpenAI provider.")
                sys.exit(1)

            # Save API key to config and set environment variable
            update_setting("api_key", provider_name=provider_name, value=api_key)

        # Always set environment variable
        os.environ["OPENAI_API_KEY"] = api_key

        # Determine model to use (in priority order)
        model_to_use = model or saved_models.get(provider_name) or DEFAULT_OPENAI_MODEL

        # Save model choice if specified on command line
        if model:
            update_setting("model", provider_name=provider_name, value=model_to_use)

        return OpenAIProvider(model=model_to_use)

    else:
        print(f"Invalid provider: {provider_name}. Please choose 'ollama' or 'openai'.")
        sys.exit(1)


def generate_commit_message(
    provider: Provider, staged_diff: str, oneline: bool = False
) -> str:
    """Generate commit message with spinner."""
    stop_spinner = threading.Event()
    model_name = getattr(provider, "model", "AI")
    spinner_thread = threading.Thread(
        target=spinner_animation, args=(stop_spinner, model_name)
    )
    spinner_thread.start()

    try:
        suggested_message = provider.generate_commit_message(
            staged_diff, oneline=oneline
        )
        return clean_commit_message(suggested_message)
    finally:
        stop_spinner.set()
        spinner_thread.join()


def handle_user_choice(
    choice: str,
    message: str,
    provider: Provider,
    staged_diff: str,
    oneline: bool = False,
) -> Tuple[str, bool]:
    """Handle user input and return (new_message, should_continue)."""
    if choice == "a":
        commit(message)
        return message, False
    elif choice == "e":
        edited_message = edit_message(message)
        if edited_message:
            commit(edited_message)
            return edited_message, False
        return message, True
    elif choice == "r":
        # Re-generate with same diff
        new_msg = generate_commit_message(provider, staged_diff, oneline=oneline)
        return new_msg, True
    elif choice == "q":
        return message, False
    else:
        print("Invalid choice.")
        return message, True


def main():
    load_dotenv()

    # Check git repository
    if not is_git_repository():
        print(
            "\033[31mError: Not a Git repository. Please initialize a Git repository or navigate to one.\033[0m"
        )
        sys.exit(1)

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="An AI-powered git commit message generator."
    )
    parser.add_argument(
        "--provider",
        type=str,
        help=f"The provider to use for generating commit messages. Can be 'ollama' or 'openai'. Default: {os.getenv('AI_PROVIDER', DEFAULT_PROVIDER)}",
    )
    parser.add_argument(
        "model", nargs="?", help="The model to use for generating commit messages."
    )
    parser.add_argument(
        "--oneline", action="store_true", help="Generate a single-line commit message."
    )
    args = parser.parse_args()

    # Get staged diff
    staged_diff = get_staged_diff()
    if not staged_diff:
        print(
            "No staged changes found. Please stage your changes with 'git add' first."
        )
        sys.exit(0)

    # Setup provider and generate initial message
    provider = setup_provider(args.provider, args.model)

    # Note: Model saving is now handled within setup_provider

    suggested_message = generate_commit_message(
        provider, staged_diff, oneline=args.oneline
    )

    # Main interaction loop
    while True:
        print("\n---")
        print("\u001b[1mSuggested Commit Message:\u001b[0m")
        print(suggested_message)
        print("---")

        choice = input(
            "\u001b[1m[A]\u001b[0mpply, \u001b[1m[E]\u001b[0mdit, \u001b[1m[R]\u001b[0m-generate, or \u001b[1m[Q]\u001b[0muit? (a/e/r/q) "
        ).lower()

        suggested_message, should_continue = handle_user_choice(
            choice, suggested_message, provider, staged_diff, oneline=args.oneline
        )
        if not should_continue:
            break


if __name__ == "__main__":
    main()
