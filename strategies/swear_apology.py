"""Strategy for analyzing user swear words vs AI apologies."""

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from .base import Strategy


class SwearApologyStrategy(Strategy):
    """Analyze user swear words and AI apologies for frustration chart."""

    name = "swear_apology"
    description = "Compare user swearing patterns vs AI apologizing"
    output_key = "frustration"

    # Swear patterns (embedded - no boundaries needed)
    EMBEDDED = [
        r"f+\*?u+\*?c+k+[a-z]*", r"sh[i1!]t[a-z]*", r"bitch[a-z]*",
        r"cunt[a-z]*", r"damn[a-z]*", r"ass[a-z]*",
    ]

    # Bounded patterns (need word boundaries)
    BOUNDED = [
        r"wtf", r"fml", r"ffs", r"omfg", r"piss[a-z]*", r"bastard[a-z]*",
        r"crap", r"hell", r"suck[a-z]*",
    ]

    # Unhappy/frustration words (not profanity but indicate frustration)
    UNHAPPY = [
        r"wrong", r"incorrect", r"mistake[s]?", r"bug[s]?", r"broken",
        r"not[\s_]*working", r"fail(?:ed|ing)?", r"failure[s]?", r"error[s]?",
        r"issue[s]?", r"problem[s]?", r"crash(?:ed|es|ing)?", r"stuck",
        r"useless", r"garbage", r"worthless", r"hallucinat\w*",
    ]

    IGNORE_WORDS = {"cocktail", "cocktails", "assume", "assess", "assignment", "class"}

    # Apology patterns
    APOLOGY_PATTERNS = [
        r"\bsorry\b", r"\bapolog(?:y|ies|ize|ised|izing)\b",
        r"\bmy mistake\b", r"\bmy bad\b", r"\bi was wrong\b",
        r"\bi made (a |an )?error\b", r"\bunfortunately\b",
        r"\bcorrection:\b", r"\blet me correct\b",
    ]

    # Word normalizations
    WORD_NORMALIZATIONS = {
        "errors": "error", "problems": "problem", "issues": "issue",
        "failures": "failure", "mistakes": "mistake", "bugs": "bug",
        "crashes": "crash", "crashing": "crash", "crashed": "crash",
    }

    def run(self) -> dict[str, Any]:
        # Build swear pattern regex
        bounded_patterns = [rf"(?<![A-Za-z]){p}(?![A-Za-z])" for p in self.BOUNDED]
        unhappy_patterns = [rf"(?<![A-Za-z]){p}(?![A-Za-z])" for p in self.UNHAPPY]
        swear_regex = re.compile(
            rf"(?i)({'|'.join(self.EMBEDDED + bounded_patterns + unhappy_patterns)})"
        )

        # Compile apology patterns
        apology_regex = re.compile("|".join(self.APOLOGY_PATTERNS), re.IGNORECASE)

        # Track counts
        user_swear_counts: Counter = Counter()
        all_timestamps: list[tuple[str, datetime]] = []

        total_user_messages = 0
        total_assistant_messages = 0
        total_swear_instances = 0
        total_apology_instances = 0

        for data in self.conversations:
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

                if not text:
                    continue

                # Get timestamp
                create_time = message.get("create_time")
                dt = None
                if create_time and create_time > 0:
                    try:
                        dt = datetime.fromtimestamp(create_time)
                    except (ValueError, OSError):
                        dt = None

                if role == "user":
                    total_user_messages += 1
                    matches = swear_regex.findall(text)
                    for match in matches:
                        word = match.lower().strip()
                        word = re.sub(r'[\s_]+', '_', word)
                        if word in self.IGNORE_WORDS:
                            continue
                        word = self.WORD_NORMALIZATIONS.get(word, word)
                        user_swear_counts[word] += 1
                        total_swear_instances += 1
                        if dt:
                            all_timestamps.append(("swear", dt))

                elif role == "assistant":
                    total_assistant_messages += 1
                    apology_matches = apology_regex.findall(text)
                    if apology_matches:
                        apology_count = len(apology_matches)
                        total_apology_instances += apology_count
                        if dt:
                            for _ in range(apology_count):
                                all_timestamps.append(("apology", dt))

        # Build 2-week periods for timeline
        swears_by_period = defaultdict(int)
        apologies_by_period = defaultdict(int)
        period_labels = []

        if all_timestamps:
            dates_only = [ts[1] for ts in all_timestamps]
            min_date = min(dates_only)
            max_date = max(dates_only)

            period_start = min_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_days = 14
            period_idx = 0

            while period_start <= max_date:
                period_end = period_start + timedelta(days=period_days)
                period_labels.append(period_start.strftime("%b %Y"))

                for event_type, event_dt in all_timestamps:
                    if period_start <= event_dt < period_end:
                        if event_type == "swear":
                            swears_by_period[period_idx] += 1
                        else:
                            apologies_by_period[period_idx] += 1

                period_start = period_end
                period_idx += 1

        # Calculate rates
        swear_rate = (total_swear_instances / total_user_messages * 100) if total_user_messages > 0 else 0
        apology_rate = (total_apology_instances / total_assistant_messages * 100) if total_assistant_messages > 0 else 0

        # Build wordcloud data
        wordcloud_data = [{"word": word, "count": count} for word, count in user_swear_counts.most_common(70)]

        # Return data.json compatible structure
        return {
            "summary": {
                "total_swear_instances": total_swear_instances,
                "total_apology_instances": total_apology_instances,
                "swear_rate": round(swear_rate, 2),
                "apology_rate": round(apology_rate, 2),
            },
            "timeline": {
                "labels": period_labels,
                "swears": [swears_by_period.get(i, 0) for i in range(len(period_labels))],
                "apologies": [apologies_by_period.get(i, 0) for i in range(len(period_labels))],
            },
            "wordcloud": wordcloud_data,
        }
