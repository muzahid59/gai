import subprocess
import os
import sys
import time
import re
from pathlib import Path
from typing import List, Optional

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

def spinner_animation(stop_event) -> None:
    """Displays a spinner animation."""
    spinner_chars = "|/-\\"
    while not stop_event.is_set():
        for char in spinner_chars:
            sys.stdout.write(f"\r\033[1;34m\u001b[0m Contacting provider to generate commit message... {char}")
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

def detect_credentials(diff_content: str) -> List[str]:
    """Detect potential credentials in the git diff and return a list of warnings."""
    warnings = []
    
    # Single pattern to detect common credential formats
    pattern = r'(?i)(password|pwd|secret|api_key|token|private_key)\s*=\s*["\']?[a-zA-Z0-9_/\-+=]{8,}["\']?'
    
    added_lines = [line[1:] for line in diff_content.split('\n') if line.startswith('+') and not line.startswith('+++')]
    
    for line in added_lines:
        if re.search(pattern, line):
            warnings.append(f"Potential credentials detected in line: {line.strip()}")
    
    return warnings

def prompt_credential_warning(warnings: List[str]) -> bool:
    """Display credential warnings and ask user if they want to continue."""
    print("\n\033[1;31m⚠️  SECURITY WARNING ⚠️\033[0m")
    print("\033[33mPotential credentials or sensitive information detected:\033[0m\n")
    
    for warning in warnings:
        print(f"  • {warning}")
    
    print("\n\033[1;33mThis could expose sensitive information in your commit history!\033[0m")
    
    while True:
        choice = input("\nDo you want to continue anyway? \033[1m[Y]\u001b[0mes/\033[1m[N]\u001b[0mo (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def save_provider_model_pair(provider: str, model: str) -> None:
    """Save the provider-model pair to the .env file."""
    env_file = Path(".env")
    
    env_content = ""
    if env_file.exists():
        with open(env_file, "r") as f:
            env_content = f.read()
    
    lines = env_content.split('\n')
    provider_updated = False
    model_updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('PROVIDER=') or line.startswith('#PROVIDER='):
            lines[i] = f"PROVIDER={provider}"
            provider_updated = True
        elif line.startswith('MODEL=') or line.startswith('#MODEL='):
            lines[i] = f"MODEL={model}"
            model_updated = True
    
    if not provider_updated:
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        lines.append(f"PROVIDER={provider}")
    
    if not model_updated:
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        lines.append(f"MODEL={model}")
    
    with open(env_file, "w") as f:
        f.write('\n'.join(lines))
    
    print(f"\033[32m✔ Provider '{provider}' with model '{model}' saved to .env file\033[0m")

def save_api_key_to_env(api_key: str) -> None:
    """Save the OpenAI API key to the .env file."""
    env_file = Path(".env")
    
    env_content = ""
    if env_file.exists():
        with open(env_file, "r") as f:
            env_content = f.read()
    
    lines = env_content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('API_KEY=') or line.startswith('#API_KEY='):
            lines[i] = f"API_KEY={api_key}"
            updated = True
            break
    
    if not updated:
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        lines.append(f"API_KEY={api_key}")
    
    with open(env_file, "w") as f:
        f.write('\n'.join(lines))
    
    print(f"\033[32m✔ API key saved to .env file\033[0m")
