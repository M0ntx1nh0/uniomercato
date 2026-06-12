"""PDF report generator for UnioMercato goalkeeper scouting."""
from __future__ import annotations

import math
import tempfile
from datetime import date
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fpdf import FPDF
from project_paths import asset_path

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
LOGO_MCODE = asset_path("mcode", "MCODE Sport Analytics.png")

def _first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


# Prefer the cleanest transparent asset if available.
LOGO_CLUB = _first_existing([
    asset_path("escudo", "IMG_2027-removebg-preview.png"),
    asset_path("escudo", "Escudo_Of.png"),
    asset_path("escudo", "Escudo Of.jpg"),
    asset_path("escudo", "IMG_2027.JPG"),
])
AUTHOR = "Ramón Codesido"

# Prefer Arial locally and use Matplotlib's bundled DejaVu fonts in deployments.
# Core PDF fonts such as Helvetica cannot encode Spanish accents or the euro sign.
_SYSTEM_FONTS_DIR = Path("/System/Library/Fonts/Supplemental")
_MPL_FONTS_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
FONT_REGULAR = _first_existing([
    _SYSTEM_FONTS_DIR / "Arial.ttf",
    _MPL_FONTS_DIR / "DejaVuSans.ttf",
])
FONT_BOLD = _first_existing([
    _SYSTEM_FONTS_DIR / "Arial Bold.ttf",
    _MPL_FONTS_DIR / "DejaVuSans-Bold.ttf",
])
FONT_ITALIC = _first_existing([
    _SYSTEM_FONTS_DIR / "Arial Italic.ttf",
    _MPL_FONTS_DIR / "DejaVuSans-Oblique.ttf",
])
_USE_TTF = FONT_REGULAR.exists() and FONT_BOLD.exists()

# ── Color palette (RGB tuples, print-friendly on white) ───────────────────────
C_NAVY = (13, 27, 87)
C_BLUE = (29, 87, 202)
C_TEAL = (0, 168, 132)
C_LIGHT_BG = (240, 245, 255)
C_MUTED = (110, 130, 180)
C_WHITE = (255, 255, 255)
C_DARK = (22, 24, 48)
C_BORDER = (210, 220, 240)
C_GREEN = (40, 180, 100)
C_YELLOW = (210, 150, 30)
C_RED = (200, 60, 80)
C_ORANGE = (220, 110, 30)
C_TEAL_LIGHT = (63, 200, 170)


def _score_color(score: float | None) -> tuple[int, int, int]:
    if score is None:
        return C_MUTED
    s = max(0.0, min(float(score), 100.0))
    if s >= 75:
        return C_GREEN
    if s >= 55:
        return C_BLUE
    if s >= 40:
        return C_YELLOW
    return C_RED


def _fmt_val(value, decimals: int = 2) -> str:
    if value is None:
        return "-"
    try:
        f = float(value)
        if math.isnan(f):
            return "-"
        return f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_market(value) -> str:
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if v <= 0 or math.isnan(v):
        return "-"
    if v >= 1_000_000:
        return f"€{v/1_000_000:.1f}M".replace(".", ",")
    return f"€{int(round(v/1000))}k"


def _metric_percentile(reference_df: pd.DataFrame, metric: str, value, higher_is_better: bool = True) -> float | None:
    if value is None or metric not in reference_df.columns:
        return None
    try:
        fval = float(value)
        if math.isnan(fval):
            return None
    except (TypeError, ValueError):
        return None
    series = pd.to_numeric(reference_df[metric], errors="coerce").dropna()
    if series.empty:
        return None
    pct = float((series <= fval).mean() * 100)
    return pct if higher_is_better else 100 - pct


_STRENGTH_METRIC_MAP: list[tuple[str, str, bool]] = [
    ("Paradas %", "save_percent", True),
    ("Goles evitados/90", "prevented_goals_avg", True),
    ("Salidas/90", "goalkeeper_exits_avg", True),
    ("Duelos aéreos/90", "gk_aerial_duels_avg", True),
    ("Pases/90", "passes_avg", True),
    ("Precisión pases %", "accurate_passes_percent", True),
    ("Pases adelante/90", "forward_passes_avg", True),
    ("Precisión adelante %", "successful_forward_passes_percent", True),
    ("Pases largos/90", "long_passes_avg", True),
    ("Precisión largos %", "successful_long_passes_percent", True),
    ("% minutos", "minutes_share", True),
    ("Goles recibidos/90", "conceded_goals_avg", False),
]


def _strengths_risks(row: pd.Series, reference_df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    rows = []
    for label, metric, higher in _STRENGTH_METRIC_MAP:
        value = row.get(metric)
        pct = _metric_percentile(reference_df, metric, value, higher)
        if pct is None:
            continue
        rows.append({"label": label, "metric": metric, "value": value, "pct": pct})
    ordered = sorted(rows, key=lambda x: x["pct"], reverse=True)
    return ordered[:4], ordered[-4:]


# ── PDF class ─────────────────────────────────────────────────────────────────

class GoalkeeperReport(FPDF):
    """Landscape A4 goalkeeper scouting PDF report."""

    # Page dimensions (landscape A4)
    PW = 297.0
    PH = 210.0
    MARGIN = 8.0
    HEADER_H = 17.0
    FOOTER_Y = 200.0

    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.set_margins(0, 0, 0)
        self._page_counter = 0

        if _USE_TTF:
            self.add_font("Arial", style="", fname=str(FONT_REGULAR))
            self.add_font("Arial", style="B", fname=str(FONT_BOLD))
            if FONT_ITALIC.exists():
                self.add_font("Arial", style="I", fname=str(FONT_ITALIC))
            self._font_name = "Arial"
        else:
            self._font_name = "Helvetica"

    def _font(self, style: str = "", size: float = 9) -> None:
        """Set font using the registered family (TTF if available, Helvetica fallback)."""
        self.set_font(self._font_name, style=style, size=size)

    # ── Repeated elements ────────────────────────────────────────────────────

    def _draw_header(self) -> None:
        """White header strip with logos and report title."""
        self.set_fill_color(*C_WHITE)
        self.rect(0, 0, self.PW, self.HEADER_H, style="F")

        # Club logo - left
        if LOGO_CLUB.exists():
            self.image(str(LOGO_CLUB), x=self.MARGIN, y=1.6, h=13)

        # MCode logo - right
        if LOGO_MCODE.exists():
            self.image(str(LOGO_MCODE), x=self.PW - 57, y=1.8, h=12)

        # Report name center
        self._font("B", 8)
        self.set_text_color(*C_TEAL)
        self.set_xy(50, 6)
        self.cell(197, 5, "UnioMercato  -  Scouting de Porteros", align="C")

        # Bottom separator
        self.set_draw_color(*C_TEAL)
        self.set_line_width(0.5)
        self.line(0, self.HEADER_H, self.PW, self.HEADER_H)

    def _draw_footer(self) -> None:
        """Footer with page number and author."""
        self._page_counter += 1
        y = self.FOOTER_Y

        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.line(self.MARGIN, y, self.PW - self.MARGIN, y)

        self._font("", 7)
        self.set_text_color(*C_MUTED)

        # Page number - center
        self.set_xy(0, y + 2)
        self.cell(self.PW, 5, str(self._page_counter), align="C")

        # Author - right
        self.set_xy(self.MARGIN, y + 2)
        self.cell(self.PW - self.MARGIN * 2, 5, f"Informe realizado por: {AUTHOR}", align="R")

    # ── Cover page ───────────────────────────────────────────────────────────

    def add_cover(self, filters_summary: str, n_visible: int, top_n: int) -> None:
        self.add_page()

        STRIP_W = 64.0
        SEP_W = 2.5

        # Left background strip
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, STRIP_W, self.PH, style="F")

        # Vertical separator
        self.set_fill_color(*C_TEAL)
        self.rect(STRIP_W, 0, SEP_W, self.PH, style="F")

        # MCode logo — top of the strip
        if LOGO_MCODE.exists():
            mcode_w = 50
            mcode_x = (STRIP_W - mcode_w) / 2
            self.image(str(LOGO_MCODE), x=mcode_x, y=14, w=mcode_w)

        # Right side content
        rx = STRIP_W + SEP_W + 14
        rw = self.PW - rx - 14

        # Unionistas logo — top-right of the white area
        if LOGO_CLUB.exists():
            club_h = 28
            club_x = self.PW - 14 - club_h  # right-aligned with margin
            self.image(str(LOGO_CLUB), x=club_x, y=10, h=club_h)

        # Season badge — centered
        self._font("B", 9)
        self.set_text_color(*C_TEAL)
        self.set_xy(rx, 44)
        self.cell(rw - club_h - 6, 6, "TEMPORADA 2025-26", align="C")

        # Main title — centered, below the logo
        self._font("B", 30)
        self.set_text_color(*C_DARK)
        self.set_xy(rx, 54)
        self.multi_cell(rw, 13, "UnioMercato\nScouting de Porteros", align="C")

        # Accent underline — centered
        line_w = 50.0
        self.set_fill_color(*C_TEAL)
        self.rect(rx + (rw - line_w) / 2, 92, line_w, 1.8, style="F")

        # Subtitle — centered
        self._font("", 11)
        self.set_text_color(70, 80, 115)
        self.set_xy(rx, 98)
        self.cell(rw, 7, f"Porteros analizados: {n_visible}  ·  Top {top_n} en informe", align="C")

        # Filters label — centered
        self._font("B", 8)
        self.set_text_color(*C_MUTED)
        self.set_xy(rx, 111)
        self.cell(rw, 5, "FILTROS APLICADOS", align="C")

        # Filters value — centered
        self._font("", 9)
        self.set_text_color(70, 80, 115)
        self.set_xy(rx, 118)
        self.multi_cell(rw, 5, filters_summary, align="C")

        # Date — centered
        self._font("", 8)
        self.set_text_color(*C_MUTED)
        self.set_xy(rx, 192)
        self.cell(rw, 5, date.today().strftime("%d / %m / %Y"), align="C")

    # ── Index page ───────────────────────────────────────────────────────────

    def add_index(self, top_n: int) -> None:
        self.add_page()
        self._draw_header()

        self._font("B", 22)
        self.set_text_color(*C_NAVY)
        self.set_xy(self.MARGIN, self.HEADER_H + 6)
        self.cell(self.PW - self.MARGIN * 2, 10, "Índice de contenidos")

        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.line(self.MARGIN, self.HEADER_H + 18, self.PW - self.MARGIN, self.HEADER_H + 18)

        entries = [
            ("Resumen ejecutivo", "Filtros aplicados, estadísticas globales, scatter plot y ranking", "3"),
            (f"Ranking Top {top_n}", f"Los {top_n} mejores porteros según el criterio seleccionado", "3"),
            ("Fichas individuales", f"Un informe detallado por cada uno de los {top_n} porteros del ranking", "4 – " + str(3 + top_n)),
        ]

        y = self.HEADER_H + 23
        for i, (title, desc, pages) in enumerate(entries):
            # Row background
            if i % 2 == 0:
                self.set_fill_color(*C_LIGHT_BG)
                self.rect(self.MARGIN, y, self.PW - self.MARGIN * 2, 16, style="F")

            # Number badge
            self.set_fill_color(*C_NAVY)
            self.rect(self.MARGIN, y + 2, 10, 10, style="F")
            self._font("B", 9)
            self.set_text_color(*C_WHITE)
            self.set_xy(self.MARGIN, y + 3)
            self.cell(10, 8, str(i + 1), align="C")

            # Title
            self._font("B", 11)
            self.set_text_color(*C_DARK)
            self.set_xy(self.MARGIN + 13, y + 2)
            self.cell(160, 6, title)

            # Description
            self._font("", 9)
            self.set_text_color(*C_MUTED)
            self.set_xy(self.MARGIN + 13, y + 9)
            self.cell(160, 5, desc)

            # Page ref
            self._font("B", 9)
            self.set_text_color(*C_BLUE)
            self.set_xy(self.PW - self.MARGIN - 35, y + 4)
            self.cell(33, 8, f"Pág. {pages}", align="R")

            y += 18

        self._draw_footer()

    # ── Summary page ─────────────────────────────────────────────────────────

    def add_summary(
        self,
        df: pd.DataFrame,
        top_n: int,
        filters_summary: str,
        ranking_label: str,
        scatter_path: str | None,
    ) -> None:
        self.add_page()
        self._draw_header()

        cy = self.HEADER_H + 4

        # Section title
        self._font("B", 15)
        self.set_text_color(*C_NAVY)
        self.set_xy(self.MARGIN, cy)
        self.cell(self.PW - self.MARGIN * 2, 8, "Resumen ejecutivo")
        cy += 9

        # Filters strip
        self.set_fill_color(*C_LIGHT_BG)
        self.rect(self.MARGIN, cy, self.PW - self.MARGIN * 2, 8, style="F")
        self._font("B", 7)
        self.set_text_color(*C_NAVY)
        self.set_xy(self.MARGIN + 3, cy + 2)
        self.cell(22, 4, "FILTROS:")
        self._font("", 7)
        self.set_text_color(70, 80, 115)
        self.set_xy(self.MARGIN + 25, cy + 2)
        self.cell(self.PW - self.MARGIN * 2 - 28, 4, filters_summary[:120])
        cy += 11

        # KPI boxes
        kpis = [
            ("Porteros visibles", str(len(df))),
            ("Criterio", ranking_label),
            ("Pies (media)", _fmt_val(df["footwork_score"].mean(), 1) if len(df) else "-"),
            ("Paradas (media)", _fmt_val(df["shotstop_score"].mean(), 1) if len(df) else "-"),
            ("% minutos (media)", f"{float(df['minutes_share'].mean())*100:.1f}%" if len(df) else "-"),
        ]
        box_w = (self.PW - self.MARGIN * 2 - 4) / len(kpis)
        bx = self.MARGIN
        for label, val in kpis:
            self.set_fill_color(*C_NAVY)
            self.rect(bx, cy, box_w - 1, 13, style="F")
            self._font("B", 12)
            self.set_text_color(*C_WHITE)
            self.set_xy(bx, cy + 1)
            self.cell(box_w - 1, 7, val[:14], align="C")
            self._font("", 6)
            self.set_text_color(*C_TEAL_LIGHT)
            self.set_xy(bx, cy + 8)
            self.cell(box_w - 1, 4, label.upper(), align="C")
            bx += box_w

        cy += 16

        # Two-column layout: scatter | ranking table
        scatter_w = 130.0 if scatter_path else 0.0
        table_x = self.MARGIN + scatter_w + (4 if scatter_path else 0)
        table_w = self.PW - table_x - self.MARGIN

        # Scatter plot image
        if scatter_path:
            self.image(scatter_path, x=self.MARGIN, y=cy, w=scatter_w, h=self.FOOTER_Y - cy - 2)

        # Ranking table
        top_df = df.head(top_n)
        th = 7.0

        # Table header
        self.set_fill_color(*C_NAVY)
        self.rect(table_x, cy, table_w, th, style="F")
        self._font("B", 7)
        self.set_text_color(*C_WHITE)

        cols = [("#", 6), ("Jugador", 44), ("Equipo", 34), ("Cat.", 14), ("Grupo", 22), ("Pies", 13), ("Paradas", 14)]
        cx = table_x
        for col_label, col_w in cols:
            self.set_xy(cx, cy)
            left_align = col_label in ("Jugador", "Equipo", "Grupo")
            self.cell(col_w, th, col_label, align="L" if left_align else "C")
            cx += col_w

        ty = cy + th
        for pos, (_, row) in enumerate(top_df.iterrows(), start=1):
            if pos % 2 == 0:
                self.set_fill_color(*C_LIGHT_BG)
                self.rect(table_x, ty, table_w, th, style="F")

            self.set_draw_color(*C_BORDER)
            self.set_line_width(0.1)
            self.line(table_x, ty + th, table_x + table_w, ty + th)

            cx = table_x
            # Rank
            self._font("B", 7)
            self.set_text_color(*C_NAVY)
            self.set_xy(cx, ty)
            self.cell(6, th, str(pos), align="C")
            cx += 6

            # Name
            self._font("", 7)
            self.set_text_color(*C_DARK)
            self.set_xy(cx, ty)
            self.cell(44, th, str(row.get("name") or "")[:24])
            cx += 44

            # Team
            self.set_xy(cx, ty)
            self.cell(34, th, str(row.get("team_name") or "")[:20])
            cx += 34

            # Category (competition)
            self._font("B", 7)
            self.set_text_color(*C_BLUE)
            self.set_xy(cx, ty)
            self.cell(14, th, str(row.get("source_competition") or "")[:8], align="C")
            cx += 14

            # Group
            self._font("", 7)
            self.set_text_color(*C_MUTED)
            self.set_xy(cx, ty)
            self.cell(22, th, str(row.get("group_name") or "")[:12])
            cx += 22

            # Footwork score
            fs = row.get("footwork_score") or 0
            self._font("B", 7)
            self.set_text_color(*_score_color(fs))
            self.set_xy(cx, ty)
            self.cell(13, th, _fmt_val(fs, 1), align="C")
            cx += 13

            # Shotstop score
            ss = row.get("shotstop_score") or 0
            self.set_text_color(*_score_color(ss))
            self.set_xy(cx, ty)
            self.cell(14, th, _fmt_val(ss, 1), align="C")

            ty += th
            if ty > self.FOOTER_Y - 4:
                break

        self._draw_footer()

    # ── Individual player page (1 page per player) ───────────────────────────

    def add_player_page(self, row: pd.Series, reference_df: pd.DataFrame,
                        rank: int, ref_row: pd.Series | None = None) -> None:
        """Single-page player report. rank>1 + ref_row → comparison radars in bio column."""
        name = str(row.get("name") or "")
        team_line = (
            f"{row.get('team_name', '')}  ·  "
            f"{row.get('source_competition', '')}  ·  "
            f"{row.get('group_name', '')}"
        )
        foot = float(row.get("footwork_score") or 0)
        stop = float(row.get("shotstop_score") or 0)

        FOOT_LABELS = ["Participación", "Prec. global", "Progresión", "Corto/medio", "Largo", "Estilo"]
        FOOT_KEYS   = ["Participación", "Precisión global", "Progresión", "Juego corto/medio", "Juego largo", "Estilo"]
        STOP_LABELS = ["Carga def.", "Parada", "Dom. área", "Resultado"]
        STOP_KEYS   = ["Carga defensiva", "Parada", "Dominio de área", "Resultado"]

        foot_vals = [float(row.get(f"footwork__{k}", 0) or 0) for k in FOOT_KEYS]
        stop_vals = [float(row.get(f"shotstop__{k}", 0) or 0) for k in STOP_KEYS]

        # Comparison overlay data (rank > 1 only)
        ref_foot_vals = ref_stop_vals = None
        ref_name_str = None
        if rank > 1 and ref_row is not None:
            ref_foot_vals = [float(ref_row.get(f"footwork__{k}", 0) or 0) for k in FOOT_KEYS]
            ref_stop_vals = [float(ref_row.get(f"shotstop__{k}", 0) or 0) for k in STOP_KEYS]
            ref_name_str  = str(ref_row.get("name") or "#1")[:14]

        # Radars with optional comparison overlay — size 2.6 for visual quality
        radar_foot = _build_radar_image(FOOT_LABELS, foot_vals, "Juego de pies", foot, "#1D57CA",
                                        fig_size=2.6,
                                        ref_vals=ref_foot_vals, ref_name=ref_name_str)
        radar_stop = _build_radar_image(STOP_LABELS, stop_vals, "Paradas", stop, "#00A884",
                                        fig_size=2.6,
                                        ref_vals=ref_stop_vals, ref_name=ref_name_str)
        dist_img   = _build_distribution_image(row, reference_df, figw=5.6, figh=3.4)

        _temps = [p for p in [radar_foot, radar_stop, dist_img] if p]

        self.add_page()
        self._draw_header()
        cy = self._draw_player_namebar(rank, name, team_line)

        # ── Layout constants ──────────────────────────────────────────────────
        TW      = self.PW - self.MARGIN * 2    # 281 mm
        CONT_H  = self.FOOTER_Y - cy - 1       # ~167 mm
        BIO_W   = 72.0
        MID_W   = TW - BIO_W - 2              # ~207 mm
        MID_X   = self.MARGIN + BIO_W + 2

        TOP_H   = CONT_H * 0.53               # ~88 mm — enough for photo+bio+context+scores
        BOT_H   = CONT_H - TOP_H - 2          # ~77 mm
        BOT_Y   = cy + TOP_H + 2

        RADAR_W  = MID_W / 2 - 1               # ~103 mm each
        BAR_W    = MID_W * 0.42               # ~87 mm
        # Glossary moves to bio column bottom → campo gets full remaining width
        CAMPO_W  = MID_W - BAR_W - 2          # ~118 mm (was 86mm, now full)

        # ── Bio column: card (top) + KPI strip + glossary (bottom) ──────────────
        SCORE_H = 14.0
        self._draw_bio_card(row, self.MARGIN, cy, BIO_W, CONT_H)

        # KPI score strip — just below bio content (photo 34mm + gap 3mm + 5 context rows×5.5mm = 64.5mm)
        score_y = cy + 34 + 3 + 5 * 5.5 + 3   # cy + ~68mm
        foot_s  = float(row.get("footwork_score") or 0)
        stop_s  = float(row.get("shotstop_score") or 0)
        bal_s   = (foot_s + stop_s) / 2
        sw = (BIO_W - 1) / 3
        sx = self.MARGIN
        for lbl, val in [("PIES", foot_s), ("PARADAS", stop_s), ("GLOBAL", bal_s)]:
            self.set_fill_color(*_score_color(val))
            self.rect(sx, score_y, sw - 0.5, SCORE_H, style="F")
            self._font("B", 13)
            self.set_text_color(*C_WHITE)
            self.set_xy(sx, score_y + 1.5)
            self.cell(sw - 0.5, 6.5, _fmt_val(val, 1), align="C")
            self._font("B", 6)
            self.set_xy(sx, score_y + 8.5)
            self.cell(sw - 0.5, 4, lbl, align="C")
            sx += sw

        # Glossary starts at BOT_Y (no overlap with score strip)
        self._draw_glossary(row, reference_df,
                             x=self.MARGIN, y=BOT_Y, w=BIO_W, h=BOT_H)

        # ── Main radars (top, with comparison overlay for rank>1) ─────────────
        if radar_foot:
            self.image(radar_foot, x=MID_X, y=cy, w=RADAR_W, h=TOP_H)
        if radar_stop:
            self.image(radar_stop, x=MID_X + RADAR_W + 1, y=cy, w=RADAR_W, h=TOP_H)

        # ── Bars + campo (bottom row, no separate glossary column) ────────────
        strengths, risks = _strengths_risks(row, reference_df)
        self._draw_bars_section(strengths, risks, MID_X, BOT_Y, BAR_W, BOT_H)
        if dist_img:
            self.image(dist_img, x=MID_X + BAR_W + 2, y=BOT_Y, w=CAMPO_W, h=BOT_H)

        self._draw_footer()

        for p in _temps:
            try:
                Path(p).unlink()
            except OSError:
                pass

    def _draw_player_namebar(self, rank: int, name: str, team_line: str) -> float:
        """Draw the player name/team bar. Returns y after the bar."""
        cy = self.HEADER_H + 2
        self.set_fill_color(*C_LIGHT_BG)
        self.rect(self.MARGIN, cy, self.PW - self.MARGIN * 2, 10, style="F")

        self.set_fill_color(*C_NAVY)
        self.rect(self.MARGIN, cy, 14, 10, style="F")
        self._font("B", 8)
        self.set_text_color(*C_WHITE)
        self.set_xy(self.MARGIN, cy)
        self.cell(14, 10, f"#{rank}", align="C")

        self._font("B", 12)
        self.set_text_color(*C_NAVY)
        self.set_xy(self.MARGIN + 16, cy + 1)
        self.cell(165, 5, name[:36])

        self._font("", 7.5)
        self.set_text_color(*C_MUTED)
        self.set_xy(self.MARGIN + 16, cy + 6)
        self.cell(180, 4, team_line[:70])

        return cy + 13

    def _draw_bio_card(self, row: pd.Series, x: float, y: float, w: float, h: float) -> None:
        """Left card: photo + bio + context rows + scores at the bottom."""
        foot = float(row.get("footwork_score") or 0)
        stop = float(row.get("shotstop_score") or 0)
        balance = (foot + stop) / 2

        SCORE_H = 13.0   # height of score strip at bottom

        # Photo placeholder (left) + bio grid (right)
        PH_W = 26.0
        PH_H = 34.0
        self.set_fill_color(*C_LIGHT_BG)
        self.rect(x, y, PH_W, PH_H, style="F")
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.15)
        self.rect(x, y, PH_W, PH_H)
        self._font("", 6)
        self.set_text_color(*C_MUTED)
        self.set_xy(x, y + PH_H / 2 - 2)
        self.cell(PH_W, 4, "Foto", align="C")

        bio = [
            ("EDAD", f"{_fmt_val(row.get('age'), 0)} a." if row.get("age") else "-"),
            ("ALTURA", f"{int(row.get('height', 0) or 0)} cm" if row.get("height") else "-"),
            ("PESO", f"{int(row.get('weight', 0) or 0)} kg" if row.get("weight") else "-"),
            ("PIERNA", str(row.get("foot") or "-").capitalize()),
            ("NACIÓN", str(row.get("birth_country_name") or "-")[:14]),
            ("CONTRATO", str(row.get("contract_expires") or "-")[:10]),
        ]
        bx = x + PH_W + 2
        by = y
        for lbl, val in bio:
            self._font("B", 6)
            self.set_text_color(*C_MUTED)
            self.set_xy(bx, by)
            self.cell(14, 5.5, lbl)
            self._font("", 7)
            self.set_text_color(*C_DARK)
            self.cell(w - PH_W - 16, 5.5, val)
            by += 5.5

        y += PH_H + 3

        # Context rows
        ctx = [
            ("Valor mercado", _fmt_market(row.get("market_value"))),
            ("Partidos", str(int(row.get("total_matches") or 0))),
            ("Minutos", f"{int(row.get('minutes_on_field') or 0):,}".replace(",", ".")),
            ("% minutos", f"{float(row.get('minutes_share') or 0)*100:.0f}%"),
            ("En cesión", "Sí" if row.get("on_loan") else "No"),
        ]
        for lbl, val in ctx:
            self.set_fill_color(*C_LIGHT_BG)
            self.rect(x, y, w, 5.5, style="F")
            self._font("B", 6.5)
            self.set_text_color(*C_NAVY)
            self.set_xy(x + 2, y + 0.5)
            self.cell(w / 2, 4.5, lbl)
            self._font("", 6.5)
            self.set_text_color(*C_DARK)
            self.set_xy(x + w / 2, y + 0.5)
            self.cell(w / 2 - 2, 4.5, val, align="R")
            y += 6

        # Score strip is drawn externally (in add_player_page) to avoid
        # overlapping with the glossary section below.

    def _draw_col1(self, row: pd.Series, x: float, y: float, w: float, h: float) -> None:
        # Scores
        foot = float(row.get("footwork_score") or 0)
        stop = float(row.get("shotstop_score") or 0)
        balance = (foot + stop) / 2

        score_items = [
            ("PIES", foot),
            ("PARADAS", stop),
            ("GLOBAL", balance),
        ]
        sw = (w - 2) / 3
        sx = x
        for label, score in score_items:
            color = _score_color(score)
            self.set_fill_color(*color)
            self.rect(sx, y, sw - 1, 13, style="F")
            self._font("B", 14)
            self.set_text_color(*C_WHITE)
            self.set_xy(sx, y + 1)
            self.cell(sw - 1, 7, _fmt_val(score, 1), align="C")
            self._font("B", 6)
            self.set_xy(sx, y + 8)
            self.cell(sw - 1, 4, label, align="C")
            sx += sw

        y += 16

        # Photo placeholder
        ph_h = 42.0
        self.set_fill_color(*C_LIGHT_BG)
        self.rect(x, y, 30, ph_h, style="F")
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.rect(x, y, 30, ph_h)
        self._font("", 7)
        self.set_text_color(*C_MUTED)
        self.set_xy(x, y + ph_h / 2 - 2)
        self.cell(30, 4, "Foto", align="C")

        # Bio data
        bio = [
            ("EDAD", f"{_fmt_val(row.get('age'), 0)} años" if row.get("age") else "-"),
            ("ALTURA", f"{int(row.get('height', 0) or 0)} cm" if row.get("height") else "-"),
            ("PESO", f"{int(row.get('weight', 0) or 0)} kg" if row.get("weight") else "-"),
            ("PIERNA", str(row.get("foot") or "-").capitalize()),
            ("NACIÓN", str(row.get("birth_country_name") or "-")[:18]),
            ("CONTRATO", str(row.get("contract_expires") or "-")[:10]),
            ("VALOR", _fmt_market(row.get("market_value"))),
        ]
        bx = x + 33
        by = y + 1
        for label, val in bio:
            self._font("B", 7)
            self.set_text_color(*C_MUTED)
            self.set_xy(bx, by)
            self.cell(18, 5, label)
            self._font("", 8)
            self.set_text_color(*C_DARK)
            self.cell(w - 35, 5, val)
            by += 6

        y += ph_h + 4

        # Additional stats
        extra = [
            ("Partidos jugados", str(int(row.get("total_matches") or 0))),
            ("Minutos", f"{int(row.get('minutes_on_field') or 0):,}".replace(",", ".")),
            ("% de minutos", f"{float(row.get('minutes_share') or 0)*100:.0f}%"),
            ("En cesión", "Sí" if row.get("on_loan") else "No"),
            ("Cantera", "Sí" if row.get("is_youth_team") else "No"),
        ]
        for label, val in extra:
            self.set_fill_color(*C_LIGHT_BG)
            self.rect(x, y, w, 6, style="F")
            self._font("B", 7)
            self.set_text_color(*C_NAVY)
            self.set_xy(x + 2, y + 1)
            self.cell(w / 2, 4, label)
            self._font("", 7)
            self.set_text_color(*C_DARK)
            self.set_xy(x + w / 2, y + 1)
            self.cell(w / 2 - 2, 4, val, align="R")
            y += 7

    def _draw_col2(self, strengths: list[dict], risks: list[dict], x: float, y: float, w: float, h: float) -> None:
        # Fortalezas header
        self.set_fill_color(*C_NAVY)
        self.rect(x, y, w, 8, style="F")
        self._font("B", 9)
        self.set_text_color(*C_TEAL_LIGHT)
        self.set_xy(x + 3, y + 1)
        self.cell(w - 6, 6, "FORTALEZAS  -  Top métricas del jugador")
        y += 10

        for item in strengths:
            self._draw_metric_bar(x, y, w, item["label"], item["value"], item["pct"], positive=True)
            y += 22

        y += 4

        # Debilidades header
        self.set_fill_color(*C_NAVY)
        self.rect(x, y, w, 8, style="F")
        self._font("B", 9)
        self.set_text_color(240, 140, 80)
        self.set_xy(x + 3, y + 1)
        self.cell(w - 6, 6, "PUNTOS A VIGILAR  -  Métricas más bajas")
        y += 10

        for item in risks:
            self._draw_metric_bar(x, y, w, item["label"], item["value"], item["pct"], positive=False)
            y += 22

    def _draw_glossary(self, row: pd.Series, reference_df: pd.DataFrame,
                       x: float, y: float, w: float, h: float) -> None:
        """Compact glossary: block scores for Juego de pies and Paradas."""

        def _pct_color_fpdf(p: float | None) -> tuple[int, int, int]:
            if p is None: return C_MUTED
            if p >= 70:   return C_GREEN
            if p >= 45:   return C_BLUE
            if p >= 25:   return C_YELLOW
            return C_RED

        foot_blocks = [
            ("Participación",   "footwork__Participación"),
            ("Prec. global",    "footwork__Precisión global"),
            ("Progresión",      "footwork__Progresión"),
            ("Corto/medio",     "footwork__Juego corto/medio"),
            ("Largo",           "footwork__Juego largo"),
            ("Estilo",          "footwork__Estilo"),
        ]
        stop_blocks = [
            ("Carga def.",  "shotstop__Carga defensiva"),
            ("Parada",      "shotstop__Parada"),
            ("Dom. área",   "shotstop__Dominio de área"),
            ("Resultado",   "shotstop__Resultado"),
        ]

        cy = y

        for section_label, section_color, blocks, score_col in [
            ("PIES", C_BLUE, foot_blocks, "footwork_score"),
            ("PARADAS", C_TEAL, stop_blocks, "shotstop_score"),
        ]:
            overall = float(row.get(score_col) or 0)

            # Section header
            self.set_fill_color(*C_NAVY)
            self.rect(x, cy, w, 6.5, style="F")
            self._font("B", 6.5)
            self.set_text_color(*C_TEAL_LIGHT)
            self.set_xy(x + 1.5, cy + 0.5)
            self.cell(w - 14, 5.5, section_label)
            self.set_text_color(*_score_color(overall))
            self.set_xy(x + w - 13, cy + 0.5)
            self.cell(11, 5.5, _fmt_val(overall, 1), align="R")
            cy += 7.5

            for lbl, col in blocks:
                val = float(row.get(col) or 0)
                pct_col = _pct_color_fpdf(val)

                # Alternating row
                if int(cy) % 10 < 5:
                    self.set_fill_color(*C_LIGHT_BG)
                    self.rect(x, cy, w, 5.5, style="F")

                self._font("", 5.5)
                self.set_text_color(*C_DARK)
                self.set_xy(x + 1.5, cy + 0.5)
                self.cell(w - 14, 4.5, lbl[:16])

                self._font("B", 5.5)
                self.set_text_color(*pct_col)
                self.set_xy(x + w - 13, cy + 0.5)
                self.cell(11, 4.5, _fmt_val(val, 1), align="R")

                # Mini bar
                bar_x = x + 1.5
                bar_y = cy + 4.8
                bar_w = w - 3
                self.set_fill_color(*C_BORDER)
                self.rect(bar_x, bar_y, bar_w, 1.0, style="F")
                fill = max(0.5, (val / 100.0) * bar_w)
                self.set_fill_color(*pct_col)
                self.rect(bar_x, bar_y, fill, 1.0, style="F")

                cy += 6.5

            cy += 3  # gap between sections

    def _draw_bars_section(
        self, strengths: list[dict], risks: list[dict], x: float, y: float, w: float, h: float
    ) -> None:
        """Bottom-left: Fortalezas + Debilidades horizontal bar charts."""
        # Split width between two panels
        PW = (w - 3) / 2

        # Fortalezas panel
        self.set_fill_color(*C_NAVY)
        self.rect(x, y, PW, 7, style="F")
        self._font("B", 8)
        self.set_text_color(*C_TEAL_LIGHT)
        self.set_xy(x + 2, y + 1)
        self.cell(PW - 4, 5, "FORTALEZAS")
        fy = y + 9
        for item in strengths[:5]:
            self._draw_metric_bar(x, fy, PW, item["label"], item["value"], item["pct"], positive=True)
            fy += 15

        # Debilidades panel
        dx = x + PW + 3
        self.set_fill_color(*C_NAVY)
        self.rect(dx, y, PW, 7, style="F")
        self._font("B", 8)
        self.set_text_color(240, 140, 80)
        self.set_xy(dx + 2, y + 1)
        self.cell(PW - 4, 5, "PUNTOS A VIGILAR")
        ry = y + 9
        for item in risks[:5]:
            self._draw_metric_bar(dx, ry, PW, item["label"], item["value"], item["pct"], positive=False)
            ry += 15

    def _draw_stats_section(
        self, row: pd.Series, reference_df: pd.DataFrame, x: float, y: float, w: float, h: float
    ) -> None:
        """Bottom-right: compact two-column stats tables (distribution + portería)."""
        # Two sub-columns
        SW = (w - 2) / 2

        dist_metrics: list[tuple[str, str, bool]] = [
            ("Pases recibidos/90", "received_pass_avg", True),
            ("Pases/90", "passes_avg", True),
            ("Precisión pases %", "accurate_passes_percent", True),
            ("Pases adelante/90", "forward_passes_avg", True),
            ("Precisión adelante %", "successful_forward_passes_percent", True),
            ("Pases largos/90", "long_passes_avg", True),
            ("Precisión largos %", "successful_long_passes_percent", True),
            ("Pases cortos/med./90", "short_medium_pass_avg", True),
            ("Prec. cortos/med. %", "accurate_short_medium_pass_percent", True),
            ("Long. media pase (m)", "average_pass_length", True),
            ("Long. media largo (m)", "average_long_pass_length", True),
        ]
        stop_metrics: list[tuple[str, str, bool]] = [
            ("Remates contra/90", "shots_against_avg", False),
            ("Paradas %", "save_percent", True),
            ("Goles evitados/90", "prevented_goals_avg", True),
            ("xG save/90", "xg_save_avg", False),
            ("Salidas/90", "goalkeeper_exits_avg", True),
            ("Duelos aéreos/90", "gk_aerial_duels_avg", True),
            ("Goles recibidos/90", "conceded_goals_avg", False),
            ("Porterías a cero", "clean_sheets", True),
        ]

        for col_idx, (header, metrics) in enumerate([
            ("DISTRIBUCIÓN", dist_metrics),
            ("PORTERÍA", stop_metrics),
        ]):
            cx = x + col_idx * (SW + 2)
            self.set_fill_color(*C_NAVY)
            self.rect(cx, y, SW, 7, style="F")
            self._font("B", 8)
            self.set_text_color(*C_LIGHT_BG)
            self.set_xy(cx + 2, y + 1)
            self.cell(SW - 4, 5, header)

            my = y + 9
            for lbl, metric, higher in metrics:
                value = row.get(metric)
                pct = _metric_percentile(reference_df, metric, value, higher)
                self._draw_stat_row(cx, my, SW, lbl, value, pct)
                my += 6
                if my > y + h:
                    break

    def _draw_metric_bar(
        self, x: float, y: float, w: float, label: str, value, pct: float | None, positive: bool
    ) -> None:
        """Compact metric bar: label + badge on one line, value on second, bar below."""
        pct_val = pct if pct is not None else 0.0
        pct_str = f"P{int(round(pct_val))}" if pct is not None else "-"
        val_str = _fmt_val(value, 2)
        bar_color = C_GREEN if positive else C_ORANGE

        # Row 1: label (left) + percentile badge (right)
        BADGE_W = 15.0
        self._font("B", 7)
        self.set_text_color(*C_DARK)
        self.set_xy(x + 2, y)
        self.cell(w - BADGE_W - 4, 4.5, label[:28])

        self.set_fill_color(*bar_color)
        self.rect(x + w - BADGE_W - 2, y, BADGE_W, 4.5, style="F")
        self._font("B", 6.5)
        self.set_text_color(*C_WHITE)
        self.set_xy(x + w - BADGE_W - 2, y)
        self.cell(BADGE_W, 4.5, pct_str, align="C")

        # Row 2: value
        self._font("", 6)
        self.set_text_color(*C_MUTED)
        self.set_xy(x + 2, y + 5)
        self.cell(w - 4, 3.5, f"Valor: {val_str}")

        # Row 3: bar
        bar_x = x + 2
        bar_y = y + 9
        bar_w = w - 4
        bar_h = 3.5
        self.set_fill_color(*C_LIGHT_BG)
        self.rect(bar_x, bar_y, bar_w, bar_h, style="F")
        fill_w = max(1.0, (pct_val / 100.0) * bar_w)
        self.set_fill_color(*bar_color)
        self.rect(bar_x, bar_y, fill_w, bar_h, style="F")

    def _draw_col3(self, row: pd.Series, reference_df: pd.DataFrame, x: float, y: float, w: float, h: float) -> None:
        # Pass distribution header
        self.set_fill_color(*C_NAVY)
        self.rect(x, y, w, 8, style="F")
        self._font("B", 9)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x + 3, y + 1)
        self.cell(w - 6, 6, "DISTRIBUCIÓN CON EL BALÓN")
        y += 10

        dist_metrics: list[tuple[str, str, bool]] = [
            ("Pases recibidos/90", "received_pass_avg", True),
            ("Pases/90", "passes_avg", True),
            ("Precisión pases %", "accurate_passes_percent", True),
            ("Pases adelante/90", "forward_passes_avg", True),
            ("Precisión adelante %", "successful_forward_passes_percent", True),
            ("Pases cortos/medios/90", "short_medium_pass_avg", True),
            ("Precisión cortos/medios %", "accurate_short_medium_pass_percent", True),
            ("Pases largos/90", "long_passes_avg", True),
            ("Precisión largos %", "successful_long_passes_percent", True),
            ("Long. media pase (m)", "average_pass_length", True),
            ("Long. media largo (m)", "average_long_pass_length", True),
        ]

        for label, metric, higher in dist_metrics:
            value = row.get(metric)
            pct = _metric_percentile(reference_df, metric, value, higher)
            self._draw_stat_row(x, y, w, label, value, pct)
            y += 8

        y += 4

        # Shotstopping header
        self.set_fill_color(*C_NAVY)
        self.rect(x, y, w, 8, style="F")
        self._font("B", 9)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x + 3, y + 1)
        self.cell(w - 6, 6, "PORTERÍA")
        y += 10

        stop_metrics: list[tuple[str, str, bool]] = [
            ("Remates en contra/90", "shots_against_avg", False),
            ("Paradas %", "save_percent", True),
            ("Goles evitados/90", "prevented_goals_avg", True),
            ("xG save/90", "xg_save_avg", False),
            ("Salidas/90", "goalkeeper_exits_avg", True),
            ("Duelos aéreos/90", "gk_aerial_duels_avg", True),
            ("Goles recibidos/90", "conceded_goals_avg", False),
            ("Porterías a cero", "clean_sheets", True),
        ]

        for label, metric, higher in stop_metrics:
            value = row.get(metric)
            pct = _metric_percentile(reference_df, metric, value, higher)
            self._draw_stat_row(x, y, w, label, value, pct)
            y += 8

    def _draw_stat_row(self, x: float, y: float, w: float, label: str, value, pct: float | None) -> None:
        row_h = 6.0
        pct_str = f"P{int(round(pct))}" if pct is not None else "-"
        val_str = _fmt_val(value, 2)
        color = _score_color(pct)

        # Alternating background
        if int(y) % 12 < 6:
            self.set_fill_color(*C_LIGHT_BG)
            self.rect(x, y, w, row_h, style="F")

        self._font("", 6.5)
        self.set_text_color(*C_DARK)
        self.set_xy(x + 2, y + 1)
        self.cell(w - 26, row_h - 2, label[:30])

        # Value
        self._font("B", 6.5)
        self.set_text_color(*C_DARK)
        self.set_xy(x + w - 24, y + 1)
        self.cell(12, row_h - 2, val_str, align="R")

        # Percentile
        self.set_text_color(*color)
        self.set_xy(x + w - 11, y + 1)
        self.cell(9, row_h - 2, pct_str, align="R")

        # Separator
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.07)
        self.line(x + 2, y + row_h, x + w - 2, y + row_h)

    # ── Back cover ────────────────────────────────────────────────────────────

    def add_back_cover(self) -> None:
        self.add_page()

        # Full navy background
        self.set_fill_color(*C_NAVY)
        self.rect(0, 0, self.PW, self.PH, style="F")

        # Logo dimensions (square 1:1) and space between bars
        LW = 80.0          # logo width = height (square)
        BAR_TOP_Y = 52.0   # top bar y
        BAR_BOT_Y = 148.0  # bottom bar y
        # Centre logo between the two bars
        space_h    = BAR_BOT_Y - (BAR_TOP_Y + 3)  # 93mm
        logo_y     = BAR_TOP_Y + 3 + (space_h - LW) / 2  # perfectly centred

        # Top teal bar
        self.set_fill_color(*C_TEAL)
        self.rect(0, BAR_TOP_Y, self.PW, 3, style="F")

        # MCode logo — centred between the two bars
        if LOGO_MCODE.exists():
            self.image(str(LOGO_MCODE), x=(self.PW - LW) / 2, y=logo_y, w=LW)

        # Bottom teal bar
        self.set_fill_color(*C_TEAL)
        self.rect(0, BAR_BOT_Y, self.PW, 3, style="F")

        # Text block — well below the bar
        self._font("", 9)
        self.set_text_color(*C_MUTED)
        self.set_xy(0, 157)
        self.cell(self.PW, 6,
                  "Datos: Wyscout  ·  Análisis: MCODE Sport Analytics  ·  Temporada 2025-26",
                  align="C")

        self._font("", 9)
        self.set_xy(0, 165)
        self.cell(self.PW, 6,
                  f"Informe generado con UnioMercato  ·  {AUTHOR}",
                  align="C")

        self._font("B", 8)
        self.set_text_color(*C_TEAL)
        self.set_xy(0, 176)
        self.cell(self.PW, 6,
                  f"© {date.today().year}  MCODE Sport Analytics",
                  align="C")


# ── Radar chart helper ────────────────────────────────────────────────────────

def _build_radar_image(
    labels: list[str],
    values: list[float],
    title: str,
    overall: float,
    accent_hex: str,
    fig_size: float = 2.6,
    ref_vals: list[float] | None = None,
    ref_name: str | None = None,
) -> str:
    """Radar chart with glow + volume effect. Optional overlay of reference player."""
    n = max(3, len(labels))
    vn = [max(0.0, min(float(v), 100.0)) / 100.0 for v in values]
    angs = [2 * math.pi * i / n for i in range(n)]
    angs_c = angs + [angs[0]]
    vn_c = vn + [vn[0]]

    r_, g_, b_ = int(accent_hex[1:3], 16), int(accent_hex[3:5], 16), int(accent_hex[5:7], 16)
    acc = (r_ / 255, g_ / 255, b_ / 255)

    fig, ax = plt.subplots(figsize=(fig_size, fig_size),
                            subplot_kw={"polar": True}, facecolor="white")

    # ── Background: alternating concentric ring fills ─────────────────────────
    ax.set_facecolor("#f0f4fd")
    for ring_r, ring_alpha in [(1.0, 0.07), (0.75, 0.07), (0.50, 0.07), (0.25, 0.07)]:
        ring_angs = np.linspace(0, 2 * math.pi, 200)
        ax.fill(ring_angs, [ring_r] * 200,
                color="#9ab4e8", alpha=ring_alpha, zorder=0)

    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25", "50", "75", "100"],
                        fontsize=4.5, color="#aabbdd", alpha=0.7)
    ax.yaxis.grid(color="#b8cae8", linewidth=0.5, linestyle="--", alpha=0.5, zorder=1)
    ax.xaxis.grid(color="#b8cae8", linewidth=0.45, alpha=0.4, zorder=1)
    ax.set_xticks(angs)
    ax.set_xticklabels([lbl[:12] for lbl in labels],
                        fontsize=6.2, color="#1a2a5e", fontweight="bold")

    # ── Reference player overlay (dashed, behind) ─────────────────────────────
    if ref_vals is not None:
        vn_r = [max(0.0, min(float(v), 100.0)) / 100.0 for v in ref_vals]
        vn_r_c = vn_r + [vn_r[0]]
        ax.fill(angs, vn_r, color=(0.85, 0.15, 0.15), alpha=0.08, zorder=2)
        ax.plot(angs_c, vn_r_c, color=(0.82, 0.18, 0.18),
                lw=1.3, ls="--", alpha=0.72, zorder=3,
                label=f"#{1} {(ref_name or '')[:12]}")

    # ── Main polygon: volume (3-layer fill, glow edge) ────────────────────────
    # Layer 1: soft outer glow
    ax.fill(angs, vn, color=acc, alpha=0.10, zorder=4)
    # Layer 2: medium fill
    ax.fill(angs, [v * 0.78 for v in vn], color=acc, alpha=0.14, zorder=5)
    # Layer 3: bright inner core
    ax.fill(angs, [v * 0.55 for v in vn], color=acc, alpha=0.20, zorder=6)

    # Glow edge: wide transparent → narrow opaque
    for lw_, alpha_ in [(5.5, 0.07), (3.5, 0.11), (2.2, 0.20), (1.6, 1.0)]:
        ax.plot(angs_c, vn_c, color=acc, lw=lw_, alpha=alpha_,
                solid_capstyle="round", zorder=7)

    # Dots with white ring
    ax.scatter(angs, vn, color=acc, s=24, zorder=9,
               edgecolors="white", linewidths=0.8)

    # Value labels at each vertex
    for ang, v, val in zip(angs, vn, values):
        r_lbl = min(v + 0.18, 1.10)
        ax.text(ang, r_lbl, f"{float(val):.0f}",
                ha="center", va="center", fontsize=5.8,
                fontweight="bold", color=acc, zorder=10,
                bbox=dict(fc="white", ec="none", alpha=0.80, pad=0.06))

    # ── Title + score ─────────────────────────────────────────────────────────
    ax.set_title(f"{title}\n{overall:.1f}", fontsize=7.5, fontweight="bold",
                 color="#0d1b57", pad=14, y=1.06)

    # ── Legend (only when comparison) ─────────────────────────────────────────
    if ref_vals is not None and ref_name:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color=acc, lw=1.5, label="Este jugador"),
            Line2D([0], [0], color=(0.82, 0.18, 0.18), lw=1.2, ls="--",
                   label=f"#{1} {ref_name[:10]}"),
        ]
        ax.legend(handles=legend_elements,
                  loc="lower center", bbox_to_anchor=(0.5, -0.28),
                  fontsize=5.2, framealpha=0.8, ncol=2,
                  handlelength=1.5, columnspacing=0.8)

    plt.tight_layout(pad=0.3)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return tmp.name


# ── Pass distribution half-pitch with embedded data cards ────────────────────

def _build_distribution_image(row: pd.Series, reference_df: pd.DataFrame,
                               figw: float = 6.4, figh: float = 4.2) -> str | None:
    """Half-pitch campo with proper markings + embedded data cards. Returns PNG path."""

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _pct(metric: str, higher: bool = True) -> float | None:
        return _metric_percentile(reference_df, metric, row.get(metric), higher)

    def _pct_str(p: float | None) -> str:
        return f"P{int(round(p))}" if p is not None else "–"

    def _pct_col(p: float | None) -> str:
        if p is None: return "#777777"
        if p >= 70:   return "#1a8c46"
        if p >= 45:   return "#1a66c8"
        if p >= 25:   return "#c47c00"
        return "#c02040"

    def _col_max(col: str, fallback: float) -> float:
        s = pd.to_numeric(reference_df.get(col, pd.Series(dtype=float)), errors="coerce").dropna()
        return float(s.max()) if len(s) > 0 else max(fallback, 1.0)

    def _scale(val: float, max_v: float, lo: float, hi: float) -> float:
        return lo + (hi - lo) * min(val / max(max_v, 1e-6), 1.0)

    # ── Data ──────────────────────────────────────────────────────────────────
    short   = float(row.get("short_medium_pass_avg") or 0)
    short_a = float(row.get("accurate_short_medium_pass_percent") or 0)
    long_   = float(row.get("long_passes_avg") or 0)
    long_a  = float(row.get("successful_long_passes_percent") or 0)
    recv    = float(row.get("received_pass_avg") or 0)
    avg_len = float(row.get("average_pass_length") or 0)

    total_p = float(row.get("passes_avg") or 0)
    fwd_p   = float(row.get("forward_passes_avg") or 0)
    back_p  = float(row.get("back_passes_avg") or 0)
    lat     = float(row.get("lateral_pass_avg") or max(0.0, total_p - fwd_p - back_p))
    lat_a   = float(row.get("accurate_passes_percent") or 0)

    p_short  = _pct("short_medium_pass_avg");  p_short_a = _pct("accurate_short_medium_pass_percent")
    p_long   = _pct("long_passes_avg");         p_long_a  = _pct("successful_long_passes_percent")
    p_lat    = _pct("lateral_pass_avg") or _pct("back_passes_avg")
    p_recv   = _pct("received_pass_avg")
    p_avg    = _pct("average_pass_length")

    # ── Figure ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(figw, figh), facecolor="white")
    ax.set_facecolor("white")
    ax.axis("off")

    # ── Half-pitch (52.5m deep × 68m wide, goal at TOP) ──────────────────────
    FX, FY = 1.35, 0.28
    FW, FH = 4.55, 3.35   # ratio ≈ 52.5/68

    mx = FW / 68.0
    my = FH / 52.5

    # Field fill
    ax.add_patch(plt.Rectangle((FX, FY), FW, FH, lw=1.4,
                                ec="#0d1b57", fc="#dce8fa", zorder=1))

    gk_x     = FX + FW / 2
    goal_top = FY + FH

    # Goal net (above top edge)
    goal_hw = 7.32 / 2 * mx
    ax.add_patch(plt.Rectangle((gk_x - goal_hw, goal_top), goal_hw * 2, FH * 0.04,
                                lw=0.8, ec="#0d1b57", fc="#b8cce8", zorder=3))

    # Big penalty area
    pen_hw = 40.32 / 2 * mx
    pen_h  = 16.5 * my
    ax.add_patch(plt.Rectangle((gk_x - pen_hw, goal_top - pen_h), pen_hw * 2, pen_h,
                                lw=0.9, ec="#0d1b57", fc="none", zorder=2))

    # 6-yard box
    six_hw = 18.32 / 2 * mx
    six_h  = 5.5 * my
    ax.add_patch(plt.Rectangle((gk_x - six_hw, goal_top - six_h), six_hw * 2, six_h,
                                lw=0.7, ec="#0d1b57", fc="none", zorder=2))

    # Penalty spot
    pen_spot_y = goal_top - 11.0 * my
    ax.add_patch(plt.Circle((gk_x, pen_spot_y), 0.03, color="#0d1b57", zorder=3))

    # Penalty arc (D) — only the part that protrudes BELOW the penalty box
    # Arc center = penalty spot. Radius = 9.15m.
    # Intersection with penalty box lower edge: sin(θ) = (pen_box_y - pen_spot_y)/r
    pen_box_y = goal_top - pen_h
    d_r = 9.15 * my
    sin_val = (pen_box_y - pen_spot_y) / d_r   # negative = box edge is below center
    half_a  = math.asin(abs(sin_val))           # always positive
    # Arc from 180°+half_a to 360°-half_a (the bottom bulge, in rad)
    theta_d = np.linspace(math.pi + half_a, 2 * math.pi - half_a, 80)
    xd = gk_x      + d_r * np.cos(theta_d)
    yd = pen_spot_y + d_r * np.sin(theta_d)
    mask = yd <= pen_box_y + 0.01
    if mask.any():
        ax.plot(xd[mask], yd[mask], color="#0d1b57", lw=0.65, alpha=0.65, zorder=2)

    # Halfway line at bottom
    ax.plot([FX, FX + FW], [FY, FY], color="#0d1b57", lw=0.75, alpha=0.45, zorder=2)

    # Centre circle — top half only (visible at halfway line)
    circ_r  = 9.15 * my
    theta_c = np.linspace(0.0, math.pi, 120)
    ax.plot(gk_x + circ_r * np.cos(theta_c),
            FY   + circ_r * np.sin(theta_c),
            color="#0d1b57", lw=0.7, alpha=0.55, zorder=2)
    ax.add_patch(plt.Circle((gk_x, FY), 0.035, color="#0d1b57", alpha=0.4, zorder=3))

    # ── GK ────────────────────────────────────────────────────────────────────
    gk_y = goal_top - 5.5 * my
    gk_c = "#f0be20" if avg_len >= 25 else ("#3abf8e" if avg_len >= 18 else "#d94040")
    ax.add_patch(plt.Circle((gk_x, gk_y), 0.16, color=gk_c, zorder=6))
    ax.text(gk_x, gk_y, "GK", ha="center", va="center",
            fontsize=6.5, fontweight="bold", color="white", zorder=7)

    # ── Card positions (fixed) — arrows will end AT the card title ───────────
    # Laterales: top-left inside penalty area
    cx_lat = FX + pen_hw * 0.30
    cy_lat = goal_top - pen_h * 0.32
    # Recibidos: top-right inside penalty area
    cx_rec = FX + FW - pen_hw * 0.30
    cy_rec = goal_top - pen_h * 0.32
    # Corto/medio: lower-left, just outside penalty area, short distance
    sl = _scale(short, _col_max("short_medium_pass_avg", short), 0.28, 0.62)  # capped at 0.62 = clearly shorter than largo
    cx_s = FX + FW * 0.14 + sl * 0.06
    cy_s = gk_y - pen_h - sl * 0.45
    # Largo: lower-right, deep into pitch (longer)
    ll2 = _scale(long_, _col_max("long_passes_avg", long_), 0.55, 1.30)  # starts at 0.55 = always longer than corto
    cx_l = gk_x + ll2 * 0.28
    cy_l = gk_y - ll2 * 1.38

    # ── Arrows from GK to card title positions ────────────────────────────────
    ak = dict(arrowstyle="-|>", mutation_scale=12, lw=2.3,
              connectionstyle="arc3,rad=0.13", zorder=5)

    # Laterales — short, almost straight line to the left.
    ak_lat = dict(arrowstyle="-|>", mutation_scale=14, lw=2.5,
                  connectionstyle="arc3,rad=0.08",
                  color="#1a5faa", zorder=10)
    ax.annotate("", xy=(cx_lat + 0.03, cy_lat + 0.03),
                xytext=(gk_x - 0.12, gk_y + 0.02),
                arrowprops=ak_lat, zorder=10)

    # Recibidos — incoming to GK (from right)
    rl = _scale(recv, _col_max("received_pass_avg", recv), 0.26, 1.00)
    tip_r = (gk_x + rl * 1.20, gk_y)
    ax.annotate("", xy=(gk_x + 0.15, gk_y),
                xytext=(cx_rec - 0.14, cy_rec - 0.05),
                arrowprops=dict(color="#b87800", **ak))

    # Corto/medio — GK → short distance, left-lower
    ax.annotate("", xy=(cx_s, cy_s),
                xytext=(gk_x - 0.12, gk_y - 0.08),
                arrowprops=dict(color="#007b7b", **ak))

    # Largo — GK → long distance, straight down-right
    ax.annotate("", xy=(cx_l, cy_l),
                xytext=(gk_x + 0.08, gk_y - 0.08),
                arrowprops=dict(color="#1a7a1a", **ak))

    # ── Avg-length bar — Min at TOP, Max at BOTTOM, fills from top downward ───
    max_avg   = _col_max("average_pass_length", avg_len)
    bx        = FX - 0.74
    bar_top   = FY + FH   # top edge = MIN
    bar_total = FH
    bar_play  = bar_total * min(avg_len / max_avg, 1.0)

    # Background (full)
    ax.add_patch(plt.Rectangle((bx - 0.055, FY), 0.11, FH,
                                color="#cccccc", alpha=0.25, zorder=3))
    # Fill starts at top, grows DOWNWARD
    ax.add_patch(plt.Rectangle((bx - 0.065, bar_top - bar_play), 0.13, bar_play,
                                color="#f0be20", alpha=0.85, zorder=4))

    ax.text(bx, bar_top + 0.10, "Min", ha="center", va="bottom",
            fontsize=4.8, color="#888888", zorder=5)
    ax.text(bx, FY - 0.12, f"Máx {max_avg:.0f}m", ha="center", va="top",
            fontsize=4.8, color="#888888", zorder=5)
    ax.text(bx + 0.21, bar_top - bar_play * 0.5,
            f"{avg_len:.1f}m\n{_pct_str(p_avg)}",
            ha="left", va="center", fontsize=5.2, color="#a07000",
            fontweight="bold", zorder=5)

    # ── Data cards — single multiline bbox, arrow ends at top corner ─────────
    cbox = dict(boxstyle="round,pad=0.42", lw=1.1, alpha=0.95)

    def _card(cx, cy_c, title, t_color, row1, row2, ha="left"):
        """One bbox wrapping title + two data rows. Arrow tip points to (cx, cy_c)."""
        txt = f"{title}\n{row1}\n{row2}"
        ax.text(cx, cy_c, txt,
                ha=ha, va="top", fontsize=5.6,
                color="#0d1b57",
                bbox=dict(fc="white", ec=t_color, **cbox),
                zorder=8, linespacing=1.65)

    # Corto/medio — left side, below penalty area
    _card(cx_s, cy_s,
          "Corto/medio",       "#007b7b",
          f"Vol: {short:.1f}/90   {_pct_str(p_short)}",
          f"Prec: {short_a:.0f}%     {_pct_str(p_short_a)}")

    # Largo — lower-right, toward centre circle
    _card(cx_l, cy_l,
          "Largo",             "#1a7a1a",
          f"Vol: {long_:.1f}/90   {_pct_str(p_long)}",
          f"Prec: {long_a:.0f}%     {_pct_str(p_long_a)}")

    # Laterales — inside campo, upper-left of penalty area
    _card(cx_lat, cy_lat,
          "Laterales (est.)",  "#1a5faa",
          f"Vol: {lat:.1f}/90   {_pct_str(p_lat)}",
          f"Prec: {lat_a:.0f}%")

    # Recibidos — inside campo, upper-right of penalty area
    _card(cx_rec, cy_rec,
          "Recibidos",         "#b87800",
          f"Vol: {recv:.1f}/90   {_pct_str(p_recv)}",
          "Prec: No aplica", ha="right")

    # Title
    ax.text(FX + FW / 2, FY + FH + 0.26, "Vías de distribución",
            ha="center", va="bottom", fontsize=8.5, fontweight="bold",
            color="#0d1b57", zorder=8)

    ax.set_xlim(0.38, figw - 0.08)
    ax.set_ylim(FY - 0.38, FY + FH + 0.55)
    plt.tight_layout(pad=0.1)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return tmp.name


# ── Scatter plot helper ────────────────────────────────────────────────────────

def _build_scatter_image(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(5.2, 5.0), facecolor="#f4f7ff")
    ax.set_facecolor("#edf1fb")

    color_map = {"1RFEF": "#1D57CA", "2RFEF": "#00A884"}
    for comp, grp in df.groupby("source_competition"):
        c = color_map.get(str(comp), "#888888")
        ax.scatter(
            grp["footwork_score"],
            grp["shotstop_score"],
            c=c, s=55, alpha=0.88,
            edgecolors="white", linewidths=0.6,
            label=str(comp), zorder=3,
        )

    x_avg = float(df["footwork_score"].mean())
    y_avg = float(df["shotstop_score"].mean())
    ax.axvline(x_avg, color="#8899bb", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.axhline(y_avg, color="#8899bb", linestyle="--", linewidth=0.9, alpha=0.7)

    for _, row in df.head(5).iterrows():
        ax.annotate(
            str(row.get("name") or "")[:16],
            (float(row["footwork_score"]), float(row["shotstop_score"])),
            fontsize=6, ha="left", va="bottom",
            xytext=(3, 3), textcoords="offset points",
            color="#0d1b57",
        )

    ax.set_xlabel("Juego de pies", fontsize=9, color="#444")
    ax.set_ylabel("Paradas", fontsize=9, color="#444")
    ax.set_title("Mapa macro: pies vs paradas", fontsize=10, fontweight="bold", color="#0d1b57")
    ax.legend(fontsize=8, framealpha=0.9)
    ax.tick_params(labelsize=7, colors="#555")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.grid(True, alpha=0.3, linewidth=0.4)

    plt.tight_layout()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return tmp.name


# ── Public entry point ────────────────────────────────────────────────────────

def build_filters_summary(
    competition: str,
    group_name: str,
    min_matches: int,
    min_minutes_pct: int,
    target_competition_only: bool,
    include_youth: bool,
    include_loans: bool,
) -> str:
    parts = [
        f"Competición: {'Todas' if competition == 'ALL' else competition}",
        f"Grupo: {group_name}",
    ]
    if min_matches > 0:
        parts.append(f"Partidos mín.: {min_matches}")
    if min_minutes_pct > 0:
        parts.append(f"% minutos disputados mín.: {min_minutes_pct}%")
    if target_competition_only:
        parts.append("Solo comp. objetivo")
    if not include_youth:
        parts.append("Sin cantera")
    if not include_loans:
        parts.append("Sin cedidos")
    return "  ·  ".join(parts)


def generate_report(
    df: pd.DataFrame,
    top_n: int,
    filters_summary: str,
    ranking_label: str,
) -> bytes:
    """Generate full PDF and return as bytes."""
    top_df = df.head(top_n).reset_index(drop=True)
    scatter_path = _build_scatter_image(top_df)

    pdf = GoalkeeperReport()

    pdf.add_cover(filters_summary, len(df), top_n)
    pdf.add_index(top_n)
    pdf.add_summary(top_df, top_n, filters_summary, ranking_label, scatter_path)

    ref_row = top_df.iloc[0] if len(top_df) > 0 else None
    for rank, (_, row) in enumerate(top_df.iterrows(), start=1):
        pdf.add_player_page(row, df, rank,
                            ref_row=ref_row if rank > 1 else None)

    pdf.add_back_cover()

    if scatter_path:
        try:
            Path(scatter_path).unlink()
        except OSError:
            pass

    return bytes(pdf.output())
