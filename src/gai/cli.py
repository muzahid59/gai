import subprocess
import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import threading
from gai.provider import Provider
from gai.ollama_client import OllamaProvider
from gai.openai_client import OpenAIProvider

# --- Configuration ---
DEFAULT_MODEL = "llama3.2"
DEFAULT_ENDPOINT = "http://localhost:11434/api"
DEFAULT_PROVIDER = "ollama"

def is_git_repository():
    """Checks if the current directory or any parent directory is a Git repository."""
    try:
        # This command will succeed if in a git repo, fail otherwise
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        # Git command not found, assume not a git repository for this check
        return False

def get_staged_diff():
    """Runs 'git diff --staged' and returns the output."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except FileNotFoundError:
        print("\033[31mError: 'git' command not found.\033[0m\n"
              "Please ensure Git is installed and accessible in your system's PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stdout and not e.stderr:
            # This can be normal if there are no staged changes but it's not an error
            return ""
        print(f"""\u001b[31mError getting git diff:\u001b[0m {e.stderr.strip()}
              Please ensure you have staged changes (e.g., using 'git add .') and Git is configured correctly.""")
        sys.exit(1)

def commit(message):
    """Performs the git commit with the given message."""
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
        print("\033[32m✔ Commit successful!\033[0m")
    except subprocess.CalledProcessError as e:
        print(f"Error during commit: {e.stderr}")
        sys.exit(1)

def edit_message(message):
    """Opens the default editor to edit the message."""
    editor = os.getenv("EDITOR", "vim")
    try:
        # Use a temporary file in the .git directory for the message
        commit_msg_file = Path(subprocess.check_output(["git", "rev-parse", "--git-dir"]).strip().decode()) / "COMMIT_EDITMSG"
        with open(commit_msg_file, "w") as f:
            f.write(message)
        
        subprocess.run([editor, str(commit_msg_file)], check=True)

        with open(commit_msg_file, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error opening editor: {e}")
        return None

def spinner_animation(stop_event):
    """Displays a spinner animation."""
    spinner_chars = "|/-\\"
    while not stop_event.is_set():
        for char in spinner_chars:
            sys.stdout.write(f"\r\033[1;34m\u001b[0m Contacting provider to generate commit message... {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write("\r" + " " * 80 + "\r") # Clear the line
    sys.stdout.flush()

def clean_commit_message(message):
    """Remove <think></think> tags and any content within them from the commit message."""
    import re
    # Remove <think>...</think> blocks (including multiline)
    cleaned = re.sub(r'<think>.*?</think>', '', message, flags=re.DOTALL)
    # Clean up excessive whitespace only around where think tags were removed
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Replace 3+ newlines with 2
    cleaned = cleaned.strip()
    return cleaned

def save_model_to_env(model):
    """Save the Ollama model to the .env file."""
    env_file = Path(".env")
    
    # Read existing .env content
    env_content = ""
    if env_file.exists():
        with open(env_file, "r") as f:
            env_content = f.read()
    
    # Check if MODEL already exists
    lines = env_content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('MODEL=') or line.startswith('#MODEL='):
            lines[i] = f"MODEL={model}"
            updated = True
            break
    
    # If not found, add it
    if not updated:
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        lines.append(f"MODEL={model}")
    
    # Write back to .env file
    with open(env_file, "w") as f:
        f.write('\n'.join(lines))
    
    print(f"\033[32m✔ Model '{model}' saved to .env file\033[0m")

def save_api_key_to_env(api_key):
    """Save the OpenAI API key to the .env file."""
    env_file = Path(".env")
    
    # Read existing .env content
    env_content = ""
    if env_file.exists():
        with open(env_file, "r") as f:
            env_content = f.read()
    
    # Check if API_KEY already exists
    lines = env_content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('API_KEY=') or line.startswith('#API_KEY='):
            lines[i] = f"API_KEY={api_key}"
            updated = True
            break
    
    # If not found, add it
    if not updated:
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        lines.append(f"API_KEY={api_key}")
    
    # Write back to .env file
    with open(env_file, "w") as f:
        f.write('\n'.join(lines))
    
    print(f"\033[32m✔ API key saved to .env file\033[0m")

def main():
    load_dotenv()

    if not is_git_repository():
        print("\033[31mError: Not a Git repository. Please initialize a Git repository or navigate to one.\033[0m")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="An AI-powered git commit message generator.")
    parser.add_argument("--provider", type=str, default=os.getenv("PROVIDER", DEFAULT_PROVIDER),
                        help=f"The provider to use for generating commit messages. Can be 'ollama' or 'openai'. Default: {DEFAULT_PROVIDER}")
    parser.add_argument("model", nargs="?", help="The model to use for generating commit messages.")
    args = parser.parse_args()

    provider_name = args.provider
    provider: Provider

    if provider_name == "ollama":
        # Always ask for model, but show the saved one as default
        saved_model = os.getenv("MODEL") if not args.model else None
        default_model = saved_model or DEFAULT_MODEL
        
        if args.model:
            # Model provided as command line argument
            model_to_use = args.model
        else:
            # Always prompt for model, showing saved one as default
            model_to_use = input(f"Enter LLM model (default: {default_model}): ") or default_model
            # Save the chosen model for future use
            save_model_to_env(model_to_use)
        
        endpoint_to_use = os.getenv("CHAT_URL")
        if not endpoint_to_use:
            endpoint_to_use = input(f"Enter LLM API endpoint (default: {DEFAULT_ENDPOINT}): ") or DEFAULT_ENDPOINT
        provider = OllamaProvider(model=model_to_use, endpoint=endpoint_to_use)
    elif provider_name == "openai":
        api_key = os.getenv("API_KEY")
        if not api_key:
            api_key = input("Enter your OpenAI API key: ").strip()
            if not api_key:
                print("OpenAI API key is required for the OpenAI provider.")
                sys.exit(1)
            # Save the API key to .env file for future use
            save_api_key_to_env(api_key)
            # Set the environment variable for this session
            os.environ["API_KEY"] = api_key
        provider = OpenAIProvider(model=args.model)
    else:
        print(f"Invalid provider: {provider_name}. Please choose 'ollama' or 'openai'.")
        sys.exit(1)

    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner,))
    spinner_thread.start()

    try:
        suggested_message = provider.generate_commit_message(staged_diff)
        # Clean up any <think></think> tags from the message
        suggested_message = clean_commit_message(suggested_message)
    finally:
        stop_spinner.set()
        spinner_thread.join()

    while True:
        print("\n---")
        print("\033[1mSuggested Commit Message:\033[0m")
        print(suggested_message)
        print("---")

        choice = input(
            "\033[1m[A]\u001b[0mpply, \033[1m[E]\u001b[0mdit, \033[1m[R]\u001b[0m-generate, or \033[1m[Q]\u001b[0muit? (a/e/r/q) "
        ).lower()

        if choice == 'a':
            commit(suggested_message)
            break
        elif choice == 'e':
            edited_message = edit_message(suggested_message)
            if edited_message:
                commit(edited_message)
                break
        elif choice == 'r':
            stop_spinner = threading.Event()
            spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner,))
            spinner_thread.start()
            try:
                suggested_message = provider.generate_commit_message(staged_diff)
                # Clean up any <think></think> tags from the message
                suggested_message = clean_commit_message(suggested_message)
            finally:
                stop_spinner.set()
                spinner_thread.join()
        elif choice == 'q':
            print("Commit aborted.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()