# gai-commit

AI-powered generator for high‑quality Conventional Commit messages from your staged diff.

## Quick Start

### Install
```bash
pip install gai-commit
```

### 1. Using Ollama
Prerequisites:
```bash
# Install Ollama (see https://ollama.com)
# Pull at least one model (only needed once):
ollama pull llama3.2
# Ensure the Ollama daemon is running (starts automatically after install)
```
Usage:
```bash
git add path/to/file.py
gai                 # uses default local model (e.g. llama3.2)
gai deepseek-r1:8b  # specify another pulled model
```

### 2. Using OpenAI
```bash
export OPEN_AI_API_KEY=sk-your-key
git add path/to/file.py
gai --provider openai            # default OpenAI model (gpt-3.5-turbo)
gai --provider openai gpt-5      # specify model
```

### Optional
```bash
# One-line (subject only)
gai --oneline
```

## What It Does

1. Verifies you are inside a git repository via [`gai.utils.is_git_repository`](src/gai/utils.py).
2. Collects staged changes (`git diff --staged --minimal --unified=5`) and strips noise using [`gai.utils.get_staged_diff`](src/gai/utils.py).
3. Sends the cleaned diff to the selected provider through [`gai.cli.generate_commit_message`](src/gai/cli.py).
4. Cleans AI output (removes hidden <think> blocks) via [`gai.utils.clean_commit_message`](src/gai/utils.py).
5. Interactive loop (Apply / Edit / Re‑generate / Quit) handled by [`gai.cli.handle_user_choice`](src/gai/cli.py).
6. Commits with your approved message.

## Interactive Flow

After generating a suggestion:

```
Suggested Commit Message:
feat(parser): improve error resilience

- add fallback recovery for malformed input
- reduce panic cases in edge parsing paths
---
[A]pply, [E]dit, [R]-generate, or [Q]uit? (a/e/r/q)
```

Options:
- a: Commit immediately (`git commit -m "<message>"`)
- e: Open `$EDITOR` (defaults to `vim`) to refine
- r: Ask AI again (same diff)
- q: Abort

## One-Line Mode

Use `--oneline` to force a single concise subject line (no body). Logic passes `oneline=True` into provider calls: [`gai.cli.generate_commit_message`](src/gai/cli.py).

## Development

```bash
git clone https://github.com/muzahid59/gai
cd gai
pip install -e .
pytest tests -v
```

## License

MIT - see [LICENSE](LICENSE)
