import subprocess
import requests
import argparse
import json
import sys
import os

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
        # This can happen if git diff returns a non-zero exit code for other reasons.
        print(f"Error getting git diff: {e.stderr}")
        sys.exit(1)

def generate_commit_message(diff, model):
    """Sends the diff to Ollama and returns the generated commit message."""
    if not diff:
        return "feat: initial commit"

    prompt = (
        "Based on the following `git diff --staged` output, please generate a concise and meaningful commit message. "
        "The message MUST follow the Conventional Commits specification (e.g., 'feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:'). "
        "The subject line should be 50 characters or less. "
        "Follow the subject line with a blank line, then a more detailed body explaining the what and why of the changes. "
        "Do not include any other explanatory text, comments, or markdown formatting in your response. Just the raw commit message."
        "\n\n---\n\n{diff}"
    ).format(diff=diff)

    print("\033[1;34mℹ\u001b[0m Contacting LLM to generate commit message...")

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30
        )
        response.raise_for_status()
        
        # We are not streaming here, so we parse the final response.
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
        with open(".git/COMMIT_EDITMSG", "w") as f:
            f.write(message)
        
        subprocess.run([editor, ".git/COMMIT_EDITMSG"], check=True)

        with open(".git/COMMIT_EDITMSG", "r") as f:
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
        default="gemma:2b",
        help="The Ollama model to use (e.g., 'llama3', 'gemma:2b')."
    )
    args = parser.parse_args()

    staged_diff = get_staged_diff()
    if not staged_diff:
        print("No staged changes found. Please stage your changes with 'git add' first.")
        sys.exit(0)

    suggested_message = generate_commit_message(staged_diff, args.model)

    while True:
        print("\n---")
        print("\033[1mSuggested Commit Message:\033[0m")
        print(suggested_message)
        print("---")

        choice = input(
            "\033[1m[A]\u001b[0mpply, \033[1m[E]\u001b[0mdit, or \033[1m[R]\u001b[0m-generate? (a/e/r/q to quit) "
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
            suggested_message = generate_commit_message(staged_diff, args.model)
        elif choice == 'q':
            print("Commit aborted.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
