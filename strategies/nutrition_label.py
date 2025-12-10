"""Strategy for generating a 'nutrition label' of conversation patterns."""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .base import Strategy


class NutritionLabelStrategy(Strategy):
    """Analyze conversation patterns like a nutrition label - what you said vs what it said."""

    name = "nutrition_label"
    description = "Nutrition facts label for conversation patterns"

    # ============================================================
    # USER MESSAGE PATTERNS
    # ============================================================

    # Micromanagement: format/length/tone constraints
    MICROMANAGING_PATTERNS = [
        r"\bbe concise\b",
        r"\bconcise\b",
        r"\bshort(er)?\b",
        r"\bno fluff\b",
        r"\bno intro\b",
        r"\b(no|not) (extra|additional) (commentary|comments)\b",
        r"\bno more than \d+\b",
        r"\bexactly \d+\b",
        r"\bgive (me )?\d+ (options|ideas|examples)\b",
        r"\b(limit|keep) (it )?(to|under)\b",
        r"\bdo not\b",
        r"\bdon't\b",
        r"\bonly\b.*\b(tables?|bullets?|json)\b",
        r"\bbullets?\b",
        r"\blist\b",
        r"\bstrictly\b",
        r"\bformat\b",
        r"\bstructured?\b",
        r"\btone\b",
        r"\bvoice\b",
        r"\bstyle\b",
        r"\b(step ?by ?step)\b",
    ]

    # Context dumping: background, setup, narrative
    CONTEXT_DUMPING_PATTERNS = [
        r"\b(for )?context\b",
        r"\blong story short\b",
        r"\bbackground\b",
        r"\bbackstory\b",
        r"\bback story\b",
        r"\bsetup\b",
        r"\bhere'?s (the )?situation\b",
        r"\bfor reference\b",
        r"\b(i|we|my|our)\b.*\b(work|working|built|building|trying|tried|need|problem|issue)\b",
    ]

    # Scope creep: adding more asks
    SCOPE_CREEP_PATTERNS = [
        r"\band also\b",
        r"\boh and\b",
        r"\bone more\b",
        r"\balso\b",
        r"\bin addition\b",
        r"\bas well as\b",
        r"\bwhile you'?re at it\b",
        r"\bbtw\b",
        r"\bby the way\b",
    ]

    # Actual questions: direct asks
    ACTUAL_QUESTION_PATTERNS = [
        r"\?",
        r"^how ",
        r"^what ",
        r"^why ",
        r"^where ",
        r"^who ",
        r"^which ",
        r"^can you\b",
        r"^could you\b",
        r"^would you\b",
        r"^will you\b",
        r"^please\b",
        r"\bcan you\b",
        r"\bcould you\b",
        r"\bwould you\b",
        r"\bplease\b",
        r"^create\b",
        r"^write\b",
        r"^draft\b",
        r"^generate\b",
        r"^build\b",
        r"^make\b",
        r"^list\b",
        r"^show me\b",
        r"^explain\b",
        r"^summarize\b",
        r"^give me\b",
        r"^provide\b",
        r"^help me\b",
        r"^tell me\b",
    ]

    # Data hemorrhage: PII patterns
    DATA_HEMORRHAGE_PATTERNS = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # email
        r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",  # US phone
        r"\+\d{1,3}[-.\s]?\d{6,12}",  # intl phone
        r"\bsk-[A-Za-z0-9]{20,}\b",  # OpenAI API key
        r"\bAKIA[A-Z0-9]{16}\b",  # AWS key
        r"\bghp_[A-Za-z0-9]{36}\b",  # GitHub token
        r"\b(password|passwd|pwd)\s*[:=]\s*\S+",  # password in context
        r"\b(api[_-]?key|secret|token)\s*[:=]\s*\S+",  # secrets in context
    ]

    # ============================================================
    # ASSISTANT MESSAGE PATTERNS
    # ============================================================

    # Sycophancy: empty validation, filler
    SYCOPHANCY_PATTERNS = [
        r"^great question",
        r"^excellent (question|point)",
        r"^wonderful (question|point)",
        r"^perfect\b",
        r"^fantastic\b",
        r"^absolutely[!.]",
        r"^certainly[!.]",
        r"^of course[!.]",
        r"\bi'?d be (happy|glad|delighted) to\b",
        r"\b(does|did|hope) that (help|make sense|clarify)",
        r"\banything else\b.*\?",
        r"\bis there anything\b.*\?",
        r"\bwould you like\b.*\?",
        r"\blet me know if\b",
        r"\bfeel free to\b",
        r"\bhappy to help\b",
        r"\bglad to assist\b",
        r"^sure[!,]",
        r"^yes[!,] (absolutely|definitely|of course)",
    ]

    # "As an AI" disclaimers - self-referential AI catch phrases
    # The iconic ChatGPT self-identification and refusal patterns
    AS_AN_AI_PATTERNS = [
        # Identity declarations - the classics
        r"\bas an? ai\b",
        r"\bas a language model\b",
        r"\bas a large language model\b",
        r"\bas an assistant\b",
        r"\bas an ai (language )?model\b",
        r"\bas a text-based ai\b",
        r"\bas an ai assistant\b",
        r"\bi('m| am) (just )?(an? )?(ai|program|assistant|language model|chatbot)\b",
        r"\bi('m| am) (only )?(an? )?(ai|virtual assistant|digital assistant)\b",
        r"\bi('m| am) chatgpt\b",
        r"\bi('m| am) an ai (created|developed|made) by\b",
        # Knowledge cutoff / training disclaimers
        r"\bmy training (data|cutoff)\b",
        r"\bmy knowledge (cutoff|is limited|only goes|ends)\b",
        r"\bas of my (last )?(training|knowledge)( update| cutoff)?\b",
        r"\bmy (information|data) (only goes|is current) (up )?to\b",
        r"\bi (was|am) trained (on data )?(up )?to\b",
        # Capability limitations
        r"\bi (don'?t|cannot|can'?t) (have|access|browse|feel|experience)\b",
        r"\bi (don'?t|do not) have (access to )?(real-?time|the internet|current|live)\b",
        r"\bi (don'?t|do not) have the ability to\b",
        r"\bi('m| am) (not )?able to\b",
        r"\bi('m| am) unable to\b",
        r"\bi (cannot|can'?t) (actually )?(browse|search|access) the (internet|web)\b",
        r"\b(beyond|outside|not within) my (capabilities|abilities)\b",
        r"\bthat('s| is) (beyond|outside) (what )?(i can|my)\b",
        # Refusal patterns - the apologetic disclaimers
        r"\bi (cannot|can'?t) (help|assist) (you )?(with|in) (that|this)\b",
        r"\bi('m| am) (not able|unable) to (help|assist) (you )?(with|in)\b",
        r"\bi (must|have to) (respectfully )?decline\b",
        r"\bi('m| am) (sorry|afraid),? (but )?(i )?(cannot|can'?t)\b",
        r"\bi apologize,? but (i )?(cannot|can'?t|am unable)\b",
        r"\bi('m| am) not (designed|programmed|equipped|built) to\b",
        r"\bthat('s| is) not something i (can|am able to)\b",
        # Emotion/experience disclaimers
        r"\bi don'?t have (personal )?(opinions?|feelings?|preferences?|emotions?)\b",
        r"\bi don'?t (actually )?(have|experience) (feelings|emotions)\b",
        r"\bi (cannot|can'?t) (truly )?(feel|experience) (emotions?|feelings?)\b",
        r"\bi don'?t have (a )?(consciousness|subjective experience|physical form)\b",
        r"\bi don'?t have (personal )?experiences?\b",
        # Meta disclaimers
        r"\bplease (note|remember|keep in mind) that (i('m| am)|as) an? ai\b",
        r"\bit('s| is) important to (note|remember) that i('m| am) (just )?an? ai\b",
        r"\bi should (mention|note|clarify) that (i('m| am)|as) an? ai\b",
    ]

    # Hallucination risk: overconfidence without hedging
    HALLUCINATION_RISK_PATTERNS = [
        r"\bdefinitely\b",
        r"\bcertainly\b",
        r"\balways\b",
        r"\bnever\b",
        r"\bguaranteed\b",
        r"\b100%\b",
        r"\bundoubtedly\b",
        r"\bthe (only|best|correct) (way|approach|method|answer)\b",
        r"\bthis will work\b",
        r"\byou should always\b",
        r"\bthe answer is\b",
        r"\bwithout a doubt\b",
    ]

    # Hedging (good - appropriate uncertainty, subtracts from hallucination risk)
    HEDGING_PATTERNS = [
        r"\bi think\b",
        r"\bi believe\b",
        r"\bit'?s possible\b",
        r"\bmight be\b",
        r"\bcould be\b",
        r"\bgenerally\b",
        r"\btypically\b",
        r"\busually\b",
        r"\boften\b",
        r"\bin most cases\b",
        r"\bit depends\b",
        r"\bprobably\b",
        r"\bperhaps\b",
        r"\bmaybe\b",
    ]

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

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
            "hedging": self._compile_patterns(self.HEDGING_PATTERNS),
        }

        # Counters
        user_chars_total = 0
        assistant_chars_total = 0

        user_category_chars = Counter()
        assistant_category_chars = Counter()

        # For data hemorrhage, track actual matches
        data_hemorrhage_matches = {
            "emails": [],
            "phones": [],
            "api_keys": [],
            "secrets": [],
        }

        total_conversations = 0
        total_user_messages = 0
        total_assistant_messages = 0

        print("Analyzing conversation nutrition facts...")
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                total_conversations += 1
                mapping = data.get("mapping", {})

                for node in mapping.values():
                    message = node.get("message")
                    if message is None:
                        continue

                    # Skip hidden messages
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
                        total_user_messages += 1
                        user_chars_total += text_len

                        # Check each user pattern
                        for category, regex in user_patterns.items():
                            if regex.search(text):
                                user_category_chars[category] += text_len

                        # Special handling for data hemorrhage - collect actual matches
                        self._collect_data_hemorrhage(text, data_hemorrhage_matches)

                    elif role == "assistant":
                        total_assistant_messages += 1
                        assistant_chars_total += text_len

                        # Check each assistant pattern
                        for category, regex in assistant_patterns.items():
                            if regex.search(text):
                                assistant_category_chars[category] += text_len

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        # Calculate percentages
        user_percentages = {}
        for cat in user_patterns.keys():
            chars = user_category_chars.get(cat, 0)
            pct = (chars / user_chars_total * 100) if user_chars_total > 0 else 0
            user_percentages[cat] = {"chars": chars, "pct": pct}

        assistant_percentages = {}
        for cat in assistant_patterns.keys():
            chars = assistant_category_chars.get(cat, 0)
            pct = (chars / assistant_chars_total * 100) if assistant_chars_total > 0 else 0
            assistant_percentages[cat] = {"chars": chars, "pct": pct}

        # Clear ask ratio: actual_question chars / user total
        clear_ask_ratio = user_percentages.get("actual_question", {}).get("pct", 0)

        # Hallucination risk score: overconfidence minus hedging
        halluc_pct = assistant_percentages.get("hallucination_risk", {}).get("pct", 0)
        hedge_pct = assistant_percentages.get("hedging", {}).get("pct", 0)
        # Adjusted hallucination risk (can go negative if lots of hedging, floor at 0)
        adjusted_halluc_risk = max(0, halluc_pct - (hedge_pct * 0.5))

        # Count PII items
        pii_counts = {
            "emails": len(set(data_hemorrhage_matches["emails"])),
            "phones": len(set(data_hemorrhage_matches["phones"])),
            "api_keys": len(set(data_hemorrhage_matches["api_keys"])),
            "secrets": len(set(data_hemorrhage_matches["secrets"])),
        }
        total_pii = sum(pii_counts.values())

        # Build output
        output = self._build_output(
            total_conversations=total_conversations,
            total_user_messages=total_user_messages,
            total_assistant_messages=total_assistant_messages,
            user_chars_total=user_chars_total,
            assistant_chars_total=assistant_chars_total,
            user_percentages=user_percentages,
            assistant_percentages=assistant_percentages,
            clear_ask_ratio=clear_ask_ratio,
            adjusted_halluc_risk=adjusted_halluc_risk,
            pii_counts=pii_counts,
            total_pii=total_pii,
        )

        self.write_output(output)

        return {
            "total_conversations": total_conversations,
            "user_chars_total": user_chars_total,
            "assistant_chars_total": assistant_chars_total,
            "clear_ask_ratio": clear_ask_ratio,
            "sycophancy_pct": assistant_percentages.get("sycophancy", {}).get("pct", 0),
            "hallucination_risk_adjusted": adjusted_halluc_risk,
            "total_pii_detected": total_pii,
        }

    def _compile_patterns(self, patterns: list[str]) -> re.Pattern:
        """Compile a list of patterns into a single regex."""
        combined = "|".join(f"({p})" for p in patterns)
        return re.compile(combined, re.IGNORECASE | re.MULTILINE)

    def _collect_data_hemorrhage(self, text: str, matches: dict) -> None:
        """Collect specific PII matches for reporting."""
        # Emails
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text, re.I)
        matches["emails"].extend(emails)

        # Phones (simplified)
        phones = re.findall(r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        matches["phones"].extend(phones)

        # API keys
        api_keys = re.findall(r"\b(sk-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{36})\b", text)
        matches["api_keys"].extend(api_keys)

        # Secrets in context
        secrets = re.findall(r"\b(password|api[_-]?key|secret|token)\s*[:=]\s*\S+", text, re.I)
        matches["secrets"].extend(secrets)

    def _build_output(
        self,
        total_conversations: int,
        total_user_messages: int,
        total_assistant_messages: int,
        user_chars_total: int,
        assistant_chars_total: int,
        user_percentages: dict,
        assistant_percentages: dict,
        clear_ask_ratio: float,
        adjusted_halluc_risk: float,
        pii_counts: dict,
        total_pii: int,
    ) -> str:
        """Build the markdown nutrition label output in classic FDA style."""

        total_chars = user_chars_total + assistant_chars_total
        total_chars_display = f"{total_chars / 1_000_000:.1f}M" if total_chars > 1_000_000 else f"{total_chars:,}"

        # Build the nutrition label
        lines = [
            "# Nutrition Facts",
            "",
            "---",
            "",
            f"{total_conversations:,} conversations analyzed",
            "",
            f"**Serving size** 1 conversation",
            "",
            "---",
            "",
            "**Amount per conversation**",
            "",
            f"## Characters {total_chars_display}",
            "",
            "---",
            "",
            "```",
            "                                        % Daily Value*",
            "```",
            "",
            "---",
            "",
            "### What You Said",
            "",
        ]

        # User categories
        user_data = [
            ("Actual Questions", user_percentages.get("actual_question", {}).get("pct", 0)),
            ("Context Dumping", user_percentages.get("context_dumping", {}).get("pct", 0)),
            ("Micromanagement", user_percentages.get("micromanaging", {}).get("pct", 0)),
            ("Scope Creep", user_percentages.get("scope_creep", {}).get("pct", 0)),
        ]

        for label, pct in user_data:
            lines.append(f"**{label}** {pct:.0f}%")
            lines.append("")

        lines.extend([
            "---",
            "",
            f"**Clear Ask Ratio {clear_ask_ratio:.0f}%**",
            "",
            "---",
            "",
            "### What It Said",
            "",
        ])

        # Assistant categories
        assistant_data = [
            ("Sycophancy", assistant_percentages.get("sycophancy", {}).get("pct", 0)),
            ("ChatGPT-isms†", assistant_percentages.get("as_an_ai", {}).get("pct", 0)),
            ("Overconfidence", assistant_percentages.get("hallucination_risk", {}).get("pct", 0)),
            ("Appropriate Hedging", assistant_percentages.get("hedging", {}).get("pct", 0)),
        ]

        for label, pct in assistant_data:
            lines.append(f"**{label}** {pct:.0f}%")
            lines.append("")

        lines.extend([
            "---",
            "",
            f"**Hallucination Risk {adjusted_halluc_risk:.0f}%**",
            "",
            "---",
            "",
            "### Data Hemorrhage",
            "",
            f"**Emails** {pii_counts['emails']}",
            "",
            f"**Phone Numbers** {pii_counts['phones']}",
            "",
            f"**API Keys** {pii_counts['api_keys']}",
            "",
            f"**Secrets** {pii_counts['secrets']}",
            "",
            "---",
            "",
            f"**Total PII {total_pii}**",
            "",
            "---",
            "",
            "\\* % Daily Value based on your entire ChatGPT history.",
            "Clear Ask Ratio is the % of your messages that were actual",
            "questions vs context, constraints, and scope creep.",
            "Hallucination Risk = Overconfidence - (Hedging × 0.5).",
            "",
            "† ChatGPT-isms: Self-referential phrases like \"as an AI assistant\",",
            "\"my knowledge cutoff\", and apologetic refusals.",
            "",
        ])

        return "\n".join(lines)

    def _get_insight(
        self,
        clear_ask_ratio: float,
        sycophancy_pct: float,
        halluc_risk: float,
        total_pii: int,
    ) -> str:
        """Generate an insight about the conversation patterns."""
        insights = []

        if clear_ask_ratio < 20:
            insights.append(f"Only {clear_ask_ratio:.0f}% of your messages were actual asks. The rest was setup, constraints, and scope creep.")
        elif clear_ask_ratio > 50:
            insights.append(f"You're direct - {clear_ask_ratio:.0f}% of your messages got straight to the point.")

        if sycophancy_pct > 10:
            insights.append(f"The AI spent {sycophancy_pct:.0f}% of its breath on empty validation. That's a lot of 'Great question!'")
        elif sycophancy_pct < 2:
            insights.append("Surprisingly low sycophancy. This AI was all business.")

        if halluc_risk > 15:
            insights.append(f"High overconfidence ({halluc_risk:.0f}%) without hedging. Trust but verify.")
        elif halluc_risk < 5:
            insights.append("Low hallucination risk - the AI hedged appropriately.")

        if total_pii > 10:
            insights.append(f"You shared {total_pii} pieces of personal info. OpenAI thanks you for the training data.")
        elif total_pii > 0:
            insights.append(f"{total_pii} PII items detected. Consider what you're sharing.")

        if not insights:
            return "A balanced exchange. Nothing too alarming in either direction."

        return " ".join(insights)
