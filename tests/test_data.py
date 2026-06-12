"""Tests for data loading and processing in build_goalkeeper_market_dashboard.py."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_goalkeeper_market_dashboard import (
    ALIAS_MAP,
    REQUIRED_COLUMNS,
    as_float,
    as_int,
    build_metadata,
    detect_group,
    is_youth_team,
    minutes_share,
    slugify,
)


# ── slugify ───────────────────────────────────────────────────────────────────

class TestSlugify:
    def test_lowercases_and_strips(self):
        assert slugify("  Real Madrid  ") == "real madrid"

    def test_removes_accents(self):
        assert slugify("Málaga") == "malaga"

    def test_normalizes_special_chars(self):
        assert slugify("Córdoba CF") == "cordoba cf"

    def test_applies_alias(self):
        assert slugify("Athletic Club") == "athletic bilbao"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_none_value(self):
        assert slugify(None) == ""


# ── as_float / as_int ────────────────────────────────────────────────────────

class TestConversions:
    def test_as_float_valid(self):
        assert as_float("3.14") == pytest.approx(3.14)

    def test_as_float_none(self):
        assert as_float(None) is None

    def test_as_float_empty(self):
        assert as_float("") is None

    def test_as_float_invalid(self):
        assert as_float("abc") is None

    def test_as_int_rounds(self):
        assert as_int("2.7") == 3

    def test_as_int_none(self):
        assert as_int(None) is None


# ── is_youth_team ─────────────────────────────────────────────────────────────

class TestIsYouthTeam:
    def test_u21_in_name(self):
        assert is_youth_team("Real Madrid U21", "") is True

    def test_juvenil_token(self):
        assert is_youth_team("CD Juvenil Madrid", "") is True

    def test_normal_team(self):
        assert is_youth_team("Unionistas de Salamanca", "Primera Division RFEF") is False

    def test_u19_in_competition(self):
        assert is_youth_team("Some Team", "Liga U19") is True


# ── minutes_share ─────────────────────────────────────────────────────────────

class TestMinutesShare:
    def test_full_season(self):
        assert minutes_share(38 * 90, 38) == pytest.approx(1.0)

    def test_half_season(self):
        assert minutes_share(19 * 90, 38) == pytest.approx(0.5)

    def test_capped_at_one(self):
        assert minutes_share(9999, 38) == pytest.approx(1.0)

    def test_none_minutes(self):
        assert minutes_share(None, 38) is None

    def test_zero_expected(self):
        assert minutes_share(100, 0) is None


# ── detect_group ─────────────────────────────────────────────────────────────

class TestDetectGroup:
    def test_known_team(self):
        assert detect_group("1RFEF", "Unionistas de Salamanca") == "Grupo I"

    def test_alias_resolution(self):
        assert detect_group("1RFEF", "Unionistas") == "Grupo I"

    def test_unknown_team(self):
        assert detect_group("1RFEF", "Equipo Desconocido XYZ") == "Sin grupo"

    def test_national2_group_from_reference_table(self):
        assert detect_group("National2", "Cannes") == "Grupo C"


# ── load_goalkeepers error handling ──────────────────────────────────────────

class TestLoadGoalkeepersErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path, monkeypatch):
        import scripts.build_goalkeeper_market_dashboard as mod

        fake_competitions = {
            "TEST": {
                "file": tmp_path / "nonexistent.csv",
                "target_competition_name": "Test League",
                "expected_matches": 30,
                "groups": {},
            }
        }
        monkeypatch.setattr(mod, "COMPETITIONS", fake_competitions)
        monkeypatch.setattr(mod, "GROUP_INDEX", {"TEST": {}})
        with pytest.raises(FileNotFoundError, match="no encontrado"):
            mod.load_goalkeepers()

    def test_missing_columns_raises_value_error(self, tmp_path, monkeypatch):
        import scripts.build_goalkeeper_market_dashboard as mod

        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("only_one_column\nvalue\n", encoding="utf-8")

        fake_competitions = {
            "TEST": {
                "file": csv_path,
                "target_competition_name": "Test League",
                "expected_matches": 30,
                "groups": {},
            }
        }
        monkeypatch.setattr(mod, "COMPETITIONS", fake_competitions)
        monkeypatch.setattr(mod, "GROUP_INDEX", {"TEST": {}})
        with pytest.raises(ValueError, match="columnas requeridas"):
            mod.load_goalkeepers()

    def test_valid_csv_loads_only_goalkeepers(self, tmp_path, monkeypatch):
        import scripts.build_goalkeeper_market_dashboard as mod

        headers = list(REQUIRED_COLUMNS) + [
            "image", "current_team_logo", "current_team_name", "age",
            "birth_date", "birth_country_name", "passport_country_names",
            "foot", "height", "weight", "contract_expires", "market_value",
            "on_loan", "save_percent", "xg_save_avg", "prevented_goals_avg",
            "conceded_goals_avg", "shots_against_avg", "clean_sheets",
            "goalkeeper_exits_avg", "gk_aerial_duels_avg", "passes_avg",
            "received_pass_avg", "accurate_passes_percent", "forward_passes_avg",
            "successful_forward_passes_percent", "back_passes_avg",
            "successful_back_passes_percent", "long_passes_avg",
            "successful_long_passes_percent", "short_medium_pass_avg",
            "accurate_short_medium_pass_percent", "average_pass_length",
            "average_long_pass_length",
        ]
        csv_path = tmp_path / "test.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerow({h: ("GK" if h == "primary_position" else "TestTeam" if h == "current_team_name" else "P1" if h == "id" else "Test" if h == "name" else "") for h in headers})
            writer.writerow({h: ("FW" if h == "primary_position" else "TeamB" if h == "current_team_name" else "P2" if h == "id" else "Forward" if h == "name" else "") for h in headers})

        fake_competitions = {
            "TEST": {
                "file": csv_path,
                "target_competition_name": "Test League",
                "expected_matches": 30,
                "groups": {},
            }
        }
        monkeypatch.setattr(mod, "COMPETITIONS", fake_competitions)
        monkeypatch.setattr(mod, "GROUP_INDEX", {"TEST": {}})

        result = mod.load_goalkeepers()
        assert len(result) == 1
        assert result[0]["name"] == "Test"


def test_derive_lateral_passes_from_directional_categories():
    from scripts.build_goalkeeper_market_dashboard import derive_lateral_passes

    lateral, accuracy = derive_lateral_passes(
        {
            "passes_avg": "40",
            "accurate_passes_percent": "80",
            "forward_passes_avg": "15",
            "successful_forward_passes_percent": "70",
            "back_passes_avg": "5",
            "successful_back_passes_percent": "90",
        }
    )

    assert lateral == pytest.approx(20.0)
    assert accuracy == pytest.approx(85.0)


# ── build_metadata ────────────────────────────────────────────────────────────

class TestBuildMetadata:
    def test_returns_expected_keys(self):
        meta = build_metadata([])
        assert "competition_order" in meta
        assert "group_order" in meta
        assert "summary" in meta
        assert "notes" in meta

    def test_notes_is_list(self):
        meta = build_metadata([])
        assert isinstance(meta["notes"], list)
        assert len(meta["notes"]) > 0

    def test_competition_order_includes_expanded_pool(self):
        meta = build_metadata([])
        assert "National2" in meta["competition_order"]
        assert "Portugal4" in meta["competition_order"]
