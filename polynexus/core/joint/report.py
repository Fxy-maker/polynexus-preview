"""Joint analysis report builder."""

import json
from io import BytesIO


def make_joint_report(name: str, figures: dict, tables: list) -> dict:
    """Create a standardised joint analysis report dictionary.

    Returns:
        {
            'name': str,
            'figures': {name: BytesIO, ...},
            'tables': list[pd.DataFrame],
            'summary': str,
        }
    """
    summary_parts = [f"Joint report: {name}"]
    if figures:
        summary_parts.append(f"{len(figures)} figures generated.")
    if tables:
        summary_parts.append(f"{len(tables)} data tables.")
    if not figures and not tables:
        summary_parts.append("No data available for comparison.")

    return {
        'name': name,
        'figures': figures,
        'tables': tables,
        'summary': ' '.join(summary_parts),
    }
