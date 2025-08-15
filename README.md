# gai-commit

AI-powered CLI tool to generate commit messages from your staged Git changes. Works with both local Ollama models and OpenAI's API.

## Installation

```bash
pip install gai-commit
```

## Usage Options

### 1. Using Ollama (Local LLMs)

Ollama provides free, locally-running AI models with no API keys required.

**Prerequisites:**
```bash
# 1. Install Ollama (https://ollama.com)
# 2. Pull a model (only needed once):
ollama pull llama3.2
# Ollama daemon should start automatically after installation
```

**Basic Usage:**
```bash
# Stage your changes first
git add path/to/modified/files

# Generate commit message with default model
gai

# Or specify a different Ollama model
gai deepseek-r1:8b
```

### 2. Using OpenAI (Cloud-based LLMs)

For higher quality results, you can use OpenAI's models (requires API key).

**Prerequisites:**
```bash
# Set your OpenAI API key (or add to .env file)
export OPENAI_API_KEY=sk-your-key
```

**Basic Usage:**
```bash
# Stage your changes first
git add path/to/modified/files

# Generate commit message with default model (gpt-3.5-turbo)
gai --provider openai

# Or specify a different OpenAI model
gai --provider openai gpt-4o
```

### Additional Options

```bash
# Generate a concise one-line commit message (subject only)
gai --oneline

# Combine with provider selection
gai --provider openai --oneline
```

## How It Works

1. **Repository Check**: Verifies you're in a git repository via [`gai.utils.is_git_repository`](src/gai/utils.py)
2. **Diff Collection**: Gets staged changes with `git diff --staged --minimal --unified=5` using [`gai.utils.get_staged_diff`](src/gai/utils.py)
3. **AI Processing**: Sends the cleaned diff to the selected AI provider through [`gai.cli.generate_commit_message`](src/gai/cli.py)
4. **Output Cleaning**: Formats the AI output and removes technical artifacts via [`gai.utils.clean_commit_message`](src/gai/utils.py)
5. **Interactive Workflow**: Presents options to apply, edit, regenerate or quit via [`gai.cli.handle_user_choice`](src/gai/cli.py)
6. **Commit**: Applies your approved message with `git commit`

## Interactive Workflow

After generating a commit message suggestion, you'll see:

```
Suggested Commit Message:
feat(parser): improve error resilience

- add fallback recovery for malformed input
- reduce panic cases in edge parsing paths
---
[A]pply, [E]dit, [R]-generate, or [Q]uit? (a/e/r/q)
```

Your options:
- **A**: Apply immediately (`git commit -m "<message>"`)
- **E**: Open your `$EDITOR` (defaults to `vim`) to refine the message
- **R**: Ask the AI to generate a new suggestion using the same diff
- **Q**: Quit without committing

## Troubleshooting

### Common Issues

- **"No staged changes found"**: Use `git add` to stage your changes first
- **"Not a Git repository"**: Make sure you're inside a valid git repository
- **"OPENAI_API_KEY environment variable not set"**: Set your OpenAI API key or use Ollama
- **"Ollama connection refused"**: Make sure the Ollama daemon is running (`ollama serve`)

## Development

```bash
# Clone the repository
git clone https://github.com/muzahid59/gai
cd gai

# Install in development mode
pip install -e .

# Run tests
pytest tests -v
```

## Benchmarking

Compare different models' performance:

```bash
# Make sure to stage some changes first
python run_benchmark.py
```

## License

MIT - see [LICENSE](LICENSE)
