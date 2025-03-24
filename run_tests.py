#!/usr/bin/env python3
"""Test runner for Terminal Command Runner MCP."""

import os
import sys
import argparse
import subprocess


def run_tests(coverage=False, verbose=False, specific_test=None):
    """Run the test suite with the specified options."""
    # Build the command
    cmd = ["python", "-m", "pytest"]
    
    # Add options
    if coverage:
        cmd.extend(["--cov=server", "--cov-report=term"])
    
    if verbose:
        cmd.append("-v")
    
    # Add specific test if provided
    if specific_test:
        cmd.append(specific_test)
    
    # Run the tests
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Terminal Command Runner MCP tests")
    parser.add_argument("--coverage", "-c", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Run with verbose output")
    parser.add_argument("--test", "-t", help="Run specific test file or test")
    
    args = parser.parse_args()
    
    exit_code = run_tests(
        coverage=args.coverage,
        verbose=args.verbose,
        specific_test=args.test
    )
    
    sys.exit(exit_code) 