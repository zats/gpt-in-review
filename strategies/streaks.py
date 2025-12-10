"""Strategy for analyzing conversation streaks (consecutive days of chatting)."""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .base import Strategy


class StreaksStrategy(Strategy):
    """Analyze conversation streaks - consecutive days of chatting."""

    name = "streaks"
    description = "Find consecutive day streaks of ChatGPT usage"

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        # Collect all unique dates with conversations
        active_dates: set[datetime.date] = set()

        print("Analyzing conversation dates for streaks...")
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                mapping = data.get("mapping", {})
                for node in mapping.values():
                    message = node.get("message")
                    if message is None:
                        continue

                    # Only count user messages (user initiated the conversation that day)
                    author = message.get("author", {})
                    if author.get("role") != "user":
                        continue

                    create_time = message.get("create_time")
                    if create_time and create_time > 0:
                        try:
                            dt = datetime.fromtimestamp(create_time)
                            active_dates.add(dt.date())
                        except (ValueError, OSError):
                            pass

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        if not active_dates:
            self.write_output("# Streaks\n\nNo conversation data found.")
            return {"error": "No data"}

        # Sort dates
        sorted_dates = sorted(active_dates)

        # Find all streaks
        streaks = self._find_streaks(sorted_dates)

        # Get statistics
        longest_streak = max(streaks, key=lambda s: s["length"])
        current_streak = self._get_current_streak(sorted_dates)
        total_active_days = len(sorted_dates)

        # Calculate date range
        first_date = sorted_dates[0]
        last_date = sorted_dates[-1]
        total_days = (last_date - first_date).days + 1
        activity_rate = (total_active_days / total_days * 100) if total_days > 0 else 0

        # Find top 5 streaks
        top_streaks = sorted(streaks, key=lambda s: s["length"], reverse=True)[:5]

        # Build output
        output_lines = ["# Conversation Streaks\n"]
        output_lines.append(f"*Analyzed {len(files):,} conversations from {first_date.strftime('%b %d, %Y')} to {last_date.strftime('%b %d, %Y')}*\n")

        # Hero stat
        output_lines.append("## Longest Streak\n")
        output_lines.append(f"# 🔥 {longest_streak['length']} days\n")
        output_lines.append(f"*{longest_streak['start'].strftime('%b %d, %Y')} → {longest_streak['end'].strftime('%b %d, %Y')}*\n")

        # Insight about longest streak
        insight = self._get_streak_insight(longest_streak["length"])
        output_lines.append(f"> {insight}\n")

        # Current streak
        output_lines.append("## Current Streak\n")
        if current_streak > 0:
            output_lines.append(f"**{current_streak} day{'s' if current_streak != 1 else ''}** and counting!\n")
        else:
            # How many days since last activity
            today = datetime.now().date()
            days_since = (today - last_date).days
            if days_since == 1:
                output_lines.append("You missed yesterday. Start a new streak today!\n")
            else:
                output_lines.append(f"No active streak. Last activity was {days_since} days ago.\n")

        # Summary stats
        output_lines.append("## Summary\n")
        output_lines.append("| Metric | Value |")
        output_lines.append("|--------|------:|")
        output_lines.append(f"| Total active days | {total_active_days:,} |")
        output_lines.append(f"| Total calendar days | {total_days:,} |")
        output_lines.append(f"| Activity rate | {activity_rate:.1f}% |")
        output_lines.append(f"| Total streaks (2+ days) | {len([s for s in streaks if s['length'] >= 2]):,} |")
        output_lines.append(f"| Average streak length | {sum(s['length'] for s in streaks) / len(streaks):.1f} days |")
        output_lines.append("")

        # Top 5 streaks
        output_lines.append("## Top 5 Streaks\n")
        output_lines.append("| Rank | Length | Period |")
        output_lines.append("|-----:|-------:|--------|")
        for i, streak in enumerate(top_streaks, 1):
            period = f"{streak['start'].strftime('%b %d')} - {streak['end'].strftime('%b %d, %Y')}"
            output_lines.append(f"| {i} | {streak['length']} days | {period} |")
        output_lines.append("")

        # Fun facts
        output_lines.append("## Fun Facts\n")

        # Day of week analysis
        dow_counts = defaultdict(int)
        for d in sorted_dates:
            dow_counts[d.strftime("%A")] += 1
        most_active_day = max(dow_counts, key=dow_counts.get)
        least_active_day = min(dow_counts, key=dow_counts.get)

        output_lines.append(f"- **Most active day:** {most_active_day} ({dow_counts[most_active_day]} times)")
        output_lines.append(f"- **Least active day:** {least_active_day} ({dow_counts[least_active_day]} times)")

        # Weekend vs weekday
        weekend_days = sum(1 for d in sorted_dates if d.weekday() >= 5)
        weekday_days = total_active_days - weekend_days
        output_lines.append(f"- **Weekday vs weekend:** {weekday_days} weekdays, {weekend_days} weekend days")

        self.write_output("\n".join(output_lines))

        return {
            "longest_streak": longest_streak["length"],
            "current_streak": current_streak,
            "total_active_days": total_active_days,
            "activity_rate": activity_rate,
            "top_streaks": [(s["length"], str(s["start"])) for s in top_streaks],
        }

    def _find_streaks(self, sorted_dates: list) -> list[dict]:
        """Find all consecutive day streaks."""
        if not sorted_dates:
            return []

        streaks = []
        streak_start = sorted_dates[0]
        streak_end = sorted_dates[0]

        for i in range(1, len(sorted_dates)):
            prev_date = sorted_dates[i - 1]
            curr_date = sorted_dates[i]

            if (curr_date - prev_date).days == 1:
                # Continue streak
                streak_end = curr_date
            else:
                # End current streak, start new one
                streaks.append({
                    "start": streak_start,
                    "end": streak_end,
                    "length": (streak_end - streak_start).days + 1,
                })
                streak_start = curr_date
                streak_end = curr_date

        # Don't forget the last streak
        streaks.append({
            "start": streak_start,
            "end": streak_end,
            "length": (streak_end - streak_start).days + 1,
        })

        return streaks

    def _get_current_streak(self, sorted_dates: list) -> int:
        """Get the current streak length (if still active)."""
        if not sorted_dates:
            return 0

        today = datetime.now().date()
        last_active = sorted_dates[-1]

        # Check if streak is still active (last activity was today or yesterday)
        days_since = (today - last_active).days
        if days_since > 1:
            return 0

        # Count backwards from the most recent date
        streak = 1
        for i in range(len(sorted_dates) - 1, 0, -1):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                streak += 1
            else:
                break

        return streak

    def _get_streak_insight(self, length: int) -> str:
        """Generate a fun insight about the streak length."""
        if length >= 365:
            return f"A full year of daily ChatGPT! That's dedication bordering on dependency."
        elif length >= 180:
            return f"Half a year straight! ChatGPT is basically your co-pilot at this point."
        elif length >= 90:
            return f"Three months without missing a day. You've formed a serious habit."
        elif length >= 30:
            return f"A full month! They say it takes 21 days to form a habit. You're way past that."
        elif length >= 14:
            return f"Two weeks strong. ChatGPT has become part of your daily routine."
        elif length >= 7:
            return f"A whole week! That's commitment to the AI conversation lifestyle."
        elif length >= 3:
            return f"A few days in a row. The beginning of a beautiful friendship."
        else:
            return f"Every streak starts somewhere. This one started here."
