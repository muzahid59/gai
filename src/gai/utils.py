import subprocess
import os
import sys
import time
import re
from pathlib import Path
from typing import Optional

def is_git_repository() -> bool:
    """Checks if the current directory or any parent directory is a Git repository."""
    try:
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
        return False

def get_staged_diff() -> str:
    """Runs 'git diff --staged --minimal --unified=5' and returns the filtered output."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--minimal", "--unified=5"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Filter out metadata lines using the same logic as the grep command
        lines = result.stdout.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that match the grep -vE pattern (invert match for these patterns)
            if (line.startswith('index ') or 
                line.startswith('@@') or 
                line.startswith('diff --git')):
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
        
    except FileNotFoundError:
        print("\033[31mError: 'git' command not found.\033[0m\n"
              "Please ensure Git is installed and accessible in your system's PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stdout and not e.stderr:
            return ""
        print(f"""\u001b[31mError getting git diff:\u001b[0m {e.stderr.strip()}
              Please ensure you have staged changes (e.g., using 'git add .') and Git is configured correctly.""")
        sys.exit(1)

def commit(message: str) -> None:
    """Performs the git commit with the given message."""
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
        print("\033[32m✔ Commit successful!\033[0m")
    except subprocess.CalledProcessError as e:
        print(f"Error during commit: {e.stderr}")
        sys.exit(1)

def edit_message(message: str) -> Optional[str]:
    """Opens the default editor to edit the message."""
    editor = os.getenv("EDITOR", "vim")
    try:
        commit_msg_file = Path(subprocess.check_output(["git", "rev-parse", "--git-dir"]).strip().decode()) / "COMMIT_EDITMSG"
        with open(commit_msg_file, "w") as f:
            f.write(message)
        
        subprocess.run([editor, str(commit_msg_file)], check=True)

        with open(commit_msg_file, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error opening editor: {e}")
        return None

def spinner_animation(stop_event, model_name: str = "AI") -> None:
    """Displays a spinner animation."""
    spinner_chars = "|/-\\"
    while not stop_event.is_set():
        for char in spinner_chars:
            sys.stdout.write(f"\rGenerating commit by {model_name} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

def clean_commit_message(message: str) -> str:
    """Remove <think></think> tags and any content within them from the commit message."""
    cleaned = re.sub(r'<think>.*?</think>', '', message, flags=re.DOTALL)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    cleaned = cleaned.strip()
    return cleaned
