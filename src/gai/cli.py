import subprocess
import requests
import argparse
import json
import sys
import os
from pathlib import Path

# --- Configuration ---
DEFAULT_MODEL = "llama3.2"
DEFAULT_PROVIDER = "ollama"
DEFAULT_ENDPOINT = "http://localhost:11434/api"

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

def generate_commit_message(diff, model, endpoint, provider, api_key):
    """Sends the diff to the LLM and returns the generated commit message."""
    prompt = (
        "Based on the following `git diff --staged` output, please generate a concise and meaningful commit message. "
        "The message MUST follow the Conventional Commits specification (e.g., 'feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:'). "
        "The subject line should be 50 characters or less. "
        "Follow the subject line with a blank line, then a more detailed body explaining the what and why of the changes. "
        "Do not include any other explanatory text, comments, or markdown formatting in your response. Just the raw commit message."
        f"\n\n---\n\n{diff}"
    )

    print(f"\u001b[1;34m\u001b[0m Contacting {provider} model '{model}' to generate commit message...")

    headers = {}
    json_payload = {}
    request_url = endpoint

    if provider == "ollama":
        json_payload = {"model": model, "prompt": prompt, "stream": False}
        request_url = f"{endpoint}/generate"
    elif provider == "openai":
        if not api_key:
            print("Error: API key is required for OpenAI provider.")
            sys.exit(1)
        headers = {"Authorization": f"Bearer {api_key}"}
        json_payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7
        }
        request_url = f"{endpoint}/v1/chat/completions"
    else:
        print(f"Error: Unsupported provider: {provider}")
        sys.exit(1)

    try:
        response = requests.post(
            request_url,
            headers=headers,
            json=json_payload,
            timeout=30
        )
        response.raise_for_status()

        if provider == "ollama":
            full_response = response.json()
            return full_response.get("response", "").strip()
        elif provider == "openai":
            full_response = response.json()
            return full_response["choices"][0]["message"]["content"].strip()

    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to LLM: {e}")
        if provider == "ollama":
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
    parser = argparse.ArgumentParser(
        description="An AI-powered git commit message generator."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("GAI_MODEL", DEFAULT_MODEL),
        help=f"The LLM model to use. Defaults to environment variable GAI_MODEL or '{DEFAULT_MODEL}'."
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=os.getenv("GAI_ENDPOINT", DEFAULT_ENDPOINT),
        help=f"The LLM API endpoint to use. Defaults to environment variable GAI_ENDPOINT or '{DEFAULT_ENDPOINT}'."
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["ollama", "openai"],
        default=os.getenv("GAI_PROVIDER", DEFAULT_PROVIDER),
        help=f"The LLM provider (e.g., 'ollama', 'openai'). Defaults to environment variable GAI_PROVIDER or '{DEFAULT_PROVIDER}'."
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("GAI_API_KEY"),
        help="The API key for the LLM provider. Defaults to environment variable GAI_API_KEY."
    )
    args = parser.parse_args()

    model_to_use = args.model
    endpoint_to_use = args.endpoint
    provider_to_use = args.provider
    api_key_to_use = args.api_key

    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    suggested_message = generate_commit_message(staged_diff, model_to_use, endpoint_to_use, provider_to_use, api_key_to_use)

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
