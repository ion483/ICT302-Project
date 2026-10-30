"""
@file main.py
@brief Command-line entry point for local CopyQ analysis.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from core.analysis_pipeline import AnalysisPipeline
from core.report_generator import generate_html_report


def build_parser() -> argparse.ArgumentParser:
    """
    @brief Create the command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Analyse one Word document locally. "
            "CopyQ reports descriptive metadata only."
        )
    )

    parser.add_argument(
        "document",
        help="Path to the .docx document to analyse.",
    )
    parser.add_argument(
        "--workspace",
        default="storage/temp_workspace",
        help="Directory used for verified working copies.",
    )
    parser.add_argument(
        "--top-sessions",
        type=int,
        default=5,
        help="Number of highest-word-count RSID sessions to include.",
    )
    parser.add_argument(
        "--report",
        help="Optional path for a generated HTML report.",
    )

    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """
    @brief Run CopyQ analysis from the command line.

    @param arguments Optional arguments for testing. Uses terminal arguments
                     when no value is supplied.
    @return Zero when analysis succeeds; otherwise one.
    """
    parser = build_parser()
    args = parser.parse_args(arguments)

    if args.top_sessions < 1:
        parser.error("--top-sessions must be at least 1")

    pipeline = AnalysisPipeline(args.workspace)
    result = pipeline.analyse(args.document, args.top_sessions)

    if not result["ok"]:
        print(f"Analysis failed: {result['message']}")
        return 1

    metrics = result["metrics"]
    integrity = result["integrity"]

    print("Analysis complete.")
    print(f"Working copy verified: {integrity['working_copy_verified']}")
    print(f"Total words: {metrics['total_word_count']}")
    print(f"Unique RSIDs: {metrics['unique_rsid_count']}")
    print(f"Top sessions found: {len(result['top_sessions'])}")

    if args.report:
        report_path = generate_html_report(result, args.report)
        print(f"HTML report created: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
