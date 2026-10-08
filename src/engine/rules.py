"""Helpers that read the workflow definition cells coming from workflows.xlsx.

The Excel sheet is the source of truth, so the engine reads Steps, Decision_Logic
and Tools_Required from it at run time instead of hard-coding them.
"""
import re

# Used only when the Excel cell does not contain a number.
DEFAULT_TIME_THRESHOLD_SECONDS = 60.0


def parse_steps(steps_text):
    """Split 'A → B → C' into ['A', 'B', 'C']."""
    parts = re.split(r'\s*(?:→|->|=>)\s*', str(steps_text or ''))
    return [p.strip() for p in parts if p.strip()]


def parse_tools(tools_text):
    """Split 'CSV reader; calculator' into ['CSV reader', 'calculator']."""
    return [t.strip() for t in str(tools_text or '').split(';') if t.strip()]


def parse_rules(decision_logic):
    """Extract numeric thresholds written in the Decision_Logic cell.

    'Flag when price difference exceeds 10%'  -> {'percent_threshold': 10.0}
    'average execution time above 30 seconds' -> {'time_threshold_seconds': 30.0}
    """
    text = str(decision_logic or '')
    rules = {}
    pct = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if pct:
        rules['percent_threshold'] = float(pct.group(1))
    tm = re.search(r'(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?)\b', text, re.I)
    if tm:
        value = float(tm.group(1))
        if tm.group(2).lower().startswith('min'):
            value *= 60
        rules['time_threshold_seconds'] = value
    return rules
