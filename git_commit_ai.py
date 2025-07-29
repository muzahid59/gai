import subprocess
import requests
import argparse
import json
import sys
import os
from pathlib import Path

# --- Configuration ---
CONFIG_DIR = Path.home() / ".own-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_MODEL = "llama3.2"

def get_config():
    """Reads the config file and returns the configuration."""
    if not CONFIG_FILE.is_file():
        return {"model": DEFAULT_MODEL}
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "model" not in config:
                config["model"] = DEFAULT_MODEL
            return config
    except (json.JSONDecodeError, IOError):
        return {"model": DEFAULT_MODEL}

def set_model_in_config(model_name):
    """Saves the selected model to the config file."""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"model": model_name}, f, indent=4)
        print(f"\033[32m✔ Default model saved to {CONFIG_FILE}\033[0m")
    except IOError as e:
        print(f"Error saving configuration: {e}")
        sys.exit(1)

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
        print("Error: 'git' command not found. Is Git installed and in your PATH?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stdout and not e.stderr:
            # This can be normal if there are no staged changes but it's not an error
            return ""
        print(f"Error getting git diff: {e.stderr}")
        sys.exit(1)

def generate_commit_message(diff, model):
    """Sends the diff to Ollama and returns the generated commit message."""
    prompt = (
        "Based on the following `git diff --staged` output, please generate a concise and meaningful commit message. "
        "The message MUST follow the Conventional Commits specification (e.g., 'feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:'). "
        "The subject line should be 50 characters or less. "
        "Follow the subject line with a blank line, then a more detailed body explaining the what and why of the changes. "
        "Do not include any other explanatory text, comments, or markdown formatting in your response. Just the raw commit message."
        f"\n\n---\n\n{diff}"
    )

    print(f"\033[1;34mℹ\033[0m Contacting model '{model}' to generate commit message...")

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30
        )
        response.raise_for_status()
        full_response = response.json()
        return full_response.get("response", "").strip()

    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to Ollama: {e}")
        print("Please ensure the Ollama server is running.")
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

def main():
    config = get_config()
    
    parser = argparse.ArgumentParser(
        description="An AI-powered git commit message generator."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=config.get("model", DEFAULT_MODEL),
        help=f"The Ollama model to use. Overrides the model in {CONFIG_FILE}. Defaults to '{config.get('model', DEFAULT_MODEL)}'."
    )
    parser.add_argument(
        "--set-model",
        type=str,
        metavar='MODEL_NAME',
        help="Set and save the default Ollama model in the config file (e.g., 'llama3')."
    )
    args = parser.parse_args()

    if args.set_model:
        set_model_in_config(args.set_model)
        sys.exit(0)

    model_to_use = args.model

    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    suggested_message = generate_commit_message(staged_diff, model_to_use)

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
            suggested_message = generate_commit_message(staged_diff, model_to_use)
        elif choice == 'q':
            print("Commit aborted.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
