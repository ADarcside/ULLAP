"""Comprehensive unit tests for the Quartus STA report parser.

Covers all 9 audit requirements from Phase C:
1. Correct parsing of all three real reports.
2. Correct association of the three expected hold-slack pairs.
3. Missing required timing corner.
4. Missing slack measurement.
5. Duplicate or ambiguous corner section.
6. Unexpected report formatting.
7. Reordered timing-model sections.
8. Malformed numerical values.
9. Source-file or report-path failures.
"""
import os
import pytest
from sta_parser import parse_sta_slacks, parse_sta_slacks_with_provenance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_RPTS = {
    "lms": os.path.join(ROOT, "results", "quartus_reports", "lms_w12", "anc_de2_115.sta.rpt"),
    "nlms": os.path.join(ROOT, "results", "quartus_reports", "nlms_w12", "anc_de2_115.sta.rpt"),
    "shift": os.path.join(ROOT, "results", "quartus_reports", "shift_w12", "anc_de2_115.sta.rpt"),
}

VALID_TEMPLATE = """
Info: Analyzing Slow 1200mV 85C Model
Info (332146): Worst-case setup slack is 3.500
Info (332146): Worst-case hold slack is 0.450
Info: Analyzing Slow 1200mV 0C Model
Info (332146): Worst-case setup slack is 5.200
Info (332146): Worst-case hold slack is 0.360
Info: Analyzing Fast 1200mV 0C Model
Info (332146): Worst-case setup slack is 11.800
Info (332146): Worst-case hold slack is 0.190
"""


def test_1_parse_all_three_real_reports():
    """Verify that all three real hardware STA reports parse without errors."""
    for algo, path in REAL_RPTS.items():
        assert os.path.exists(path), f"Real report missing: {path}"
        slacks, prov = parse_sta_slacks_with_provenance(path)
        assert len(slacks) == 6
        assert len(prov) == 6
        for k in [
            "slack_setup_slow_85c", "slack_hold_slow_85c",
            "slack_setup_slow_0c",  "slack_hold_slow_0c",
            "slack_setup_fast_0c",  "slack_hold_fast_0c"
        ]:
            assert k in slacks
            assert isinstance(slacks[k], float)
            assert prov[k]["rpt_path"] == os.path.abspath(path)


def test_2_correct_association_of_hold_slack_pairs():
    """Verify exact reference hold-slack ground truth values across all corners."""
    expected_hold = {
        "lms":   {"slow_85c": 0.402, "slow_0c": 0.354, "fast_0c": 0.182},
        "nlms":  {"slow_85c": 0.401, "slow_0c": 0.353, "fast_0c": 0.181},
        "shift": {"slow_85c": 0.402, "slow_0c": 0.353, "fast_0c": 0.181},
    }
    expected_setup = {
        "lms":   {"slow_85c": 3.305, "slow_0c": 4.819, "fast_0c": 11.654},
        "nlms":  {"slow_85c": 3.798, "slow_0c": 5.115, "fast_0c": 11.707},
        "shift": {"slow_85c": 3.867, "slow_0c": 5.177, "fast_0c": 11.688},
    }
    for algo, path in REAL_RPTS.items():
        slacks = parse_sta_slacks(path)
        exp_h = expected_hold[algo]
        exp_s = expected_setup[algo]

        assert slacks["slack_hold_slow_85c"] == exp_h["slow_85c"]
        assert slacks["slack_hold_slow_0c"] == exp_h["slow_0c"]
        assert slacks["slack_hold_fast_0c"] == exp_h["fast_0c"]

        assert slacks["slack_setup_slow_85c"] == exp_s["slow_85c"]
        assert slacks["slack_setup_slow_0c"] == exp_s["slow_0c"]
        assert slacks["slack_setup_fast_0c"] == exp_s["fast_0c"]


def test_3_missing_required_timing_corner(tmp_path):
    """Fails explicitly if a required timing corner section is omitted."""
    # Omit Fast 1200mV 0C Model
    content = """
    Info: Analyzing Slow 1200mV 85C Model
    Info (332146): Worst-case setup slack is 3.500
    Info (332146): Worst-case hold slack is 0.450
    Info: Analyzing Slow 1200mV 0C Model
    Info (332146): Worst-case setup slack is 5.200
    Info (332146): Worst-case hold slack is 0.360
    """
    f = tmp_path / "missing_corner.sta.rpt"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="missing required slack measurements.*fast_0c"):
        parse_sta_slacks(str(f))


def test_4_missing_slack_measurement(tmp_path):
    """Fails explicitly if a setup or hold line is missing within an existing corner."""
    content = """
    Info: Analyzing Slow 1200mV 85C Model
    Info (332146): Worst-case setup slack is 3.500
    -- hold slack line omitted --
    Info: Analyzing Slow 1200mV 0C Model
    Info (332146): Worst-case setup slack is 5.200
    Info (332146): Worst-case hold slack is 0.360
    Info: Analyzing Fast 1200mV 0C Model
    Info (332146): Worst-case setup slack is 11.800
    Info (332146): Worst-case hold slack is 0.190
    """
    f = tmp_path / "missing_slack.sta.rpt"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="missing required slack measurements.*slack_hold_slow_85c"):
        parse_sta_slacks(str(f))


def test_5_duplicate_or_ambiguous_corner_section(tmp_path):
    """Fails explicitly if a timing-model section appears more than once."""
    content = """
    Info: Analyzing Slow 1200mV 85C Model
    Info (332146): Worst-case setup slack is 3.500
    Info (332146): Worst-case hold slack is 0.450
    Info: Analyzing Slow 1200mV 85C Model
    Info (332146): Worst-case setup slack is 3.490
    Info (332146): Worst-case hold slack is 0.440
    Info: Analyzing Slow 1200mV 0C Model
    Info (332146): Worst-case setup slack is 5.200
    Info (332146): Worst-case hold slack is 0.360
    Info: Analyzing Fast 1200mV 0C Model
    Info (332146): Worst-case setup slack is 11.800
    Info (332146): Worst-case hold slack is 0.190
    """
    f = tmp_path / "duplicate_corner.sta.rpt"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate or ambiguous timing-model section"):
        parse_sta_slacks(str(f))


def test_6_unexpected_report_formatting(tmp_path):
    """Handles varied spacing, case, and message ID formats gracefully or fails safely."""
    content = """
    Info: Analyzing Slow 1200mV 85C Model
    Info: Worst-case setup slack is 3.500
    Info: Worst-case hold slack is 0.450
    Info: Analyzing Slow 1200mV 0C Model
    Info (12345): Worst-case setup slack is 5.200
    Info (12345): Worst-case hold slack is 0.360
    Info: Analyzing Fast 1200mV 0C Model
    Info:  Worst-case   setup   slack   is   11.800
    Info:  Worst-case   hold   slack   is   0.190
    """
    f = tmp_path / "varied_format.sta.rpt"
    f.write_text(content, encoding="utf-8")
    slacks = parse_sta_slacks(str(f))
    assert slacks["slack_setup_slow_85c"] == 3.5
    assert slacks["slack_setup_fast_0c"] == 11.8
    assert slacks["slack_hold_fast_0c"] == 0.19


def test_7_reordered_timing_model_sections(tmp_path):
    """Correctly associates corners even if the sections appear in non-chronological order."""
    # Fast 0C first, then Slow 0C, then Slow 85C
    content = """
    Info: Analyzing Fast 1200mV 0C Model
    Info (332146): Worst-case setup slack is 11.800
    Info (332146): Worst-case hold slack is 0.190
    Info: Analyzing Slow 1200mV 0C Model
    Info (332146): Worst-case setup slack is 5.200
    Info (332146): Worst-case hold slack is 0.360
    Info: Analyzing Slow 1200mV 85C Model
    Info (332146): Worst-case setup slack is 3.500
    Info (332146): Worst-case hold slack is 0.450
    """
    f = tmp_path / "reordered.sta.rpt"
    f.write_text(content, encoding="utf-8")
    slacks = parse_sta_slacks(str(f))
    assert slacks["slack_setup_slow_85c"] == 3.500
    assert slacks["slack_hold_slow_85c"] == 0.450
    assert slacks["slack_setup_slow_0c"] == 5.200
    assert slacks["slack_hold_slow_0c"] == 0.360
    assert slacks["slack_setup_fast_0c"] == 11.800
    assert slacks["slack_hold_fast_0c"] == 0.190


def test_8_malformed_numerical_values(tmp_path):
    """Fails explicitly if a slack measurement contains non-numeric text like 'N/A' or 'INF'."""
    content = """
    Info: Analyzing Slow 1200mV 85C Model
    Info (332146): Worst-case setup slack is N/A
    Info (332146): Worst-case hold slack is 0.450
    Info: Analyzing Slow 1200mV 0C Model
    Info (332146): Worst-case setup slack is 5.200
    Info (332146): Worst-case hold slack is 0.360
    Info: Analyzing Fast 1200mV 0C Model
    Info (332146): Worst-case setup slack is 11.800
    Info (332146): Worst-case hold slack is 0.190
    """
    f = tmp_path / "malformed.sta.rpt"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed numerical slack 'N/A'"):
        parse_sta_slacks(str(f))


def test_9_source_file_or_report_path_failures():
    """Fails explicitly with FileNotFoundError when path does not exist."""
    bad_path = os.path.join(ROOT, "results", "quartus_reports", "nonexistent.sta.rpt")
    with pytest.raises(FileNotFoundError, match="STA report not found"):
        parse_sta_slacks(bad_path)
