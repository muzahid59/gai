import os
from openai import OpenAI
from gai.provider import Provider
from gai.prompt import (
    build_system_prompt,
    build_human_prompt
)

DEFAULT_OPENAI_MODEL = "gpt-3.5-turbo"


class OpenAIProvider(Provider):
    def __init__(self, model=None):
        self.model = model or DEFAULT_OPENAI_MODEL
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = OpenAI(api_key=self.api_key)

    def generate_commit_message(self, diff, oneline: bool = False):
        commit_type = "oneline" if oneline else "descriptive"
        system_prompt = build_system_prompt(commit_type)
        user_prompt = build_human_prompt(diff)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating commit message with OpenAI: {e}")
            return None
