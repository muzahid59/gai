# `gai` - AI-Powered Git Assistant

`gai` is a command-line tool that uses the power of Large Language Models (LLMs) to help you write meaningful and well-formatted git commit messages.

It analyzes your staged changes, generates a conventional commit message, and asks for your approval before committing.

## Features

- **AI-Generated Commit Messages:** Automatically generates commit messages based on your staged changes.
- **Conventional Commits:** Enforces the Conventional Commits specification for clean and readable git history.
- **Interactive Workflow:** You can apply, edit, or re-generate the suggested commit message.
- **Local LLM Support:** Works with your own local Ollama instance for privacy and control.
- **Configurable:** Set your preferred Ollama model once and forget it.

## Installation

You can install `gai` using pip:

```bash
pip install gai
```

## Configuration

Before using the tool, you need to tell it which Ollama model to use. You only need to do this once.

```bash
gai --set-model llama3
```

Replace `llama3` with your preferred model (e.g., `gemma:2b`, `codellama`). This command saves your choice in a configuration file at `~/.own-cli/config.json`.

## Usage

1.  Make your code changes.
2.  Stage your changes as you normally would:
    ```bash
    git add .
    ```
3.  Run `gai`:
    ```bash
    gai
    ```

The tool will analyze your changes, generate a commit message, and present it to you with the following options:

- **[A]pply:** Commit the changes with the suggested message.
- **[E]dit:** Open the message in your default text editor for you to modify before committing.
- **[R]e-generate:** Request a new commit message from the LLM.
- **[Q]uit:** Abort the commit process.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
