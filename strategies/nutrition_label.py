"""Strategy for generating a 'nutrition label' of conversation patterns."""

import re
from collections import Counter
from typing import Any

from .base import Strategy


class NutritionLabelStrategy(Strategy):
    """Analyze conversation patterns like a nutrition label."""

    name = "nutrition_label"
    description = "Nutrition facts label for conversation patterns"
    output_key = "static.nutrition"

    # User patterns
    MICROMANAGING_PATTERNS = [
        r"\bbe concise\b", r"\bconcise\b", r"\bshort(er)?\b", r"\bno fluff\b",
        r"\bno intro\b", r"\bno more than \d+\b", r"\bexactly \d+\b",
        r"\bdo not\b", r"\bdon't\b", r"\bonly\b.*\b(tables?|bullets?|json)\b",
        r"\bbullets?\b", r"\blist\b", r"\bstrictly\b", r"\bformat\b",
        r"\bstructured?\b", r"\btone\b", r"\bvoice\b", r"\bstyle\b",
    ]

    CONTEXT_DUMPING_PATTERNS = [
        r"\b(for )?context\b", r"\blong story short\b", r"\bbackground\b",
        r"\bbackstory\b", r"\bsetup\b", r"\bhere'?s (the )?situation\b",
        r"\bfor reference\b",
    ]

    SCOPE_CREEP_PATTERNS = [
        r"\band also\b", r"\boh and\b", r"\bone more\b", r"\balso\b",
        r"\bin addition\b", r"\bas well as\b", r"\bwhile you'?re at it\b",
        r"\bbtw\b", r"\bby the way\b",
    ]

    ACTUAL_QUESTION_PATTERNS = [
        r"\?", r"^how ", r"^what ", r"^why ", r"^where ", r"^who ", r"^which ",
        r"^can you\b", r"^could you\b", r"^please\b", r"\bcan you\b",
        r"^create\b", r"^write\b", r"^generate\b", r"^explain\b", r"^help me\b",
    ]

    DATA_HEMORRHAGE_PATTERNS = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
        r"\bsk-[A-Za-z0-9]{20,}\b",  # OpenAI API key
        r"\bghp_[A-Za-z0-9]{36}\b",  # GitHub token
        r"\b(api[_-]?key|secret|token)\s*[:=]\s*\S+",
    ]

    # Assistant patterns
    SYCOPHANCY_PATTERNS = [
        r"^great question", r"^excellent (question|point)", r"^wonderful",
        r"\bi'?d be (happy|glad|delighted) to\b", r"\banything else\b.*\?",
        r"\blet me know if\b", r"\bfeel free to\b", r"\bhappy to help\b",
    ]

    AS_AN_AI_PATTERNS = [
        r"\bas an? ai\b", r"\bas a(n?)( \w+)* language model\b", r"\bas an assistant\b",
        r"\bi('m| am) (just )?(an? )?(\w+ )*(ai|assistant|language model)\b",
        r"\bmy training (data|cutoff)\b", r"\bmy knowledge (cutoff|is limited)\b",
        r"\bi cannot (browse|access|search)\b", r"\bi don't have (access|the ability)\b",
    ]

    HALLUCINATION_RISK_PATTERNS = [
        r"\bdefinitely\b", r"\bcertainly\b", r"\balways\b", r"\bnever\b",
        r"\bguaranteed\b", r"\b100%\b", r"\bundoubtedly\b",
    ]

    def run(self) -> dict[str, Any]:
        # Compile all regex patterns
        user_patterns = {
            "micromanaging": self._compile_patterns(self.MICROMANAGING_PATTERNS),
            "context_dumping": self._compile_patterns(self.CONTEXT_DUMPING_PATTERNS),
            "scope_creep": self._compile_patterns(self.SCOPE_CREEP_PATTERNS),
            "actual_question": self._compile_patterns(self.ACTUAL_QUESTION_PATTERNS),
            "data_hemorrhage": self._compile_patterns(self.DATA_HEMORRHAGE_PATTERNS),
        }

        assistant_patterns = {
            "sycophancy": self._compile_patterns(self.SYCOPHANCY_PATTERNS),
            "as_an_ai": self._compile_patterns(self.AS_AN_AI_PATTERNS),
            "hallucination_risk": self._compile_patterns(self.HALLUCINATION_RISK_PATTERNS),
        }

        # Counters
        user_chars_total = 0
        assistant_chars_total = 0
        user_category_chars = Counter()
        assistant_category_chars = Counter()
        total_conversations = 0
        data_hemorrhage_count = 0

        for data in self.conversations:
            total_conversations += 1
            mapping = data.get("mapping", {})

            for node in mapping.values():
                message = node.get("message")
                if message is None:
                    continue

                metadata = message.get("metadata", {})
                if metadata.get("is_visually_hidden_from_conversation"):
                    continue

                author = message.get("author", {})
                role = author.get("role")
                if role not in ("user", "assistant"):
                    continue

                content = message.get("content", {})
                parts = content.get("parts", [])
                text = "".join(p for p in parts if isinstance(p, str))

                if not text.strip():
                    continue

                text_len = len(text)

                if role == "user":
                    user_chars_total += text_len
                    for category, regex in user_patterns.items():
                        if regex.search(text):
                            user_category_chars[category] += text_len
                    # Count data hemorrhage instances
                    data_hemorrhage_count += len(re.findall(
                        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                        text, re.I
                    ))

                elif role == "assistant":
                    assistant_chars_total += text_len
                    for category, regex in assistant_patterns.items():
                        if regex.search(text):
                            assistant_category_chars[category] += text_len

        # Calculate percentages - one decimal for <10%, integer for >=10%
        def pct(chars: int, total: int) -> str:
            if total <= 0:
                return "0"
            value = chars / total * 100
            if value >= 10:
                return str(int(value))
            return f"{value:.1f}"

        sycophancy_pct = pct(assistant_category_chars.get("sycophancy", 0), assistant_chars_total)
        hallucination_pct = pct(assistant_category_chars.get("hallucination_risk", 0), assistant_chars_total)
        micromanagement_pct = pct(user_category_chars.get("micromanaging", 0), user_chars_total)
        context_dumping_pct = pct(user_category_chars.get("context_dumping", 0), user_chars_total)
        scope_creep_pct = pct(user_category_chars.get("scope_creep", 0), user_chars_total)
        actual_question_pct = pct(user_category_chars.get("actual_question", 0), user_chars_total)
        chatgpt_isms_pct = pct(assistant_category_chars.get("as_an_ai", 0), assistant_chars_total)

        # Build data.json compatible output
        return {
            "serving": f"{total_conversations:,} conversations",
            "rows": [
                {"name": "Sycophancy", "sup": "†", "desc": "\"Great question!\"", "val": f"{sycophancy_pct}%"},
                {"name": "Hallucination Risk", "sup": "", "desc": "\"The 1987 study showed...\"", "val": f"{hallucination_pct}%"},
                {"name": "Micromanagement", "sup": "", "desc": "\"Use exactly 3 paragraphs...\"", "val": f"{micromanagement_pct}%"},
                {"name": "Data Hemorrhage", "sup": "‡", "desc": "\"My email is john@...\"", "val": str(data_hemorrhage_count)},
                {"name": "Context Dumping", "sup": "§", "desc": "\"Here's the full codebase...\"", "val": f"{context_dumping_pct}%"},
                {"name": "Scope Creep", "sup": "", "desc": "\"Also, while you're at it...\"", "val": f"{scope_creep_pct}%"},
                {"name": "ChatGPT-isms", "sup": "", "desc": "\"As an AI language model...\"", "val": f"{chatgpt_isms_pct}%"},
                {"name": "Actual Questions", "sup": "", "desc": "\"How do I fix this bug?\"", "val": f"{actual_question_pct}%"},
            ],
            "clearAskRatio": f"{actual_question_pct}%",
        }

    def _compile_patterns(self, patterns: list[str]) -> re.Pattern:
        """Compile a list of patterns into a single regex."""
        combined = "|".join(f"({p})" for p in patterns)
        return re.compile(combined, re.IGNORECASE | re.MULTILINE)
