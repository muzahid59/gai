import argparse
import sys
import os
import threading
from dotenv import load_dotenv

from gai.provider import Provider
from gai.ollama_client import OllamaProvider
from gai.openai_client import OpenAIProvider
from gai.utils import (
    is_git_repository,
    get_staged_diff,
    commit,
    edit_message,
    spinner_animation,
    clean_commit_message,
    detect_credentials,
    prompt_credential_warning,
    save_provider_model_pair,
    save_api_key_to_env
)

# Configuration
DEFAULT_MODEL = "llama3.2"
DEFAULT_ENDPOINT = "http://localhost:11434/api"
DEFAULT_PROVIDER = "ollama"

def setup_provider(provider_name: str, model: str) -> Provider:
    """Setup and return the appropriate provider."""
    if provider_name == "ollama":
        if model:
            save_provider_model_pair(provider_name, model)
            model_to_use = model
        else:
            model_to_use = DEFAULT_MODEL
            save_provider_model_pair(provider_name, model_to_use)
        
        endpoint_to_use = os.getenv("CHAT_URL")
        if not endpoint_to_use:
            endpoint_to_use = input(f"Enter LLM API endpoint (default: {DEFAULT_ENDPOINT}): ") or DEFAULT_ENDPOINT
        
        return OllamaProvider(model=model_to_use, endpoint=endpoint_to_use)
    
    elif provider_name == "openai":
        from gai.openai_client import DEFAULT_OPENAI_MODEL
        
        api_key = os.getenv("API_KEY")
        if not api_key:
            api_key = input("Enter your OpenAI API key: ").strip()
            if not api_key:
                print("OpenAI API key is required for the OpenAI provider.")
                sys.exit(1)
            save_api_key_to_env(api_key)
            os.environ["API_KEY"] = api_key
        
        if model:
            save_provider_model_pair(provider_name, model)
            model_to_use = model
        else:
            model_to_use = DEFAULT_OPENAI_MODEL
            save_provider_model_pair(provider_name, model_to_use)
        
        return OpenAIProvider(model=model_to_use)
    
    else:
        print(f"Invalid provider: {provider_name}. Please choose 'ollama' or 'openai'.")
        sys.exit(1)

def generate_commit_message(provider: Provider, staged_diff: str, oneline: bool = False) -> str:
    """Generate commit message with spinner."""
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner,))
    spinner_thread.start()

    try:
        suggested_message = provider.generate_commit_message(staged_diff, oneline=oneline)
        return clean_commit_message(suggested_message)
    finally:
        stop_spinner.set()
        spinner_thread.join()

def handle_user_choice(choice: str, message: str, provider: Provider, staged_diff: str) -> tuple[str, bool]:
    """Handle user input and return (new_message, should_continue)."""
    if choice == 'a':
        commit(message)
        return message, False
    elif choice == 'e':
        edited_message = edit_message(message)
        if edited_message:
            commit(edited_message)
            return edited_message, False
    elif choice == 'r':
        return generate_commit_message(provider, staged_diff), True
    elif choice == 'q':
        print("Commit aborted.")
        return message, False
    else:
        print("Invalid choice. Please try again.")
        return message, True

def main():
    load_dotenv()

    # Check git repository
    if not is_git_repository():
        print("\033[31mError: Not a Git repository. Please initialize a Git repository or navigate to one.\033[0m")
        sys.exit(1)

    # Parse arguments
    parser = argparse.ArgumentParser(description="An AI-powered git commit message generator.")
    parser.add_argument("--provider", type=str, default=os.getenv("PROVIDER", DEFAULT_PROVIDER),
                        help=f"The provider to use for generating commit messages. Can be 'ollama' or 'openai'. Default: {DEFAULT_PROVIDER}")
    parser.add_argument("model", nargs="?", help="The model to use for generating commit messages.")
    parser.add_argument("--multi-commit", action="store_true", help="Enable multi-commit summarization workflow.")
    parser.add_argument("--oneline", action="store_true", help="Generate a single-line commit message.")
    args = parser.parse_args()

    # Get staged diff
    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    # Security check
    credential_warnings = detect_credentials(staged_diff)
    if credential_warnings:
        if not prompt_credential_warning(credential_warnings):
            print("Commit aborted for security reasons.")
            sys.exit(0)

    # Setup provider and generate initial message
    provider = setup_provider(args.provider, args.model)

    if args.multi_commit:
        run_multi_commit_workflow(provider, staged_diff)
    else:
        suggested_message = generate_commit_message(provider, staged_diff, oneline=args.oneline)

        # Main interaction loop
        while True:
            print("\n---")
            print("\033[1mSuggested Commit Message:\033[0m")
            print(suggested_message)
            print("---")

            choice = input(
                "\033[1m[A]\u001b[0mpply, \033[1m[E]\u001b[0mdit, \033[1m[R]\u001b[0m-generate, or \033[1m[Q]\u001b[0muit? (a/e/r/q) "
            ).lower()

            suggested_message, should_continue = handle_user_choice(choice, suggested_message, provider, staged_diff)
            if not should_continue:
                break

def run_multi_commit_workflow(provider: Provider, staged_diff: str):
    print("\nAnalyzing diff for potential commit splits...")
    suggested_commits = provider.analyze_diff_for_commits(staged_diff)

    if not suggested_commits:
        print("No logical commit splits found. Falling back to single commit message generation.")
        suggested_message = generate_commit_message(provider, staged_diff)
        # Main interaction loop for single commit
        while True:
            print("\n---")
            print("\u001b[1mSuggested Commit Message:\u001b[0m")
            print(suggested_message)
            print("---")

            choice = input(
                "\u001b[1m[A]\u001b[0mpply, \u001b[1m[E]\u001b[0mdit, \u001b[1m[R]\u001b[0m-generate, or \u001b[1m[Q]\u001b[0muit? (a/e/r/q) "
            ).lower()

            suggested_message, should_continue = handle_user_choice(choice, suggested_message, provider, staged_diff)
            if not should_continue:
                break
        return

    print("\n--- Suggested Commit Splits ---")
    for i, commit_data in enumerate(suggested_commits):
        print(f"{i + 1}. {commit_data['description']}")
    print("-----------------------------")

    while True:
        choice = input(
            "\u001b[1m[S]\u001b[0mplit into multiple commits, \u001b[1m[U]\u001b[0msummarize into one, or \u001b[1m[Q]\u001b[0muit? (s/u/q) "
        ).lower()

        if choice == 's':
            handle_split_commits(suggested_commits, provider, staged_diff)
            break
        elif choice == 'u':
            handle_summarize_commit(provider, staged_diff)
            break
        elif choice == 'q':
            print("Commit aborted.")
            break
        else:
            print("Invalid choice. Please try again.")

def handle_split_commits(suggested_commits: list[dict], provider: Provider, full_staged_diff: str):
    print("\n--- Splitting into Multiple Commits ---")
    for i, commit_data in enumerate(suggested_commits):
        print(f"Generating message for commit {i + 1}: {commit_data['description']}")
        # For now, we'll generate a message based on the description and full diff
        # In a more advanced version, we'd try to isolate the diff for this specific commit
        prompt_for_llm = f"Generate a commit message for the following change: {commit_data['description']}\n\nGIT DIFF:\n{full_staged_diff}"
        
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner,))
        spinner_thread.start()
        try:
            # Temporarily override generate_commit_message to use the specific prompt
            original_generate_commit_message = provider.generate_commit_message
            provider.generate_commit_message = lambda diff: original_generate_commit_message(prompt_for_llm)
            suggested_message = generate_commit_message(provider, full_staged_diff)
            provider.generate_commit_message = original_generate_commit_message # Restore original
        finally:
            stop_spinner.set()
            spinner_thread.join()

        print(f"\nSuggested message for commit {i + 1}:\n{suggested_message}")
        print("\nIMPORTANT: Please manually stage the files relevant to this change before proceeding.")
        input("Press Enter to commit this change (or Ctrl+C to abort this specific commit)...")
        commit(suggested_message)
        print(f"Commit {i + 1} applied.")

def handle_summarize_commit(provider: Provider, full_staged_diff: str):
    print("\n--- Summarizing into One Commit ---")
    suggested_message = generate_commit_message(provider, full_staged_diff)
    # Main interaction loop for single commit
    while True:
        print("\n---")
        print("\u001b[1mSuggested Commit Message:\u001b[0m")
        print(suggested_message)
        print("---")

        choice = input(
            "\u001b[1m[A]\u001b[0mpply, \u001b[1m[E]\u001b[0mdit, \u001b[1m[R]\u001b[0m-generate, or \u001b[1m[Q]\u001b[0muit? (a/e/r/q) "
        ).lower()

        suggested_message, should_continue = handle_user_choice(choice, suggested_message, provider, full_staged_diff)
        if not should_continue:
            break

if __name__ == "__main__":
    main()