import csv
import json
import math
import re
import unicodedata
from pathlib import Path

from project_paths import data_dir


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = data_dir()
CONFIG_DIR = ROOT / "config"
DASHBOARD_DIR = ROOT / "dashboard"
DATA_JS_PATH = DASHBOARD_DIR / "gk_market_data.js"


def load_n2_groups() -> dict[str, set[str]]:
    path = CONFIG_DIR / "n2_groups.csv"
    groups = {"Grupo A": set(), "Grupo B": set(), "Grupo C": set()}
    if not path.exists():
        return groups
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            team = (row.get("team") or "").strip()
            group = f"Grupo {(row.get('grupo') or '').strip()}"
            if team and group in groups:
                groups[group].add(team)
    return groups


COMPETITIONS = {
    "1RFEF": {
        "file": DATA_DIR / "1RFEF_2025-26.csv",
        "target_competition_name": "Primera Division RFEF",
        "expected_matches": 38,
        "groups": {
            "Grupo I": {
                "Arenas Club",
                "Arenteiro",
                "Athletic Bilbao",
                "Barakaldo",
                "Cacereño",
                "Celta Fortuna",
                "Guadalajara",
                "Lugo",
                "Mérida AD",
                "Osasuna Promesas",
                "Ourense CF",
                "Ponferradina",
                "Pontevedra",
                "Racing Ferrol",
                "Real Avilés",
                "Real Madrid Castilla",
                "Talavera CF",
                "Tenerife",
                "Unionistas de Salamanca",
                "Zamora",
            },
            "Grupo II": {
                "Alcorcón",
                "Algeciras",
                "Antequera",
                "Atlético Madrid B",
                "Atlético Sanluqueño",
                "Betis Deportivo",
                "Cartagena",
                "Eldense",
                "Europa",
                "Gimnàstic Tarragona",
                "Hércules",
                "Ibiza",
                "Juventud Torremolinos",
                "Marbella",
                "Real Murcia",
                "Sabadell",
                "Sevilla Atlético",
                "Tarazona",
                "Teruel",
                "Villarreal B",
            },
        },
    },
    "2RFEF": {
        "file": DATA_DIR / "2RFEF_2025-26.csv",
        "target_competition_name": "Segunda Division RFEF",
        "expected_matches": 34,
        "groups": {
            "Grupo I": {
                "Atlético Astorga",
                "Bergantiños",
                "Burgos Promesas",
                "Coruxo",
                "Deportivo Fabril",
                "Gimnástica Segoviana",
                "Langreo",
                "Lealtad",
                "Marino de Luanco",
                "Numancia",
                "Racing Santander II",
                "Real Oviedo Vetusta",
                "Real Valladolid Promesas",
                "Real Ávila",
                "Salamanca CF UDS",
                "Sarriana",
                "Sámano",
                "UD Ourense",
            },
            "Grupo II": {
                "Alfaro",
                "Amorebieta",
                "Basconia",
                "Beasain",
                "Deportivo Alavés B",
                "Ebro",
                "Eibar B",
                "Ejea",
                "Gernika",
                "Mutilvera",
                "Náxara",
                "RSD Alcalá",
                "Real Unión",
                "SD Logroñés",
                "Sestao River",
                "Tudelano",
                "UD Logroñés",
                "Utebo",
            },
            "Grupo III": {
                "Alcoyano",
                "Andratx",
                "Atlético Baleares",
                "Barbastro",
                "Barcelona Atlètic",
                "CE Atletic Lleida 2019",
                "Castellón B",
                "Espanyol B",
                "Girona B",
                "Ibiza Islas Pitiusas",
                "Olot",
                "Poblense",
                "Porreres",
                "Reus FCR",
                "Sant Andreu",
                "Terrassa",
                "Torrent",
                "Valencia Mestalla",
            },
            "Grupo IV": {
                "Almería B",
                "Antoniano",
                "Atlético Malagueño",
                "Deportiva Minera",
                "Estepona",
                "Extremadura 1924",
                "Linares Deportivo",
                "Lorca Deportiva",
                "Melilla",
                "Puente Genil",
                "Real Jaén",
                "Recreativo Huelva",
                "UCAM Murcia",
                "Unión Malacitano",
                "Xerez",
                "Xerez Deportivo",
                "Yeclano",
                "Águilas",
            },
            "Grupo V": {
                "CD Coria",
                "Colonia Moscardó",
                "Conquense",
                "Elche Illicitano",
                "Fuenlabrada",
                "Getafe B",
                "Intercity SJ D' Alacant",
                "Las Palmas Atlético",
                "Navalcarnero",
                "Orihuela",
                "Quintanar del Rey",
                "Rayo Majadahonda",
                "Rayo Vallecano B",
                "Real Madrid C",
                "Socuéllamos",
                "Tenerife B",
                "UD Sanse",
            },
        },
    },
    "LaLiga2": {
        "file": DATA_DIR / "LaLiga2_2025-26.csv",
        "target_competition_name": "LaLiga 2",
        "expected_matches": 42,
        "groups": {},
    },
    "National1": {
        "file": DATA_DIR / "National1_2025-26.csv",
        "target_competition_name": "National 1",
        "expected_matches": 34,
        "groups": {},
    },
    "National2": {
        "file": DATA_DIR / "National2_2025-26.csv",
        "target_competition_name": "National 2",
        "expected_matches": 30,
        "groups": load_n2_groups(),
    },
    "Portugal2": {
        "file": DATA_DIR / "Portugal2_2025-26.csv",
        "target_competition_name": "Segunda Liga",
        "expected_matches": 34,
        "groups": {},
    },
    "Portugal3": {
        "file": DATA_DIR / "Portugal3_2025-26.csv",
        "target_competition_name": "Liga 3",
        "expected_matches": 32,
        "groups": {},
    },
    "Portugal4": {
        "file": DATA_DIR / "Portugal4_2025-26.csv",
        "target_competition_name": "Campeonato de Portugal",
        "expected_matches": 26,
        "groups": {},
    },
}


ALIAS_MAP = {
    "athletic club": "athletic bilbao",
    "athletic b": "athletic bilbao",
    "athletic club b": "athletic bilbao",
    "athletic club b u21": "athletic bilbao",
    "bilbao athletic": "athletic bilbao",
    "real aviles industrial": "real aviles",
    "cf talavera de la reina": "talavera cf",
    "merida": "merida ad",
    "ad merida": "merida ad",
    "racing ferrol": "racing ferrol",
    "racing de ferrol": "racing ferrol",
    "fc cartagena": "cartagena",
    "ce europa": "europa",
    "europa": "europa",
    "gimnastic de tarragona": "gimnastic tarragona",
    "gimnastic tarragona": "gimnastic tarragona",
    "nastic": "gimnastic tarragona",
    "nastic de tarragona": "gimnastic tarragona",
    "juventud de torremolinos cf": "juventud torremolinos",
    "juventud torremolinos cf": "juventud torremolinos",
    "torremolinos": "juventud torremolinos",
    "unionistas": "unionistas de salamanca",
    "atletico b": "atletico madrid b",
    "atletico madrileno": "atletico madrid b",
    "atletico madrileño": "atletico madrid b",
    "at sanluqueno": "atletico sanluqueno",
    "atletico sanluqueno": "atletico sanluqueno",
    "atletico sanluqueño": "atletico sanluqueno",
    "celta b": "celta fortuna",
    "celta vigo b": "celta fortuna",
    "villarreal cf b": "villarreal b",
    "villarreal cf b u23": "villarreal b",
    "cp cacereno": "cacereno",
    "cacereno": "cacereno",
    "cp cacereno": "cacereno",
    "deportivo alaves b": "deportivo alaves b",
    "alaves b": "deportivo alaves b",
    "sd beasain": "beasain",
    "real union de irun": "real union",
    "cd andrach": "andratx",
    "ce andratx": "andratx",
    "atletic lleida": "ce atletic lleida 2019",
    "ce atletic lleida": "ce atletic lleida 2019",
    "lleida": "ce atletic lleida 2019",
    "barca atletic": "barcelona atletic",
    "barca athletic": "barcelona atletic",
    "barça atlètic": "barcelona atletic",
    "barcelona athletic": "barcelona atletic",
    "espanyol b": "espanyol b",
    "girona fc b": "girona b",
    "girona b": "girona b",
    "reus fc reddis": "reus fcr",
    "reus": "reus fcr",
    "resu fc reddis": "reus fcr",
    "salerm puente genil": "puente genil",
    "puente genil": "puente genil",
    "fc union atletico": "union malacitano",
    "fc la union atletico": "union malacitano",
    "la union": "union malacitano",
    "la union atletico": "union malacitano",
    "xerez cd": "xerez",
    "xerez deportivo fc": "xerez deportivo",
    "aguilas fc": "aguilas",
    "aguilas": "aguilas",
    "ud san sebastian de los reyes": "ud sanse",
    "ud sanse": "ud sanse",
    "san sebastian de los reyes": "ud sanse",
    "s s reyes": "ud sanse",
    "rayo vallecano b": "rayo vallecano b",
    "r majadahonda": "rayo majadahonda",
    "majadahonda": "rayo majadahonda",
    "cf intercity": "intercity sj d alacant",
    "cf intercity sj d alacant": "intercity sj d alacant",
    "intercity": "intercity sj d alacant",
    "coria": "cd coria",
    "racing santander b": "racing santander ii",
    "rayo cantabria": "racing santander ii",
    "racing b": "racing santander ii",
    "las palmas atletico b": "las palmas atletico",
    "up langreo": "langreo",
    "langreo": "langreo",
    "ue sant andreu": "sant andreu",
    "andratx": "andratx",
    "deportivo aragon": "real zaragoza b",
    "rz deportivo aragon": "real zaragoza b",
    "zaragoza b": "real zaragoza b",
    "real valladolid b": "real valladolid promesas",
    "valladolid b": "real valladolid promesas",
    "valladolid promesas": "real valladolid promesas",
    "union deportiva barbastro": "barbastro",
    "ud yugo socuellamos": "socuellamos",
    "socuellamos": "socuellamos",
    "extremadura": "extremadura 1924",
    "cd extremadura": "extremadura 1924",
    "cd extremadura 1924": "extremadura 1924",
    "recreativo": "recreativo huelva",
    "recre": "recreativo huelva",
    "recreativo de huelva": "recreativo huelva",
    "recreativo de hugelva": "recreativo huelva",
    "ucam": "ucam murcia",
    "ucam murcia": "ucam murcia",
    "union deportiva ourense": "ud ourense",
}


def slugify(value: str) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    value = value.replace('"', "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return ALIAS_MAP.get(value, value)


def as_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def as_int(value):
    number = as_float(value)
    if number is None:
        return None
    return int(round(number))


def derive_lateral_passes(row):
    """Estimate lateral passes from the exhaustive directional pass categories."""
    passes = as_float(row.get("passes_avg"))
    forward = as_float(row.get("forward_passes_avg"))
    backward = as_float(row.get("back_passes_avg"))
    if passes is None or forward is None or backward is None:
        return None, None

    lateral = max(passes - forward - backward, 0.0)
    if lateral <= 0:
        return lateral, None

    total_accuracy = as_float(row.get("accurate_passes_percent"))
    forward_accuracy = as_float(row.get("successful_forward_passes_percent"))
    backward_accuracy = as_float(row.get("successful_back_passes_percent"))
    if total_accuracy is None or forward_accuracy is None or backward_accuracy is None:
        return lateral, None

    accurate_lateral = (
        passes * total_accuracy / 100
        - forward * forward_accuracy / 100
        - backward * backward_accuracy / 100
    )
    accurate_lateral = min(max(accurate_lateral, 0.0), lateral)
    return lateral, accurate_lateral / lateral * 100


def is_youth_team(team_name: str, competition_name: str) -> bool:
    team_name = team_name or ""
    competition_name = competition_name or ""
    youth_tokens = ("U17", "U18", "U19", "U20", "U21", "Juvenil")
    return any(token in team_name for token in youth_tokens) or any(
        token.lower() in competition_name.lower() for token in youth_tokens
    )


def build_group_index():
    group_index = {}
    for comp_key, comp_config in COMPETITIONS.items():
        group_index[comp_key] = {}
        for group_name, team_names in comp_config["groups"].items():
            for team_name in team_names:
                group_index[comp_key][slugify(team_name)] = group_name
    return group_index


GROUP_INDEX = build_group_index()


def detect_group(source_competition: str, team_name: str):
    return GROUP_INDEX[source_competition].get(slugify(team_name), "Sin grupo")


def minutes_share(minutes_on_field, expected_matches):
    if minutes_on_field is None:
        return None
    denominator = expected_matches * 90
    if denominator <= 0:
        return None
    return min(minutes_on_field / denominator, 1.0)


def matches_share(total_matches, expected_matches):
    if total_matches is None or expected_matches <= 0:
        return None
    return min(total_matches / expected_matches, 1.0)


def dedupe_key(source_competition, row):
    return (
        source_competition,
        row.get("id") or "",
        slugify(row.get("full_name") or row.get("name") or ""),
        slugify(row.get("current_team_name") or ""),
        slugify(row.get("primary_position") or ""),
    )


REQUIRED_COLUMNS = {
    "primary_position", "id", "name", "full_name", "current_team_name",
    "minutes_on_field", "total_matches", "domestic_competition_name",
}


def load_goalkeepers():
    deduped = {}

    for source_competition, config in COMPETITIONS.items():
        path = config["file"]
        if not path.exists():
            raise FileNotFoundError(
                f"Archivo de datos no encontrado: {path}\n"
                "Comprueba que los CSV de Wyscout están en la carpeta data/."
            )
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"No se pudo leer {path.name}: {exc}") from exc

        if not rows:
            continue
        missing = REQUIRED_COLUMNS - set(rows[0].keys())
        if missing:
            raise ValueError(
                f"{path.name} le faltan columnas requeridas: {', '.join(sorted(missing))}"
            )

        for row in rows:
            if (row.get("primary_position") or "").strip() != "GK":
                continue

            key = dedupe_key(source_competition, row)
            current_minutes = as_float(row.get("minutes_on_field")) or -1
            previous = deduped.get(key)
            previous_minutes = as_float(previous.get("minutes_on_field")) if previous else -1

            if previous is None or current_minutes > (previous_minutes or -1):
                deduped[key] = row | {"_source_competition": source_competition}

    enriched = []
    for row in deduped.values():
        source_competition = row["_source_competition"]
        config = COMPETITIONS[source_competition]
        team_name = (row.get("current_team_name") or "").strip()
        competition_name = (row.get("domestic_competition_name") or "").strip()
        expected_matches = config["expected_matches"]

        minutes_on_field = as_float(row.get("minutes_on_field"))
        total_matches = as_float(row.get("total_matches"))
        market_value = as_float(row.get("market_value"))

        group_name = detect_group(source_competition, team_name)
        competition_matches_source = competition_name == config["target_competition_name"]
        youth_flag = is_youth_team(team_name, competition_name)
        on_loan = str(row.get("on_loan")).strip().lower() == "true"
        lateral_pass_avg, accurate_lateral_pass_percent = derive_lateral_passes(row)

        enriched.append(
            {
                "player_id": row.get("id"),
                "name": row.get("name"),
                "full_name": row.get("full_name"),
                "image_url": row.get("image"),
                "team_logo_url": row.get("current_team_logo"),
                "source_competition": source_competition,
                "target_competition_name": config["target_competition_name"],
                "domestic_competition_name": competition_name,
                "group_name": group_name,
                "group_known": group_name != "Sin grupo",
                "competition_matches_source": competition_matches_source,
                "team_name": team_name,
                "age": as_float(row.get("age")),
                "birth_date": row.get("birth_date"),
                "birth_country_name": row.get("birth_country_name"),
                "passport_country_names": row.get("passport_country_names"),
                "minutes_on_field": minutes_on_field,
                "total_matches": total_matches,
                "minutes_share": minutes_share(minutes_on_field, expected_matches),
                "matches_share": matches_share(total_matches, expected_matches),
                "expected_matches": expected_matches,
                "market_value": market_value,
                "on_loan": on_loan,
                "is_youth_team": youth_flag,
                "foot": row.get("foot"),
                "height": as_int(row.get("height")),
                "weight": as_int(row.get("weight")),
                "contract_expires": row.get("contract_expires"),
                "save_percent": as_float(row.get("save_percent")),
                "xg_save_avg": as_float(row.get("xg_save_avg")),
                "prevented_goals_avg": as_float(row.get("prevented_goals_avg")),
                "conceded_goals_avg": as_float(row.get("conceded_goals_avg")),
                "shots_against_avg": as_float(row.get("shots_against_avg")),
                "clean_sheets": as_float(row.get("clean_sheets")),
                "goalkeeper_exits_avg": as_float(row.get("goalkeeper_exits_avg")),
                "gk_aerial_duels_avg": as_float(row.get("gk_aerial_duels_avg")),
                "assists": as_float(row.get("assists")),
                "assists_avg": as_float(row.get("assists_avg")),
                "xg_assist": as_float(row.get("xg_assist")),
                "xg_assist_avg": as_float(row.get("xg_assist_avg")),
                "pre_assist_avg": as_float(row.get("pre_assist_avg")),
                "pre_pre_assist_avg": as_float(row.get("pre_pre_assist_avg")),
                "shot_assists_avg": as_float(row.get("shot_assists_avg")),
                "key_passes_avg": as_float(row.get("key_passes_avg")),
                "passes_avg": as_float(row.get("passes_avg")),
                "received_pass_avg": as_float(row.get("received_pass_avg")),
                "received_long_pass_avg": as_float(row.get("received_long_pass_avg")),
                "accurate_passes_percent": as_float(row.get("accurate_passes_percent")),
                "forward_passes_avg": as_float(row.get("forward_passes_avg")),
                "successful_forward_passes_percent": as_float(
                    row.get("successful_forward_passes_percent")
                ),
                "vertical_passes_avg": as_float(row.get("vertical_passes_avg")),
                "successful_vertical_passes_percent": as_float(
                    row.get("successful_vertical_passes_percent")
                ),
                "progressive_pass_avg": as_float(row.get("progressive_pass_avg")),
                "successful_progressive_pass_percent": as_float(
                    row.get("successful_progressive_pass_percent")
                ),
                "back_passes_avg": as_float(row.get("back_passes_avg")),
                "successful_back_passes_percent": as_float(
                    row.get("successful_back_passes_percent")
                ),
                "lateral_pass_avg": lateral_pass_avg,
                "accurate_lateral_pass_percent": accurate_lateral_pass_percent,
                "long_passes_avg": as_float(row.get("long_passes_avg")),
                "successful_long_passes_percent": as_float(
                    row.get("successful_long_passes_percent")
                ),
                "short_medium_pass_avg": as_float(row.get("short_medium_pass_avg")),
                "accurate_short_medium_pass_percent": as_float(
                    row.get("accurate_short_medium_pass_percent")
                ),
                "average_pass_length": as_float(row.get("average_pass_length")),
                "average_long_pass_length": as_float(row.get("average_long_pass_length")),
            }
        )

    enriched.sort(
        key=lambda item: (
            item["source_competition"],
            -(item["minutes_on_field"] or 0),
            item["team_name"] or "",
            item["name"] or "",
        )
    )
    return enriched


def build_metadata(goalkeepers):
    summary = {}
    for source_competition in COMPETITIONS:
        subset = [gk for gk in goalkeepers if gk["source_competition"] == source_competition]
        summary[source_competition] = {
            "goalkeepers": len(subset),
            "target_competition_rows": sum(1 for gk in subset if gk["competition_matches_source"]),
            "with_group": sum(1 for gk in subset if gk["group_known"]),
            "youth_rows": sum(1 for gk in subset if gk["is_youth_team"]),
            "loan_rows": sum(1 for gk in subset if gk["on_loan"]),
        }
    return {
        "competition_order": ["1RFEF", "2RFEF", "LaLiga2", "National1", "National2", "Portugal2", "Portugal3", "Portugal4"],
        "group_order": {
            "1RFEF": ["Grupo I", "Grupo II", "Sin grupo"],
            "2RFEF": ["Grupo I", "Grupo II", "Grupo III", "Grupo IV", "Grupo V", "Sin grupo"],
            "LaLiga2": ["Sin grupo"],
            "National1": ["Sin grupo"],
            "National2": ["Grupo A", "Grupo B", "Grupo C", "Sin grupo"],
            "Portugal2": ["Sin grupo"],
            "Portugal3": ["Sin grupo"],
            "Portugal4": ["Sin grupo"],
        },
        "summary": summary,
        "notes": [
            "Los porteros se incluyen aunque el registro pertenezca a cantera, cesión o equipo fuera de la competición objetivo.",
            "El grupo se ha enriquecido mediante una tabla manual de equipos para la temporada 2025-26.",
            "El porcentaje de minutos usa 90 minutos por partido como base teórica y se limita a 100%.",
        ],
    }


def main():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    goalkeepers = load_goalkeepers()
    payload = {
        "metadata": build_metadata(goalkeepers),
        "goalkeepers": goalkeepers,
    }

    DATA_JS_PATH.write_text(
        "window.GK_MARKET_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    print(f"Porteros exportados: {len(goalkeepers)}")
    print(f"Fichero generado: {DATA_JS_PATH.relative_to(ROOT)}")
    for comp_name, info in payload["metadata"]["summary"].items():
        print(
            f"{comp_name}: total={info['goalkeepers']} | "
            f"competicion_objetivo={info['target_competition_rows']} | "
            f"con_grupo={info['with_group']}"
        )


if __name__ == "__main__":
    main()
