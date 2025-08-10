import requests
import sys
from gai.provider import Provider

DEFAULT_OLLAMA_MODEL = "llama3.2"
class OllamaProvider(Provider):
    def __init__(self, model, endpoint):
        self.model = model
        self.endpoint = endpoint

    def generate_commit_message(self, diff, oneline: bool = False):
        # Unified system prompt (mirrors OpenAI provider prompt)
        system_prompt = (
            "You are to act as an expert author of git commit messages. "
            "Your mission is to create clean and concise commit messages following the Conventional Commit specification. "
            "I will provide you with the output of 'git diff --staged' and you must convert it into a proper commit message.\n\n"
            "**COMMIT FORMAT RULES:**\n"
            "- Use ONLY these conventional commit keywords: fix, feat, build, chore, ci, docs, style, refactor, perf, test\n"
            "- Format: <type>[optional scope]: <description>\n"
            "- Use present tense (e.g., 'add feature' not 'added feature')\n"
            "- Keep subject line under 50 characters\n"
        )
        if not oneline:
            system_prompt += (
                "\n- Lines in body must not exceed 72 characters\n\n"
                "**BODY FORMAT (for multiple changes):**\n"
                "- Use bullet points (- ) for multiple changes\n"
                "- Each bullet point should be concise and specific\n"
                "- Start each bullet with a verb (add, fix, update, remove, etc.)\n"
                "- Focus on WHAT changed, not HOW it was implemented\n\n"
            )
        system_prompt += (
            "**OUTPUT REQUIREMENTS:**\n"
            "- Your response MUST contain ONLY the raw commit message text\n"
            "- NO introductory phrases like 'Here is the commit message:'\n"
            "- NO markdown formatting or code blocks\n"
            "- NO explanations or comments\n"
            "- NO quotation marks around the message\n"
        )
        if not oneline:
            system_prompt += (
                "\n\n**EXAMPLES:**\n"
                "feat: add user authentication system\n\n"
                    "- Implement JWT-based authentication for API security\n"
                    "- Add login and registration with password hashing\n"
                    "- Include middleware for protecting sensitive routes\n\n"
                "fix: resolve database connection issues\n\n"
                    "- Fix connection pool timeout configuration\n"
                    "- Add retry logic for failed database queries\n"
                    "- Update error handling for connection failures"
            )
        if oneline:
            system_prompt += (
                "\n\n**ONE-LINE COMMIT MESSAGE REQUIREMENTS:**\n"
                "- Your response MUST be a single line.\n"
                "- NO body or footer.\n"
                "- Keep the entire message concise and under 72 characters.\n"
            )
        user_prompt = f"Generate a commit message for this git diff:\n\n{diff}"
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
            print(f"\n\u001b[31mError connecting to Ollama:\u001b[0m {e}\n"
                  f"Please ensure the Ollama server is running and accessible at {self.endpoint}.")
            sys.exit(1)

