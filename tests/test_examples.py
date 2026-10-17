import json
import re
from pathlib import Path

from dqdetect.io import load_data
from dqdetect.profiler import profile_dataframe
from dqdetect.report import render_json, render_markdown


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_committed_json_sample_matches_current_profiler():
    df = load_data(EXAMPLES / "messy_orders.csv")
    profile = profile_dataframe(df, source_name="messy_orders.csv")

    generated = json.loads(render_json(profile))
    committed = json.loads(
        (EXAMPLES / "messy_orders_report.json").read_text(encoding="utf-8")
    )

    generated.pop("generated_at")
    committed.pop("generated_at")

    assert committed == generated


def test_committed_markdown_sample_matches_current_renderer():
    df = load_data(EXAMPLES / "messy_orders.csv")
    profile = profile_dataframe(df, source_name="messy_orders.csv")

    generated = render_markdown(profile)
    committed = (EXAMPLES / "messy_orders_report.md").read_text(
        encoding="utf-8"
    )

    normalize_generated = lambda text: re.sub(
        r"\*\*Generated:\*\* .*",
        "**Generated:** <timestamp>",
        text,
    )

    assert normalize_generated(committed).strip() == normalize_generated(
        generated
    ).strip()
