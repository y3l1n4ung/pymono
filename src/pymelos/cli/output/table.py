"""Table rendering utility for CLI output."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def print_table(
    data: Sequence[dict[str, Any]],
    columns: list[str],
    column_widths: dict[str, int] | None = None,
) -> None:
    """Print a formatted table to stdout.

    Args:
        data: List of dictionaries containing the row data.
        columns: List of keys to include as columns.
        column_widths: Optional mapping of column name to width.
    """
    if not data:
        return

    # 1. Calculate or use provided widths
    widths = {}
    for col in columns:
        if column_widths and col in column_widths:
            widths[col] = column_widths[col]
        else:
            # Auto-calculate based on the longest string in the column or the header name
            max_content = max((len(str(row.get(col, ""))) for row in data), default=0)
            widths[col] = max(len(col), max_content)

    # 2. Construct the format string dynamically
    # Result looks like: "{:<25} | {:<15} | {:<8}"
    format_str = " | ".join([f"{{:<{widths[col]}}}" for col in columns])

    # 3. Create the header and separator line
    header_titles = [col.upper() for col in columns]
    header_row = format_str.format(*header_titles)
    separator = "-" * len(header_row)

    # 4. Print the table to the console
    print(separator)
    print(header_row)
    print(separator)

    for row in data:
        # Extract values in order of columns list
        values = [str(row.get(col, "")) for col in columns]
        print(format_str.format(*values))

    print(separator)
