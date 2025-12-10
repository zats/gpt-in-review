#!/usr/bin/env python3
"""
Main driver for running conversation analysis and generating website data.

Usage:
    python main.py /path/to/conversations.json

Outputs:
    website/data.json
    website/tarot_card.png
"""

import argparse
import importlib
import inspect
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Type

# Fail fast on missing dependencies
REQUIRED_PACKAGES = {
    "tiktoken": "tiktoken",
    "emoji": "emoji",
    "openai": "openai",
    "google.genai": "google-genai",
    "sklearn": "scikit-learn",
    "numpy": "numpy",
    "dotenv": "python-dotenv",
}


def check_dependencies() -> None:
    """Check all required packages are installed. Exit if any missing."""
    missing = []
    for module, package in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("ERROR: Missing required packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        sys.exit(1)


def load_env() -> None:
    """Load .env file from script directory. Exit if missing or keys not set."""
    from dotenv import load_dotenv

    script_dir = Path(__file__).parent
    env_path = script_dir / ".env"

    if not env_path.exists():
        print(f"ERROR: .env file not found at {env_path}")
        print("Copy .env.example to .env and fill in your API keys")
        sys.exit(1)

    load_dotenv(env_path)

    # Check required API keys
    openai_key = os.environ.get("OPENAI_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    errors = []
    if not openai_key or openai_key.startswith("sk-..."):
        errors.append("OPENAI_API_KEY not set or still placeholder")
    if not google_key or google_key == "...":
        errors.append("GOOGLE_API_KEY (or GEMINI_API_KEY) not set or still placeholder")

    if errors:
        print("ERROR: API keys not properly configured in .env:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


# Check dependencies before any other imports
check_dependencies()

# Now safe to import after dependency check
from strategies.base import Strategy


SCRIPT_DIR = Path(__file__).parent
WEBSITE_DIR = SCRIPT_DIR / "website"

# Strategies to skip (not used in data.json)
SKIP_STRATEGIES = {"topic_timeline", "abandoned_conversations"}


def discover_strategies() -> dict[str, Type[Strategy]]:
    """Discover all strategy classes in the strategies directory."""
    strategies_dir = SCRIPT_DIR / "strategies"
    strategies = {}

    for file_path in strategies_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "base.py":
            continue

        module_name = file_path.stem
        if module_name in SKIP_STRATEGIES:
            continue

        try:
            module = importlib.import_module(f"strategies.{module_name}")
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Strategy) and obj is not Strategy:
                    strategies[obj.name] = obj
        except Exception as e:
            print(f"  [!] Failed to load {module_name}: {e}")

    return strategies


def load_conversations(path: Path) -> list[dict]:
    """Load conversations from JSON file."""
    print(f"Loading {path}...")
    start = time.time()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not read {path}: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print(f"ERROR: Expected JSON array, got {type(data).__name__}")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"Loaded {len(data):,} conversations ({elapsed:.1f}s)\n")
    return data


def run_strategy(
    strategy_class: Type[Strategy],
    conversations: list[dict],
    output_dir: Path,
) -> tuple[str, dict[str, Any], float, str | None]:
    """Run a single strategy and return results."""
    start_time = time.time()
    error_msg = None

    try:
        strategy = strategy_class(conversations, output_dir)
        results = strategy.run()
        if "error" in results:
            error_msg = results["error"]
    except Exception as e:
        results = {"error": str(e)}
        error_msg = str(e)

    elapsed = time.time() - start_time
    return strategy_class.name, results, elapsed, error_msg


def merge_results(all_results: dict[str, dict]) -> dict[str, Any]:
    """Merge all strategy results into the final data.json structure."""
    data = {
        "static": {
            "firstConversation": {},
            "overview": {},
            "longestConversation": {},
            "longestMessage": {},
            "streak": {},
            "perspective": {},
            "nutrition": {},
        },
        "topics": [],
        "charts": {},
        "streamgraph": {},
        "frustration": {},
        "emojis": {},
        "tarot": {},
        "apiKey": "",
    }

    for strategy_name, result in all_results.items():
        if "error" in result and strategy_name != "topics":
            continue

        if strategy_name == "basic_counts":
            data["static"]["overview"] = result
        elif strategy_name == "first_conversation":
            data["static"]["firstConversation"] = result
        elif strategy_name == "conversation_durations":
            data["static"]["longestConversation"] = result
        elif strategy_name == "response_lengths":
            data["static"]["longestMessage"] = result
        elif strategy_name == "streaks":
            data["static"]["streak"] = result
        elif strategy_name == "token_counts":
            data["static"]["perspective"].update(result)
        elif strategy_name == "page_count":
            data["static"]["perspective"].update(result)
        elif strategy_name == "nutrition_label":
            data["static"]["nutrition"] = result
        elif strategy_name == "message_timing":
            data["charts"] = result
        elif strategy_name == "topics":
            # Merged strategy returns topics, tarot, and streamgraph
            data["topics"] = result.get("topics", [])
            data["tarot"] = result.get("tarot", {})
            data["streamgraph"] = result.get("streamgraph", {})
        elif strategy_name == "swear_apology":
            data["frustration"] = result
        elif strategy_name == "emoji_stats":
            data["emojis"] = result
        elif strategy_name == "api_key":
            data["apiKey"] = result.get("key", "")

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Generate GPT-in-Review website data from conversations.json"
    )
    parser.add_argument(
        "conversations_file",
        type=str,
        help="Path to conversations.json file",
    )
    args = parser.parse_args()

    # Validate input file
    conversations_path = Path(args.conversations_file)
    if not conversations_path.exists():
        print(f"ERROR: File not found: {conversations_path}")
        sys.exit(1)

    # Load environment
    load_env()

    # Add script directory to path for imports
    sys.path.insert(0, str(SCRIPT_DIR))

    # Load conversations
    conversations = load_conversations(conversations_path)

    # Discover strategies
    all_strategies = discover_strategies()
    strategy_names = sorted(all_strategies.keys())
    print(f"Running {len(strategy_names)} strategies in parallel...\n")

    # Create output directory
    output_dir = SCRIPT_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    # Track status for each strategy
    status = {name: "pending" for name in strategy_names}
    results = {}
    total_start = time.time()

    def print_status():
        """Print current status line."""
        running = [n for n, s in status.items() if s == "running"]
        done = sum(1 for s in status.values() if s in ("done", "error"))
        total = len(status)
        if running:
            print(f"\r[{done}/{total}] Running: {', '.join(running)}", end="", flush=True)

    # Run strategies in parallel
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}
        for name in strategy_names:
            strategy_class = all_strategies[name]
            future = executor.submit(run_strategy, strategy_class, conversations, output_dir)
            futures[future] = name
            status[name] = "running"

        print_status()

        for future in as_completed(futures):
            name = futures[future]
            strategy_name, result, elapsed, error = future.result()
            results[strategy_name] = result

            if error:
                status[name] = "error"
                print(f"\r[x] {name}: FAILED ({elapsed:.1f}s) - {error}")
            else:
                status[name] = "done"
                print(f"\r[✓] {name} ({elapsed:.1f}s)" + " " * 40)

            print_status()

    total_elapsed = time.time() - total_start
    print(f"\r" + " " * 60)  # Clear status line
    print(f"\nCompleted in {total_elapsed:.1f}s")

    # Count errors
    errors = sum(1 for s in status.values() if s == "error")
    if errors:
        print(f"  {errors} strategy(ies) failed")

    # Merge results
    data = merge_results(results)

    # Write data.json
    WEBSITE_DIR.mkdir(exist_ok=True)
    data_path = WEBSITE_DIR / "data.json"
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\nWrote {data_path}")

    # Check tarot image
    tarot_path = WEBSITE_DIR / "tarot_card.png"
    if tarot_path.exists():
        print(f"Wrote {tarot_path}")


if __name__ == "__main__":
    main()
