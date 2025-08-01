import os
from openai import OpenAI
from gai.provider import Provider

DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo"

class OpenAIProvider(Provider):
    def __init__(self, model=None):
        self.model = model or os.getenv("MODEL") or DEFAULT_OPENAI_MODEL
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY environment variable not set.")
        self.client = OpenAI(api_key=self.api_key)

    def generate_commit_message(self, diff):
        system_prompt = (
            "You are to act as an expert author of git commit messages. "
            "Your mission is to create clean and comprehensive commit messages following the Conventional Commit specification. "
            "You must explain WHAT the changes are and WHY they were made.\n\n"

            "I will provide you with the output of 'git diff --staged' and you must convert it into a proper commit message.\n\n"

            "**COMMIT FORMAT RULES:**\n"
            "- Use ONLY these conventional commit keywords: fix, feat, build, chore, ci, docs, style, refactor, perf, test\n"
            "- Format: <type>[optional scope]: <description>\n"
            "- Use present tense (e.g., 'add feature' not 'added feature')\n"
            "- Keep subject line under 50 characters\n"
            "- Lines in body must not exceed 72 characters\n\n"

            "**BODY FORMAT (for multiple changes):**\n"
            "- Use bullet points (- ) for multiple changes\n"
            "- Each bullet point should be concise and specific\n"
            "- Start each bullet with a verb (add, fix, update, remove, etc.)\n"
            "- Focus on WHAT changed, not HOW it was implemented\n\n"

            "**OUTPUT REQUIREMENTS:**\n"
            "- Your response MUST contain ONLY the raw commit message text\n"
            "- NO introductory phrases like 'Here is the commit message:'\n"
            "- NO markdown formatting or code blocks\n"
            "- NO explanations or comments\n"
            "- NO quotation marks around the message\n\n"

            "**EXAMPLES:**\n"
            "feat: add user authentication system\n\n"
            "- Implement JWT-based authentication for API security\n"
            "- Add login and registration with password hashing\n"
            "- Include middleware for protecting sensitive routes\n\n"

            "fix: resolve database connection issues\n\n"
            "- Fix connection pool timeout configuration\n"
            "- Add retry logic for failed database queries\n"
            "- Update error handling for connection failures"
        )

        user_prompt = f"Generate a commit message for this git diff:\n\n{diff}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating commit message with OpenAI: {e}")
            return None