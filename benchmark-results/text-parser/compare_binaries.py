import json
import os
from pathlib import Path
import statistics
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("baseline", type=Path)
parser.add_argument("candidate", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
binaries = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
ORDER = ["baseline", "candidate", "candidate", "baseline", "baseline", "candidate"]
results = []
for index, variant in enumerate(ORDER):
    run = OUT / "runs" / f"{index + 1}-{variant}"
    run.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CRITERION_HOME=str(run / "criterion"))
    command = [
        str(binaries[variant]), "--bench", "--warm-up-time", "1",
        "--measurement-time", "2", "--sample-size", "20", "--noplot",
    ]
    with (run / "console.log").open("w") as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    for estimates in sorted((run / "criterion").glob("**/new/estimates.json")):
        metadata = json.loads((estimates.parent / "benchmark.json").read_text())
        values = json.loads(estimates.read_text())
        results.append({"run": index + 1, "variant": variant, "id": metadata["full_id"],
                        "mean_ns": values["mean"]["point_estimate"],
                        "mean_ci": values["mean"]["confidence_interval"],
                        "median_ns": values["median"]["point_estimate"]})
    (OUT / "measurements.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"Finished {index + 1}/{len(ORDER)}: {variant}", flush=True)

summary = []
for name in sorted({r["id"] for r in results}):
    row = {"id": name}
    for variant in ["baseline", "candidate"]:
        times = [r["mean_ns"] for r in results if r["id"] == name and r["variant"] == variant]
        row[variant + "_ns"] = statistics.median(times)
        row[variant + "_runs_ns"] = times
    row["time_reduction_pct"] = 100 * (1 - row["candidate_ns"] / row["baseline_ns"])
    row["speedup"] = row["baseline_ns"] / row["candidate_ns"]
    summary.append(row)
(OUT / "benchmark-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
