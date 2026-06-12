"""Tests for scoring and percentile functions in app.py."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import (
    FOOTWORK_BLOCKS,
    SHOTSTOPPING_BLOCKS,
    color_for_score,
    compute_macro,
    compute_metric_score,
    enrich_all_scores,
    filter_dataframe,
    fmt_number,
    fmt_percent,
    format_market_value,
    metric_percentile,
    score_band,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Minimal DataFrame with the metrics needed by scoring functions."""
    return pd.DataFrame(
        {
            "name": ["Portero A", "Portero B", "Portero C"],
            "full_name": ["Portero A apellido", "Portero B apellido", "Portero C apellido"],
            "team_name": ["Equipo 1", "Equipo 2", "Equipo 3"],
            "source_competition": ["1RFEF", "1RFEF", "2RFEF"],
            "group_name": ["Grupo I", "Grupo II", "Grupo I"],
            "is_youth_team": [False, False, True],
            "on_loan": [False, True, False],
            "competition_matches_source": [True, True, False],
            "total_matches": [20, 15, 5],
            "minutes_share": [0.8, 0.6, 0.2],
            # Footwork metrics
            "passes_avg": [40.0, 30.0, 20.0],
            "received_pass_avg": [12.0, 10.0, 8.0],
            "accurate_passes_percent": [85.0, 75.0, 65.0],
            "forward_passes_avg": [15.0, 12.0, 9.0],
            "successful_forward_passes_percent": [70.0, 60.0, 50.0],
            "short_medium_pass_avg": [20.0, 15.0, 10.0],
            "accurate_short_medium_pass_percent": [88.0, 78.0, 68.0],
            "long_passes_avg": [8.0, 6.0, 4.0],
            "successful_long_passes_percent": [55.0, 45.0, 35.0],
            "average_pass_length": [25.0, 22.0, 19.0],
            "average_long_pass_length": [40.0, 38.0, 35.0],
            # Shotstopping metrics
            "shots_against_avg": [5.0, 4.0, 3.0],
            "save_percent": [80.0, 70.0, 60.0],
            "prevented_goals_avg": [0.4, 0.2, 0.0],
            "xg_save_avg": [3.5, 2.5, 1.5],
            "goalkeeper_exits_avg": [2.0, 1.5, 1.0],
            "gk_aerial_duels_avg": [1.5, 1.0, 0.5],
            "conceded_goals_avg": [1.0, 1.5, 2.0],
            "clean_sheets": [8.0, 5.0, 2.0],
        }
    )


# ── compute_metric_score ─────────────────────────────────────────────────────

class TestComputeMetricScore:
    def test_returns_series_of_correct_length(self, sample_df):
        result = compute_metric_score(sample_df, {"passes_avg": 1.0})
        assert len(result) == len(sample_df)

    def test_higher_value_gets_higher_score(self, sample_df):
        result = compute_metric_score(sample_df, {"passes_avg": 1.0})
        # Portero A has highest passes_avg → highest score
        assert result.iloc[0] > result.iloc[1] > result.iloc[2]

    def test_negative_weight_inverts_ranking(self, sample_df):
        result = compute_metric_score(sample_df, {"conceded_goals_avg": -1.0})
        # Portero A concedes least → best score with negative weight
        assert result.iloc[0] > result.iloc[1] > result.iloc[2]

    def test_scores_bounded_0_to_100(self, sample_df):
        result = compute_metric_score(sample_df, {"passes_avg": 1.0, "save_percent": 1.0})
        assert result.between(0, 100).all()

    def test_missing_metric_skipped_gracefully(self, sample_df):
        result = compute_metric_score(sample_df, {"nonexistent_metric": 1.0})
        assert (result == 0.0).all()

    def test_empty_metrics_returns_zeros(self, sample_df):
        result = compute_metric_score(sample_df, {})
        assert (result == 0.0).all()

    def test_all_nan_column_skipped(self):
        df = pd.DataFrame({"metric": [float("nan"), float("nan")]})
        result = compute_metric_score(df, {"metric": 1.0})
        assert (result == 0.0).all()


# ── metric_percentile ────────────────────────────────────────────────────────

class TestMetricPercentile:
    def test_highest_value_near_100(self, sample_df):
        pct = metric_percentile(sample_df, "passes_avg", 40.0, higher_is_better=True)
        assert pct == pytest.approx(100.0, abs=1.0)

    def test_lowest_value_near_0(self, sample_df):
        pct = metric_percentile(sample_df, "passes_avg", 20.0, higher_is_better=True)
        assert pct == pytest.approx(33.3, abs=1.0)

    def test_lower_is_better_inverts(self, sample_df):
        pct_hi = metric_percentile(sample_df, "conceded_goals_avg", 1.0, higher_is_better=True)
        pct_lo = metric_percentile(sample_df, "conceded_goals_avg", 1.0, higher_is_better=False)
        assert pct_hi + pct_lo == pytest.approx(100.0, abs=1.0)

    def test_none_value_returns_none(self, sample_df):
        assert metric_percentile(sample_df, "passes_avg", None) is None

    def test_missing_column_returns_none(self, sample_df):
        assert metric_percentile(sample_df, "nonexistent", 10.0) is None

    def test_empty_series_returns_none(self):
        df = pd.DataFrame({"metric": [float("nan"), float("nan")]})
        assert metric_percentile(df, "metric", 1.0) is None


# ── enrich_all_scores ────────────────────────────────────────────────────────

class TestEnrichAllScores:
    def test_adds_footwork_score_column(self, sample_df):
        result = enrich_all_scores(sample_df)
        assert "footwork_score" in result.columns

    def test_adds_shotstop_score_column(self, sample_df):
        result = enrich_all_scores(sample_df)
        assert "shotstop_score" in result.columns

    def test_adds_custom_score_column(self, sample_df):
        result = enrich_all_scores(sample_df)
        assert "custom_score" in result.columns

    def test_scores_bounded_0_to_100(self, sample_df):
        result = enrich_all_scores(sample_df)
        assert result["footwork_score"].between(0, 100).all()
        assert result["shotstop_score"].between(0, 100).all()

    def test_custom_metrics_applied(self, sample_df):
        result = enrich_all_scores(sample_df, custom_metrics={"save_percent": 1.0})
        assert result["custom_score"].gt(0).any()

    def test_no_custom_metrics_gives_zeros(self, sample_df):
        result = enrich_all_scores(sample_df)
        assert (result["custom_score"] == 0.0).all()

    def test_block_columns_added(self, sample_df):
        result = enrich_all_scores(sample_df)
        for block_name in FOOTWORK_BLOCKS:
            assert f"footwork__{block_name}" in result.columns
        for block_name in SHOTSTOPPING_BLOCKS:
            assert f"shotstop__{block_name}" in result.columns

    def test_best_player_has_higher_scores(self, sample_df):
        result = enrich_all_scores(sample_df)
        # Portero A has the best stats across the board
        assert result.loc[0, "footwork_score"] > result.loc[2, "footwork_score"]
        assert result.loc[0, "shotstop_score"] > result.loc[2, "shotstop_score"]


# ── filter_dataframe ─────────────────────────────────────────────────────────

class TestFilterDataframe:
    def _filter(self, df, **kwargs):
        defaults = dict(
            competition="ALL",
            group_name="Total",
            search_text="",
            min_matches=0,
            min_minutes_share=0.0,
            target_competition_only=False,
            include_youth=True,
            include_loans=True,
            include_unknown_group=True,
        )
        defaults.update(kwargs)
        return filter_dataframe(df, **defaults)

    def test_no_filters_returns_all(self, sample_df):
        result = self._filter(sample_df)
        assert len(result) == len(sample_df)

    def test_competition_filter(self, sample_df):
        result = self._filter(sample_df, competition="1RFEF")
        assert all(result["source_competition"] == "1RFEF")

    def test_group_filter(self, sample_df):
        result = self._filter(sample_df, group_name="Grupo I")
        assert all(result["group_name"] == "Grupo I")

    def test_search_by_name(self, sample_df):
        result = self._filter(sample_df, search_text="portero a")
        assert len(result) == 1
        assert result.iloc[0]["name"] == "Portero A"

    def test_search_by_team(self, sample_df):
        result = self._filter(sample_df, search_text="equipo 2")
        assert len(result) == 1
        assert result.iloc[0]["team_name"] == "Equipo 2"

    def test_search_no_regex_special_chars(self, sample_df):
        # Should not raise even with regex special characters
        result = self._filter(sample_df, search_text="portero (a)")
        assert isinstance(result, pd.DataFrame)

    def test_min_matches_filter(self, sample_df):
        result = self._filter(sample_df, min_matches=10)
        assert all(result["total_matches"] >= 10)

    def test_exclude_youth(self, sample_df):
        result = self._filter(sample_df, include_youth=False)
        assert not any(result["is_youth_team"])

    def test_exclude_loans(self, sample_df):
        result = self._filter(sample_df, include_loans=False)
        assert not any(result["on_loan"])

    def test_target_competition_only(self, sample_df):
        result = self._filter(sample_df, target_competition_only=True)
        assert all(result["competition_matches_source"])

    def test_empty_result_returns_empty_df(self, sample_df):
        result = self._filter(sample_df, search_text="xxxxxxxxxxx")
        assert len(result) == 0


# ── Formatting helpers ────────────────────────────────────────────────────────

class TestFormatHelpers:
    def test_fmt_number_none(self):
        assert fmt_number(None) == "-"

    def test_fmt_number_integer(self):
        assert fmt_number(1234) == "1.234"

    def test_fmt_number_float(self):
        assert fmt_number(1.567, 2) == "1,57"

    def test_fmt_percent_none(self):
        assert fmt_percent(None) == "-"

    def test_fmt_percent_value(self):
        assert fmt_percent(0.856) == "85,6%"

    def test_format_market_value_millions(self):
        assert format_market_value(1_500_000) == "€1,5M"

    def test_format_market_value_thousands(self):
        assert format_market_value(250_000) == "€250k"

    def test_format_market_value_zero(self):
        assert format_market_value(0) == "-"

    def test_format_market_value_none(self):
        assert format_market_value(None) == "-"

    def test_color_for_score_low(self):
        color = color_for_score(0)
        assert color.startswith("rgb(")

    def test_color_for_score_high(self):
        assert color_for_score(100) == color_for_score(100)

    def test_color_for_score_none(self):
        assert color_for_score(None) == "#7dc9ff"

    def test_score_band_high(self):
        label, _ = score_band(80)
        assert label == "ALTO"

    def test_score_band_medium(self):
        label, _ = score_band(60)
        assert label == "MEDIO"

    def test_score_band_low(self):
        label, _ = score_band(30)
        assert label == "BAJO"

    def test_score_band_none(self):
        label, _ = score_band(None)
        assert label == "SIN MUESTRA"
