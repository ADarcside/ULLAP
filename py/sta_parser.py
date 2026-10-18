"""Quartus TimeQuest STA Report Parser.

Provides robust, verified extraction of setup and hold slacks across
timing corners from Quartus .sta.rpt files.
"""
import os
import re

CORNER_MAP = {
    "Slow 1200mV 85C": "slow_85c",
    "Slow 1200mV 0C":  "slow_0c",
    "Fast 1200mV 0C":  "fast_0c",
}

REQUIRED_KEYS = [
    "slack_setup_slow_85c", "slack_hold_slow_85c",
    "slack_setup_slow_0c",  "slack_hold_slow_0c",
    "slack_setup_fast_0c",  "slack_hold_fast_0c",
]


def parse_sta_slacks_with_provenance(rpt_path):
    """Parse Worst-case setup and hold slacks with provenance details.

    Returns:
        tuple: (slacks_dict, provenance_dict)
        where slacks_dict maps key -> float slack value
        and provenance_dict maps key -> dict(value, corner, corner_label, line_no, rpt_path)
    """
    if not os.path.exists(rpt_path):
        raise FileNotFoundError(f"STA report not found: {rpt_path}")

    result = {}
    provenance = {}
    seen_corners = set()
    current_corner_key = None
    current_corner_label = None

    slack_regex = re.compile(r"^Info\s*(?:\(\d+\))?:\s*Worst-case\s+(setup|hold)\s+slack\s+is\s+(\S+)", re.IGNORECASE)

    with open(rpt_path, "r", encoding="utf-8", errors="replace") as fh:
        for line_no, line in enumerate(fh, 1):
            # Detect model section header
            matched_header = False
            for label, key in CORNER_MAP.items():
                if f"Analyzing {label} Model" in line:
                    if label in seen_corners:
                        raise ValueError(
                            f"Duplicate or ambiguous timing-model section '{label}' "
                            f"detected at line {line_no} in {rpt_path}"
                        )
                    seen_corners.add(label)
                    current_corner_key = key
                    current_corner_label = label
                    matched_header = True
                    break

            if matched_header:
                continue

            if current_corner_key is None:
                continue

            m = slack_regex.search(line.strip())
            if m:
                kind = m.group(1).lower()
                raw_val = m.group(2)
                try:
                    val = float(raw_val)
                except ValueError as exc:
                    raise ValueError(
                        f"Malformed numerical slack '{raw_val}' at line {line_no} "
                        f"in corner '{current_corner_label}' of {rpt_path}"
                    ) from exc

                key = f"slack_{kind}_{current_corner_key}"
                if key in result:
                    raise ValueError(
                        f"Duplicate measurement for '{key}' at line {line_no} "
                        f"in corner '{current_corner_label}' of {rpt_path}"
                    )

                result[key] = val
                provenance[key] = {
                    "value": val,
                    "kind": kind,
                    "corner_key": current_corner_key,
                    "corner_label": current_corner_label,
                    "line_no": line_no,
                    "rpt_path": os.path.abspath(rpt_path),
                }

    missing_keys = [k for k in REQUIRED_KEYS if k not in result]
    if missing_keys:
        raise ValueError(
            f"parse_sta_slacks: incomplete report {rpt_path}; missing required slack measurements: {missing_keys}"
        )

    return result, provenance


def parse_sta_slacks(rpt_path):
    """Parse Worst-case setup and hold slacks from a Quartus .sta.rpt file.

    Returns a dict mapping required keys:
      slack_setup_slow_85c, slack_hold_slow_85c
      slack_setup_slow_0c,  slack_hold_slow_0c
      slack_setup_fast_0c,  slack_hold_fast_0c
    to their float values.
    """
    slacks, _ = parse_sta_slacks_with_provenance(rpt_path)
    return slacks
