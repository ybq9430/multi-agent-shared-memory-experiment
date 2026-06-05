"""Console and CSV reporting for experiment results."""

import csv
import os
from datetime import datetime

from prototype.experiments.metrics import GroupSummary


def print_results(summaries: list[GroupSummary]):
    """Print results table to console."""
    scenarios = sorted(set(s.scenario for s in summaries))
    groups = sorted(set(s.group for s in summaries))

    print("\n" + "=" * 120)
    print("EXPERIMENT RESULTS")
    print("=" * 120)

    for scenario in scenarios:
        print(f"\n--- Scenario: {scenario} ---")
        print(f"{'Group':<30} {'Accuracy%':>10} {'Consist%':>10} {'Success%':>10} {'AvgLat(ms)':>12} {'LLMCalls':>10}")
        print("-" * 90)

        scenario_summaries = [s for s in summaries if s.scenario == scenario]
        scenario_summaries.sort(key=lambda s: s.group)

        for s in scenario_summaries:
            if s.iterations == 0:
                continue
            print(f"{s.group:<30} {s.accuracy:>10.1f} {s.consistency_rate:>10.1f} "
                  f"{s.task_success_rate:>10.1f} {s.avg_latency_ms:>12.2f} {s.total_llm_calls:>10}")

    # Overall ranking
    print(f"\n--- Overall (averaged across scenarios) ---")
    print(f"{'Group':<30} {'Accuracy%':>10} {'Consist%':>10} {'Success%':>10} {'AvgLat(ms)':>12}")
    print("-" * 80)

    overall = {}
    for s in summaries:
        if s.iterations == 0:
            continue
        if s.group not in overall:
            overall[s.group] = {"accuracy": [], "consistency": [], "success": [], "latency": []}
        overall[s.group]["accuracy"].append(s.accuracy)
        overall[s.group]["consistency"].append(s.consistency_rate)
        overall[s.group]["success"].append(s.task_success_rate)
        overall[s.group]["latency"].append(s.avg_latency_ms)

    for group in sorted(overall.keys()):
        d = overall[group]
        n = len(d["accuracy"])
        print(f"{group:<30} {sum(d['accuracy'])/n:>10.1f} {sum(d['consistency'])/n:>10.1f} "
              f"{sum(d['success'])/n:>10.1f} {sum(d['latency'])/n:>12.2f}")

    # Ablation study: delta comparison
    _print_ablation_delta(summaries)

    print("\n" + "=" * 120)


def _print_ablation_delta(summaries: list[GroupSummary]):
    """Print ablation study delta: Ablation1/2 vs FullProposed."""
    full = {s.scenario: s for s in summaries if s.group == "8_FullProposed"}
    abl1 = {s.scenario: s for s in summaries if s.group == "6_Ablation1_NoJudge"}
    abl2 = {s.scenario: s for s in summaries if s.group == "7_Ablation2_NoPreFilter"}

    if not full:
        return

    print(f"\n--- Ablation Study: Δ vs 8_FullProposed ---")
    print(f"{'Comparison':<45} {'Scenario':<22} {'ΔAcc%':>8} {'ΔConsist%':>10} {'ΔLat(ms)':>10} {'ΔLLM':>8}")
    print("-" * 110)

    for scenario in sorted(full.keys()):
        f = full[scenario]

        # Ablation1 (no Judge) vs FullProposed
        if scenario in abl1:
            a1 = abl1[scenario]
            print(f"{'6_Ablation1_NoJudge vs 8_FullProposed':<45} {scenario:<22} "
                  f"{a1.accuracy - f.accuracy:>+8.1f} {a1.consistency_rate - f.consistency_rate:>+10.1f} "
                  f"{a1.avg_latency_ms - f.avg_latency_ms:>+10.1f} {a1.total_llm_calls - f.total_llm_calls:>+8}")

        # Ablation2 (no pre-filter) vs FullProposed
        if scenario in abl2:
            a2 = abl2[scenario]
            print(f"{'7_Ablation2_NoPreFilter vs 8_FullProposed':<45} {scenario:<22} "
                  f"{a2.accuracy - f.accuracy:>+8.1f} {a2.consistency_rate - f.consistency_rate:>+10.1f} "
                  f"{a2.avg_latency_ms - f.avg_latency_ms:>+10.1f} {a2.total_llm_calls - f.total_llm_calls:>+8}")

    # Overall ablation delta
    print("-" * 110)
    for label, abl_map, abl_name in [
        ("6_Ablation1_NoJudge vs 8_FullProposed (overall)", abl1, "6_Ablation1_NoJudge"),
        ("7_Ablation2_NoPreFilter vs 8_FullProposed (overall)", abl2, "7_Ablation2_NoPreFilter"),
    ]:
        if not abl_map:
            continue
        scenarios = list(abl_map.keys())
        if not scenarios:
            continue
        d_acc = sum(abl_map[s].accuracy - full[s].accuracy for s in scenarios) / len(scenarios)
        d_con = sum(abl_map[s].consistency_rate - full[s].consistency_rate for s in scenarios) / len(scenarios)
        d_lat = sum(abl_map[s].avg_latency_ms - full[s].avg_latency_ms for s in scenarios) / len(scenarios)
        d_llm = sum(abl_map[s].total_llm_calls - full[s].total_llm_calls for s in scenarios)
        print(f"{label:<45} {'(avg across scenarios)':<22} "
              f"{d_acc:>+8.1f} {d_con:>+10.1f} {d_lat:>+10.1f} {d_llm:>+8}")


def export_csv(summaries: list[GroupSummary], output_dir: str = "."):
    """Export results to CSV files for thesis tables and figures."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Per-scenario detail
    detail_path = os.path.join(output_dir, f"experiment_detail_{timestamp}.csv")
    with open(detail_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Group", "Scenario", "Accuracy%", "ConsistencyRate%",
                         "TaskSuccessRate%", "AvgLatencyMs", "LLMCalls", "Iterations"])
        for s in sorted(summaries, key=lambda s: (s.group, s.scenario)):
            writer.writerow([s.group, s.scenario, f"{s.accuracy:.2f}",
                             f"{s.consistency_rate:.2f}", f"{s.task_success_rate:.2f}",
                             f"{s.avg_latency_ms:.2f}", s.total_llm_calls, s.iterations])

    # Summary pivot: groups × scenarios = accuracy
    pivot_path = os.path.join(output_dir, f"experiment_pivot_{timestamp}.csv")
    scenarios = sorted(set(s.scenario for s in summaries))
    groups = sorted(set(s.group for s in summaries))

    with open(pivot_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Group"] + scenarios + ["Overall_Accuracy", "Overall_Latency"])

        for group in groups:
            row = [group]
            accs = []
            lats = []
            for scenario in scenarios:
                match = [s for s in summaries if s.group == group and s.scenario == scenario]
                if match and match[0].iterations > 0:
                    row.append(f"{match[0].accuracy:.2f}")
                    accs.append(match[0].accuracy)
                    lats.append(match[0].avg_latency_ms)
                else:
                    row.append("N/A")
            row.append(f"{sum(accs)/len(accs):.2f}" if accs else "N/A")
            row.append(f"{sum(lats)/len(lats):.2f}" if lats else "N/A")
            writer.writerow(row)

    print(f"\nCSV exported to: {detail_path}")
    print(f"Pivot exported to: {pivot_path}")
