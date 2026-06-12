from __future__ import annotations

import html
import math
import textwrap

import pandas as pd
import plotly.express as px
import streamlit as st

from project_paths import asset_path


def esc(value) -> str:
    """Escape any value before embedding it inside an HTML string."""
    return html.escape(str(value or ""))


def safe_number(value, default: float = 0.0) -> float:
    """Return a finite float for optional or incomplete scouting values."""
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric) or not math.isfinite(float(numeric)):
        return default
    return float(numeric)


def numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    """Return a clean numeric series even when a source column is absent."""
    if column not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").dropna()


def visible_max(df: pd.DataFrame, column: str, fallback: float = 1.0) -> float:
    """Get a positive visible-group maximum with a safe player fallback."""
    values = numeric_column(df, column)
    maximum = safe_number(values.max(), default=0.0) if not values.empty else 0.0
    return max(maximum, safe_number(fallback, default=0.0), 1e-6)


from reports.pdf_report import build_filters_summary, generate_report
from scripts.build_goalkeeper_market_dashboard import build_metadata, load_goalkeepers


st.set_page_config(page_title="UnioMercato | Porteros", page_icon=":soccer:", layout="wide")

st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(circle at top left, rgba(29, 87, 202, 0.18), transparent 26%),
          radial-gradient(circle at top right, rgba(31, 202, 182, 0.12), transparent 20%),
          linear-gradient(180deg, #071235 0%, #091842 58%, #06102d 100%);
      }
      section[data-testid="stSidebar"] {
        background:
          radial-gradient(circle at top left, rgba(29, 87, 202, 0.16), transparent 28%),
          linear-gradient(180deg, #0a153f 0%, #0c1c56 52%, #081231 100%) !important;
        border-right: 1px solid rgba(123, 207, 255, 0.12);
      }
      .block-container {
        padding-top: 4.5rem;
        padding-bottom: 2.4rem;
      }
      div[data-testid="stAppViewBlockContainer"] h1,
      div[data-testid="stAppViewBlockContainer"] h2,
      div[data-testid="stAppViewBlockContainer"] h3,
      div[data-testid="stAppViewBlockContainer"] h4,
      div[data-testid="stAppViewBlockContainer"] h5,
      div[data-testid="stAppViewBlockContainer"] p,
      div[data-testid="stAppViewBlockContainer"] li,
      div[data-testid="stAppViewBlockContainer"] label,
      div[data-testid="stAppViewBlockContainer"] span,
      div[data-testid="stAppViewBlockContainer"] div {
        color: #eef4ff;
      }
      div[data-testid="stAppViewBlockContainer"] [data-testid="stMarkdownContainer"] p,
      div[data-testid="stAppViewBlockContainer"] [data-testid="stMarkdownContainer"] li,
      div[data-testid="stAppViewBlockContainer"] [data-testid="stMarkdownContainer"] span,
      div[data-testid="stAppViewBlockContainer"] [data-testid="stMarkdownContainer"] strong,
      div[data-testid="stAppViewBlockContainer"] [data-testid="stMarkdownContainer"] em {
        color: #f3f7ff !important;
      }
      .stMarkdown, .stMarkdown * {
        color: #f3f7ff !important;
      }
      div[data-testid="stAppViewBlockContainer"] h1 {
        color: #ffffff !important;
        font-weight: 900 !important;
      }
      div[data-testid="stAppViewBlockContainer"] h3,
      div[data-testid="stAppViewBlockContainer"] h4 {
        color: #f8fbff !important;
        font-weight: 800 !important;
      }
      .um-dark-wrap {
        background: linear-gradient(180deg, #0d1b57 0%, #0a153f 100%);
        border: 1px solid rgba(95, 218, 255, 0.14);
        border-radius: 28px;
        box-shadow: 0 24px 60px rgba(5, 10, 30, 0.42);
      }
      .um-dark-card {
        background: linear-gradient(180deg, rgba(17, 34, 96, 0.98) 0%, rgba(11, 24, 71, 0.98) 100%);
        border: 1px solid rgba(132, 184, 255, 0.12);
        border-radius: 24px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 18px 42px rgba(3, 8, 24, 0.26);
      }
      .um-muted {
        color: #eef4ff;
      }
      .um-label {
        color: #7bcfff;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-weight: 700;
        font-size: 12px;
      }
      .um-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 16px;
        border-radius: 999px;
        background: rgba(146, 189, 255, 0.10);
        border: 1px solid rgba(146, 189, 255, 0.16);
        color: #f3f7ff;
        font-weight: 700;
      }
      .um-section-title {
        color: #f3f7ff;
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.02em;
      }
      .um-section-copy {
        color: #eef4ff;
      }
      .stMetric {
        background: linear-gradient(180deg, rgba(17, 34, 96, 0.94) 0%, rgba(11, 24, 71, 0.94) 100%);
        border: 1px solid rgba(132, 184, 255, 0.12);
        border-radius: 18px;
        padding: 14px 16px;
      }
      .stMetric label, .stMetric [data-testid="stMetricLabel"] {
        color: #eef4ff !important;
      }
      .stMetric [data-testid="stMetricValue"] {
        color: #f3f7ff !important;
      }
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .stCaption, .stCaption p {
        color: #eef4ff !important;
      }
      section[data-testid="stSidebar"] * {
        color: #eef4ff !important;
      }
      section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #eef4ff !important;
      }
      section[data-testid="stSidebar"] h1,
      section[data-testid="stSidebar"] h2,
      section[data-testid="stSidebar"] h3,
      section[data-testid="stSidebar"] label,
      section[data-testid="stSidebar"] p,
      section[data-testid="stSidebar"] span,
      section[data-testid="stSidebar"] div {
        color: #f8fbff !important;
      }
      section[data-testid="stSidebar"] [data-baseweb="select"] > div,
      section[data-testid="stSidebar"] input,
      section[data-testid="stSidebar"] textarea,
      section[data-testid="stSidebar"] [data-baseweb="input"] > div {
        background: rgba(255,255,255,0.06) !important;
        border-color: rgba(123,207,255,0.16) !important;
        color: #f8fbff !important;
      }
      section[data-testid="stSidebar"] [data-baseweb="select"] svg,
      section[data-testid="stSidebar"] [data-baseweb="input"] svg {
        fill: #eef4ff !important;
        color: #eef4ff !important;
      }
      section[data-testid="stSidebar"] hr {
        border-color: rgba(123,207,255,0.14) !important;
      }
      section[data-testid="stSidebar"] [data-testid="stCheckbox"] label {
        color: #f8fbff !important;
      }
      .stDataFrame, div[data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
      }
      div[data-testid="stExpander"] {
        border: 1px solid rgba(132, 184, 255, 0.12);
        border-radius: 18px;
        background: rgba(10, 23, 65, 0.72);
      }
      div[data-testid="stExpander"] summary,
      div[data-testid="stExpander"] p,
      div[data-testid="stExpander"] div {
        color: #eef4ff !important;
      }
      /* Compact vertical gaps between all elements */
      .element-container {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
      }
      /* Remove extra space around iframes */
      iframe {
        display: block !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
      }
      /* Compact dividers */
      hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


FOOTWORK_BLOCKS = {
    "Participación": {
        "weight": 1.0,
        "description": "Cuánto entra el portero en circuito de pase y cuántas veces se le activa.",
        "metrics": {
            "received_pass_avg": 0.8,
            "passes_avg": 1.0,
        },
    },
    "Precisión global": {
        "weight": 1.1,
        "description": "Calidad general del pase en su volumen total.",
        "metrics": {
            "accurate_passes_percent": 1.0,
        },
    },
    "Progresión": {
        "weight": 1.2,
        "description": "Capacidad para activar juego hacia delante con uso y limpieza.",
        "metrics": {
            "forward_passes_avg": 0.9,
            "successful_forward_passes_percent": 1.1,
        },
    },
    "Juego corto/medio": {
        "weight": 1.0,
        "description": "Uso del pase corto/medio y su precisión para sostener salida.",
        "metrics": {
            "short_medium_pass_avg": 0.9,
            "accurate_short_medium_pass_percent": 1.1,
        },
    },
    "Juego largo": {
        "weight": 1.15,
        "description": "Frecuencia, eficacia y alcance del pase largo.",
        "metrics": {
            "long_passes_avg": 0.9,
            "successful_long_passes_percent": 1.0,
            "average_long_pass_length": 0.45,
        },
    },
    "Estilo": {
        "weight": 0.5,
        "description": "Tendencia general a jugar más corto o más directo.",
        "metrics": {
            "average_pass_length": 1.0,
        },
    },
}


SHOTSTOPPING_BLOCKS = {
    "Carga defensiva": {
        "weight": 0.95,
        "description": "Volumen de remates y exigencia que soporta.",
        "metrics": {
            "shots_against_avg": 1.0,
        },
    },
    "Parada": {
        "weight": 1.5,
        "description": "Respuesta de portería y valor generado bajo remate.",
        "metrics": {
            "save_percent": 1.05,
            "prevented_goals_avg": 1.2,
            "xg_save_avg": 0.7,
        },
    },
    "Dominio de área": {
        "weight": 0.85,
        "description": "Intervención fuera de línea y respuesta aérea.",
        "metrics": {
            "goalkeeper_exits_avg": 1.0,
            "gk_aerial_duels_avg": 0.9,
        },
    },
    "Resultado": {
        "weight": 0.6,
        "description": "Resultado defensivo final, con menor peso por dependencia del contexto.",
        "metrics": {
            "conceded_goals_avg": -1.0,
            "clean_sheets": 0.8,
        },
    },
}


FREE_METRICS = {
    "received_pass_avg": "Pases recibidos/90",
    "passes_avg": "Pases/90",
    "accurate_passes_percent": "Precisión pases %",
    "forward_passes_avg": "Pases hacia adelante/90",
    "successful_forward_passes_percent": "Precisión pases hacia adelante %",
    "short_medium_pass_avg": "Pases cortos/medios /90",
    "accurate_short_medium_pass_percent": "Precisión cortos/medios %",
    "long_passes_avg": "Pases largos/90",
    "successful_long_passes_percent": "Precisión largos %",
    "average_pass_length": "Longitud media del pase",
    "average_long_pass_length": "Longitud media del pase largo",
    "shots_against_avg": "Remates en contra/90",
    "save_percent": "Paradas %",
    "prevented_goals_avg": "Goles evitados/90",
    "xg_save_avg": "xG en contra/90",
    "goalkeeper_exits_avg": "Salidas/90",
    "gk_aerial_duels_avg": "Duelos aéreos/90",
    "conceded_goals_avg": "Goles recibidos/90",
    "clean_sheets": "Porterías a cero",
}


@st.cache_data(show_spinner=False)
def load_goalkeeper_dataframe() -> tuple[pd.DataFrame, dict]:
    try:
        rows = load_goalkeepers()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        st.error(f"Error al cargar los datos: {exc}")
        st.stop()
    return pd.DataFrame(rows), build_metadata(rows)


def fmt_number(value: float | int | None, digits: int = 0, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "-"
    if digits == 0:
        return f"{int(round(float(value))):,}".replace(",", ".") + suffix
    return f"{float(value):,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".") + suffix


def fmt_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return fmt_number(value * 100, 1, "%")


def render_svg(svg: str, height: int) -> None:
    render_html(svg, height)


def render_html(html: str, height: int, scrolling: bool = False) -> None:
    payload = textwrap.dedent(html).strip()
    if "<html" not in payload.lower():
        payload = f"""
        <html>
          <body style="margin:0;background:transparent;overflow:hidden;">
            {payload}
          </body>
        </html>
        """
    st.components.v1.html(textwrap.dedent(payload).strip(), height=height, scrolling=scrolling)


def silhouette_svg() -> str:
    return """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 300" width="240" height="300">
      <defs><linearGradient id="sil-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#fffaf1"/><stop offset="100%" stop-color="#efe6d7"/></linearGradient></defs>
      <rect width="240" height="300" rx="28" fill="url(#sil-bg)"/><circle cx="120" cy="92" r="44" fill="#d9d1c4"/><path d="M52 264c8-52 42-82 68-82s60 30 68 82" fill="#d9d1c4"/>
    </svg>
    """


def color_for_score(score: float | None) -> str:
    if score is None or pd.isna(score):
        return "#7dc9ff"
    score = max(0.0, min(float(score), 100.0))
    if score <= 50:
        start, end, ratio = (255, 99, 132), (255, 209, 102), score / 50
    else:
        start, end, ratio = (255, 209, 102), (134, 255, 120), (score - 50) / 50
    r = round(start[0] + (end[0] - start[0]) * ratio)
    g = round(start[1] + (end[1] - start[1]) * ratio)
    b = round(start[2] + (end[2] - start[2]) * ratio)
    return f"rgb({r},{g},{b})"


def metric_percentile(reference_df: pd.DataFrame, metric: str, value: float | int | None, higher_is_better: bool = True) -> float | None:
    if value is None or pd.isna(value) or metric not in reference_df.columns:
        return None
    series = pd.to_numeric(reference_df[metric], errors="coerce").dropna()
    if series.empty:
        return None
    pct = float((series <= float(value)).mean() * 100)
    return pct if higher_is_better else 100 - pct


def compute_metric_score(df: pd.DataFrame, metrics: dict[str, float]) -> pd.Series:
    score = pd.Series([0.0] * len(df), index=df.index, dtype="float64")
    total_weight = 0.0
    for metric, weight in metrics.items():
        if metric not in df.columns or weight == 0:
            continue
        series = pd.to_numeric(df[metric], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            continue
        ranks = valid.rank(pct=True, ascending=weight > 0)
        component = pd.Series(0.5, index=df.index, dtype="float64")
        component.loc[valid.index] = ranks
        score += component * abs(weight)
        total_weight += abs(weight)
    return pd.Series([0.0] * len(df), index=df.index, dtype="float64") if total_weight == 0 else ((score / total_weight) * 100).round(2)


def compute_macro(df: pd.DataFrame, blocks: dict[str, dict], prefix: str) -> pd.DataFrame:
    out = df.copy()
    weighted = pd.Series([0.0] * len(out), index=out.index, dtype="float64")
    total_weight = 0.0
    for block_name, config in blocks.items():
        block_score = compute_metric_score(out, config.get("metrics", {}))
        out[f"{prefix}__{block_name}"] = block_score
        weight = float(config.get("weight", 0))
        weighted += block_score * weight
        total_weight += weight
    out[f"{prefix}_score"] = 0.0 if total_weight == 0 else (weighted / total_weight).round(2)
    return out


def enrich_all_scores(df: pd.DataFrame, custom_metrics: dict[str, float] | None = None) -> pd.DataFrame:
    out = df.copy()
    def aligned_numeric(column: str) -> pd.Series:
        if column not in out.columns:
            return pd.Series(float("nan"), index=out.index, dtype="float64")
        return pd.to_numeric(out[column], errors="coerce")

    passes = aligned_numeric("passes_avg")
    forward = aligned_numeric("forward_passes_avg")
    backward = aligned_numeric("back_passes_avg")
    lateral = (passes - forward - backward).clip(lower=0)
    accurate_total = passes * aligned_numeric("accurate_passes_percent") / 100
    accurate_forward = forward * aligned_numeric("successful_forward_passes_percent") / 100
    accurate_backward = backward * aligned_numeric("successful_back_passes_percent") / 100
    accurate_lateral = (accurate_total - accurate_forward - accurate_backward).clip(lower=0)
    out["lateral_pass_avg"] = lateral
    out["accurate_lateral_pass_percent"] = (accurate_lateral.clip(upper=lateral) / lateral * 100).where(lateral > 0)

    out = compute_macro(out, FOOTWORK_BLOCKS, "footwork")
    out = compute_macro(out, SHOTSTOPPING_BLOCKS, "shotstop")
    if custom_metrics:
        out["custom_score"] = compute_metric_score(out, custom_metrics)
    else:
        out["custom_score"] = 0.0
    return out


def player_flags(row: pd.Series) -> list[str]:
    flags = []
    if row.get("is_youth_team"):
        flags.append("Cantera")
    if row.get("on_loan"):
        flags.append("Cesión")
    if not row.get("competition_matches_source"):
        flags.append("Fuera competición objetivo")
    if row.get("group_name") == "Sin grupo":
        flags.append("Sin grupo")
    return flags


def player_meta_line(row: pd.Series) -> str:
    parts = []
    if not pd.isna(row.get("age")):
        parts.append(f"{fmt_number(row['age'],1)} años")
    if row.get("height") not in (None, 0) and not pd.isna(row.get("height")):
        parts.append(f"{fmt_number(row['height'])} cm")
    if row.get("weight") not in (None, 0) and not pd.isna(row.get("weight")):
        parts.append(f"{fmt_number(row['weight'])} kg")
    return " · ".join(parts)


def format_market_value(value: float | int | None) -> str:
    if value is None or pd.isna(value) or float(value) <= 0:
        return "-"
    value = float(value)
    if value >= 1_000_000:
        return f"€{value/1_000_000:.1f}M".replace(".", ",")
    return f"€{int(round(value/1000))}k"


def score_band(score: float | None) -> tuple[str, str]:
    if score is None or pd.isna(score):
        return "SIN MUESTRA", "#7bcfff"
    score = float(score)
    if score >= 75:
        return "ALTO", "#86ff78"
    if score >= 55:
        return "MEDIO", "#7bcfff"
    if score >= 40:
        return "EN DESARROLLO", "#ffd166"
    return "BAJO", "#ff7a9a"


COUNTRY_DISPLAY = {
    "Argentina": ("🇦🇷", "Argentina"),
    "Brazil": ("🇧🇷", "Brasil"),
    "Bulgaria": ("🇧🇬", "Bulgaria"),
    "Canada": ("🇨🇦", "Canadá"),
    "Colombia": ("🇨🇴", "Colombia"),
    "England": ("🏴", "Inglaterra"),
    "France": ("🇫🇷", "Francia"),
    "Georgia": ("🇬🇪", "Georgia"),
    "Germany": ("🇩🇪", "Alemania"),
    "Greece": ("🇬🇷", "Grecia"),
    "Guinea": ("🇬🇳", "Guinea"),
    "Guinea-Bissau": ("🇬🇼", "Guinea-Bisáu"),
    "Hungary": ("🇭🇺", "Hungría"),
    "Italy": ("🇮🇹", "Italia"),
    "Lithuania": ("🇱🇹", "Lituania"),
    "Netherlands": ("🇳🇱", "Países Bajos"),
    "Peru": ("🇵🇪", "Perú"),
    "Portugal": ("🇵🇹", "Portugal"),
    "Romania": ("🇷🇴", "Rumanía"),
    "Russia": ("🇷🇺", "Rusia"),
    "Réunion": ("🇷🇪", "Reunión"),
    "Scotland": ("🏴", "Escocia"),
    "Spain": ("🇪🇸", "España"),
    "Switzerland": ("🇨🇭", "Suiza"),
    "Ukraine": ("🇺🇦", "Ucrania"),
    "United States": ("🇺🇸", "Estados Unidos"),
    "Uruguay": ("🇺🇾", "Uruguay"),
    "Venezuela": ("🇻🇪", "Venezuela"),
}


def player_countries(row: pd.Series) -> list[str]:
    raw = [part.strip() for part in str(row.get("passport_country_names") or "").split("|") if part.strip()]
    birth_country = str(row.get("birth_country_name") or "").strip()
    if birth_country and birth_country not in raw:
        raw.insert(0, birth_country)
    result = []
    for country in raw:
        flag, translated = COUNTRY_DISPLAY.get(country, ("", country))
        result.append(f"{flag} {translated}".strip())
    return result


def player_country(row: pd.Series) -> str:
    countries = player_countries(row)
    return " · ".join(countries) if countries else "-"


def translated_foot(value) -> str:
    return {"right": "Derecha", "left": "Izquierda", "unknown": "Sin dato"}.get(str(value or "").strip().lower(), "Sin dato")


def donut_svg(label: str, score: float | None, size: int = 120, stroke: int = 12) -> str:
    score = 0.0 if score is None or pd.isna(score) else max(0.0, min(float(score), 100.0))
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    offset = c * (1 - score / 100)
    color = color_for_score(score)
    return f"""
    <svg viewBox="0 0 {size} {size+24}" width="{size}" height="{size+24}" xmlns="http://www.w3.org/2000/svg">
      <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="rgba(125, 201, 255, 0.14)" stroke-width="{stroke}"/>
      <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"
        stroke-dasharray="{c:.2f}" stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {size/2} {size/2})"/>
      <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#f3f7ff" font-size="24" font-weight="800">{fmt_number(score,0)}</text>
      <text x="50%" y="{size+16}" text-anchor="middle" fill="#90a5dc" font-size="12" font-weight="700" letter-spacing="2">{label}</text>
    </svg>
    """


def stacked_kpi_svg(global_score: float | None, foot_score: float | None, stop_score: float | None) -> str:
    return f"""
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;">
      {donut_svg("KPI GLOBAL", global_score, size=128, stroke=13)}
      <div style="display:flex;gap:14px;align-items:flex-end;">
        {donut_svg("PIES", foot_score, size=78, stroke=9)}
        {donut_svg("PARADAS", stop_score, size=78, stroke=9)}
      </div>
    </div>
    """


def _safe_img_url(url: str) -> str:
    """Only allow https:// URLs from known CDNs to prevent mixed-content and injection."""
    url = url.strip()
    if url.startswith("https://") and "wyscout.com" in url:
        return url
    return ""


def build_player_header_html(row: pd.Series) -> str:
    image_url = _safe_img_url(str(row.get("image_url") or ""))
    if not image_url or "photo-not-found" in image_url:
        image_html = """
        <div style="width:200px;height:200px;border-radius:28px;background:linear-gradient(180deg,#172d78 0%,#0f1f5b 100%);display:flex;align-items:center;justify-content:center;border:1px solid rgba(123,207,255,.16);overflow:hidden;">
          <svg viewBox="0 0 240 240" width="170" height="170" xmlns="http://www.w3.org/2000/svg">
            <circle cx="120" cy="70" r="34" fill="rgba(255,255,255,.16)"/>
            <path d="M56 210c8-44 38-72 64-72s56 28 64 72" fill="rgba(255,255,255,.16)"/>
          </svg>
        </div>
        """
    else:
        image_html = f'<img src="{image_url}" style="width:200px;height:200px;object-fit:cover;border-radius:28px;border:1px solid rgba(123,207,255,.16);display:block;background:#10215c;" />'

    team_logo = _safe_img_url(str(row.get("team_logo_url") or ""))
    team_logo_html = ""
    if team_logo:
        team_logo_html = f'<img src="{team_logo}" style="width:44px;height:44px;object-fit:contain;display:block;" />'

    balance = (float(row.get("footwork_score", 0) or 0) + float(row.get("shotstop_score", 0) or 0)) / 2
    chips = []
    meta = player_meta_line(row)
    if meta:
        chips.extend(part.strip() for part in meta.split("·"))
    chips.extend(
        [
            player_country(row),
            f"Contrato: {row.get('contract_expires') or '-'}",
            "Cesión: Sí" if row.get("on_loan") else "Cesión: No",
            f"Pierna: {translated_foot(row.get('foot'))}",
            f"Valor: {format_market_value(row.get('market_value'))}",
        ]
    )
    chips_html = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:999px;background:rgba(146,189,255,.10);border:1px solid rgba(146,189,255,.16);color:#f3f7ff;font-weight:700;">{esc(chip)}</span>'
        for chip in chips
        if chip and chip != "-"
    )

    flag_line = player_flags(row)
    flags_html = ""
    if flag_line:
        flags_html = f'<div style="margin-top:10px;color:#eef4ff;font-size:14px;">{esc(" · ".join(flag_line))}</div>'

    return f"""
    <div style="background:linear-gradient(180deg,#0d1b57 0%,#0a153f 100%);border:1px solid rgba(95,218,255,.14);border-radius:28px;box-shadow:0 24px 60px rgba(5,10,30,.42);padding:26px 28px;">
      <div style="display:flex;gap:28px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;">
        <div style="display:flex;gap:28px;align-items:center;flex:1 1 620px;min-width:320px;">
          {image_html}
          <div style="flex:1 1 auto;min-width:260px;">
            <div style="font-size:56px;line-height:0.96;font-weight:900;color:#f8fbff;letter-spacing:-0.04em;">{esc(row["name"])}</div>
            <div style="margin-top:10px;color:#7bcfff;font-weight:800;letter-spacing:.08em;text-transform:uppercase;font-size:18px;">{esc((row.get("primary_position") or "Portero").upper())}</div>
            <div style="display:flex;align-items:center;gap:14px;margin-top:18px;flex-wrap:wrap;">
              {team_logo_html}
              <div style="font-size:20px;font-weight:800;color:#f3f7ff;">{esc(row["team_name"])}</div>
              <div style="color:#eef4ff;">·</div>
              <div style="font-size:18px;color:#3fe8be;font-weight:700;">{esc(row["source_competition"])}</div>
              <div style="color:#eef4ff;">·</div>
              <div style="font-size:18px;color:#d5ddff;font-weight:600;">{esc(row["group_name"])}</div>
            </div>
            <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:18px;">{chips_html}</div>
            {flags_html}
          </div>
        </div>
        <div style="display:flex;gap:18px;align-items:flex-end;justify-content:flex-end;flex:0 0 auto;flex-wrap:nowrap;min-width:340px;padding-top:8px;">
          {stacked_kpi_svg(balance, row.get("footwork_score"), row.get("shotstop_score"))}
        </div>
      </div>
    </div>
    """


def find_strengths_risks(row: pd.Series, reference_df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    metric_map = {
        "Paradas %": ("save_percent", True),
        "Goles evitados/90": ("prevented_goals_avg", True),
        "Salidas/90": ("goalkeeper_exits_avg", True),
        "Duelos aéreos/90": ("gk_aerial_duels_avg", True),
        "Pases/90": ("passes_avg", True),
        "Precisión pases %": ("accurate_passes_percent", True),
        "Pases hacia adelante/90": ("forward_passes_avg", True),
        "Precisión adelante %": ("successful_forward_passes_percent", True),
        "Pases largos/90": ("long_passes_avg", True),
        "Precisión largos %": ("successful_long_passes_percent", True),
        "% minutos": ("minutes_share", True),
        "Goles recibidos/90": ("conceded_goals_avg", False),
    }
    rows = []
    for label, (metric, higher) in metric_map.items():
        value = row.get(metric)
        pct = metric_percentile(reference_df, metric, value, higher)
        if pct is None:
            continue
        rows.append({"label": label, "value": value, "pct": pct})
    ordered = sorted(rows, key=lambda item: item["pct"], reverse=True)
    return ordered[:3], ordered[-3:]


def build_spider_svg(title: str, subtitle: str, labels: list[str], values: list[float], overall_score: float, accent: str) -> str:
    width, height = 520, 394
    cx, cy, radius = 190, 220, 92
    n = max(3, len(labels))

    def point(idx: int, factor: float) -> tuple[float, float]:
        angle = -math.pi / 2 + (2 * math.pi * idx / n)
        return cx + radius * factor * math.cos(angle), cy + radius * factor * math.sin(angle)

    grid = []
    for factor in [0.25, 0.5, 0.75, 1.0]:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in [point(i, factor) for i in range(n)])
        grid.append(f'<polygon points="{pts}" fill="none" stroke="rgba(123,207,255,.10)" stroke-width="1"/>')

    axes, texts = [], []
    for idx, label in enumerate(labels):
        angle = -math.pi / 2 + (2 * math.pi * idx / n)
        x2, y2 = point(idx, 1.0)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(123,207,255,.14)" stroke-width="1"/>')
        lx, ly = point(idx, 1.22)
        anchor = "middle"
        if lx < cx - 16:
            anchor = "end"
        elif lx > cx + 16:
            anchor = "start"
        # Keep the metric and its value as one compact label group.
        is_top = abs(angle + math.pi / 2) < 0.2
        is_bottom = abs(angle - math.pi / 2) < 0.2
        label_y = ly - 5 if is_top else ly
        value_y = label_y + (15 if is_bottom else 14)
        texts.append(
            f'<text x="{lx:.1f}" y="{label_y:.1f}" text-anchor="{anchor}" fill="#f3f7ff" font-size="12" font-weight="700">{label}</text>'
            f'<text x="{lx:.1f}" y="{value_y:.1f}" text-anchor="{anchor}" fill="{accent}" font-size="11" font-weight="800">{fmt_number(value if (value:=values[idx]) is not None else 0,1)}</text>'
        )

    pts = []
    for idx, value in enumerate(values):
        pts.append(point(idx, max(0.0, min(float(value), 100.0)) / 100.0))
    polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    band, band_color = score_band(overall_score)

    return f"""
    <div class="um-dark-card" style="padding:12px 14px;">
      <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">
        <defs><linearGradient id="fill-{title}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="{accent}" stop-opacity="0.06"/><stop offset="100%" stop-color="{accent}" stop-opacity="0.01"/></linearGradient></defs>
        <text x="28" y="34" fill="#f3f7ff" font-size="28" font-weight="900">{title}</text>
        <text x="28" y="57" fill="#eef4ff" font-size="13">{subtitle}</text>
        <text x="484" y="34" fill="{band_color}" font-size="13" text-anchor="end" font-weight="800" letter-spacing="2">{band}</text>
        <text x="484" y="68" fill="{color_for_score(overall_score)}" font-size="48" text-anchor="end" font-weight="900">{fmt_number(overall_score,1)}</text>
        <text x="484" y="86" fill="#eef4ff" font-size="12" text-anchor="end" font-weight="700" letter-spacing="2">ENCAJE</text>
        {"".join(grid)}{"".join(axes)}
        <polygon points="{polygon}" fill="none" stroke="{accent}" stroke-width="3"/>
        {"".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{accent}" stroke="#fffaf1" stroke-width="1.8"/>' for x,y in pts)}
        {"".join(texts)}
      </svg>
    </div>
    """


def build_distribution_svg(row: pd.Series, reference_df: pd.DataFrame) -> str:
    short_medium = safe_number(row.get("short_medium_pass_avg"))
    short_medium_acc = safe_number(row.get("accurate_short_medium_pass_percent"))
    long = safe_number(row.get("long_passes_avg"))
    long_acc = safe_number(row.get("successful_long_passes_percent"))
    lateral = safe_number(row.get("lateral_pass_avg"))
    lateral_acc = safe_number(row.get("accurate_lateral_pass_percent"))
    received = safe_number(row.get("received_pass_avg"))
    avg_len = safe_number(row.get("average_pass_length"))
    max_avg_len = visible_max(reference_df, "average_pass_length", avg_len)
    max_short = visible_max(reference_df, "short_medium_pass_avg", short_medium)
    max_long = visible_max(reference_df, "long_passes_avg", long)
    max_lateral = visible_max(reference_df, "lateral_pass_avg", lateral)
    max_received = visible_max(reference_df, "received_pass_avg", received)
    short_pct = metric_percentile(reference_df, "short_medium_pass_avg", row.get("short_medium_pass_avg"))
    short_acc_pct = metric_percentile(reference_df, "accurate_short_medium_pass_percent", row.get("accurate_short_medium_pass_percent"))
    long_pct = metric_percentile(reference_df, "long_passes_avg", row.get("long_passes_avg"))
    long_acc_pct = metric_percentile(reference_df, "successful_long_passes_percent", row.get("successful_long_passes_percent"))
    lateral_pct = metric_percentile(reference_df, "lateral_pass_avg", row.get("lateral_pass_avg"))
    lateral_acc_pct = metric_percentile(reference_df, "accurate_lateral_pass_percent", row.get("accurate_lateral_pass_percent"))
    received_pct = metric_percentile(reference_df, "received_pass_avg", row.get("received_pass_avg"))

    def pct_label(value: float | None) -> str:
        return "-" if value is None or pd.isna(value) else f"P{int(round(value))}"

    def pitch_metric_card(
        x: float,
        y: float,
        width: int,
        title: str,
        accent: str,
        volume: str,
        volume_pct: float | None,
        accuracy: str,
        accuracy_pct: float | None,
    ) -> str:
        return f"""
        <g transform="translate({x:.1f}, {y:.1f})">
          <rect x="0" y="0" width="{width}" height="66" rx="12" fill="rgba(9,24,66,.92)" stroke="{accent}" stroke-opacity=".28"/>
          <text x="12" y="17" fill="{accent}" font-size="12" font-weight="800">{title}</text>
          <line x1="12" y1="24" x2="{width - 12}" y2="24" stroke="rgba(123,207,255,.12)"/>
          <text x="12" y="41" fill="#eef4ff" font-size="10">Vol. {volume}</text>
          <text x="{width - 12}" y="41" text-anchor="end" fill="{accent}" font-size="11" font-weight="900">{pct_label(volume_pct)}</text>
          <text x="12" y="57" fill="#eef4ff" font-size="10">Prec. {accuracy}</text>
          <text x="{width - 12}" y="57" text-anchor="end" fill="{accent}" font-size="11" font-weight="900">{pct_label(accuracy_pct)}</text>
        </g>
        """

    short_scale = max(0.0, min(short_medium / max(max_short, 1e-6), 1.0))
    long_scale = max(0.0, min(long / max(max_long, 1e-6), 1.0))
    lateral_scale = max(0.0, min(lateral / max(max_lateral, 1e-6), 1.0))
    received_scale = max(0.0, min(received / max(max_received, 1e-6), 1.0))
    player_scale = max(0.0, min(avg_len / max(max_avg_len, 1e-6), 1.0))
    scale_height = 294
    player_scale_height = scale_height * player_scale
    style_color = color_for_score(min(100.0, max(0.0, avg_len * 2)))

    field_x, field_y, field_w, field_h = 110, 82, 700, 390
    gk_x, gk_y = field_x + field_w / 2, field_y + 42

    short_max_end = (gk_x - 96, gk_y + 158)
    short_end = (gk_x - (22 + 74 * short_scale), gk_y + (24 + 134 * short_scale))
    short_start = (gk_x - 10, gk_y + 28)
    short_c1 = (gk_x - 12, gk_y + 42)
    short_c2_max = (gk_x - 48, gk_y + 94)
    short_c2 = (gk_x - (16 + 32 * short_scale), gk_y + (26 + 68 * short_scale))

    long_max_end = (gk_x + 166, gk_y + 244)
    long_end = (gk_x + (34 + 132 * long_scale), gk_y + (36 + 208 * long_scale))
    long_start = (gk_x + 10, gk_y + 28)
    long_c1 = (gk_x + 16, gk_y + 48)
    long_c2_max = (gk_x + 92, gk_y + 148)
    long_c2 = (gk_x + (24 + 68 * long_scale), gk_y + (38 + 110 * long_scale))

    lateral_max_end = (gk_x - 216, gk_y + 12)
    lateral_end = (gk_x - (26 + 190 * lateral_scale), gk_y + 12)
    lateral_start = (gk_x - 16, gk_y + 24)
    lateral_c1 = (gk_x - 42, gk_y + 30)
    lateral_c2_max = (lateral_max_end[0] + 70, gk_y + 12)
    lateral_c2 = (lateral_end[0] + 48, gk_y + 12)

    recv_start_max = (gk_x + 224, gk_y + 12)
    recv_start = (gk_x + (32 + 192 * received_scale), gk_y + 12)
    recv_c1_max = (gk_x + 166, gk_y + 8)
    received_end = (gk_x + 16, gk_y + 24)
    recv_c2_max = (gk_x + 62, gk_y + 24)
    recv_c1 = (gk_x + (28 + 138 * received_scale), gk_y + 8)
    recv_c2 = (gk_x + (18 + 44 * received_scale), gk_y + 24)

    return f"""
    <div class="um-dark-card" style="padding:12px 14px;">
      <svg viewBox="0 0 940 500" width="100%" height="500" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="arrow-short" markerWidth="6" markerHeight="6" refX="5.2" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#49e4c8"/></marker>
          <marker id="arrow-long" markerWidth="6" markerHeight="6" refX="5.2" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#b7ff62"/></marker>
          <marker id="arrow-lateral" markerWidth="6" markerHeight="6" refX="5.2" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#7bcfff"/></marker>
          <marker id="arrow-received" markerWidth="6" markerHeight="6" refX="5.2" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#f8c36f"/></marker>
        </defs>
        <text x="24" y="32" fill="#f3f7ff" font-size="28" font-weight="900">Vías de distribución</text>
        <text x="24" y="54" fill="#eef4ff" font-size="14">Medio campo en planta para leer corto/medio, largo, lateral estimado y pases recibidos</text>

        <rect x="{field_x}" y="{field_y}" width="{field_w}" height="{field_h}" rx="20" fill="rgba(8,24,66,.46)" stroke="rgba(123,207,255,.18)" stroke-width="2"/>
        <rect x="{gk_x - 58:.1f}" y="{field_y}" width="116" height="50" fill="none" stroke="rgba(123,207,255,.14)" stroke-width="2"/>
        <rect x="{gk_x - 28:.1f}" y="{field_y}" width="56" height="18" fill="none" stroke="rgba(123,207,255,.14)" stroke-width="2"/>

        <line x1="76" y1="98" x2="76" y2="{98 + scale_height:.1f}" stroke="rgba(240,223,97,.22)" stroke-width="5" stroke-linecap="round"/>
        <line x1="76" y1="98" x2="76" y2="{98 + player_scale_height:.1f}" stroke="#f0df61" stroke-width="9" stroke-linecap="round"/>
        <text x="34" y="100" fill="#eef4ff" font-size="12" font-weight="700">Min</text>
        <text x="20" y="{102 + scale_height:.1f}" fill="#eef4ff" font-size="12" font-weight="700">Máx {fmt_number(max_avg_len,1)} m</text>
        <text x="72" y="{112 + player_scale_height/2:.1f}" fill="#f0df61" font-size="12" font-weight="800" text-anchor="end">Jugador {fmt_number(avg_len,1)} m</text>

        <circle cx="{gk_x}" cy="{gk_y}" r="17" fill="{style_color}"/>
        <text x="{gk_x}" y="{gk_y + 5}" fill="#06102d" text-anchor="middle" font-size="11" font-weight="900">GK</text>

        <path d="M{short_start[0]:.1f} {short_start[1]:.1f} C{short_c1[0]:.1f} {short_c1[1]:.1f}, {short_c2_max[0]:.1f} {short_c2_max[1]:.1f}, {short_max_end[0]:.1f} {short_max_end[1]:.1f}" fill="none" stroke="rgba(73,228,200,.18)" stroke-width="5" stroke-linecap="round"/>
        <path d="M{short_start[0]:.1f} {short_start[1]:.1f} C{short_c1[0]:.1f} {short_c1[1]:.1f}, {short_c2[0]:.1f} {short_c2[1]:.1f}, {short_end[0]:.1f} {short_end[1]:.1f}" fill="none" stroke="#49e4c8" stroke-width="5" stroke-linecap="round" marker-end="url(#arrow-short)"/>
        <text x="{short_max_end[0] - 8:.1f}" y="{short_max_end[1] + 18:.1f}" fill="#49e4c8" font-size="11" font-weight="800">Máx {fmt_number(max_short,1)}</text>

        <path d="M{long_start[0]:.1f} {long_start[1]:.1f} C{long_c1[0]:.1f} {long_c1[1]:.1f}, {long_c2_max[0]:.1f} {long_c2_max[1]:.1f}, {long_max_end[0]:.1f} {long_max_end[1]:.1f}" fill="none" stroke="rgba(183,255,98,.18)" stroke-width="5" stroke-linecap="round"/>
        <path d="M{long_start[0]:.1f} {long_start[1]:.1f} C{long_c1[0]:.1f} {long_c1[1]:.1f}, {long_c2[0]:.1f} {long_c2[1]:.1f}, {long_end[0]:.1f} {long_end[1]:.1f}" fill="none" stroke="#b7ff62" stroke-width="5" stroke-linecap="round" marker-end="url(#arrow-long)"/>
        <text x="{long_max_end[0] + 8:.1f}" y="{long_max_end[1] + 10:.1f}" fill="#b7ff62" font-size="11" font-weight="800">Máx {fmt_number(max_long,1)}</text>

        <path d="M{lateral_start[0]:.1f} {lateral_start[1]:.1f} C{lateral_c1[0]:.1f} {lateral_c1[1]:.1f}, {lateral_c2_max[0]:.1f} {lateral_c2_max[1]:.1f}, {lateral_max_end[0]:.1f} {lateral_max_end[1]:.1f}" fill="none" stroke="rgba(123,207,255,.18)" stroke-width="5" stroke-linecap="round"/>
        <path d="M{lateral_start[0]:.1f} {lateral_start[1]:.1f} C{lateral_c1[0]:.1f} {lateral_c1[1]:.1f}, {lateral_c2[0]:.1f} {lateral_c2[1]:.1f}, {lateral_end[0]:.1f} {lateral_end[1]:.1f}" fill="none" stroke="#7bcfff" stroke-width="5" stroke-linecap="round" marker-end="url(#arrow-lateral)"/>
        <text x="{lateral_max_end[0] - 8:.1f}" y="{lateral_max_end[1] - 10:.1f}" text-anchor="end" fill="#7bcfff" font-size="11" font-weight="800">Máx {fmt_number(max_lateral,1)}</text>

        <path d="M{recv_start_max[0]:.1f} {recv_start_max[1]:.1f} C{recv_c1_max[0]:.1f} {recv_c1_max[1]:.1f}, {recv_c2_max[0]:.1f} {recv_c2_max[1]:.1f}, {received_end[0]:.1f} {received_end[1]:.1f}" fill="none" stroke="rgba(248,195,111,.18)" stroke-width="5" stroke-linecap="round"/>
        <path d="M{recv_start[0]:.1f} {recv_start[1]:.1f} C{recv_c1[0]:.1f} {recv_c1[1]:.1f}, {recv_c2[0]:.1f} {recv_c2[1]:.1f}, {received_end[0]:.1f} {received_end[1]:.1f}" fill="none" stroke="#f8c36f" stroke-width="5" stroke-linecap="round" marker-end="url(#arrow-received)"/>
        <text x="{recv_start_max[0] + 8:.1f}" y="{recv_start_max[1] - 10:.1f}" fill="#f8c36f" font-size="11" font-weight="800">Máx {fmt_number(max_received,1)}</text>

        {pitch_metric_card(gk_x - 188, gk_y + 178, 164, "Corto/medio", "#49e4c8", f"{fmt_number(short_medium,1)} /90", short_pct, f"{fmt_number(short_medium_acc,1)}%", short_acc_pct)}
        {pitch_metric_card(gk_x + 70, gk_y + 246, 154, "Largo", "#b7ff62", f"{fmt_number(long,1)} /90", long_pct, f"{fmt_number(long_acc,1)}%", long_acc_pct)}
        {pitch_metric_card(field_x + 24, gk_y + 32, 174, "Laterales estimados", "#7bcfff", f"{fmt_number(lateral,1)} /90", lateral_pct, f"{fmt_number(lateral_acc,1)}%", lateral_acc_pct)}
        {pitch_metric_card(gk_x + 82, gk_y + 32, 160, "Recibidos", "#f8c36f", f"{fmt_number(received,1)} /90", received_pct, "No aplica", None)}

      </svg>
    </div>
    """


def stat_card(title: str, value: str, percentile: float | None, subtitle: str) -> str:
    color = color_for_score(percentile)
    label = "-" if percentile is None else f"{percentile:.0f}/100"
    return f'<div class="um-dark-card" style="padding:18px 18px 16px;position:relative;overflow:hidden;min-height:142px;"><div style="position:absolute; inset:0 auto 0 0; width:8px; background:{color};"></div><div style="font-size:13px; color:#eef4ff; margin-bottom:10px; text-transform:uppercase; letter-spacing:.08em; font-weight:700;">{title}</div><div style="font-size:34px; line-height:1; font-weight:900; color:#f3f7ff; margin-bottom:12px;">{value}</div><div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-end;"><div style="font-size:12px; color:#eef4ff; max-width:70%;">{subtitle}</div><div style="font-size:12px; color:{color}; font-weight:800; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.06); padding:6px 10px; border-radius:999px;">P{label.replace('/100','')}</div></div></div>'


def build_metric_bars_html(items: list[tuple[str, str, float | None, str]], columns: int = 2) -> str:
    rows = []
    for title, value, percentile, subtitle in items:
        pct = 0 if percentile is None or pd.isna(percentile) else max(0.0, min(float(percentile), 100.0))
        color = color_for_score(percentile)
        pill = "-" if percentile is None or pd.isna(percentile) else f"P{int(round(float(percentile)))}"
        rows.append(
            f"""
            <div class="um-dark-card" style="padding:16px 18px;">
              <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:8px;">
                <div>
                  <div style="font-size:13px;color:#eef4ff;text-transform:uppercase;letter-spacing:.08em;font-weight:800;">{esc(title)}</div>
                  <div style="font-size:13px;color:#eef4ff;opacity:.92;margin-top:6px;">{esc(subtitle)}</div>
                </div>
                <div style="text-align:right;min-width:96px;">
                  <div style="font-size:28px;color:#f3f7ff;font-weight:900;line-height:1;">{esc(value)}</div>
                  <div style="font-size:12px;color:{color};font-weight:800;margin-top:6px;">{pill}</div>
                </div>
              </div>
              <div style="height:10px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;">
                <div style="width:{pct:.1f}%;height:100%;background:{color};border-radius:999px;"></div>
              </div>
              <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:#eef4ff;opacity:.88;">
                <span>0</span><span>Percentil {pct:.0f}</span><span>100</span>
              </div>
            </div>
            """
        )
    return f'<div style="display:grid;grid-template-columns:repeat({columns}, minmax(0,1fr));gap:14px;">{"".join(rows)}</div>'


def build_block_explanations_html() -> str:
    def section(title: str, blocks: dict[str, dict]) -> str:
        items = []
        for block_name, block in blocks.items():
            metrics = [FREE_METRICS[k] for k, v in block["metrics"].items() if v != 0]
            items.append(
                f"""
                <div style="padding:12px 0;border-top:1px solid rgba(123,207,255,.10);">
                  <div style="color:#f8fbff;font-size:18px;font-weight:800;">{esc(block_name)}</div>
                  <div style="color:#eef4ff;font-size:14px;line-height:1.6;margin-top:6px;">{esc(block["description"])}. Métricas: {esc(", ".join(metrics))}.</div>
                </div>
                """
            )
        return f"""
        <div class="um-dark-card" style="padding:18px 20px;">
          <div class="um-label" style="margin-bottom:6px;">{esc(title)}</div>
          {''.join(items)}
        </div>
        """

    return f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
      {section("Juego de pies", FOOTWORK_BLOCKS)}
      {section("Paradas", SHOTSTOPPING_BLOCKS)}
    </div>
    """


def build_axis_explanations_html() -> str:
    foot_items = [
        "Participación: pases recibidos y pases totales.",
        "Precisión global: limpieza del pase total.",
        "Progresión: uso y precisión del pase hacia delante.",
        "Juego corto/medio: frecuencia y precisión en salida corta/media.",
        "Juego largo: frecuencia, precisión y alcance del pase largo.",
        "Estilo: longitud media del pase, para entender si juega más corto o más directo.",
    ]
    stop_items = [
        "Carga defensiva: volumen de remates que afronta.",
        "Parada: paradas %, goles evitados y xG save.",
        "Dominio de área: salidas y duelos aéreos.",
        "Resultado: goles recibidos y porterías a cero, con menor peso por contexto de equipo.",
    ]

    def group(title: str, items: list[str]) -> str:
        return f"""
        <div>
          <div class="um-label" style="margin-bottom:8px;">{esc(title)}</div>
          <div style="display:flex;flex-direction:column;gap:8px;">
            {''.join(f'<div style="color:#f3f7ff;font-size:14px;line-height:1.5;">• {esc(item)}</div>' for item in items)}
          </div>
        </div>
        """

    return f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      {group("Juego de pies", foot_items)}
      {group("Paradas", stop_items)}
    </div>
    """


def build_notes_html(notes: list[str]) -> str:
    rows = "".join(
        f'<div style="color:#f3f7ff;font-size:14px;line-height:1.55;padding:8px 0;border-top:1px solid rgba(123,207,255,.10);">• {esc(note)}</div>'
        for note in notes
    )
    return f'<div class="um-dark-card" style="padding:12px 18px;">{rows}</div>'


def build_attacking_contribution_html(row: pd.Series, reference_df: pd.DataFrame) -> str:
    metrics = [
        ("Asistencias", "assists", 0),
        ("Asistencias/90", "assists_avg", 2),
        ("xA total", "xg_assist", 2),
        ("xA/90", "xg_assist_avg", 2),
        ("Asistencias de tiro/90", "shot_assists_avg", 2),
        ("Preasistencias/90", "pre_assist_avg", 2),
        ("Pre-preasistencias/90", "pre_pre_assist_avg", 2),
    ]
    cards = []
    sample_size = len(reference_df)
    for label, metric, digits in metrics:
        value = row.get(metric)
        numeric = numeric_column(reference_df, metric)
        positives = numeric[numeric > 0]
        positive_count = len(positives)
        if value is None or pd.isna(value) or float(value) <= 0:
            standing = "Sin registro positivo"
            accent = "#90a5dc"
        else:
            rank = int((positives > float(value)).sum()) + 1
            standing = f"{rank}.º entre {positive_count} casos positivos"
            accent = "#f8c36f"
        cards.append(
            f"""
            <div style="padding:13px 15px;background:linear-gradient(180deg,rgba(17,34,96,.98) 0%,rgba(11,24,71,.98) 100%);border:1px solid rgba(132,184,255,.12);border-radius:16px;">
              <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;">
                <div>
                  <div style="color:#f3f7ff;font-size:13px;font-weight:800;">{esc(label)}</div>
                  <div style="color:{accent};font-size:10px;font-weight:800;margin-top:4px;">{standing}</div>
                </div>
                <div style="color:{accent};font-size:23px;font-weight:900;">{fmt_number(value, digits)}</div>
              </div>
            </div>
            """
        )
    return f"""
    <div style="padding:16px;background:rgba(9,24,66,.42);border:1px solid rgba(123,207,255,.10);border-radius:24px;">
      <div style="color:#f3f7ff;font-size:20px;font-weight:900;margin-bottom:12px;">Contribución ofensiva</div>
      <div style="display:grid;grid-template-columns:1fr;gap:9px;">{''.join(cards)}</div>
      <div style="color:#aebde5;font-size:11px;line-height:1.4;margin-top:12px;">Comparación entre los {sample_size} porteros visibles; la posición solo se calcula entre registros positivos.</div>
    </div>
    """


COMPETITION_LABELS = {
    "1RFEF": "1RFEF",
    "2RFEF": "2RFEF",
    "LaLiga2": "LaLiga 2",
    "National1": "National 1",
    "National2": "National 2",
    "Portugal2": "Portugal 2",
    "Portugal3": "Portugal 3",
    "Portugal4": "Portugal 4",
}


def filter_dataframe(
    df: pd.DataFrame,
    competitions: list[str],
    search_text: str,
    min_matches: int,
    min_minutes_share: float,
    target_competition_only: bool,
    include_youth: bool,
    include_loans: bool,
    include_unknown_group: bool,
) -> pd.DataFrame:
    filtered = df.copy()
    if competitions:
        filtered = filtered[filtered["source_competition"].isin(competitions)]
    if target_competition_only:
        filtered = filtered[filtered["competition_matches_source"]]
    if not include_youth:
        filtered = filtered[~filtered["is_youth_team"]]
    if not include_loans:
        filtered = filtered[~filtered["on_loan"]]
    if not include_unknown_group:
        filtered = filtered[filtered["group_name"] != "Sin grupo"]
    filtered = filtered[filtered["total_matches"].fillna(0) >= min_matches]
    filtered = filtered[filtered["minutes_share"].fillna(0) >= min_minutes_share]
    query = search_text.strip().lower()
    if query:
        mask = (
            filtered["name"].fillna("").str.lower().str.contains(query, regex=False)
            | filtered["full_name"].fillna("").str.lower().str.contains(query, regex=False)
            | filtered["team_name"].fillna("").str.lower().str.contains(query, regex=False)
        )
        filtered = filtered[mask]
    return filtered.reset_index(drop=True)


def build_plot(df: pd.DataFrame):
    if df.empty:
        return None
    color_map = {
        "1RFEF": "#7bcfff",
        "2RFEF": "#86ff78",
        "LaLiga2": "#ffd166",
        "National1": "#ff9f6e",
        "National2": "#d98cff",
        "Portugal2": "#4de2c5",
        "Portugal3": "#ff7fb0",
        "Portugal4": "#a6b8ff",
    }
    fig = px.scatter(
        df,
        x="footwork_score",
        y="shotstop_score",
        color="source_competition",
        hover_name="name",
        hover_data={"team_name": True, "group_name": True, "footwork_score": ":.1f", "shotstop_score": ":.1f"},
        color_discrete_map=color_map,
        labels={"footwork_score": "Juego de pies", "shotstop_score": "Paradas"},
    )
    fig.update_traces(marker=dict(size=12, line=dict(width=1.4, color="rgba(4,8,20,.85)"), opacity=0.9))
    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,23,65,0.82)",
        font=dict(color="#dfe7ff"),
        legend=dict(
            title=dict(text="Competición", font=dict(color="#ffffff", size=13)),
            font=dict(color="#f3f7ff", size=12),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(7,18,53,0.78)",
            bordercolor="rgba(123,207,255,0.22)",
            borderwidth=1,
        ),
    )
    fig.update_xaxes(gridcolor="rgba(123,207,255,0.12)", zerolinecolor="rgba(123,207,255,0.12)")
    fig.update_yaxes(gridcolor="rgba(123,207,255,0.12)", zerolinecolor="rgba(123,207,255,0.12)")
    if len(df):
        x_avg = float(df["footwork_score"].mean())
        y_avg = float(df["shotstop_score"].mean())
        fig.add_vline(x=x_avg, line_width=1.5, line_dash="dash", line_color="rgba(123,207,255,0.45)")
        fig.add_hline(y=y_avg, line_width=1.5, line_dash="dash", line_color="rgba(123,207,255,0.45)")
        fig.add_annotation(x=x_avg, y=float(df["shotstop_score"].max()), text=f"Media pies {fmt_number(x_avg,1)}", showarrow=False, yshift=14, font=dict(size=11, color="#dfe7ff"))
        fig.add_annotation(x=float(df["footwork_score"].max()), y=y_avg, text=f"Media paradas {fmt_number(y_avg,1)}", showarrow=False, xshift=-48, font=dict(size=11, color="#dfe7ff"))
    return fig


def build_table_view(df: pd.DataFrame) -> pd.DataFrame:
    view = df.copy()
    view["Pies"] = view["footwork_score"].apply(lambda v: fmt_number(v, 1))
    view["Paradas"] = view["shotstop_score"].apply(lambda v: fmt_number(v, 1))
    view["Minutos"] = view["minutes_on_field"].apply(fmt_number)
    view["Contexto"] = view.apply(lambda row: " · ".join([row["source_competition"], row["group_name"], *player_flags(row)]), axis=1)
    return view[["name", "team_name", "Pies", "Paradas", "Minutos", "Contexto"]].rename(columns={"name": "Jugador", "team_name": "Equipo"})


def build_ranking_cards_html(df: pd.DataFrame, limit: int = 12) -> str:
    rows = []
    for idx, (_, row) in enumerate(df.head(limit).iterrows(), start=1):
        rows.append(
            f"""
            <div style="display:grid;grid-template-columns:58px 1.35fr 1.2fr .55fr .6fr .7fr 1.2fr;gap:12px;align-items:center;padding:16px 18px;margin-top:10px;background:linear-gradient(180deg,rgba(17,34,96,.98) 0%, rgba(11,24,71,.98) 100%);border:1px solid rgba(132,184,255,.10);border-radius:18px;box-shadow:0 8px 24px rgba(4,10,30,.18);">
              <div style="color:#7bcfff;font-weight:900;font-size:18px;">#{idx}</div>
              <div><div style="color:#f3f7ff;font-weight:800;font-size:15px;">{esc(row['name'])}</div></div>
              <div style="color:#d8e4ff;font-weight:600;font-size:14px;">{esc(row['team_name'])}</div>
              <div style="color:#86ff78;font-weight:800;">{fmt_number(row.get('footwork_score'),1)}</div>
              <div style="color:#b7ff62;font-weight:800;">{fmt_number(row.get('shotstop_score'),1)}</div>
              <div style="color:#eef4ff;font-weight:700;">{fmt_number(row.get('minutes_on_field'))}</div>
              <div style="color:#eef4ff;font-size:13px;">{esc(str(row['source_competition']))} · {esc(str(row['group_name']))}</div>
            </div>
            """
        )
    return f"""
    <div style="display:flex;flex-direction:column;gap:0;height:100%;min-height:0;">
      <div style="display:grid;grid-template-columns:58px 1.35fr 1.2fr .55fr .6fr .7fr 1.2fr;gap:12px;align-items:center;padding:14px 18px;background:rgba(123,207,255,.08);border:1px solid rgba(132,184,255,.14);border-radius:18px;color:#7bcfff;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;position:sticky;top:0;z-index:2;">
        <div>#</div><div>Jugador</div><div>Equipo</div><div>Pies</div><div>Paradas</div><div>Minutos</div><div>Contexto</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:0;overflow-y:auto;max-height:680px;padding-right:4px;">
        {''.join(rows)}
      </div>
    </div>
    """


def render_player_detail(row: pd.Series, reference_df: pd.DataFrame) -> None:
    render_html(build_player_header_html(row), 270)

    top_cards_left, top_cards_right = st.columns(2)
    foot_labels = list(FOOTWORK_BLOCKS.keys())
    foot_values = [float(row.get(f"footwork__{label}", 0)) for label in foot_labels]
    stop_labels = list(SHOTSTOPPING_BLOCKS.keys())
    stop_values = [float(row.get(f"shotstop__{label}", 0)) for label in stop_labels]
    with top_cards_left:
        render_svg(build_spider_svg("Portero con los pies", "Salida, distribución y progresión", foot_labels, foot_values, float(row.get("footwork_score", 0)), "#7bcfff"), 400)
    with top_cards_right:
        render_svg(build_spider_svg("Portero de paradas", "Portería, dominio defensivo y respuesta", stop_labels, stop_values, float(row.get("shotstop_score", 0)), "#86ff78"), 400)

    cards = [
        ("Partidos", fmt_number(row.get("total_matches")), metric_percentile(reference_df, "total_matches", row.get("total_matches")), "Presencia competitiva"),
        ("Minutos", fmt_number(row.get("minutes_on_field")), metric_percentile(reference_df, "minutes_on_field", row.get("minutes_on_field")), "Volumen competitivo"),
        ("% minutos", fmt_percent(row.get("minutes_share")), metric_percentile(reference_df, "minutes_share", row.get("minutes_share")), "Peso en la temporada"),
        ("Paradas %", fmt_number(row.get("save_percent"), 1), metric_percentile(reference_df, "save_percent", row.get("save_percent")), "Respuesta bajo remate"),
        ("Goles evitados/90", fmt_number(row.get("prevented_goals_avg"), 2), metric_percentile(reference_df, "prevented_goals_avg", row.get("prevented_goals_avg")), "Diferencial de portería"),
        ("Salidas/90", fmt_number(row.get("goalkeeper_exits_avg"), 2), metric_percentile(reference_df, "goalkeeper_exits_avg", row.get("goalkeeper_exits_avg")), "Dominio de área"),
        ("Pases/90", fmt_number(row.get("passes_avg"), 1), metric_percentile(reference_df, "passes_avg", row.get("passes_avg")), "Participación con balón"),
        ("Precisión pase %", fmt_number(row.get("accurate_passes_percent"), 1), metric_percentile(reference_df, "accurate_passes_percent", row.get("accurate_passes_percent")), "Limpieza global"),
    ]
    st.markdown("#### Indicadores clave")
    render_html(build_metric_bars_html(cards, columns=2), 640)

    strengths, risks = find_strengths_risks(row, reference_df)
    sr_left, sr_right = st.columns(2)
    with sr_left:
        items = "".join(
            f'<div style="padding:14px 0;border-top:1px solid rgba(125,201,255,.10);"><div style="display:flex;justify-content:space-between;align-items:center;"><div style="color:#f3f7ff;font-size:22px;font-weight:800;">{item["label"]}</div><div style="color:#86ff78;font-size:28px;font-weight:900;">P{int(round(item["pct"]))}</div></div><div style="color:#eef4ff;margin-top:4px;">{fmt_number(item["value"],2) if isinstance(item["value"], float) else fmt_number(item["value"],1)}</div></div>'
            for item in strengths
        )
        st.markdown(f'<div class="um-dark-card" style="padding:18px 20px;"><div class="um-label" style="margin-bottom:10px;">Fortalezas</div>{items}</div>', unsafe_allow_html=True)
    with sr_right:
        items = "".join(
            f'<div style="padding:14px 0;border-top:1px solid rgba(125,201,255,.10);"><div style="display:flex;justify-content:space-between;align-items:center;"><div style="color:#f3f7ff;font-size:22px;font-weight:800;">{item["label"]}</div><div style="color:#ffb454;font-size:28px;font-weight:900;">P{int(round(item["pct"]))}</div></div><div style="color:#eef4ff;margin-top:4px;">{fmt_number(item["value"],2) if isinstance(item["value"], float) else fmt_number(item["value"],1)}</div></div>'
            for item in risks
        )
        st.markdown(f'<div class="um-dark-card" style="padding:18px 20px;"><div class="um-label" style="margin-bottom:10px;">Puntos a vigilar</div>{items}</div>', unsafe_allow_html=True)

    distribution_col, attacking_col = st.columns([3, 1])
    with distribution_col:
        render_svg(build_distribution_svg(row, reference_df), 520)
    with attacking_col:
        render_html(build_attacking_contribution_html(row, reference_df), 660)

    with st.expander("Cómo leer las vías de distribución y la contribución ofensiva"):
        st.markdown(
            """
            Las líneas oscuras del campograma representan el máximo del grupo visible y las flechas brillantes muestran hasta dónde llega el portero seleccionado. Los pases laterales son una estimación calculada como `pases totales - pases hacia delante - pases hacia atrás`. La contribución ofensiva se presenta aparte porque son acciones poco frecuentes y no forma parte del scoring principal.
            """
        )

    st.markdown("#### Qué incluye cada bloque")
    render_html(build_block_explanations_html(), 560)


df, metadata = load_goalkeeper_dataframe()
df = enrich_all_scores(df)

header_logo, header_title = st.columns([0.075, 0.925], vertical_alignment="center")
with header_logo:
    st.image(str(asset_path("escudo", "Escudo_Of.png")), width=82)
with header_title:
    st.markdown(
        """
        <div style="padding:8px 0 12px;">
          <div style="font-size:56px;line-height:1.08;font-weight:900;letter-spacing:-0.04em;color:#ffffff;">UnioMercato</div>
          <div style="margin-top:10px;font-size:24px;font-weight:800;color:#8fd8ff;">Scouting de porteros · mercado comparado</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.image(str(asset_path("mcode", "MCODE Sport Analytics.png")), width=220)
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    st.header("Filtros")
    ranking_mode = st.selectbox("Orden del ranking", ["Juego de pies", "Paradas", "Equilibrado", "Libre"])
    free_metric_weights = {}
    if ranking_mode == "Libre":
        st.caption("Construye un criterio libre con métricas propias.")
        selected_metrics = st.multiselect("Métricas del criterio libre", list(FREE_METRICS.keys()), default=["save_percent", "prevented_goals_avg", "passes_avg"], format_func=lambda x: FREE_METRICS[x])
        for metric in selected_metrics:
            free_metric_weights[metric] = st.slider(FREE_METRICS[metric], -3.0, 3.0, 1.0, 0.5)
        df = enrich_all_scores(df, free_metric_weights)
    available_competitions = metadata.get("competition_order", ["1RFEF", "2RFEF"])
    default_competitions = [comp for comp in ["1RFEF"] if comp in available_competitions] or available_competitions[:1]
    selected_competitions = st.multiselect(
        "Competiciones",
        available_competitions,
        default=default_competitions,
        format_func=lambda x: COMPETITION_LABELS.get(x, x),
    )
    search_text = st.text_input("Buscar jugador o equipo")
    min_matches = st.number_input("Partidos mínimos", min_value=0, step=1, value=0)
    min_minutes_pct = st.slider("% mínimo de minutos", 0, 100, 0, 5)
    st.divider()
    target_competition_only = st.checkbox("Solo competición objetivo", value=False)
    include_youth = st.checkbox("Incluir cantera / juveniles", value=True)
    include_loans = st.checkbox("Incluir cedidos", value=True)
    include_unknown_group = st.checkbox("Incluir 'Sin grupo'", value=True)

    st.divider()
    st.markdown('<div class="um-label" style="margin-bottom:6px;">Exportar informe PDF</div>', unsafe_allow_html=True)
    top_n_pdf = st.selectbox("Jugadores en el informe", [5, 10, 15], index=1, key="top_n_pdf")
    generate_pdf = st.button("Generar informe PDF", type="primary", use_container_width=True)

filtered_df = filter_dataframe(df, selected_competitions, search_text, int(min_matches), min_minutes_pct / 100, target_competition_only, include_youth, include_loans, include_unknown_group)

if ranking_mode == "Juego de pies":
    sorted_df = filtered_df.sort_values(by=["footwork_score", "name"], ascending=[False, True], na_position="last").reset_index(drop=True)
elif ranking_mode == "Paradas":
    sorted_df = filtered_df.sort_values(by=["shotstop_score", "name"], ascending=[False, True], na_position="last").reset_index(drop=True)
elif ranking_mode == "Equilibrado":
    tmp = filtered_df.copy()
    tmp["balanced_score"] = ((tmp["footwork_score"] + tmp["shotstop_score"]) / 2).round(2)
    sorted_df = tmp.sort_values(by=["balanced_score", "name"], ascending=[False, True], na_position="last").reset_index(drop=True)
else:
    sorted_df = filtered_df.sort_values(by=["custom_score", "name"], ascending=[False, True], na_position="last").reset_index(drop=True)

if generate_pdf:
    if sorted_df.empty:
        st.sidebar.warning("No hay porteros con los filtros actuales.")
    else:
        with st.sidebar:
            with st.spinner("Generando PDF…"):
                _filters_text = build_filters_summary(
                    ", ".join(selected_competitions) if selected_competitions else "ALL", "Sin filtro de grupo", int(min_matches), min_minutes_pct,
                    target_competition_only, include_youth, include_loans,
                )
                _pdf_bytes = generate_report(sorted_df, top_n_pdf, _filters_text, ranking_mode)
            st.download_button(
                label="⬇ Descargar PDF",
                data=_pdf_bytes,
                file_name="UnioMercato_Porteros.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

c1, c2, c3, c4 = st.columns(4)
c1.metric("Porteros visibles", fmt_number(len(filtered_df)))
c2.metric("Juego de pies medio", fmt_number(filtered_df["footwork_score"].mean() if len(filtered_df) else 0, 1))
c3.metric("Paradas media", fmt_number(filtered_df["shotstop_score"].mean() if len(filtered_df) else 0, 1))
c4.metric("% medio de minutos", fmt_percent(filtered_df["minutes_share"].mean() if len(filtered_df) else 0))

left, right = st.columns([1.7, 1.1])
with left:
    st.markdown("#### Mapa macro: juego de pies vs paradas")
    fig = build_plot(filtered_df)
    st.caption("Eje X: comportamiento del portero con balón. Eje Y: comportamiento del portero ante remates y acciones defensivas. Las líneas discontinuas marcan la media del grupo visible.")
    with st.expander("Qué incluye cada eje", expanded=False):
        render_html(build_axis_explanations_html(), 300)
    if fig is None:
        st.info("No hay porteros con los filtros actuales.")
    else:
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right:
    st.markdown("#### Ranking visible")
    st.caption(f"Criterio activo: {ranking_mode}")
    render_html(build_ranking_cards_html(sorted_df, limit=len(sorted_df)), 760, scrolling=True)
    st.download_button("Descargar selección CSV", sorted_df.to_csv(index=False).encode("utf-8"), "porteros_filtrados_unionistas.csv", "text/csv", width="stretch")

st.divider()
options = sorted_df.apply(lambda r: f"{r['name']} | {r['team_name']} | {r['source_competition']} | {r['group_name']}", axis=1).tolist()
if options:
    st.markdown(
        """
        <style>
          /* Compact selectbox label for player selector */
          div[data-testid="stSelectbox"] > label {
            color: #f3f7ff !important;
            font-size: 13px !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 4px !important;
          }
          /* Reduce gap between player selector and the player card iframe */
          div[data-testid="stSelectbox"] + div > iframe,
          div[data-testid="stSelectbox"] ~ div iframe {
            margin-top: -8px !important;
          }
          /* Tighten vertical gaps between iframes in the player detail section */
          iframe + div, div + iframe {
            margin-top: 0 !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    selected_label = st.selectbox("Portero — ficha rápida", options, label_visibility="visible")
    selected_row = sorted_df.iloc[options.index(selected_label)]
    render_player_detail(selected_row, filtered_df)
else:
    st.info("No hay ningún portero disponible para mostrar ficha con los filtros actuales.")

st.markdown("#### Notas")
render_html(build_notes_html(metadata.get("notes", [])), 180)

st.markdown(
    """
    <div style="margin-top:28px;padding:18px 20px;border-top:1px solid rgba(123,207,255,.14);display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
      <div style="color:#eef4ff;font-size:14px;font-weight:700;">Diseñado por Ramón Codesido</div>
      <div style="color:#eef4ff;font-size:14px;font-weight:700;">© MCode App</div>
    </div>
    """,
    unsafe_allow_html=True,
)
