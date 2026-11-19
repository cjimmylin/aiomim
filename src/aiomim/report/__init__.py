"""The curator review page: one self-contained HTML file per run."""

from .build import build_report, collect_report_data

__all__ = ["build_report", "collect_report_data"]
