from typing import Literal


# Core system prompt with explicit role and structured format
SYSTEM_PROMPT_MAIN = """
Role: You are a git commit message generator
Task: Generate a concise commit message based on the git diff
Format: Follow conventional commit format: type(scope): description

**COMMIT FORMAT RULES:**
- Use ONLY these types: feat, fix, docs, style, refactor, test, chore
- Format: <type>[optional scope]: <description>
- Use imperative mood ("add" not "added")
- Maximum 50 characters for subject line
- Use present tense
- No period at end of subject
- Capitalize first letter after colon

**ANALYSIS APPROACH:**
1. Identify changed files and their roles
2. Determine type of change
3. Extract main modifications
4. Generate commit message

**PRIORITY ORDER:**
- Problem context first
- What changed (not how)
- Why it matters
- Side effects if any
""".strip()

# Simplified prompt for one-line commits
ONELINE_PROMPT = """
**SINGLE LINE REQUIREMENTS:**
- Response MUST be one line only
- No body or footer
- Maximum 72 characters total
- Focus on most important change

**EXAMPLES:**
feat(auth): add OAuth2 integration
fix(payment): resolve double-charging bug
docs: update API endpoints documentation
refactor(utils): extract validation logic
""".strip()

# Structured prompt for descriptive commits with backward reasoning
DESCRIPTIVE_PROMPT = """
**MULTI-LINE FORMAT:**
Subject: type(scope): description (max 50 chars)
[blank line]
Body: Explain what and why (wrap at 72 chars)

**DIFF ANALYSIS STEPS:**
1. SCAN: Identify file types and locations
2. CATEGORIZE: Determine change type
3. SUMMARIZE: Extract key modifications
4. GENERATE: Create commit message

**BODY STRUCTURE:**
- Problem/context statement
- Solution approach
- Testing verification (if relevant)
- Breaking changes (if any)

**BULLET POINTS FOR MULTIPLE CHANGES:**
- Start with verb (add, fix, update, remove)
- Focus on semantic meaning
- Maximum 72 characters per line

**GOOD EXAMPLE:**
fix(payment): resolve subscription renewal issues

Double-charging occurred when users renewed within
the grace period. This fix adds idempotency checks
to prevent duplicate transactions.

- Add transaction ID validation
- Implement retry logic with backoff
- Update error handling for edge cases

Tested with 1000 concurrent renewals.
""".strip()

# Output formatting with strict rules and anti-patterns
OUTPUT_FORMATTING = """
**OUTPUT REQUIREMENTS:**
- Raw commit message text only
- NO markdown formatting or code blocks
- NO explanatory text or comments
- NO quotation marks
- Start directly with commit type

**VALIDATION CHECKLIST:**
✓ Correct type prefix
✓ Optional scope in parentheses
✓ Colon and space after type/scope
✓ Imperative mood
✓ Under character limits

**ANTI-PATTERNS TO AVOID:**
❌ "Fixed stuff" - Too vague
❌ "Updated user.py" - Lists files not changes
❌ "Added new feature" - No specifics
❌ "minor changes" - Meaningless
❌ "WIP" - Not descriptive
""".strip()

# Template for human prompt
HUMAN_PROMPT_TEMPLATE = (
    "Generate a commit message for this git diff:\n\n{diff_chunk}"
)


def build_system_prompt(commit_type: Literal["oneline", "descriptive"]) -> str:
    """
    Build system prompt optimized for git commit generation.
    
    Args:
        commit_type: Whether to generate oneline or descriptive commits
    
    Returns:
        Optimized system prompt string
    """
    commit_type_prompt = ONELINE_PROMPT if commit_type == "oneline" else DESCRIPTIVE_PROMPT
    return SYSTEM_PROMPT_MAIN + "\n\n" + commit_type_prompt + "\n\n" + OUTPUT_FORMATTING


def build_human_prompt(diff_chunk: str) -> str:
    """
    Build human prompt with git diff.
    
    Args:
        diff_chunk: Git diff output (already chunked externally if needed)
    
    Returns:
        Formatted human prompt
    """
    return HUMAN_PROMPT_TEMPLATE.format(diff_chunk=diff_chunk)
