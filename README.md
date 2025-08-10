# gai-commit

An AI-powered git commit message generator that helps you create meaningful commit messages using AI.

## Installation

```bash
pip install gai-commit
```

## Usage

```bash
gai --help
gai --provider openai
gai --provider ollama
```

## Features

- 🤖 **AI-Powered**: Generate commit messages using OpenAI or Ollama
- 🔄 **Interactive**: Choose from generated suggestions or edit them
- ⚙️ **Configurable**: Support for multiple AI providers

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
# OPEN_AI_API_KEY=your_api_key_here
```

## Command Line Options

```bash
gai --provider ollama    # Override provider
gai --provider openai    # Use OpenAI instead of default
```

## Requirements

- **For Ollama:** Install and run [Ollama](https://ollama.ai) locally
- **For OpenAI:** Valid API key with available credits (set OPEN_AI_API_KEY)

## License

MIT License - see [LICENSE](LICENSE) file for details.
