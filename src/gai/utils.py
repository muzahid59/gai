import subprocess
import os
import sys
import time
import re
from pathlib import Path
from typing import Optional, List


def is_git_repository() -> bool:
    """Checks if the current directory or any parent directory is a Git repository."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=True,
            text=True,
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
            check=True,
        )

        # Filter out metadata lines using the same logic as the grep command
        lines = result.stdout.split("\n")
        filtered_lines = []

        for line in lines:
            # Skip lines that match the grep -vE pattern (invert match for these patterns)
            if (
                line.startswith("index ")
                or line.startswith("@@")
                or line.startswith("diff --git")
            ):
                continue
            filtered_lines.append(line)

        return "\n".join(filtered_lines)

    except FileNotFoundError:
        print(
            "\033[31mError: 'git' command not found.\033[0m\n"
            "Please ensure Git is installed and accessible in your system's PATH."
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stdout and not e.stderr:
            return ""
        print(
            f"""\u001b[31mError getting git diff:\u001b[0m {e.stderr.strip()}
              Please ensure you have staged changes (e.g., using 'git add .') and Git is configured correctly."""
        )
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
        commit_msg_file = (
            Path(
                subprocess.check_output(["git", "rev-parse", "--git-dir"])
                .strip()
                .decode()
            )
            / "COMMIT_EDITMSG"
        )
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
            sys.stdout.write(f"\rGenerating commit message by {model_name} {char}")
            sys.stdout.flush()
            time.sleep(0.1)
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


def clean_commit_message(message: str) -> str:
    """Remove <think></think> tags and any content within them from the commit message."""
    if message is None:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", message, flags=re.DOTALL)
    cleaned = re.sub(r"\n\s*\n\s*\n", "\n\n", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters for most models)."""
    return len(text) // 4


def split_diff_by_files(diff: str, max_tokens_per_chunk: int = 1000) -> List[str]:
    """Split diff by files, respecting token limits."""
    lines = diff.split('\n')
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    file_header_pattern = r'^[+-]{3} [ab]/'
    
    for line in lines:
        line_tokens = estimate_tokens(line)
        
        # If this is a new file header and we have content, start new chunk
        if re.match(file_header_pattern, line) and current_chunk:
            if current_tokens + line_tokens > max_tokens_per_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_tokens = line_tokens
                continue
        
        # Add line to current chunk
        current_chunk.append(line)
        current_tokens += line_tokens
        
        # If chunk is too large, split it
        if current_tokens > max_tokens_per_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_tokens = 0
    
    # Add remaining chunk
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return [chunk for chunk in chunks if chunk.strip()]


def aggregate_commit_messages(messages: List[str], oneline: bool = False) -> str:
    """Aggregate multiple commit messages into a coherent single message."""
    if not messages:
        return ""
    
    if len(messages) == 1:
        return messages[0]
    
    # Extract types and scopes
    commit_types = []
    scopes = set()
    descriptions = []
    body_points = []
    
    conventional_pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(?:\(([^)]+)\))?: (.+)$'
    
    for msg in messages:
        lines = msg.strip().split('\n')
        first_line = lines[0] if lines else ""
        
        match = re.match(conventional_pattern, first_line)
        if match:
            commit_type, scope, desc = match.groups()
            commit_types.append(commit_type)
            if scope:
                scopes.add(scope)
            descriptions.append(desc)
            
            # Extract body points
            if len(lines) > 2:  # Skip empty line after subject
                body_points.extend([line.strip() for line in lines[2:] if line.strip().startswith('-')])
        else:
            # Fallback for non-conventional commits
            descriptions.append(first_line)
            if len(lines) > 1:
                body_points.extend([line.strip() for line in lines[1:] if line.strip()])
    
    # Determine primary type (most common, with priority order for ties)
    if commit_types:
        type_counts = {}
        for t in commit_types:
            type_counts[t] = type_counts.get(t, 0) + 1
        
        # Priority order for conventional commits
        priority_order = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore"]
        
        max_count = max(type_counts.values())
        candidates = [t for t, count in type_counts.items() if count == max_count]
        
        # Pick the highest priority type among candidates
        for priority_type in priority_order:
            if priority_type in candidates:
                primary_type = priority_type
                break
        else:
            primary_type = candidates[0]  # Fallback
    else:
        primary_type = "feat"
    
    # Create scope string
    scope_str = f"({','.join(sorted(scopes))})" if scopes else ""
    
    # Create aggregated description
    if len(set(descriptions)) == 1:
        # All descriptions are the same
        agg_description = descriptions[0]
    else:
        # Multiple different changes
        if len(commit_types) > 1 and len(set(commit_types)) > 1:
            agg_description = "multiple improvements and fixes"
        else:
            # Take the most descriptive one or combine
            agg_description = max(descriptions, key=len)[:40] + "..."
    
    # Build final message
    subject = f"{primary_type}{scope_str}: {agg_description}"
    
    if oneline:
        return subject
    
    # Add body with unique points
    unique_points = list(dict.fromkeys(body_points))  # Preserve order, remove duplicates
    if unique_points:
        body = '\n'.join(f"- {point.lstrip('- ')}" for point in unique_points[:5])  # Limit to 5 points
        return f"{subject}\n\n{body}"
    
    return subject
