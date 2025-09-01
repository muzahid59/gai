import requests
from gai.provider import Provider
from gai.logger import logger

DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_MAX_TOKENS = 2000  # Conservative limit for context window


class OllamaProvider(Provider):
    def __init__(self, model, endpoint, max_tokens_per_chunk=DEFAULT_MAX_TOKENS):
        self.model = model
        self.endpoint = endpoint
        self.max_tokens_per_chunk = max_tokens_per_chunk
        logger.info(
            f"Initialized Ollama provider with model: {model}, endpoint: {endpoint}"
        )
        logger.debug(f"Max tokens per chunk: {max_tokens_per_chunk}")

    def _generate_single_chunk_message(
        self, diff_chunk: str, oneline: bool = False
    ) -> str:
        """Generate commit message for a single diff chunk."""
        logger.debug(f"Generating message for chunk with {len(diff_chunk)} characters")

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
            "- FOCUS on this specific part of the changes\n"
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
        user_prompt = f"Generate a commit message for this git diff:\n\n{diff_chunk}"
        json_payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        request_url = f"{self.endpoint}/chat"
        logger.debug(f"Making request to Ollama at: {request_url}")
        try:
            response = requests.post(request_url, json=json_payload, timeout=60)
            response.raise_for_status()
            full_response = response.json()
            if "message" in full_response and "content" in full_response["message"]:
                content = full_response["message"]["content"].strip()
                logger.debug(f"Ollama response received: {len(content)} characters")
                return content
            else:
                logger.error(f"Unexpected response format from Ollama: {full_response}")
                print("\n\033[31mError: Unexpected response format from Ollama.\033[0m")
                print(f"Response: {full_response}")
                return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Ollama: {e}")
            print(f"\n\u001b[31mError connecting to Ollama:\u001b[0m {e}")
            return ""

    def generate_commit_message(self, diff, oneline: bool = False):
        """Generate commit message, splitting large diffs if needed."""
        from gai.utils import (
            estimate_tokens,
            split_diff_by_files,
            aggregate_commit_messages,
        )

        total_tokens = estimate_tokens(diff)
        logger.info(f"Generating commit message for diff with {total_tokens} tokens")
        logger.debug(f"Oneline mode: {oneline}")
        print(f"Total tokens in diff: {total_tokens}")

        # If diff is small enough, use original method
        if total_tokens <= self.max_tokens_per_chunk:
            logger.debug("Diff size within limit, using single chunk processing")
            return self._generate_single_chunk_message(diff, oneline)

        logger.info(
            f"Large diff detected ({total_tokens} tokens). Splitting into chunks..."
        )
        print(f"Large diff detected ({total_tokens} tokens). Splitting into chunks...")

        # Split diff into manageable chunks
        chunks = split_diff_by_files(diff, self.max_tokens_per_chunk)

        if not chunks:
            logger.warning("No chunks created from diff")
            return "chore: update files"

        logger.info(f"Processing {len(chunks)} chunks...")
        print(f"Processing {len(chunks)} chunks...")

        # Generate messages for each chunk
        chunk_messages = []
        for i, chunk in enumerate(chunks):
            logger.debug(
                f"Processing chunk {i+1}/{len(chunks)} ({estimate_tokens(chunk)} tokens)"
            )
            print(f"  Processing chunk {i+1}/{len(chunks)}...")
            message = self._generate_single_chunk_message(chunk, oneline)
            if message:
                chunk_messages.append(message)
                logger.debug(
                    f"Chunk {i+1} generated message: {message.split(chr(10))[0]}"
                )
            else:
                logger.warning(f"Failed to generate message for chunk {i+1}")

        if not chunk_messages:
            logger.error("No messages generated from any chunks")
            return "chore: update multiple files"

        # Aggregate results
        logger.info("Aggregating chunk results...")
        print("Aggregating results...")
        final_message = aggregate_commit_messages(chunk_messages, oneline)
        logger.info(f"Final aggregated message: {final_message.split(chr(10))[0]}")
        return final_message
