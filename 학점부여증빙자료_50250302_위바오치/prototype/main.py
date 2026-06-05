#!/usr/bin/env python3
"""Main entry point for the multi-agent shared memory experiment.

Usage:
    python -m prototype.main
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.experiments.runner import ExperimentRunner
from prototype.experiments.reporter import print_results, export_csv


def main():
    runner = ExperimentRunner()

    try:
        runner.run_all()
        summaries = runner.get_results()
        print_results(summaries)
        export_csv(summaries, output_dir=os.path.dirname(os.path.abspath(__file__)))
    finally:
        runner.close()


if __name__ == "__main__":
    main()
