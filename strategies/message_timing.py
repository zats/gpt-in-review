"""Strategy for analyzing message timing patterns."""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-GUI backend for thread safety
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .base import Strategy


class MessageTimingStrategy(Strategy):
    """Analyze when messages are sent - by hour, day of week, month."""

    name = "message_timing"
    description = "Generate histograms of message timing patterns"

    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def run(self) -> dict[str, Any]:
        files = self.get_conversation_files()

        # Collect all message timestamps
        timestamps: list[datetime] = []

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

                    create_time = message.get("create_time")
                    if create_time and create_time > 0:
                        try:
                            dt = datetime.fromtimestamp(create_time)
                            timestamps.append(dt)
                        except (ValueError, OSError):
                            continue

            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")

        if not timestamps:
            self.write_output("# Message Timing\\n\\nNo timestamps found.")
            return {"error": "No timestamps"}

        # Filter to only complete months (exclude current month)
        now = datetime.now()
        first_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        timestamps = [dt for dt in timestamps if dt < first_of_current_month]

        if not timestamps:
            self.write_output("# Message Timing\\n\\nNo complete months found.")
            return {"error": "No complete months"}

        print(f"Collected {len(timestamps):,} message timestamps (excluding current month)")

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

        # Create figure with 4 subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("Message Timing Patterns", fontsize=16, fontweight="bold")

        # Style settings (black & white)
        line_color = "#000000"
        fill_alpha = 0.2
        point_size = 20

        # Import for smooth curves
        import numpy as np
        from scipy.interpolate import make_interp_spline

        def plot_smooth(ax, x, y, x_labels=None, wrap=False):
            """Plot smooth curve with fill and data points."""
            x_arr = np.array(x, dtype=float)
            y_arr = np.array(y, dtype=float)

            if wrap:
                # For cyclical data (hours, days, months), wrap around
                x_ext = np.concatenate([x_arr - len(x_arr), x_arr, x_arr + len(x_arr)])
                y_ext = np.concatenate([y_arr, y_arr, y_arr])
                x_smooth = np.linspace(x_arr.min(), x_arr.max(), 200)
                spline = make_interp_spline(x_ext, y_ext, k=3)
            else:
                x_smooth = np.linspace(x_arr.min(), x_arr.max(), 200)
                spline = make_interp_spline(x_arr, y_arr, k=3)

            y_smooth = spline(x_smooth)
            y_smooth = np.maximum(y_smooth, 0)

            ax.plot(x_smooth, y_smooth, color=line_color, linewidth=2)
            ax.fill_between(x_smooth, y_smooth, alpha=fill_alpha, color=line_color)
            ax.scatter(x, y, color=line_color, s=point_size, zorder=5)
            ax.grid(axis="y", alpha=0.3)
            # Remove top and right spines
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

        # 1. Messages by hour of day
        ax1 = axes[0, 0]
        hours = list(range(24))
        hour_counts = [by_hour[h] for h in hours]
        plot_smooth(ax1, hours, hour_counts, wrap=True)
        ax1.set_title("Messages by Hour of Day")
        ax1.set_xticks(range(0, 24, 2))
        ax1.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], rotation=45, ha="right")

        # 2. Messages by day of week
        ax2 = axes[0, 1]
        days = list(range(7))
        day_counts = [by_day_of_week[d] for d in days]
        plot_smooth(ax2, days, day_counts, wrap=True)
        ax2.set_title("Messages by Day of Week")
        ax2.set_xticks(days)
        ax2.set_xticklabels(self.DAYS_OF_WEEK, rotation=45, ha="right")

        # 3. Messages by month (aggregate across years)
        ax3 = axes[1, 0]
        months = list(range(1, 13))
        month_counts = [by_month[m] for m in months]
        plot_smooth(ax3, months, month_counts, wrap=True)
        ax3.set_title("Messages by Month (All Years)")
        ax3.set_xticks(months)
        ax3.set_xticklabels(self.MONTHS, rotation=45, ha="right")

        # 4. Messages over time (line graph with smooth curve)
        ax4 = axes[1, 1]
        sorted_ym = sorted(by_year_month.keys())
        ym_dates = [datetime.strptime(ym, "%Y-%m") for ym in sorted_ym]
        ym_counts = [by_year_month[ym] for ym in sorted_ym]

        x_numeric = mdates.date2num(ym_dates)
        y_array = np.array(ym_counts)

        x_smooth = np.linspace(x_numeric.min(), x_numeric.max(), 300)
        spline = make_interp_spline(x_numeric, y_array, k=3)
        y_smooth = spline(x_smooth)
        y_smooth = np.maximum(y_smooth, 0)

        x_smooth_dates = mdates.num2date(x_smooth)

        ax4.plot(x_smooth_dates, y_smooth, color=line_color, linewidth=2)
        ax4.fill_between(x_smooth_dates, y_smooth, alpha=fill_alpha, color=line_color)
        ax4.scatter(ym_dates, ym_counts, color=line_color, s=point_size, zorder=5)
        ax4.set_title("Messages Over Time")
        ax4.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha="right")
        ax4.grid(axis="y", alpha=0.3)
        ax4.spines["top"].set_visible(False)
        ax4.spines["right"].set_visible(False)

        plt.tight_layout()

        # Save plot
        plot_path = self.output_dir / "message_timing.png"
        plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close()

        # Find peak times
        peak_hour = max(by_hour, key=by_hour.get)
        peak_day = self.DAYS_OF_WEEK[max(by_day_of_week, key=by_day_of_week.get)]
        peak_month = self.MONTHS[max(by_month, key=by_month.get) - 1]
        peak_ym = max(by_year_month, key=by_year_month.get)

        # Generate personality insight
        personality = self._get_personality_insight(by_hour, by_day_of_week)

        # Build markdown output
        output = f"""# Message Timing Patterns

![Message Timing](message_timing.png)

> {personality}

## Summary

| Metric | Value |
|--------|-------|
| Total Messages | {len(timestamps):,} |
| Date Range | {min(timestamps).strftime('%Y-%m-%d')} to {max(timestamps).strftime('%Y-%m-%d')} |
| Peak Hour | {peak_hour:02d}:00 ({by_hour[peak_hour]:,} messages) |
| Peak Day | {peak_day} ({by_day_of_week[self.DAYS_OF_WEEK.index(peak_day)]:,} messages) |
| Peak Month | {peak_month} ({by_month[self.MONTHS.index(peak_month) + 1]:,} messages) |
| Busiest Month Ever | {peak_ym} ({by_year_month[peak_ym]:,} messages) |

## Hourly Distribution

| Hour | Messages |
|------|----------|
"""
        for h in range(24):
            output += f"| {h:02d}:00 | {by_hour[h]:,} |\n"

        output += """
## Daily Distribution

| Day | Messages |
|-----|----------|
"""
        for d, name in enumerate(self.DAYS_OF_WEEK):
            output += f"| {name} | {by_day_of_week[d]:,} |\n"

        output += """
## Monthly Distribution (All Years)

| Month | Messages |
|-------|----------|
"""
        for m, name in enumerate(self.MONTHS, 1):
            output += f"| {name} | {by_month[m]:,} |\n"

        output += """
## Timeline

| Month | Messages |
|-------|----------|
"""
        for ym in sorted_ym:
            output += f"| {ym} | {by_year_month[ym]:,} |\n"

        self.write_output(output)

        return {
            "total_messages": len(timestamps),
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "busiest_month": peak_ym,
            "personality": personality,
        }

    def _get_personality_insight(
        self, by_hour: dict[int, int], by_day_of_week: dict[int, int]
    ) -> str:
        """Generate a personality insight based on messaging patterns."""
        total = sum(by_hour.values())
        if total == 0:
            return "Not enough data to determine your ChatGPT personality."

        # Calculate percentages for time blocks
        early_morning = sum(by_hour.get(h, 0) for h in range(5, 8)) / total  # 5-7
        morning = sum(by_hour.get(h, 0) for h in range(8, 12)) / total  # 8-11
        afternoon = sum(by_hour.get(h, 0) for h in range(12, 17)) / total  # 12-16
        evening = sum(by_hour.get(h, 0) for h in range(17, 21)) / total  # 17-20
        night = sum(by_hour.get(h, 0) for h in range(21, 24)) / total  # 21-23
        late_night = sum(by_hour.get(h, 0) for h in range(0, 5)) / total  # 0-4

        # Calculate weekday vs weekend
        weekday_total = sum(by_day_of_week.get(d, 0) for d in range(5))  # Mon-Fri
        weekend_total = sum(by_day_of_week.get(d, 0) for d in range(5, 7))  # Sat-Sun
        # Normalize by number of days (5 weekdays vs 2 weekend days)
        weekday_avg = weekday_total / 5
        weekend_avg = weekend_total / 2
        weekend_ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 1

        # Find dominant time block
        time_blocks = {
            "early_morning": early_morning,
            "morning": morning,
            "afternoon": afternoon,
            "evening": evening,
            "night": night,
            "late_night": late_night,
        }
        dominant_block = max(time_blocks, key=time_blocks.get)

        # Determine personality
        work_hours = morning + afternoon  # 8-16

        if late_night > 0.15:
            return "**The Night Owl** - When the world sleeps, you're deep in conversation with AI. Your best ideas come after midnight."
        elif early_morning > 0.15:
            return "**The Early Bird** - Up before dawn and already prompting. You squeeze productivity out of hours others don't even know exist."
        elif work_hours > 0.55 and weekend_ratio < 0.8:
            return "**The 9-to-5 Professional** - Your ChatGPT usage mirrors a classic workday. AI is your office productivity partner."
        elif weekend_ratio > 1.5:
            return "**The Weekend Warrior** - Weekends are your AI exploration time. When work stops, your curiosity kicks in."
        elif evening > 0.35:
            return "**The Evening Tinkerer** - After dinner, the real work begins. You wind down your day with AI-assisted projects."
        elif night > 0.25:
            return "**The Late Night Researcher** - The quiet hours between dinner and sleep are when you dive deepest into AI conversations."
        elif morning > 0.35:
            return "**The Morning Maximizer** - Your mornings are for serious work, and AI is part of your peak productivity hours."
        elif afternoon > 0.35:
            return "**The Afternoon Explorer** - Post-lunch is your prime AI time. Maybe it's creative block, maybe it's curiosity - either way, you're prompting."
        else:
            return "**The All-Day Conversationalist** - No single pattern defines you. AI is woven throughout your day, ready whenever inspiration strikes."
