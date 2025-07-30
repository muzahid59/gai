import subprocess
import requests
import argparse
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import threading

# --- Configuration ---
DEFAULT_MODEL = "llama3.2"
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
        print("\033[31mError: 'git' command not found.\033[0m\n" \
              "Please ensure Git is installed and accessible in your system's PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stdout and not e.stderr:
            # This can be normal if there are no staged changes but it's not an error
            return ""
        print(f"\033[31mError getting git diff:\033[0m {e.stderr.strip()}\n" \
              "Please ensure you have staged changes (e.g., using 'git add .') and Git is configured correctly.")
        sys.exit(1)

def generate_commit_message(diff, model, endpoint):
    """Sends the diff to the LLM and returns the generated commit message."""
    system_prompt=(
        "You are the best git assistant whose aim is to generate a git commit message."
        "IT MUST BE written in English, be concise, be lowercase, relevant and straight to the point."
        "IT MUST FOLLOW conventional commits specifications and the following template:"
        "<type>[optional scope]: <short description>"
       
        "[optional body]"
        
        "Where <type> MUST BE ONE OF: fix, feat, build, chore, ci, docs, style, refactor, perf, test"
        "Where <type> MUST NOT BE: add, update, delete etc."
        "A commit that has a footer BREAKING CHANGE:, or appends a ! after the type, introduces a breaking API change."
        "DO NOT ADD UNDER ANY CIRCUMSTANCES: explanation about the commit, details such as file, changes, hash or the conventional commits specs."
        "Here is the git diff:"
    )
    
    # system_prompt = (
    #     "You are an expert programmer tasked with writing a Git commit message. "
    #     "Based on the following `git diff --staged` output, generate a commit message that follows the Conventional Commits specification. "
    #     "The commit message must have a subject line of 50 characters or less, followed by a blank line, and then a more detailed explanatory body. "
    #     "Do not include any introductory phrases, comments, or markdown formatting like ```. Your entire response should be only the raw commit message text."
    #     "\n\nHere is an example of the desired format:\n"
    #     "feat: add user authentication\n\n"
    #     "Implement JWT-based authentication for the API.\n"
    #     "Add login and registration endpoints.\n"
    #     "Protect sensitive routes with an authentication middleware."
    # )
    user_prompt = f"---\n\nGIT DIFF:\n{diff}"

    json_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False
    }
    request_url = f"{endpoint}/chat"

    try:
        response = requests.post(
            request_url,
            json=json_payload,
            timeout=60
        )
        response.raise_for_status()

        full_response = response.json()
        
        if "message" in full_response and "content" in full_response["message"]:
            return full_response["message"]["content"].strip()
        else:
            print(f"\n\033[31mError: Unexpected response format from Ollama.\033[0m")
            print(f"Response: {full_response}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"\n\033[31mError connecting to Ollama:\033[0m {e}\n" \
              f"Please ensure the Ollama server is running and accessible at {endpoint}.")
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
            sys.stdout.write(f"\r\033[1;34m\u001b[0m Contacting ollama model to generate commit message... {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write("\r" + " " * 80 + "\r") # Clear the line
    sys.stdout.flush()

def main():
    load_dotenv() # Load environment variables from .env file

    model_to_use = os.getenv("MODEL")
    endpoint_to_use = os.getenv("CHAT_URL")

    if not model_to_use:
        model_to_use = input(f"Enter LLM model (default: {DEFAULT_MODEL}): ") or DEFAULT_MODEL
    if not endpoint_to_use:
        endpoint_to_use = input(f"Enter LLM API endpoint (default: {DEFAULT_ENDPOINT}): ") or DEFAULT_ENDPOINT

    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=spinner_animation, args=(stop_spinner,))
    spinner_thread.start()

    try:
        suggested_message = generate_commit_message(staged_diff, model_to_use, endpoint_to_use)
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
                suggested_message = generate_commit_message(staged_diff, model_to_use, endpoint_to_use)
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
