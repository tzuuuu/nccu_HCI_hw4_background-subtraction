"""Summarize completed experiment CSVs as report-ready Markdown tables."""

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


APP_DIR = Path(__file__).resolve().parent


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _is_true(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "yes", "y")


def calculate_metrics(rows: Sequence[Dict[str, str]]) -> Dict[str, float]:
    if not rows:
        return {"trials": 0, "success_rate": 0.0, "false_triggers": 0, "missed_triggers": 0, "mean_motion_ratio": 0.0, "mean_trigger_time_ms": 0.0}
    successful = sum(1 for row in rows if _is_true(row.get("correct", "")))
    false_triggers = sum(1 for row in rows if _is_true(row.get("false_trigger", "")))
    missed_triggers = sum(1 for row in rows if _is_true(row.get("missed_trigger", "")))
    ratios = [float(row["motion_ratio"]) for row in rows if row.get("motion_ratio")]
    trigger_times = [float(row["trigger_time_ms"]) for row in rows if row.get("trigger_time_ms")]
    return {
        "trials": len(rows),
        "success_rate": 100.0 * successful / len(rows),
        "false_triggers": false_triggers,
        "missed_triggers": missed_triggers,
        "mean_motion_ratio": 100.0 * sum(ratios) / len(ratios) if ratios else 0.0,
        "mean_trigger_time_ms": sum(trigger_times) / len(trigger_times) if trigger_times else 0.0,
    }


def _group_rows(rows: Sequence[Dict[str, str]], field: str, combine_with_command: bool = False) -> Dict[str, List[Dict[str, str]]]:
    groups: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        condition = row.get(field, "") or "Unspecified"
        if combine_with_command:
            condition = "{} / {}".format(condition, row.get("target_command", "Unspecified"))
        groups.setdefault(condition, []).append(row)
    return groups


def _format_table(groups: Iterable[tuple]) -> str:
    lines = [
        "| 條件 | 次數 | 成功率 | 誤觸 | 漏觸 | 平均 motion ratio | 平均觸發時間 (ms) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, rows in groups:
        metrics = calculate_metrics(rows)
        lines.append("| {} | {} | {:.1f}% | {} | {} | {:.2f}% | {:.1f} |".format(
            label,
            metrics["trials"],
            metrics["success_rate"],
            int(metrics["false_triggers"]),
            int(metrics["missed_triggers"]),
            metrics["mean_motion_ratio"],
            metrics["mean_trigger_time_ms"],
        ))
    return "\n".join(lines)


def summarize(path: Path) -> str:
    rows = read_rows(path)
    if not rows:
        return "## {}\n\n沒有已記錄的試驗資料。\n".format(path.name)
    experiment = rows[0].get("experiment", path.stem)
    sections = ["## {} — {} 次完成試驗".format(experiment, len(rows)), "", "### 整體", _format_table([("Overall", rows)])]
    if path.stem.startswith("experiment1"):
        groups = _group_rows(rows, "target_command")
        sections.extend(("", "### 各指令", _format_table(sorted(groups.items()))))
    elif path.stem.startswith("experiment2"):
        groups = _group_rows(rows, "threshold_level", combine_with_command=True)
        sections.extend(("", "### 門檻與指令", _format_table(sorted(groups.items()))))
    elif path.stem.startswith("experiment3"):
        groups = _group_rows(rows, "lighting", combine_with_command=True)
        sections.extend(("", "### 光線與指令", _format_table(sorted(groups.items()))))
    return "\n".join(sections) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize HW4 experiment CSVs")
    parser.add_argument("files", nargs="*", help="one or more experiment CSV paths; defaults to results/experiment*.csv")
    parser.add_argument("--output", type=Path, help="write the Markdown summary to a file instead of standard output")
    args = parser.parse_args()
    files = [Path(item) for item in args.files] if args.files else sorted((APP_DIR / "results").glob("experiment*.csv"))
    if not files:
        parser.error("找不到實驗 CSV；先完成試驗，或指定 results/*.csv")
    report = "\n\n".join(summarize(path) for path in files)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print("已輸出：{}".format(args.output))
    else:
        print(report)


if __name__ == "__main__":
    main()
