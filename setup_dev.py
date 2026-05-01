#!/usr/bin/env python3
"""
Setup script for VisionFlow development.
"""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"▶ {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        return False


def main() -> None:
    """Run setup tasks."""
    print("🔧 VisionFlow Development Setup")
    print("="*60)

    all_passed = True

    # Format code
    if not run_command(["black", "visionflow", "tests"], "Formatting code with black"):
        all_passed = False

    # Sort imports
    if not run_command(["isort", "visionflow", "tests"], "Sorting imports with isort"):
        all_passed = False

    # Lint
    if not run_command(["flake8", "visionflow", "tests"], "Linting with flake8"):
        all_passed = False

    # Type check
    if not run_command(["mypy", "visionflow"], "Type checking with mypy"):
        all_passed = False

    # Run tests
    if not run_command(
        ["pytest", "tests", "-v", "--cov=visionflow", "--cov-report=term-missing"],
        "Running tests with pytest"
    ):
        all_passed = False

    # Summary
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ All checks passed!")
    else:
        print("❌ Some checks failed. Review output above.")
        sys.exit(1)
    print("="*60)


if __name__ == "__main__":
    main()
