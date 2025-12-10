"""Strategy for analyzing message timing patterns."""

from collections import defaultdict
from datetime import datetime
from typing import Any

from .base import Strategy


class MessageTimingStrategy(Strategy):
    """Analyze when messages are sent - by hour, day of week, month."""

    name = "message_timing"
    description = "Generate chart data for message timing patterns"
    output_key = "charts"

    HOUR_LABELS = [
        "12a", "1a", "2a", "3a", "4a", "5a", "6a", "7a", "8a", "9a", "10a", "11a",
        "12p", "1p", "2p", "3p", "4p", "5p", "6p", "7p", "8p", "9p", "10p", "11p"
    ]
    DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"]
    MONTH_LABELS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def run(self) -> dict[str, Any]:
        # Collect all message timestamps
        timestamps: list[datetime] = []

        for data in self.conversations:
            mapping = data.get("mapping", {})
            for node in mapping.values():
                message = node.get("message")
                if message is None:
                    continue

                # Skip hidden messages
                metadata = message.get("metadata", {})
                if metadata.get("is_visually_hidden_from_conversation"):
                    continue

                create_time = message.get("create_time")
                if create_time and create_time > 0:
                    try:
                        dt = datetime.fromtimestamp(create_time)
                        timestamps.append(dt)
                    except (ValueError, OSError):
                        continue

        if not timestamps:
            return {
                "hourly": {"values": [], "labels": []},
                "daily": {"values": [], "labels": []},
                "monthly": {"values": [], "labels": []},
                "timeline": {"values": [], "labels": [], "years": []},
            }

        # Filter to only complete months (exclude current month)
        now = datetime.now()
        first_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        timestamps = [dt for dt in timestamps if dt < first_of_current_month]

        if not timestamps:
            return {
                "hourly": {"values": [], "labels": []},
                "daily": {"values": [], "labels": []},
                "monthly": {"values": [], "labels": []},
                "timeline": {"values": [], "labels": [], "years": []},
            }

        # Aggregate data
        by_hour = defaultdict(int)
        by_day_of_week = defaultdict(int)
        by_month = defaultdict(int)
        by_year_month = defaultdict(int)

        for dt in timestamps:
            by_hour[dt.hour] += 1
            by_day_of_week[dt.weekday()] += 1
            by_month[dt.month] += 1
            # Year-month key for timeline
            ym_key = dt.strftime("%Y-%m")
            by_year_month[ym_key] += 1

        # Build hourly data
        hourly_values = [by_hour[h] for h in range(24)]

        # Build daily data
        daily_values = [by_day_of_week[d] for d in range(7)]

        # Build monthly data (aggregated across years)
        monthly_values = [by_month[m] for m in range(1, 13)]

        # Build timeline data
        sorted_ym = sorted(by_year_month.keys())
        timeline_values = [by_year_month[ym] for ym in sorted_ym]
        timeline_labels = [self.MONTH_NAMES[int(ym.split("-")[1]) - 1] for ym in sorted_ym]
        timeline_years = [int(ym.split("-")[0]) for ym in sorted_ym]

        return {
            "hourly": {
                "values": hourly_values,
                "labels": self.HOUR_LABELS,
            },
            "daily": {
                "values": daily_values,
                "labels": self.DAY_LABELS,
            },
            "monthly": {
                "values": monthly_values,
                "labels": self.MONTH_LABELS,
            },
            "timeline": {
                "values": timeline_values,
                "labels": timeline_labels,
                "years": timeline_years,
            },
        }
