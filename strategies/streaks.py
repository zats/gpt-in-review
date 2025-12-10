"""Strategy for analyzing conversation streaks (consecutive days of chatting)."""

from datetime import datetime, timedelta
from typing import Any

from .base import Strategy


class StreaksStrategy(Strategy):
    """Analyze conversation streaks - find longest streak with from/to dates."""

    name = "streaks"
    description = "Find longest ChatGPT usage streak"
    output_key = "static.streak"

    def run(self) -> dict[str, Any]:
        # Collect all unique dates with conversations
        active_dates: set[datetime.date] = set()

        for data in self.conversations:
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

        if not active_dates:
            return {"from": "", "to": "", "days": 0, "isCurrent": False}

        # Sort dates
        sorted_dates = sorted(active_dates)

        # Find all streaks
        all_streaks = self._find_all_streaks(sorted_dates)

        if not all_streaks:
            return {"from": "", "to": "", "days": 0, "isCurrent": False}

        # Check if there's a current active streak
        today = datetime.now().date()
        current_streak = None
        for streak in all_streaks:
            days_since_end = (today - streak["end"]).days
            if days_since_end <= 1:  # Active if ended today or yesterday
                current_streak = streak
                break

        # Use current streak if active, otherwise use longest streak
        if current_streak:
            best_streak = current_streak
            is_current = True
        else:
            # Find longest streak
            best_streak = max(all_streaks, key=lambda s: s["days"])
            is_current = False

        result = {
            "from": best_streak["start"].strftime("%Y-%m-%d"),
            "isCurrent": is_current,
        }
        # Only include "to" if it's not a current streak
        if not is_current:
            result["to"] = best_streak["end"].strftime("%Y-%m-%d")
        return result

    def _find_all_streaks(self, sorted_dates: list) -> list[dict]:
        """Find all streaks in the date list."""
        if not sorted_dates:
            return []

        streaks = []
        streak_start = sorted_dates[0]
        streak_end = sorted_dates[0]

        for i in range(1, len(sorted_dates)):
            # Check if consecutive day
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                streak_end = sorted_dates[i]
            else:
                # Save current streak
                days = (streak_end - streak_start).days + 1
                streaks.append({
                    "start": streak_start,
                    "end": streak_end,
                    "days": days,
                })
                # Start new streak
                streak_start = sorted_dates[i]
                streak_end = sorted_dates[i]

        # Don't forget the last streak
        days = (streak_end - streak_start).days + 1
        streaks.append({
            "start": streak_start,
            "end": streak_end,
            "days": days,
        })

        return streaks
