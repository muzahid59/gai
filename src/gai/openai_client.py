import os
from openai import OpenAI

class OpenAIProvider:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
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
            "- Subject line MUST be 50 characters or less\n"
            "- Use present tense (e.g., 'add feature' not 'added feature')\n"
            "- First line should be a concise summary\n"
            "- Leave a blank line after the subject\n"
            "- Body should explain what and why, not how\n"
            "- Lines must not exceed 72 characters\n\n"
            
            "**OUTPUT REQUIREMENTS:**\n"
            "- Your response MUST contain ONLY the raw commit message text\n"
            "- NO introductory phrases like 'Here is the commit message:'\n"
            "- NO markdown formatting or code blocks\n"
            "- NO explanations or comments\n"
            "- NO quotation marks around the message\n\n"
            
            "**EXAMPLE:**\n"
            "feat: add user authentication system\n\n"
            "Implement JWT-based authentication to secure API endpoints.\n"
            "Add login and registration functionality with password hashing.\n"
            "Include middleware for protecting sensitive routes."
        )
        
        user_prompt = f"Generate a commit message for this git diff:\n\n{diff}"

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
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
