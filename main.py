import requests
import argparse
import json
import sys

def get_llm_response(prompt, model):
    """
    Sends a prompt to the Ollama API and streams the response.
    """
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_lines():
                if chunk:
                    try:
                        json_chunk = json.loads(chunk)
                        if 'response' in json_chunk:
                            print(json_chunk['response'], end='', flush=True)
                        if json_chunk.get('done'):
                            print()  # Print a newline when the stream is done
                    except json.JSONDecodeError:
                        # Handle cases where a chunk is not valid JSON
                        pass
    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the Ollama server is running and accessible at http://localhost:11434.")
        return

def chat_loop(model):
    """
    Starts an interactive chat session with the LLM.
    """
    print(f"Starting interactive chat with model: {model}")
    print("Type 'exit' or 'quit' to end the session.")
    while True:
        try:
            prompt = input("You: ")
            if prompt.lower() in ["exit", "quit"]:
                print("Exiting chat.")
                break
            if not prompt.strip():
                continue
            
            print("AI: ", end="")
            get_llm_response(prompt, model)

        except KeyboardInterrupt:
            print("\nExiting chat.")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            break

def main():
    """
    Main function to parse arguments and run the CLI.
    Supports both a single prompt execution and an interactive chat mode.
    """
    parser = argparse.ArgumentParser(
        description="A CLI to interact with a local Ollama LLM. Runs in interactive chat mode if no prompt is provided."
    )
    parser.add_argument(
        "prompt", 
        nargs='?', 
        default=None, 
        type=str, 
        help="The prompt to send to the LLM. If omitted, starts an interactive chat session."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemma:2b",
        help="The Ollama model to use (e.g., 'llama3', 'gemma:2b'). Defaults to 'gemma:2b'."
    )
    args = parser.parse_args()

    try:
        if args.prompt:
            # If a prompt is provided, execute it once and exit.
            get_llm_response(args.prompt, args.model)
        else:
            # If no prompt is provided, start the interactive chat loop.
            chat_loop(args.model)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
