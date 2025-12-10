"""Strategy for analyzing user swear words vs AI apologies."""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud

from .base import Strategy


class SwearApologyStrategy(Strategy):
    """Analyze user swear words and AI apologies with pyramid visualization."""

    name = "swear_apology"
    description = "Compare user swearing patterns vs AI apologizing"

    # Regex patterns from original swearword_scan.py
    # Two buckets: embedded (no boundaries) and bounded (needs non-letter edges)
    EMBEDDED = [
        r"f+\*?u+\*?c+k+[a-z]*",       # fuck, fucking, fucck, f*ck
        r"f[@a]ck[a-z]*",                # f@ck
        r"fck[a-z]*",
        r"fuk[a-z]*",
        r"fook[a-z]*",
        r"feck[a-z]*",
        r"phuck[a-z]*",
        r"fvck[a-z]*",
        r"fuxk[a-z]*",
        r"fcuk[a-z]*",
        r"motherf[a-z]*",
        r"clusterf[a-z]*",
        r"fk\b",
        r"fkn\b",
        r"shit[a-z]*",                  # shit, shite, shitty, shitshow
        r"sh1t[a-z]*",
        r"sh!t[a-z]*",
        r"sht[a-z]*",
        r"shiz[z]*[a-z]*",
        r"shizzle[a-z]*",
        r"bullshit[a-z]*",
        r"batshit[a-z]*",
        r"dipshit[a-z]*",
        r"bitch[a-z]*",
        r"b!tch[a-z]*",
        r"biotch[a-z]*",
        r"bish+[a-z]*",
        r"beeyotch[a-z]*",
        r"biatch[a-z]*",
        r"cunt[a-z]*",
        r"c\*nt[a-z]*",
        r"c0nt[a-z]*",
        r"twat[a-z]*",
        r"tw@t[a-z]*",
        r"wank[a-z]*",
        r"bollock[a-z]*",
        r"dick[a-z]*",
        r"d1ck[a-z]*",
        r"nutsack[a-z]*",
        r"ball[s]y?",
        r"douche[a-z]*",
        r"jackass[a-z]*",
        r"sumbitch",
        r"god ?damn[a-z]*",
        r"g[d@]amn[a-z]*",
        r"god ?dammit[a-z]*",
        r"god ?dammit",
        r"dammit",
    ]

    BOUNDED = [
        r"wtf",
        r"fml",
        r"ffs",
        r"omfg",
        r"mf(?:er|ing)?",
        r"frick[a-z]*",
        r"frik[a-z]*",
        r"frig+in[g]*",
        r"freakin[g]*",
        r"(?<![A-Za-z])kunt(?![ia])[a-z]*",
        r"bugger",
        r"tosser",
        r"arsehole",
        r"arse",
        r"asshole[s]?",
        r"ass",
        r"sod\s*off",
        r"prick[a-z]*",
        r"knob[a-z]*",
        r"bellend[a-z]*",
        r"slag[a-z]*",
        r"piss[a-z]*",
        r"bastard[a-z]*",
        r"shag[a-z]*",
        r"jerk\s*off",
        r"cum[a-z]*",
        r"screw\s*you",
        r"cock(?!tails?|atoo|pit|burn|le|ney|roach|y)[a-z]*",
        r"c0ck(?!tails?)[a-z]*",
    ]

    SPACED = [
        r"f[\W_]{0,3}u[\W_]{0,3}c[\W_]{0,3}k[a-z]*",   # f u c k, f.u.c.k
        r"s[\W_]{0,3}h[\W_]{0,3}i[\W_]{0,3}t[a-z]*",   # s h i t
        r"b[\W_]{0,3}i[\W_]{0,3}t[\W_]{0,3}c[\W_]{0,3}h[a-z]*",
        r"c[\W_]{0,3}u[\W_]{0,3}n[\W_]{0,3}t[a-z]*",
        r"d[\W_]{0,3}i[\W_]{0,3}c[\W_]{0,3}k[a-z]*",
        r"w[\W_]{0,3}a[\W_]{0,3}n[\W_]{0,3}k[a-z]*",
        r"f[\W_]{0,3}u[\W_]{0,3}k[a-z]*",               # f u k
    ]

    UNHAPPY = [
        r"wrong",
        r"incorrect",
        r"mistake[s]?",
        r"bug[s]?",
        r"broken",
        r"broke",
        r"not[\s_]*working",
        r"doesn'?t[\s_]*work",
        r"didn'?t[\s_]*work",
        r"isn'?t[\s_]*working",
        r"fail(?:ed|ing)?",
        r"failure[s]?",
        r"error[s]?",
        r"issue[s]?",
        r"problem[s]?",
        r"crash(?:ed|es|ing)?",
        r"hang(?:s|ing)?",
        r"frozen",
        r"freeze|freezing",
        r"stuck",
        r"timeout[s]?",
        r"time[\s_]*out",
        r"laggy",
        r"slow",
        r"off[\s_]*by",
        r"nonsense",
        r"useless",
        r"garbage",
        r"worthless",
        r"rubbish",
        r"junk",
        r"misleading",
        r"inaccurate",
        r"hallucinat\w*",
        r"made[\s_]*up",
        r"screw(?:ed)?[\s_]*up",
        r"mess(?:ed)?[\s_]*up",
        r"borked",
        r"off[\s_]*the[\s_]*rails",
        r"redo",
        r"revert",
    ]

    IGNORE_WORDS = {
        "cocktail", "cocktails", "cockpit", "cockburn", "cockatoo",
        "cockroach", "cntainer", "container", "as",
    }

    # Apology patterns for AI (merged from original apology_scan.py)
    APOLOGY_PATTERNS = [
        # Direct apologies
        r"\bsorry\b",
        r"\bsorry about\b",
        r"\bsorry for\b",
        r"\bsorry,? but\b",
        r"\bsorry to\b",
        r"\bapolog(?:y|ies|ize|ised|izing)\b",
        r"\bapologies\b",
        r"\bmy apologies\b",
        r"\bapologies for\b",
        # Fault acknowledgment
        r"\bmy fault\b",
        r"\bmy mistake\b",
        r"\bmy bad\b",
        r"\bthat(?:'s| is)? on me\b",
        r"\bi(?:'m| am) at fault\b",
        r"\bi(?:'m| am) to blame\b",
        r"\bi(?:'m| am) responsible\b",
        r"\bi was wrong\b",
        # Regret expressions
        r"\bi didn'?t mean\b",
        r"\bdidn'?t intend\b",
        r"\bi regret\b",
        r"\bi should have\b",
        r"\bi made (a |an )?error\b",
        r"\bi misspoke\b",
        # Forgiveness requests
        r"\bpardon me\b",
        r"\bforgive me\b",
        r"\bplease forgive\b",
        r"\bi owe you an apology\b",
        # Gratitude for patience
        r"\bthanks for your patience\b",
        r"\bthanks for (the |your )?understanding\b",
        r"\bi understand your frustration\b",
        # Situation acknowledgment
        r"\bmisunderstanding\b",
        r"\bmistake\b",
        r"\binconvenience\b",
        r"\bconfusion\b",
        r"\bmix[- ]?up\b",
        r"\bunfortunately\b",
        # Corrections
        r"\bcorrection:\b",
        r"\blet me correct\b",
    ]

    DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Mapping of plural/variant forms to their canonical singular form
    WORD_NORMALIZATIONS = {
        "errors": "error",
        "problems": "problem",
        "issues": "issue",
        "failures": "failure",
        "mistakes": "mistake",
        "bugs": "bug",
        "crashes": "crash",
        "crashing": "crash",
        "crashed": "crash",
        "timeouts": "timeout",
        "failing": "fail",
        "failed": "fail",
        "hangs": "hang",
        "hanging": "hang",
        "freezing": "freeze",
        "hallucinates": "hallucinate",
        "hallucinating": "hallucinate",
        "hallucinated": "hallucinate",
    }

    def _normalize_word(self, word: str) -> str:
        """Normalize word to canonical singular form."""
        return self.WORD_NORMALIZATIONS.get(word, word)

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        # Track swear word counts
        user_swear_counts: Counter = Counter()

        # Track by 2-week periods
        swears_by_period = defaultdict(int)
        apologies_by_period = defaultdict(int)

        # Track all timestamps to determine period range
        all_timestamps: list[datetime] = []

        total_user_messages = 0
        total_assistant_messages = 0
        total_swear_instances = 0
        total_apology_instances = 0

        # Compile apology patterns
        apology_regex = re.compile(
            "|".join(self.APOLOGY_PATTERNS),
            re.IGNORECASE
        )

        # Build swear pattern regex (same as original swearword_scan.py)
        bounded_patterns = [rf"(?<![A-Za-z]){p}(?![A-Za-z])" for p in self.BOUNDED]
        unhappy_patterns = [rf"(?<![A-Za-z]){p}(?![A-Za-z])" for p in self.UNHAPPY]
        swear_regex = re.compile(
            rf"(?i)({'|'.join(self.EMBEDDED + bounded_patterns + self.SPACED + unhappy_patterns)})"
        )

        print("Analyzing swear words and apologies...")
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

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
                        # Check for swear words using regex
                        matches = swear_regex.findall(text)
                        for match in matches:
                            # Normalize: lowercase, strip, replace spaces/underscores
                            word = match.lower().strip()
                            word = re.sub(r'[\s_]+', '_', word)  # Normalize spaces
                            # Skip ignored words
                            if word in self.IGNORE_WORDS:
                                continue
                            # Normalize plural/variant forms to singular
                            word = self._normalize_word(word)
                            user_swear_counts[word] += 1
                            total_swear_instances += 1
                            # Add timestamp for each swear instance
                            if dt:
                                all_timestamps.append(("swear", dt))

                    elif role == "assistant":
                        total_assistant_messages += 1
                        # Check for apologies
                        apology_matches = apology_regex.findall(text)
                        if apology_matches:
                            apology_count = len(apology_matches)
                            total_apology_instances += apology_count
                            if dt:
                                for _ in range(apology_count):
                                    all_timestamps.append(("apology", dt))

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        # Build 2-week periods and assign events
        period_labels = []
        if all_timestamps:
            # Find date range
            dates_only = [ts[1] for ts in all_timestamps]
            min_date = min(dates_only)
            max_date = max(dates_only)

            # Create 2-week periods from min to max
            from datetime import timedelta
            period_start = min_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_days = 14

            period_idx = 0
            while period_start <= max_date:
                period_end = period_start + timedelta(days=period_days)
                period_labels.append(period_start.strftime("%b %Y"))

                # Count events in this period
                for event_type, event_dt in all_timestamps:
                    if period_start <= event_dt < period_end:
                        if event_type == "swear":
                            swears_by_period[period_idx] += 1
                        else:
                            apologies_by_period[period_idx] += 1

                period_start = period_end
                period_idx += 1

        # Generate timeline chart
        self._generate_pyramid_chart(swears_by_period, apologies_by_period, period_labels)

        # Generate swear word cloud
        self._generate_swear_cloud(user_swear_counts)

        # Get top 50 swear words
        top_swears = user_swear_counts.most_common(50)

        # Build output
        output_lines = ["# Swear Words & Apologies\n"]
        output_lines.append(f"*Analyzed {len(files):,} conversations*\n")

        # Summary comparison
        swear_rate = (total_swear_instances / total_user_messages * 100) if total_user_messages > 0 else 0
        apology_rate = (total_apology_instances / total_assistant_messages * 100) if total_assistant_messages > 0 else 0

        output_lines.append("## Summary\n")
        output_lines.append("| Metric | You | AI |")
        output_lines.append("|--------|----:|---:|")
        output_lines.append(f"| Total instances | {total_swear_instances:,} swears | {total_apology_instances:,} apologies |")
        output_lines.append(f"| Messages analyzed | {total_user_messages:,} | {total_assistant_messages:,} |")
        output_lines.append(f"| Rate | {swear_rate:.2f}% | {apology_rate:.2f}% |")
        output_lines.append("")

        # Insight
        insight = self._get_insight(total_swear_instances, total_apology_instances, swear_rate, apology_rate)
        output_lines.append(f"> {insight}\n")

        # Pyramid chart
        output_lines.append("## Timing Patterns\n")
        output_lines.append("![Swear vs Apology Patterns](swear_apology.png)\n")

        # Swear word cloud
        output_lines.append("## Word Cloud\n")
        output_lines.append("![Swear Word Cloud](swear_cloud.png)\n")

        # Top 50 swear words
        output_lines.append("## Top 50 Swear Words\n")
        if top_swears:
            output_lines.append("| Rank | Word | Count |")
            output_lines.append("|-----:|------|------:|")
            for i, (word, count) in enumerate(top_swears, 1):
                output_lines.append(f"| {i} | {word} | {count:,} |")
        else:
            output_lines.append("*No swear words detected. You're surprisingly polite!*")

        self.write_output("\n".join(output_lines))

        # Export JSON data for D3.js visualizations
        json_data = {
            "summary": {
                "total_swear_instances": total_swear_instances,
                "total_apology_instances": total_apology_instances,
                "total_user_messages": total_user_messages,
                "total_assistant_messages": total_assistant_messages,
                "swear_rate": round(swear_rate, 2),
                "apology_rate": round(apology_rate, 2),
                "insight": insight,
            },
            "timeline": {
                "labels": period_labels,
                "swears": [swears_by_period.get(i, 0) for i in range(len(period_labels))],
                "apologies": [apologies_by_period.get(i, 0) for i in range(len(period_labels))],
            },
            "wordcloud": [{"word": word, "count": count} for word, count in user_swear_counts.most_common()],
        }

        json_path = self.output_dir / "swear_apology.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)
        print(f"JSON data saved: {json_path}")

        return {
            "total_swear_instances": total_swear_instances,
            "total_apology_instances": total_apology_instances,
            "unique_swear_words": len(user_swear_counts),
            "top_swears": top_swears[:10],
        }

    def _generate_pyramid_chart(
        self,
        swears_by_period: dict,
        apologies_by_period: dict,
        period_labels: list[str],
    ) -> None:
        """Generate a horizontal butterfly timeline chart with smooth lines."""
        from scipy.interpolate import make_interp_spline

        # 16:9 aspect ratio (landscape)
        fig, ax = plt.subplots(figsize=(16, 9))

        human_color = "#4A90D9"  # Blue
        ai_color = "#E991B0"     # Pink

        # Get values aligned with periods
        swear_values = [swears_by_period.get(i, 0) for i in range(len(period_labels))]
        apology_values = [apologies_by_period.get(i, 0) for i in range(len(period_labels))]

        x = np.arange(len(period_labels))

        # Create smooth curves if we have enough points
        if len(x) > 3:
            x_smooth = np.linspace(x.min(), x.max(), 300)

            # Swears (negative, bottom side)
            swear_arr = np.array(swear_values, dtype=float)
            spline_swear = make_interp_spline(x, -swear_arr, k=min(3, len(x)-1))
            swear_smooth = spline_swear(x_smooth)
            # Clip to ensure swears never cross to positive side
            swear_smooth = np.clip(swear_smooth, None, 0)

            # Apologies (positive, top side)
            apology_arr = np.array(apology_values, dtype=float)
            spline_apology = make_interp_spline(x, apology_arr, k=min(3, len(x)-1))
            apology_smooth = spline_apology(x_smooth)
            # Clip to ensure apologies never cross to negative side
            apology_smooth = np.clip(apology_smooth, 0, None)

            # Plot smooth lines (horizontal: x is time, y is value)
            ax.plot(x_smooth, swear_smooth, color=human_color, linewidth=2, label='your frustration')
            ax.fill_between(x_smooth, swear_smooth, 0, alpha=0.3, color=human_color)

            ax.plot(x_smooth, apology_smooth, color=ai_color, linewidth=2, label='ai apologizing')
            ax.fill_between(x_smooth, 0, apology_smooth, alpha=0.3, color=ai_color)

            # Let each side extend to its own data extent
            ax.set_ylim(swear_smooth.min() * 1.1, apology_smooth.max() * 1.1)
        else:
            # Fallback for few data points
            ax.plot(x, [-v for v in swear_values], color=human_color, linewidth=2, label='your frustration')
            ax.fill_between(x, [-v for v in swear_values], 0, alpha=0.3, color=human_color)

            ax.plot(x, apology_values, color=ai_color, linewidth=2, label='ai apologizing')
            ax.fill_between(x, 0, apology_values, alpha=0.3, color=ai_color)

            # Let each side extend to its own data extent
            bottom_extent = max(swear_values) if swear_values else 1
            top_extent = max(apology_values) if apology_values else 1
            ax.set_ylim(-bottom_extent * 1.1, top_extent * 1.1)

        # X-axis: time labels at center (y=0)
        # Show ~12-15 labels to avoid crowding
        step = max(1, len(period_labels) // 15)
        tick_positions = list(range(0, len(period_labels), step))

        # Remove default x-axis ticks and add centered text labels
        ax.set_xticks([])
        for pos in tick_positions:
            ax.text(pos, 0, period_labels[pos], ha='center', va='center',
                   fontsize=9, color='#333333', rotation=45,
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                            edgecolor='none', alpha=0.8))

        # Y-axis formatting (absolute values)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, p: f'{abs(int(y))}'))

        # Labels and styling
        ax.set_xlabel("")
        ax.set_ylabel("Count")
        ax.set_title("Your Frustration vs AI Apologizing", fontsize=14, fontweight="bold", pad=20)
        ax.legend(loc='upper right')

        # Clean up spines - remove all except left
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plot_path = self.output_dir / "swear_apology.png"
        plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        print(f"Timeline chart saved: {plot_path}")

    def _generate_swear_cloud(self, swear_counts: Counter) -> None:
        """Generate a monochromatic word cloud of swear words."""
        if not swear_counts:
            print("No swear words to generate cloud from")
            return

        # Create word frequency dict
        word_freq = dict(swear_counts)

        # Generate word cloud - 9:16 portrait aspect ratio
        # Settings from original swearword_scan.py
        wc = WordCloud(
            width=900,
            height=1600,
            background_color="white",
            color_func=lambda *args, **kwargs: "black",  # Pure black only
            min_font_size=12,
            max_font_size=260,
            prefer_horizontal=0.9,
            max_words=10000,
            relative_scaling=0.4,
            collocations=False,
        ).generate_from_frequencies(word_freq)

        # Save - 9:16 portrait
        fig, ax = plt.subplots(figsize=(9, 16))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        plt.tight_layout(pad=0)

        plot_path = self.output_dir / "swear_cloud.png"
        plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()
        print(f"Word cloud saved: {plot_path}")

    def _get_insight(self, swear_count: int, apology_count: int,
                    swear_rate: float, apology_rate: float) -> str:
        """Generate an insight about the swear/apology relationship."""
        if swear_count == 0 and apology_count == 0:
            return "A perfectly civil exchange. No swearing, no apologizing. Just pure productivity."

        if swear_count == 0:
            return f"You kept it clean while the AI apologized {apology_count:,} times. Maybe it felt guilty for something?"

        if apology_count == 0:
            return f"You dropped {swear_count:,} expletives but the AI never once apologized. Confidence or obliviousness?"

        ratio = apology_count / swear_count if swear_count > 0 else 0

        if ratio > 5:
            return f"For every swear word you uttered, the AI apologized {ratio:.1f} times. It's not your fault, AI is just really sorry about everything."
        elif ratio > 2:
            return f"The AI apologized {ratio:.1f}x more than you swore. Classic overcompensation."
        elif ratio > 1:
            return f"Roughly balanced: {swear_count:,} swears vs {apology_count:,} apologies. A healthy give-and-take."
        elif ratio > 0.5:
            return f"You swore more than the AI apologized. Either you're venting or the AI has thick skin."
        else:
            return f"You really let loose with {swear_count:,} expletives while the AI barely apologized ({apology_count:,}). No judgment here."
