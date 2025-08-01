# `gai` - AI-Powered Git Assistant

`gai` is a command-line tool that uses Large Language Models to generate meaningful, well-formatted git commit messages following the Conventional Commits specification.

## Features

- **AI-Generated Commit Messages:** Automatically generates commit messages based on your staged changes
- **Conventional Commits:** Enforces clean and readable git history
- **Interactive Workflow:** Apply, edit, or re-generate suggested messages
- **Multiple AI Providers:** Supports both Ollama (local) and OpenAI (cloud)

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: `.venv\Scripts\activate`
pip install gai .
```

## Configuration

Create a `.env` file in your project root:

```dotenv
# Choose provider: 'ollama' or 'openai'
PROVIDER=ollama

# For Ollama (local)
MODEL=llama3.2
CHAT_URL=http://localhost:11434/api

# For OpenAI (cloud)
# PROVIDER=openai
# API_KEY=your_api_key_here
```

## Usage

1. Stage your changes: `git add .`
2. Run: `gai`
3. Choose: **[A]**pply, **[E]**dit, **[R]**e-generate, or **[Q]**uit

## Command Line Options

```bash
gai --provider ollama    # Override provider
gai --provider openai    # Use OpenAI instead of default
```

## Requirements

- **For Ollama:** Install and run [Ollama](https://ollama.ai) locally
- **For OpenAI:** Valid API key with available credits

## License

MIT License - see [LICENSE](LICENSE) file for details.
