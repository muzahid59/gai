

import requests
import sys
from gai.provider import Provider

class OllamaProvider(Provider):
    def __init__(self, model, endpoint):
        self.model = model
        self.endpoint = endpoint

    def generate_commit_message(self, diff, oneline: bool = False):
        system_prompt=(
            "You are the best git assistant whose aim is to generate a git commit message."
            "IT MUST BE written in English, be concise, be lowercase, relevant and straight to the point."
            "IT MUST FOLLOW conventional commits specifications and the following template:"
            "<type>[optional scope]: <short description>"
           
            "[optional body]"
            
            "Where <type> MUST BE ONE OF: fix, feat, build, chore, ci, docs, style, refactor, perf, test"
            "Where <type> MUST NOT BE: add, update, delete etc."
            "A commit that has a footer BREAKING CHANGE:, or appends a ! after the type, introduces a breaking API change."
            "DO NOT ADD UNDER ANY CIRCUMSTANCES: explanation about the commit, details such as file, changes, hash or the conventional commits specs."
        )
        if oneline:
            system_prompt += "IT MUST BE A SINGLE LINE COMMIT MESSAGE. DO NOT INCLUDE ANY BODY OR FOOTER."
        system_prompt += "Here is the git diff:"
        user_prompt = f"---\n\nGIT DIFF:\n{diff}"

        json_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        request_url = f"{self.endpoint}/chat"

        try:
            response = requests.post(
                request_url,
                json=json_payload,
                timeout=60
            )
            response.raise_for_status()

            full_response = response.json()
            
            if "message" in full_response and "content" in full_response["message"]:
                return full_response["message"]["content"].strip()
            else:
                print(f"\n\033[31mError: Unexpected response format from Ollama.\033[0m")
                print(f"Response: {full_response}")
                sys.exit(1)

        except requests.exceptions.RequestException as e:
            print(f"\n\u001b[31mError connecting to Ollama:\u001b[0m {e}\n" \
                  f"Please ensure the Ollama server is running and accessible at {self.endpoint}.")
            sys.exit(1)

