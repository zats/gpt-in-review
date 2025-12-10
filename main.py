#!/usr/bin/env python3
"""
Main driver for running conversation analysis strategies in parallel.

Usage:
    python main.py                     # Run all strategies with default parallelism (4)
    python main.py --parallel 8        # Run with 8 parallel workers
    python main.py --list              # List available strategies
    python main.py --strategies basic_counts,token_counts  # Run specific strategies
"""

import argparse
import importlib
import inspect
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Type

# Add the script directory to the path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from strategies.base import Strategy

# Paths
CONVERSATIONS_DIR = (
    SCRIPT_DIR.parent
    / "derived"
    / "conversations_split"
)
OUTPUT_BASE_DIR = SCRIPT_DIR / "output"


def discover_strategies() -> dict[str, Type[Strategy]]:
    """Discover all strategy classes in the strategies directory."""
    strategies_dir = SCRIPT_DIR / "strategies"
    strategies = {}

    for file_path in strategies_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "base.py":
            continue

        module_name = file_path.stem
        try:
            module = importlib.import_module(f"strategies.{module_name}")
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Strategy) and obj is not Strategy:
                    strategies[obj.name] = obj
        except Exception as e:
            print(f"Warning: Could not load {module_name}: {e}")

    return strategies


def run_strategy(
    strategy_class: Type[Strategy],
    conversations_dir: Path,
    output_dir: Path,
    progress_callback: callable = None,
) -> tuple[str, dict, float]:
    """Run a single strategy and return results."""
    start_time = time.time()

    try:
        strategy = strategy_class(conversations_dir, output_dir)
        results = strategy.run()
        elapsed = time.time() - start_time
        return strategy_class.name, results, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return strategy_class.name, {"error": str(e)}, elapsed


class ProgressTracker:
    """Thread-safe progress tracking."""

    def __init__(self, total: int, strategy_names: list[str]):
        self.total = total
        self.completed = 0
        self.running = set()
        self.strategy_names = strategy_names
        self.lock = threading.Lock()

    def start(self, name: str):
        with self.lock:
            self.running.add(name)
            self._print_status()

    def finish(self, name: str):
        with self.lock:
            self.running.discard(name)
            self.completed += 1
            self._print_status()

    def _print_status(self):
        pct = (self.completed / self.total) * 100
        running_str = ", ".join(sorted(self.running)) if self.running else "none"
        # Clear line and print status
        print(
            f"\r[{self.completed}/{self.total}] {pct:.0f}% complete | Running: {running_str}",
            end="",
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run conversation analysis strategies in parallel"
    )
    parser.add_argument(
        "--parallel",
        "-p",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available strategies and exit",
    )
    parser.add_argument(
        "--strategies",
        "-s",
        type=str,
        help="Comma-separated list of strategies to run (default: all)",
    )
    args = parser.parse_args()

    # Discover strategies
    all_strategies = discover_strategies()

    if args.list:
        print("Available strategies:\n")
        for name, cls in sorted(all_strategies.items()):
            print(f"  {name:25} - {cls.description}")
        return

    # Select strategies to run
    if args.strategies:
        selected_names = [s.strip() for s in args.strategies.split(",")]
        strategies_to_run = {}
        for name in selected_names:
            if name in all_strategies:
                strategies_to_run[name] = all_strategies[name]
            else:
                print(f"Warning: Unknown strategy '{name}', skipping")
        if not strategies_to_run:
            print("Error: No valid strategies selected")
            sys.exit(1)
    else:
        strategies_to_run = all_strategies

    # Validate conversations directory
    if not CONVERSATIONS_DIR.exists():
        print(f"Error: Conversations directory not found: {CONVERSATIONS_DIR}")
        sys.exit(1)

    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = OUTPUT_BASE_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Conversation Analysis Runner")
    print(f"=" * 50)
    print(f"Conversations dir: {CONVERSATIONS_DIR}")
    print(f"Output dir: {output_dir}")
    print(f"Strategies: {len(strategies_to_run)}")
    print(f"Parallel workers: {args.parallel}")
    print(f"=" * 50)
    print()

    # Initialize progress tracker
    tracker = ProgressTracker(len(strategies_to_run), list(strategies_to_run.keys()))

    # Run strategies in parallel
    results = {}
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {}
        for name, strategy_class in strategies_to_run.items():
            tracker.start(name)
            future = executor.submit(
                run_strategy, strategy_class, CONVERSATIONS_DIR, output_dir
            )
            futures[future] = name

        for future in as_completed(futures):
            name = futures[future]
            try:
                strategy_name, result, elapsed = future.result()
                results[strategy_name] = {"result": result, "elapsed": elapsed}
                tracker.finish(name)
            except Exception as e:
                results[name] = {"error": str(e), "elapsed": 0}
                tracker.finish(name)

    print()  # New line after progress
    print()

    total_elapsed = time.time() - start_time

    # Print summary
    print(f"Results Summary")
    print(f"=" * 50)
    for name, data in sorted(results.items()):
        elapsed = data.get("elapsed", 0)
        if "error" in data.get("result", {}):
            status = f"ERROR: {data['result']['error']}"
        else:
            status = "OK"
        print(f"  {name:25} [{elapsed:6.2f}s] {status}")

    print(f"=" * 50)
    print(f"Total time: {total_elapsed:.2f}s")
    print(f"Output written to: {output_dir}")


if __name__ == "__main__":
    main()
