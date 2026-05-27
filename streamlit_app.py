"""Streamlit app for the Bio-Behavioral Team Dynamics Analytics Chatbot.

Run from the repository root:
    streamlit run streamlit_app.py

Revision focus:
    - Align the prototype with the dissertation RQ2 proposal.
    - Match the provided UI concept: run selection at left, event-aligned metric
      visualization in the center, and a plain-language AI interpretation chat
      panel at right.
    - Include a standard statistical-report condition so the same synthetic
      information can be compared with the customized AI-bot condition.

The app uses synthetic demonstration data only. It does not use BioTDMS data,
score real trainees, or test dissertation hypotheses.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from team_dynamics_metrics import (  # noqa: E402
    DEFAULT_USER_QUESTION,
    ROLES,
    build_explanation_packet,
    build_gemini_prompt,
    build_output_paths,
    call_gemini,
    extract_symbolic_state_table,
    generate_synthetic_biobehavioral_timeseries,
    load_identity_text,
    moving_window_entropy,
    moving_window_inverse_sample_entropy,
    moving_window_role_ami,
    plot_entropy,
    plot_inverse_sampen,
    plot_role_ami_summary,
    plot_role_influence_heatmap,
    plot_team_state,
    summarize_role_ami,
    validate_outputs,
    write_api_status,
)

OUTPUT_DIR = ROOT / "outputs"
IDENTITY_CANDIDATES = [
    ROOT / "docs" / "team_dynamics_chatbot_identity.md",
    ROOT / "team_dynamics_chatbot_identity.md",
]

DEFAULT_SETTINGS: Dict[str, int | str] = {
    "entropy_window": 120,
    "sampen_window": 180,
    "ami_window": 180,
    "step": 15,
    "model": "gemini-2.5-flash",
}

# Synthetic de-identified run catalog for the RQ2 prototype. The hidden
# synthetic_mr_overall values support the demo ranking task; they are not shown
# in the customized bot or standard report condition unless demo scoring is used.
RUN_CATALOG: List[Dict[str, Any]] = [
    {
        "run_key": "run_a",
        "display_id": "Run A",
        "scenario": "Scenario 1",
        "scenario_title": "Defensive position and surprise task transition",
        "seed": 42,
        "n_seconds": 900,
        "event_time_sec": 450,
        "event_label": "Synthetic task change",
        "phase_note": "Orientation -> fire planning -> execution -> assessment",
        "context_note": "A de-identified demonstration run with a mid-scenario event marker.",
        "synthetic_mr_overall": 2,
    },
    {
        "run_key": "run_b",
        "display_id": "Run B",
        "scenario": "Scenario 1",
        "scenario_title": "Fire-planning update and coordination demand",
        "seed": 7,
        "n_seconds": 960,
        "event_time_sec": 510,
        "event_label": "Synthetic fire-plan update",
        "phase_note": "Orientation -> fire planning -> execution -> assessment",
        "context_note": "A de-identified demonstration run emphasizing coordination around a planning change.",
        "synthetic_mr_overall": 3,
    },
    {
        "run_key": "run_c",
        "display_id": "Run C",
        "scenario": "Scenario 3",
        "scenario_title": "Hidden reinforcement and communication-heavy phase",
        "seed": 19,
        "n_seconds": 1080,
        "event_time_sec": 600,
        "event_label": "Synthetic reinforcement event",
        "phase_note": "Orientation -> fire planning -> execution -> assessment",
        "context_note": "A de-identified demonstration run with an event-aligned adaptation signal.",
        "synthetic_mr_overall": 4,
    },
    {
        "run_key": "run_d",
        "display_id": "Run D",
        "scenario": "Scenario 4",
        "scenario_title": "Late-stage reassessment and role redistribution",
        "seed": 99,
        "n_seconds": 840,
        "event_time_sec": 390,
        "event_label": "Synthetic reassessment event",
        "phase_note": "Orientation -> fire planning -> execution -> assessment",
        "context_note": "A de-identified demonstration run with a shorter scenario timeline.",
        "synthetic_mr_overall": 1,
    },
]

FIGURE_SPECS = {
    "team_state": {
        "title": "Symbolic team-state trajectory",
        "path_attr": "team_state_figure",
        "caption": "Synthetic symbolic team-state trajectory used by the metric pipeline.",
    },
    "entropy": {
        "title": "Adaptation: moving-window Shannon entropy",
        "path_attr": "entropy_figure",
        "caption": "Higher values indicate more variability or reorganization in the symbolic team-state sequence for that window.",
    },
    "inverse_sampen": {
        "title": "Dynamic interdependency: inverse sample entropy",
        "path_attr": "inverse_sampen_figure",
        "caption": "Higher values indicate more temporal regularity in the symbolic sequence for this synthetic example.",
    },
    "ami_summary": {
        "title": "Influence distribution: role-level AMI summary",
        "path_attr": "role_ami_figure",
        "caption": "Role-level descriptive coupling with the team-state sequence; not an individual evaluation.",
    },
    "ami_heatmap": {
        "title": "Influence distribution: moving-window AMI heatmap",
        "path_attr": "role_influence_heatmap",
        "caption": "Relative AMI share by role across time windows.",
    },
}

TABLE_SPECS = {
    "entropy": {"title": "Moving-window Shannon entropy table", "key": "entropy_df"},
    "inverse_sampen": {"title": "Moving-window inverse sample entropy table", "key": "inverse_df"},
    "ami_summary": {"title": "Role-level AMI summary table", "key": "ami_summary_df"},
    "ami_long": {"title": "Moving-window role AMI table", "key": "ami_long_df"},
    "synthetic_data": {"title": "Synthetic 1 Hz time-series preview", "key": "timeseries_df"},
    "states": {"title": "Symbolic state table", "key": "states_df"},
}

METRIC_GLOSSARY: Dict[str, Dict[str, str]] = {
    "adaptation": {
        "display": "Adaptation",
        "metric": "Moving-window Shannon entropy",
        "plain": "How much the symbolic team-state pattern varies within a time window.",
        "high": "A higher value may indicate reorganization or a wider variety of coordination states.",
        "low": "A lower value may indicate a more stable or repetitive coordination state.",
        "caution": "More adaptation is not automatically better; it needs scenario and performance context.",
    },
    "interdependence": {
        "display": "Dynamic interdependency",
        "metric": "Inverse sample entropy",
        "plain": "How regular or sequentially structured the symbolic team-state pattern is over time.",
        "high": "A higher value may indicate more structured dependency among team-state changes.",
        "low": "A lower value may indicate less regularity or weaker sequential structure.",
        "caution": "The interpretation depends on the coding scheme, task phase, and ground-truth context.",
    },
    "influence": {
        "display": "Influence distribution",
        "metric": "Role-level average mutual information share",
        "plain": "How strongly each role's symbolic state is statistically coupled with the team-state sequence.",
        "high": "A concentrated profile may show one role is more coupled with team-state changes.",
        "low": "A distributed profile may show coupling spread across several roles.",
        "caution": "AMI is descriptive coupling, not proof of causal influence or individual performance quality.",
    },
}

SUGGESTED_PROMPTS = [
    "What does the adaptation spike mean?",
    "How is inverse sample entropy connected to dynamic interdependency?",
    "Which role is most coupled with the team-state sequence?",
    "What can and cannot be concluded from these synthetic outputs?",
]


def resolve_identity_path() -> Optional[Path]:
    """Return the first existing identity file path."""

    for path in IDENTITY_CANDIDATES:
        if path.exists():
            return path
    return None


def get_gemini_key() -> Optional[str]:
    """Read Gemini key from Streamlit secrets, then environment variables."""

    secret_key = None
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    except Exception:
        secret_key = None
    return secret_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def run_catalog_by_key() -> Dict[str, Dict[str, Any]]:
    return {run["run_key"]: run for run in RUN_CATALOG}


def run_settings(run_meta: Mapping[str, Any]) -> Dict[str, int | str]:
    """Combine fixed run metadata with analysis settings."""

    settings = dict(DEFAULT_SETTINGS)
    settings.update(st.session_state.get("analysis_settings", {}))
    settings.update(
        {
            "seed": int(run_meta["seed"]),
            "n_seconds": int(run_meta["n_seconds"]),
            "event_time_sec": int(run_meta["event_time_sec"]),
        }
    )
    return settings


def dataset_id_from_dataframe(df: pd.DataFrame, settings: Dict[str, int | str], run_key: str) -> str:
    """Create a compact fingerprint for the current synthetic data and settings."""

    hasher = hashlib.sha1()
    hasher.update(run_key.encode("utf-8"))
    hasher.update(json.dumps(settings, sort_keys=True).encode("utf-8"))
    hasher.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    return hasher.hexdigest()[:12]


def add_proposal_context_to_packet(
    packet: Dict[str, Any],
    run_meta: Mapping[str, Any],
    settings: Mapping[str, int | str],
    dataset_id: str,
) -> Dict[str, Any]:
    """Add RQ2/UI context required by the proposal."""

    enriched = dict(packet)
    enriched["dataset_id"] = dataset_id
    enriched["scenario_context"] = {
        "display_id": run_meta["display_id"],
        "scenario": run_meta["scenario"],
        "scenario_title": run_meta["scenario_title"],
        "phase_note": run_meta["phase_note"],
        "event_label": run_meta["event_label"],
        "event_time_sec": int(run_meta["event_time_sec"]),
        "context_note": run_meta["context_note"],
    }
    enriched["metric_definitions_plain_language"] = METRIC_GLOSSARY
    enriched["rq2_interface_alignment"] = {
        "customized_ai_bot_condition": [
            "left run-selection panel",
            "center event-aligned visualization panel",
            "right AI chat panel for follow-up questions",
            "plain-language explanations paired with visual summaries",
            "explicit cautions and limits of interpretation",
        ],
        "standard_report_condition": [
            "metric names",
            "brief calculation descriptions",
            "statistical summaries",
            "concise written result statements",
            "no conversational chat support",
        ],
        "evaluation_focus": "understanding, confidence, and interpretation accuracy rather than general interface usability",
    }
    enriched["active_analysis_settings"] = dict(settings)
    return enriched


def run_analysis_for_dataframe(
    df: pd.DataFrame,
    *,
    run_meta: Mapping[str, Any],
    entropy_window: int,
    sampen_window: int,
    ami_window: int,
    step: int,
    model: str,
    user_question: str = DEFAULT_USER_QUESTION,
    settings_for_id: Optional[Dict[str, int | str]] = None,
) -> Dict[str, Any]:
    """Run all local analyses on the current synthetic run."""

    paths = build_output_paths(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    active_settings = dict(settings_for_id or {})
    active_settings.update(
        {
            "entropy_window": int(entropy_window),
            "sampen_window": int(sampen_window),
            "ami_window": int(ami_window),
            "step": int(step),
            "model": str(model),
        }
    )
    current_dataset_id = dataset_id_from_dataframe(df, active_settings, str(run_meta["run_key"]))

    states_df = extract_symbolic_state_table(df)
    entropy_df = moving_window_entropy(df, window=int(entropy_window), step=int(step))
    inverse_df = moving_window_inverse_sample_entropy(df, window=int(sampen_window), step=int(step))
    ami_long_df = moving_window_role_ami(df, window=int(ami_window), step=int(step))
    ami_summary_df = summarize_role_ami(ami_long_df)

    df.to_csv(paths.synthetic_csv, index=False)
    states_df.to_csv(paths.state_csv, index=False)
    entropy_df.to_csv(paths.entropy_csv, index=False)
    inverse_df.to_csv(paths.inverse_sampen_csv, index=False)
    ami_long_df.to_csv(paths.role_ami_long_csv, index=False)
    ami_summary_df.to_csv(paths.role_ami_summary_csv, index=False)

    plot_team_state(df, paths.team_state_figure)
    plot_entropy(entropy_df, paths.entropy_figure)
    plot_inverse_sampen(inverse_df, paths.inverse_sampen_figure)
    plot_role_ami_summary(ami_summary_df, paths.role_ami_figure)
    plot_role_influence_heatmap(ami_long_df, paths.role_influence_heatmap)

    packet = build_explanation_packet(
        df,
        entropy_df,
        inverse_df,
        ami_long_df,
        ami_summary_df,
        paths,
        user_question=user_question,
    )
    packet = add_proposal_context_to_packet(packet, run_meta, active_settings, current_dataset_id)
    packet["streamlit_connection_status"] = {
        "dataset_id": current_dataset_id,
        "uses_current_synthetic_data_from_session_state": True,
        "local_python_runs_metrics_before_llm_explanation": True,
        "dashboard_and_chatbot_share_same_analysis_bundle": True,
        "settings": active_settings,
    }
    paths.packet_json.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    write_api_status(paths, api_key_detected=bool(get_gemini_key()), response_generated=False, model=str(model))

    required_files = [
        paths.synthetic_csv,
        paths.state_csv,
        paths.entropy_csv,
        paths.inverse_sampen_csv,
        paths.role_ami_long_csv,
        paths.role_ami_summary_csv,
        paths.team_state_figure,
        paths.entropy_figure,
        paths.inverse_sampen_figure,
        paths.role_ami_figure,
        paths.role_influence_heatmap,
        paths.packet_json,
        paths.api_status_json,
    ]
    validate_outputs(df, entropy_df, inverse_df, ami_long_df, ami_summary_df, required_files)

    return {
        "paths": paths,
        "timeseries_df": df,
        "states_df": states_df,
        "entropy_df": entropy_df,
        "inverse_df": inverse_df,
        "ami_long_df": ami_long_df,
        "ami_summary_df": ami_summary_df,
        "packet": packet,
        "dataset_id": current_dataset_id,
        "run_meta": dict(run_meta),
        "last_analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "settings": active_settings,
    }


def load_run(run_key: str, *, user_question: str = DEFAULT_USER_QUESTION) -> None:
    """Generate the selected synthetic run and compute all analyses."""

    run_meta = run_catalog_by_key()[run_key]
    settings = run_settings(run_meta)
    df = generate_synthetic_biobehavioral_timeseries(
        n_seconds=int(settings["n_seconds"]),
        seed=int(settings["seed"]),
        event_time_sec=int(settings["event_time_sec"]),
    )
    bundle = run_analysis_for_dataframe(
        df,
        run_meta=run_meta,
        entropy_window=int(settings["entropy_window"]),
        sampen_window=int(settings["sampen_window"]),
        ami_window=int(settings["ami_window"]),
        step=int(settings["step"]),
        model=str(settings["model"]),
        user_question=user_question,
        settings_for_id=settings,
    )
    st.session_state.selected_run_key = run_key
    st.session_state.timeseries_df = df
    st.session_state.analysis_bundle = bundle
    st.session_state.dataset_id = bundle["dataset_id"]
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                f"I am connected to {run_meta['display_id']} ({run_meta['scenario_title']}). "
                "Ask me to explain a metric, connect it to the event marker, or show the calculation tables."
            ),
            "artifacts": {},
            "dataset_id": bundle["dataset_id"],
        }
    ]


def ensure_connected_state() -> None:
    """Initialize selected run, analysis settings, and chat state."""

    if "analysis_settings" not in st.session_state:
        st.session_state.analysis_settings = dict(DEFAULT_SETTINGS)
    if "selected_run_key" not in st.session_state or "analysis_bundle" not in st.session_state:
        load_run(RUN_CATALOG[0]["run_key"])


def parse_generation_overrides(question: str, settings: Dict[str, int | str]) -> Dict[str, int | str]:
    """Parse simple generation overrides from a user message."""

    updated = dict(settings)
    lower = question.lower()
    seed_match = re.search(r"seed\s*(?:=|is|:)?\s*(\d+)", lower)
    seconds_match = re.search(r"(\d{3,4})\s*(?:seconds|sec|s)\b", lower)
    duration_match = re.search(r"duration\s*(?:=|is|:)?\s*(\d{3,4})", lower)
    event_match = re.search(r"event\s*(?:time|at|=|is|:)?\s*(\d{2,4})", lower)

    if seed_match:
        updated["seed"] = int(seed_match.group(1))
    if duration_match:
        updated["n_seconds"] = max(300, min(1800, int(duration_match.group(1))))
    elif seconds_match:
        updated["n_seconds"] = max(300, min(1800, int(seconds_match.group(1))))
    if event_match:
        event_time = int(event_match.group(1))
        n_seconds = int(updated["n_seconds"])
        updated["event_time_sec"] = max(30, min(n_seconds - 30, event_time))
    return updated


def classify_user_request(question: str) -> Dict[str, Any]:
    """Classify the user request into local analysis actions and UI artifacts."""

    q = question.lower()
    wants_generate = any(
        term in q
        for term in [
            "generate",
            "create",
            "new synthetic",
            "new data",
            "new dataset",
            "regenerate",
            "simulate",
            "different data",
            "different dataset",
            "change data",
            "change the data",
            "use seed",
            "set seed",
            "change seed",
            "with seed",
        ]
    )
    wants_run = any(term in q for term in ["run", "compute", "calculate", "analyze", "analyse", "analysis", "analyses"])
    wants_figures = any(term in q for term in ["figure", "figures", "plot", "plots", "graph", "visual", "visualization"])
    wants_tables = any(term in q for term in ["table", "tables", "dataframe", "data frame", "csv", "values", "output"])

    figure_keys: List[str] = []
    table_keys: List[str] = []

    if any(term in q for term in ["entropy", "shannon", "adaptation", "reorganization", "reorganisation"]):
        figure_keys.append("entropy")
        table_keys.append("entropy")
    if any(term in q for term in ["sample", "sampen", "inverse", "regularity", "interdependence", "interdependency"]):
        figure_keys.append("inverse_sampen")
        table_keys.append("inverse_sampen")
    if any(term in q for term in ["ami", "mutual information", "influence", "role", "jtac", "fso", "fom", "foa", "leader"]):
        figure_keys.extend(["ami_summary", "ami_heatmap"])
        table_keys.extend(["ami_summary", "ami_long"])
    if any(term in q for term in ["team state", "symbolic state", "state trajectory", "timeline", "event"]):
        figure_keys.append("team_state")
        table_keys.append("states")

    asks_for_everything = wants_run and (
        "all" in q or "everything" in q or "figures and tables" in q or "outputs" in q or "data analyses" in q
    )
    if asks_for_everything or (wants_figures and not figure_keys):
        figure_keys.extend(["team_state", "entropy", "inverse_sampen", "ami_summary", "ami_heatmap"])
    if asks_for_everything or (wants_tables and not table_keys):
        table_keys.extend(["entropy", "inverse_sampen", "ami_summary", "ami_long"])

    figure_keys = list(dict.fromkeys(figure_keys))
    table_keys = list(dict.fromkeys(table_keys))

    return {
        "generate": wants_generate,
        "run_analysis": wants_run or wants_generate,
        "figure_keys": figure_keys,
        "table_keys": table_keys,
        "wants_gemini_explanation": not (wants_figures or wants_tables)
        or any(term in q for term in ["explain", "interpret", "meaning", "understand", "why", "what does", "what do"]),
    }


def fmt(value: Any, digits: int = 3) -> str:
    """Format floats safely for UI text."""

    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "not available"
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def local_interpretation_response(
    question: str,
    bundle: Dict[str, Any],
    figure_keys: Optional[List[str]] = None,
    table_keys: Optional[List[str]] = None,
) -> str:
    """Create a proposal-aligned fallback response without an LLM call."""

    packet = bundle["packet"]
    entropy = packet["adaptation_entropy_summary"]
    inverse = packet["interdependence_inverse_sample_entropy_summary"]
    influence = packet["influence_distribution_summary"]
    run_meta = bundle["run_meta"]
    figures = figure_keys or []
    tables = table_keys or []

    q = question.lower()
    if any(term in q for term in ["adaptation", "entropy", "reorganization", "reorganisation"]):
        focus = "adaptation"
    elif any(term in q for term in ["interdependence", "interdependency", "sampen", "sample entropy", "regularity"]):
        focus = "interdependence"
    elif any(term in q for term in ["influence", "ami", "role", "leader", "jtac", "fso", "foa", "fom"]):
        focus = "influence"
    else:
        focus = "overview"

    output_note = ""
    if figures:
        output_note += " Displayed figure(s): " + ", ".join(FIGURE_SPECS[key]["title"] for key in figures) + "."
    if tables:
        output_note += " Displayed table(s): " + ", ".join(TABLE_SPECS[key]["title"] for key in tables) + "."

    if focus == "adaptation":
        brief = (
            f"For {run_meta['display_id']}, the adaptation metric peaks at {fmt(entropy['peak_entropy_bits'])} bits "
            f"at {fmt(entropy['peak_time_min'])} min. This may indicate a window with more varied symbolic team-state patterns."
            f"{output_note}"
        )
    elif focus == "interdependence":
        brief = (
            f"For {run_meta['display_id']}, the inverse sample entropy peak is {fmt(inverse['peak_inverse_sample_entropy'])} "
            f"at {fmt(inverse['peak_time_min'])} min. In this prototype, higher values mean the symbolic sequence is more regular."
            f"{output_note}"
        )
    elif focus == "influence":
        brief = (
            f"For {run_meta['display_id']}, the role with the highest mean AMI share is "
            f"{influence['top_role_by_mean_ami_share']} ({fmt(influence['top_role_mean_ami_share'])}). "
            "This describes statistical coupling with the team-state sequence, not individual quality."
            f"{output_note}"
        )
    else:
        brief = (
            f"For {run_meta['display_id']}, the prototype computed all three teamness metrics: adaptation, "
            "dynamic interdependency, and influence distribution. The results are synthetic demonstration outputs, "
            "so they support interface testing rather than dissertation findings."
            f"{output_note}"
        )

    return f"""### 1. Brief answer
{brief}

### 2. What the visualization or output shows
The center panel aligns metric plots with the selected run and the synthetic event marker ({run_meta['event_label']} at {run_meta['event_time_sec']} seconds). Use the plot shape first as an observed pattern, then connect it cautiously to a teamwork construct.

### 3. How the relevant metric is derived in plain language
- Adaptation uses moving-window Shannon entropy of the symbolic team-state sequence.
- Dynamic interdependency uses inverse sample entropy, so more regular symbolic sequencing gives a higher index.
- Influence distribution uses each role's AMI share with the team-state sequence.

### 4. Interpretation connected to team constructs
The values may help a non-expert discuss coordination, reorganization, and role coupling during the run. They do not by themselves establish whether the team performed well or poorly.

### 5. What cannot be concluded
The prototype cannot infer mental states, diagnose stress, score individual trainees, or make causal claims. It also cannot claim dissertation evidence because the current data are synthetic.

### 6. Human validation check
A human analyst should compare the timing of the pattern with the scenario event log, inspect missingness or sensor artifacts, and compare the interpretation with ground-truth ratings when available.

### 7. Stakeholder-facing summary
These synthetic visuals and explanations show how the customized AI-bot condition can help users connect metric values to the team-dynamics concepts in the proposal while keeping uncertainty and limits visible.
"""


def build_chat_prompt_with_current_outputs(
    question: str,
    bundle: Dict[str, Any],
    requested_figures: List[str],
    requested_tables: List[str],
) -> str:
    """Build a Gemini prompt that separates local computation from LLM explanation."""

    identity_path = resolve_identity_path()
    identity_text = load_identity_text(identity_path)
    packet = dict(bundle["packet"])
    packet["user_question"] = question
    packet["local_python_status"] = {
        "analysis_has_been_run": True,
        "analysis_source": "Streamlit app local Python functions",
        "llm_role": "Explain the already-computed outputs; do not invent additional calculations.",
        "requested_figures": requested_figures,
        "requested_tables": requested_tables,
    }
    base_prompt = build_gemini_prompt(identity_text, packet, user_question=question)
    extra = """

Additional instruction for this Streamlit RQ2 prototype:
The user is interacting with the customized AI-bot condition from the dissertation proposal. The screen has a run-selection panel, event-aligned visualizations, and this chat panel. Explain the current selected run, refer to the displayed metric and event marker when relevant, and use plain language for non-experts. Separate observed values from interpretation. Do not reveal hidden synthetic MR_Overall labels unless the user is explicitly in the optional demo ranking scorer.
"""
    return base_prompt + extra


def figure_payloads_for_message(figure_keys: List[str], bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Store figure bytes in the chat message to avoid stale cached files."""

    payloads: List[Dict[str, Any]] = []
    paths = bundle["paths"]
    for key in figure_keys:
        spec = FIGURE_SPECS[key]
        path = getattr(paths, spec["path_attr"])
        if path.exists():
            payloads.append(
                {
                    "key": key,
                    "title": spec["title"],
                    "caption": f"{spec['caption']} Dataset ID: {bundle['dataset_id']}.",
                    "image_bytes": path.read_bytes(),
                }
            )
    return payloads


def table_payloads_for_message(table_keys: List[str], bundle: Dict[str, Any], *, max_rows: int = 80) -> List[Dict[str, Any]]:
    """Store table snapshots in the chat message."""

    payloads: List[Dict[str, Any]] = []
    for key in table_keys:
        spec = TABLE_SPECS[key]
        table_df = bundle[spec["key"]].head(max_rows).copy()
        payloads.append({"key": key, "title": f"{spec['title']} (dataset ID {bundle['dataset_id']})", "df": table_df})
    return payloads


def artifact_payload_for_message(
    figure_keys: List[str],
    table_keys: List[str],
    bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """Create immutable chat artifacts from the current analysis bundle."""

    return {
        "dataset_id": bundle["dataset_id"],
        "figures": figure_payloads_for_message(figure_keys, bundle),
        "tables": table_payloads_for_message(table_keys, bundle),
    }


def render_message(message: Dict[str, Any]) -> None:
    """Render a stored chat message with its own figure/table snapshots."""

    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        artifacts = message.get("artifacts", {}) or {}
        for fig in artifacts.get("figures", []):
            st.image(fig["image_bytes"], caption=fig["caption"], use_container_width=True)
        for table in artifacts.get("tables", []):
            st.markdown(f"**{table['title']}**")
            st.dataframe(table["df"], use_container_width=True)


def render_metric_cards(bundle: Dict[str, Any]) -> None:
    """Display compact metric cards for the selected run."""

    packet = bundle["packet"]
    entropy = packet["adaptation_entropy_summary"]
    inverse = packet["interdependence_inverse_sample_entropy_summary"]
    influence = packet["influence_distribution_summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Selected run", bundle["run_meta"]["display_id"])
    c2.metric("Peak adaptation", f"{entropy['peak_entropy_bits']:.3f} bits", f"{entropy['peak_time_min']:.2f} min")
    c3.metric("Peak interdependency", f"{inverse['peak_inverse_sample_entropy']:.3f}", f"{inverse['peak_time_min']:.2f} min")
    c4.metric("Top AMI role", influence["top_role_by_mean_ami_share"], f"share {influence['top_role_mean_ami_share']:.3f}")


def render_figures_from_bundle(figure_keys: List[str], bundle: Dict[str, Any]) -> None:
    """Render current figures from bytes rather than static browser-cached paths."""

    paths = bundle["paths"]
    for key in figure_keys:
        spec = FIGURE_SPECS[key]
        path = getattr(paths, spec["path_attr"])
        if path.exists():
            st.image(path.read_bytes(), caption=f"{spec['caption']} Dataset ID: {bundle['dataset_id']}.", use_container_width=True)
        else:
            st.warning(f"Missing figure: {path.name}")


def render_tables_from_bundle(table_keys: List[str], bundle: Dict[str, Any], *, max_rows: int = 80) -> None:
    """Render current tables."""

    for key in table_keys:
        spec = TABLE_SPECS[key]
        df = bundle[spec["key"]]
        st.markdown(f"**{spec['title']}**")
        st.dataframe(df.head(max_rows), use_container_width=True)


def current_dataset_status(bundle: Dict[str, Any]) -> str:
    """Return a compact status line for the active connected dataset."""

    settings = bundle.get("settings", run_settings(bundle["run_meta"]))
    return (
        f"Connected {bundle['run_meta']['display_id']} | dataset ID `{bundle['dataset_id']}` | "
        f"{len(bundle['timeseries_df']):,} rows at 1 Hz | seed={settings['seed']} | "
        f"event={settings['event_time_sec']} sec | last analysis={bundle['last_analysis_time']}"
    )


def phase_for_time(time_sec: float, n_seconds: int) -> str:
    """Return a scenario-like phase label for storyboard display."""

    if time_sec < 0.22 * n_seconds:
        return "orientation"
    if time_sec < 0.47 * n_seconds:
        return "fire planning"
    if time_sec < 0.78 * n_seconds:
        return "execution"
    return "assessment"


def render_storyboard(bundle: Dict[str, Any]) -> None:
    """Render the proposal-aligned event storyboard."""

    run_meta = bundle["run_meta"]
    n_seconds = int(run_meta["n_seconds"])
    event_sec = int(run_meta["event_time_sec"])
    event_pct = min(96, max(4, event_sec / n_seconds * 100))
    event_phase = phase_for_time(event_sec, n_seconds)
    html = f"""
    <div class="story-card">
      <div class="story-header">
        <div>
          <div class="eyebrow">Mission storyboard</div>
          <h3>{run_meta['scenario']} - {run_meta['scenario_title']}</h3>
        </div>
        <div class="pill">{run_meta['display_id']}</div>
      </div>
      <div class="timeline">
        <div class="segment segment-1" style="left:0%;width:22%">Orientation</div>
        <div class="segment segment-2" style="left:22%;width:25%">Fire planning</div>
        <div class="segment segment-3" style="left:47%;width:31%">Execution</div>
        <div class="segment segment-4" style="left:78%;width:22%">Assessment</div>
        <div class="event-marker" style="left:{event_pct}%">
          <div class="event-dot">!</div>
          <div class="event-text">{run_meta['event_label']}<br><span>{event_sec}s - {event_phase}</span></div>
        </div>
      </div>
      <p>{run_meta['context_note']} Metrics should be interpreted against the event marker and phase context.</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_teamwork_translation(bundle: Dict[str, Any]) -> None:
    """Render plain-language construct definitions."""

    packet = bundle["packet"]
    entropy = packet["adaptation_entropy_summary"]
    inverse = packet["interdependence_inverse_sample_entropy_summary"]
    influence = packet["influence_distribution_summary"]
    cards = [
        ("Adaptation", "Moving-window entropy", f"Peak {fmt(entropy['peak_entropy_bits'])} bits", METRIC_GLOSSARY["adaptation"]["plain"]),
        (
            "Dynamic interdependency",
            "Inverse sample entropy",
            f"Peak {fmt(inverse['peak_inverse_sample_entropy'])}",
            METRIC_GLOSSARY["interdependence"]["plain"],
        ),
        (
            "Influence distribution",
            "AMI share",
            f"Top role: {influence['top_role_by_mean_ami_share']}",
            METRIC_GLOSSARY["influence"]["plain"],
        ),
    ]
    for title, metric, stat, plain in cards:
        st.markdown(
            f"""
            <div class="mini-card">
              <div class="mini-title">{title}</div>
              <div class="mini-subtitle">{metric} - {stat}</div>
              <div class="mini-text">{plain}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def report_markdown(bundle: Dict[str, Any]) -> str:
    """Build a conventional standard-report condition from the same outputs."""

    packet = bundle["packet"]
    run_meta = bundle["run_meta"]
    entropy = packet["adaptation_entropy_summary"]
    inverse = packet["interdependence_inverse_sample_entropy_summary"]
    influence = packet["influence_distribution_summary"]
    return f"""# Standard statistical-report condition

## Run information
- Run: {run_meta['display_id']}
- Scenario: {run_meta['scenario']} - {run_meta['scenario_title']}
- Data status: synthetic demonstration data only
- Event marker: {run_meta['event_label']} at {run_meta['event_time_sec']} seconds

## Metric definitions and calculation descriptions
- Adaptation: {METRIC_GLOSSARY['adaptation']['metric']}. {METRIC_GLOSSARY['adaptation']['plain']}
- Dynamic interdependency: {METRIC_GLOSSARY['interdependence']['metric']}. {METRIC_GLOSSARY['interdependence']['plain']}
- Influence distribution: {METRIC_GLOSSARY['influence']['metric']}. {METRIC_GLOSSARY['influence']['plain']}

## Statistical summaries
- Mean adaptation entropy: {fmt(entropy['mean_entropy_bits'])}; peak adaptation entropy: {fmt(entropy['peak_entropy_bits'])} bits at {fmt(entropy['peak_time_min'])} min.
- Mean inverse sample entropy: {fmt(inverse['mean_inverse_sample_entropy'])}; peak inverse sample entropy: {fmt(inverse['peak_inverse_sample_entropy'])} at {fmt(inverse['peak_time_min'])} min.
- Top role by mean AMI share: {influence['top_role_by_mean_ami_share']} ({fmt(influence['top_role_mean_ami_share'])}). Mean HHI: {fmt(influence['mean_hhi'])}; peak HHI: {fmt(influence['peak_hhi'])}.

## Concise result statements
- The entropy trajectory summarizes time-varying symbolic team-state variability.
- The inverse sample entropy trajectory summarizes time-varying symbolic regularity.
- The AMI profile summarizes descriptive role coupling with the team-state sequence.

## Interpretation limitations
These values do not score individual trainees, infer stress or mental state, prove causal effects, or show dissertation findings. Interpretation should be checked against scenario logs, missingness, sensor artifacts, and available ground-truth ratings.
"""


def render_standard_report_condition(bundle: Dict[str, Any]) -> None:
    """Render the proposal's comparison condition."""

    st.subheader("Standard statistical-report condition")
    st.caption("Same synthetic outputs, presented without interactive visual-chat support.")
    report = report_markdown(bundle)
    st.markdown(report)
    st.download_button(
        "Download standard report markdown",
        data=report.encode("utf-8"),
        file_name=f"standard_report_{bundle['run_meta']['display_id'].replace(' ', '_').lower()}_{bundle['dataset_id']}.md",
        mime="text/markdown",
        use_container_width=True,
    )


def process_question(question: str) -> None:
    """Run the connected chatbot workflow for a user question."""

    if not question.strip():
        return

    st.session_state.messages.append(
        {"role": "user", "content": question, "artifacts": {}, "dataset_id": st.session_state.get("dataset_id")}
    )
    request = classify_user_request(question)
    bundle = st.session_state.analysis_bundle
    settings = dict(bundle["settings"])

    if request["generate"]:
        # This remains available for developer testing, but the main proposal UI
        # is run-selection based.
        updated_settings = parse_generation_overrides(question, settings)
        run_meta = dict(bundle["run_meta"])
        run_meta["seed"] = int(updated_settings.get("seed", run_meta["seed"]))
        run_meta["n_seconds"] = int(updated_settings.get("n_seconds", run_meta["n_seconds"]))
        run_meta["event_time_sec"] = int(updated_settings.get("event_time_sec", run_meta["event_time_sec"]))
        df = generate_synthetic_biobehavioral_timeseries(
            n_seconds=int(run_meta["n_seconds"]),
            seed=int(run_meta["seed"]),
            event_time_sec=int(run_meta["event_time_sec"]),
        )
        bundle = run_analysis_for_dataframe(
            df,
            run_meta=run_meta,
            entropy_window=int(settings["entropy_window"]),
            sampen_window=int(settings["sampen_window"]),
            ami_window=int(settings["ami_window"]),
            step=int(settings["step"]),
            model=str(settings["model"]),
            user_question=question,
            settings_for_id=updated_settings,
        )
        st.session_state.analysis_bundle = bundle
        st.session_state.dataset_id = bundle["dataset_id"]
    elif request["run_analysis"]:
        run_meta = bundle["run_meta"]
        bundle = run_analysis_for_dataframe(
            bundle["timeseries_df"],
            run_meta=run_meta,
            entropy_window=int(settings["entropy_window"]),
            sampen_window=int(settings["sampen_window"]),
            ami_window=int(settings["ami_window"]),
            step=int(settings["step"]),
            model=str(settings["model"]),
            user_question=question,
            settings_for_id=settings,
        )
        st.session_state.analysis_bundle = bundle

    figure_keys = request["figure_keys"]
    table_keys = request["table_keys"]
    if request["run_analysis"] and not figure_keys and not table_keys:
        figure_keys = ["team_state", "entropy", "inverse_sampen", "ami_summary", "ami_heatmap"]
        table_keys = ["entropy", "inverse_sampen", "ami_summary"]

    prompt = build_chat_prompt_with_current_outputs(question, bundle, figure_keys, table_keys)
    bundle["paths"].prompt_md.write_text(prompt, encoding="utf-8")

    if get_gemini_key() and request["wants_gemini_explanation"]:
        try:
            response = call_gemini(prompt, model=str(settings["model"]), api_key=get_gemini_key())
            bundle["paths"].api_response_md.write_text(response, encoding="utf-8")
            write_api_status(bundle["paths"], api_key_detected=True, response_generated=True, model=str(settings["model"]))
        except Exception as exc:
            response = local_interpretation_response(question, bundle, figure_keys, table_keys)
            response += f"\n\nGemini explanation failed: `{exc}`"
    else:
        response = local_interpretation_response(question, bundle, figure_keys, table_keys)
        if not get_gemini_key():
            response += "\n\nGemini is not configured, so this is a local Python-computed interpretation scaffold."
        elif not request["wants_gemini_explanation"]:
            response += "\n\nThe requested computed artifacts are displayed without an added LLM narrative."

    artifacts = artifact_payload_for_message(figure_keys, table_keys, bundle)
    st.session_state.messages.append(
        {"role": "assistant", "content": response, "artifacts": artifacts, "dataset_id": bundle["dataset_id"]}
    )
    st.rerun()


def render_chat_panel(bundle: Dict[str, Any]) -> None:
    """Render right-side chat panel."""

    st.markdown("### AI interpretation assistant")
    st.caption("Plain-language, event-linked explanations for non-experts.")
    for i, prompt in enumerate(SUGGESTED_PROMPTS):
        if st.button(prompt, key=f"prompt_{i}", use_container_width=True):
            process_question(prompt)
    st.divider()
    for message in st.session_state.messages:
        render_message(message)
    user_question = st.chat_input("Ask about the selected run, metric, event, or limitation")
    if user_question:
        process_question(user_question)


def render_visual_workspace(bundle: Dict[str, Any]) -> None:
    """Render center panel with storyboard, visuals, and tables."""

    render_storyboard(bundle)
    st.markdown("### Event-aligned metric displays")
    render_metric_cards(bundle)
    metric_view = st.radio(
        "Choose a visual focus",
        options=["Adaptation", "Dynamic interdependency", "Influence distribution", "All outputs"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if metric_view == "Adaptation":
        render_figures_from_bundle(["entropy"], bundle)
        st.info(METRIC_GLOSSARY["adaptation"]["high"] + " " + METRIC_GLOSSARY["adaptation"]["caution"])
    elif metric_view == "Dynamic interdependency":
        render_figures_from_bundle(["inverse_sampen"], bundle)
        st.info(METRIC_GLOSSARY["interdependence"]["high"] + " " + METRIC_GLOSSARY["interdependence"]["caution"])
    elif metric_view == "Influence distribution":
        c1, c2 = st.columns(2)
        with c1:
            render_figures_from_bundle(["ami_summary"], bundle)
        with c2:
            render_figures_from_bundle(["ami_heatmap"], bundle)
        st.info(METRIC_GLOSSARY["influence"]["high"] + " " + METRIC_GLOSSARY["influence"]["caution"])
    else:
        c1, c2 = st.columns(2)
        with c1:
            render_figures_from_bundle(["team_state", "entropy", "ami_summary"], bundle)
        with c2:
            render_figures_from_bundle(["inverse_sampen", "ami_heatmap"], bundle)

    with st.expander("Metric tables and calculation outputs"):
        table_choice = st.selectbox(
            "Choose a table",
            options=["entropy", "inverse_sampen", "ami_summary", "ami_long", "synthetic_data", "states"],
            format_func=lambda key: TABLE_SPECS[key]["title"],
            key="workspace_table_choice",
        )
        render_tables_from_bundle([table_choice], bundle, max_rows=150)


def render_run_selection_panel(bundle: Dict[str, Any]) -> None:
    """Render left-side run selector and construct translation."""

    st.markdown("### Scenario runs")
    current_key = st.session_state.selected_run_key
    for run in RUN_CATALOG:
        selected = run["run_key"] == current_key
        selected_class = "selected-run" if selected else ""
        st.markdown(
            f"""
            <div class="run-card {selected_class}">
              <div class="run-title">{run['display_id']} - {run['scenario']}</div>
              <div class="run-subtitle">{run['scenario_title']}</div>
              <div class="run-detail">Event: {run['event_label']} at {run['event_time_sec']}s</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not selected:
            if st.button(f"Select {run['display_id']}", key=f"select_left_{run['run_key']}", use_container_width=True):
                load_run(run["run_key"])
                st.rerun()
    st.divider()
    st.markdown("### Teamwork translation")
    render_teamwork_translation(bundle)
    st.divider()
    st.markdown("### Interpretation confidence")
    st.warning(
        "Moderate for demo purposes: the app uses synthetic data and does not include real ground-truth ratings, sensor missingness checks, or scenario logs."
    )


def render_custom_bot_condition(bundle: Dict[str, Any]) -> None:
    """Render the customized AI-bot condition."""

    left, center, right = st.columns([0.95, 2.0, 1.15], gap="large")
    with left:
        render_run_selection_panel(bundle)
    with center:
        render_visual_workspace(bundle)
    with right:
        render_chat_panel(bundle)


def render_ranking_task_scaffold() -> None:
    """Render optional RQ2 behavioral ranking task scaffold."""

    with st.expander("Optional RQ2 ranking-task scaffold"):
        st.write(
            "This mirrors the proposal's behavioral interpretation-accuracy task using synthetic hidden labels. "
            "Participants would rank four de-identified runs from lowest to highest team performance."
        )
        options = [run["display_id"] for run in RUN_CATALOG]
        cols = st.columns(4)
        selected_order: List[str] = []
        for i, col in enumerate(cols, start=1):
            with col:
                selected_order.append(st.selectbox(f"Rank {i}", options=options, key=f"rank_{i}"))
        if len(set(selected_order)) < len(selected_order):
            st.warning("Each rank should use a different run.")
        if st.button("Score synthetic demo ranking", use_container_width=True):
            display_to_mr = {run["display_id"]: int(run["synthetic_mr_overall"]) for run in RUN_CATALOG}
            correct_pairs = 0
            total_pairs = 0
            for i in range(len(selected_order)):
                for j in range(i + 1, len(selected_order)):
                    total_pairs += 1
                    if display_to_mr[selected_order[i]] <= display_to_mr[selected_order[j]]:
                        correct_pairs += 1
            st.success(f"Synthetic pairwise-order accuracy: {correct_pairs} / {total_pairs}")
            st.caption("In the dissertation study, real labels would remain hidden and be used only for analysis.")


def sidebar_controls() -> None:
    """Render global controls in the sidebar."""

    st.sidebar.header("Run selection")
    current_key = st.session_state.selected_run_key
    keys = [run["run_key"] for run in RUN_CATALOG]
    selected_key = st.sidebar.selectbox(
        "Choose de-identified scenario run",
        options=keys,
        format_func=lambda key: f"{run_catalog_by_key()[key]['display_id']} - {run_catalog_by_key()[key]['scenario_title']}",
        index=keys.index(current_key),
    )
    if selected_key != current_key:
        load_run(selected_key)
        st.rerun()

    st.sidebar.divider()
    st.sidebar.header("Analysis settings")
    current_settings = dict(st.session_state.analysis_settings)
    pending_settings = dict(current_settings)
    pending_settings["entropy_window"] = st.sidebar.slider(
        "Entropy window (seconds)", 60, 300, int(current_settings["entropy_window"]), 15
    )
    pending_settings["sampen_window"] = st.sidebar.slider(
        "Sample entropy window (seconds)", 90, 360, int(current_settings["sampen_window"]), 15
    )
    pending_settings["ami_window"] = st.sidebar.slider("AMI window (seconds)", 90, 360, int(current_settings["ami_window"]), 15)
    pending_settings["step"] = st.sidebar.slider("Window step (seconds)", 5, 60, int(current_settings["step"]), 5)
    pending_settings["model"] = st.sidebar.text_input("Gemini model", value=str(current_settings["model"]))

    if pending_settings != current_settings:
        st.sidebar.warning("Settings changed. Apply to recompute the selected run.")
        if st.sidebar.button("Apply analysis settings", type="primary", use_container_width=True):
            st.session_state.analysis_settings = pending_settings
            load_run(st.session_state.selected_run_key, user_question="Recompute analyses with updated settings.")
            st.rerun()
    else:
        if st.sidebar.button("Recompute selected run", use_container_width=True):
            load_run(st.session_state.selected_run_key, user_question="Recompute selected run.")
            st.rerun()

    st.sidebar.divider()
    st.sidebar.header("Gemini API")
    if get_gemini_key():
        st.sidebar.success("Gemini key detected.")
    else:
        st.sidebar.warning("No Gemini key detected.")
        st.sidebar.caption("Use Streamlit secrets or environment variables. Do not embed keys in source code.")

    st.sidebar.divider()
    st.sidebar.header("Download outputs")
    bundle = st.session_state.analysis_bundle
    st.sidebar.download_button(
        "Synthetic time series CSV",
        data=bundle["timeseries_df"].to_csv(index=False).encode("utf-8"),
        file_name=f"synthetic_timeseries_{bundle['run_meta']['display_id'].replace(' ', '_').lower()}_{bundle['dataset_id']}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.sidebar.download_button(
        "Explanation packet JSON",
        data=json.dumps(bundle["packet"], indent=2).encode("utf-8"),
        file_name=f"explanation_packet_{bundle['run_meta']['display_id'].replace(' ', '_').lower()}_{bundle['dataset_id']}.json",
        mime="application/json",
        use_container_width=True,
    )


def inject_css() -> None:
    """Inject lightweight UI styling inspired by the supplied React mockup."""

    st.markdown(
        """
        <style>
        .main .block-container {padding-top: 1.5rem; max-width: 1500px;}
        .stApp {background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 46%, #ecfeff 100%);}
        .story-card, .mini-card, .run-card {
            background: rgba(255,255,255,0.94); border: 1px solid #e2e8f0;
            border-radius: 22px; padding: 16px; box-shadow: 0 8px 24px rgba(15,23,42,0.06);
            margin-bottom: 12px;
        }
        .story-header {display:flex; justify-content:space-between; gap:16px; align-items:start;}
        .story-header h3 {margin:0; color:#0f172a; font-size: 1.1rem;}
        .eyebrow {font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:#64748b; font-weight:700;}
        .pill {background:#dbeafe; color:#1d4ed8; padding:6px 12px; border-radius:999px; font-weight:700; white-space:nowrap;}
        .timeline {position:relative; height:112px; margin: 18px 4px 10px 4px;}
        .segment {position:absolute; top:42px; height:22px; font-size:.72rem; text-align:center; color:#334155; font-weight:700; padding-top:2px;}
        .segment-1 {background:#bfdbfe; border-radius:999px 0 0 999px;}
        .segment-2 {background:#fde68a;}
        .segment-3 {background:#fecaca;}
        .segment-4 {background:#bbf7d0; border-radius:0 999px 999px 0;}
        .event-marker {position:absolute; top:6px; transform:translateX(-50%); text-align:center; min-width:140px;}
        .event-dot {margin:auto; height:36px; width:36px; border-radius:999px; background:#991b1b; color:white; font-weight:900; display:flex; align-items:center; justify-content:center; box-shadow:0 6px 18px rgba(153,27,27,.28);}
        .event-text {font-weight:700; font-size:.78rem; color:#7f1d1d; margin-top:4px;}
        .event-text span {font-weight:500; color:#64748b;}
        .mini-title {font-weight:800; color:#0f172a;}
        .mini-subtitle {font-size:.78rem; color:#2563eb; font-weight:700; margin:.15rem 0 .35rem;}
        .mini-text {font-size:.82rem; color:#475569; line-height:1.35;}
        .run-card {padding:14px;}
        .selected-run {border-color:#2563eb; background:#eff6ff;}
        .run-title {font-weight:800; color:#0f172a;}
        .run-subtitle {font-size:.82rem; color:#475569; margin:.12rem 0;}
        .run-detail {font-size:.75rem; color:#64748b;}
        div[data-testid="stMetric"] {background: rgba(255,255,255,.82); border: 1px solid #e2e8f0; border-radius: 18px; padding: 10px 12px;}
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Bio-Behavioral Team Dynamics Chatbot",
    page_icon="💬",
    layout="wide",
)

inject_css()
ensure_connected_state()
sidebar_controls()

bundle = st.session_state.analysis_bundle

st.title("Bio-Behavioral Team Dynamics Interpretation Prototype")
st.caption(
    "RQ2 scaffold: a customized AI-bot condition that pairs event-aligned visual summaries with plain-language chat, "
    "plus a standard statistical-report comparison condition. Synthetic demonstration data only."
)
st.info(current_dataset_status(bundle))

condition = st.radio(
    "Presentation condition",
    options=["Customized AI-bot condition", "Standard statistical-report condition"],
    horizontal=True,
)

if condition == "Customized AI-bot condition":
    render_custom_bot_condition(bundle)
else:
    render_standard_report_condition(bundle)

render_ranking_task_scaffold()
