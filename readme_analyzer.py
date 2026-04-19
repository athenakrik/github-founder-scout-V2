# Anthropic API call for README product voice classification

import anthropic

SYSTEM_PROMPT = (
    "You are a classifier that reads GitHub README files and determines whether they are "
    "written in a product voice or a technical/engineering voice. A product voice README "
    "describes a problem, articulates who the product is for, and makes a value proposition "
    "— it reads like a landing page. A technical voice README documents how the code works, "
    "lists functions, and explains implementation details. Respond with exactly one word: "
    "either 'product' or 'technical'. No explanation, no punctuation, just the single word."
)

MODEL = "claude-sonnet-4-20250514"
MAX_README_CHARS = 3000
VALID_LABELS = {"product", "technical"}


class ReadmeAnalyzer:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    def classify_readme(self, readme_text: str) -> str:
        truncated = readme_text[:MAX_README_CHARS]

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=10,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Classify this README:\n\n{truncated}"}
            ],
        )

        raw = response.content[0].text.strip().lower()
        if raw in VALID_LABELS:
            return raw
        return "technical"
