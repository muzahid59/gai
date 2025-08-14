import argparse
import sys
import os
import threading
from dotenv import load_dotenv
from typing import Tuple  # added for Python 3.8 compatibility

from gai.provider import Provider
from gai.ollama_client import OllamaProvider
from gai.openai_client import OpenAIProvider
from gai.utils import (
    is_git_repository,
    get_staged_diff,
    commit,
    edit_message,
    spinner_animation,
    clean_commit_message
)

# Configuration
DEFAULT_ENDPOINT = "http://localhost:11434/api"
DEFAULT_PROVIDER = "ollama"

def setup_provider(provider_name: str, model: str) -> Provider:
    from gai.ollama_client import DEFAULT_OLLAMA_MODEL
    """Setup and return the appropriate provider."""

    provider_name = (provider_name or DEFAULT_PROVIDER).lower()

    if provider_name == "ollama":
        model_to_use = model or DEFAULT_OLLAMA_MODEL
        endpoint_to_use = DEFAULT_ENDPOINT
        return OllamaProvider(model=model_to_use, endpoint=endpoint_to_use)
    
    elif provider_name == "openai":
        from gai.openai_client import DEFAULT_OPENAI_MODEL
    
        api_key = os.getenv("OPEN_AI_API_KEY")       
        if not api_key:
            api_key = input("Enter your OpenAI API key: ").strip()
            if not api_key:
                print("OpenAI API key is required for the OpenAI provider.")
                sys.exit(1)
            os.environ["OPEN_AI_API_KEY"] = api_key
        
        model_to_use = model or DEFAULT_OPENAI_MODEL
        return OpenAIProvider(model=model_to_use)
    
    else:
        print(f"Invalid provider: {provider_name}. Please choose 'ollama' or 'openai'.")
        sys.exit(1)

def generate_commit_message(provider: Provider, staged_diff: str, oneline: bool = False) -> str:
    """Generate commit message with spinner."""
    stop_spinner = threading.Event()
    model_name = getattr(provider, 'model', 'AI')
    spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner, model_name))
    spinner_thread.start()

    try:
        suggested_message = provider.generate_commit_message(staged_diff, oneline=oneline)
        return clean_commit_message(suggested_message)
    finally:
        stop_spinner.set()
        spinner_thread.join()

def handle_user_choice(choice: str, message: str, provider: Provider, staged_diff: str, oneline: bool = False) -> Tuple[str, bool]:
    """Handle user input and return (new_message, should_continue)."""
    if choice == 'a':
        commit(message)
        return message, False
    elif choice == 'e':
        edited_message = edit_message(message)
        if edited_message:
            commit(edited_message)
            return edited_message, False
        return message, True
    elif choice == 'r':
        # Re-generate with same diff
        new_msg = generate_commit_message(provider, staged_diff, oneline=oneline)
        return new_msg, True
    elif choice == 'q':
        return message, False
    else:
        print("Invalid choice.")
        return message, True

def main():
    load_dotenv()

    # Check git repository
    if not is_git_repository():
        print("\033[31mError: Not a Git repository. Please initialize a Git repository or navigate to one.\033[0m")
        sys.exit(1)

    # Parse arguments
    parser = argparse.ArgumentParser(description="An AI-powered git commit message generator.")
    parser.add_argument("--provider", type=str, default=DEFAULT_PROVIDER,
                        help=f"The provider to use for generating commit messages. Can be 'ollama' or 'openai'. Default: {DEFAULT_PROVIDER}")
    parser.add_argument("model", nargs="?", help="The model to use for generating commit messages.")
    parser.add_argument("--oneline", action="store_true", help="Generate a single-line commit message.")
    args = parser.parse_args()

    # Get staged diff
    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    # Setup provider and generate initial message
    provider = setup_provider(args.provider, args.model)

    suggested_message = generate_commit_message(provider, staged_diff, oneline=args.oneline)

    # Main interaction loop
    while True:
        print("\n---")
        print("\u001b[1mSuggested Commit Message:\u001b[0m")
        print(suggested_message)
        print("---")

        choice = input(
            "\u001b[1m[A]\u001b[0mpply, \u001b[1m[E]\u001b[0mdit, \u001b[1m[R]\u001b[0m-generate, or \u001b[1m[Q]\u001b[0muit? (a/e/r/q) "
        ).lower()

        suggested_message, should_continue = handle_user_choice(choice, suggested_message, provider, staged_diff, oneline=args.oneline)
        if not should_continue:
            break

if __name__ == "__main__":
    main()