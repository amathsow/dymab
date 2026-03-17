#!/usr/bin/env python3
"""
Compute AUC from LaCAM* verbose output log.
Parses lines like:
  "Iteration N, group size = X, solution cost = C, remaining time = R"
and integrates the cost curve over [0, time_budget].
"""
import sys
import re

def compute_auc(log_file, time_budget=500.0):
    pattern = re.compile(
        r"solution cost = (\d+), remaining time = ([\d.]+)"
    )

    times  = []   # elapsed time (s)
    costs  = []   # solution cost at that point

    with open(log_file) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                cost      = int(m.group(1))
                remaining = float(m.group(2))
                elapsed   = time_budget - remaining
                times.append(elapsed)
                costs.append(cost)

    if not times:
        return None, None

    # Sort by elapsed time (should already be in order)
    pairs = sorted(zip(times, costs))
    times  = [p[0] for p in pairs]
    costs  = [p[1] for p in pairs]

    # AUC = area under step function from 0 to time_budget
    # Before first improvement: cost stays at initial value
    auc = 0.0
    prev_t    = 0.0
    prev_cost = costs[0]   # initial solution cost

    for t, c in zip(times, costs):
        auc += prev_cost * (t - prev_t)
        prev_t    = t
        prev_cost = c

    # Remaining time after last improvement
    auc += prev_cost * (time_budget - prev_t)

    final_cost = costs[-1]
    return int(auc), final_cost


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 compute_lacam2_auc.py <log_file> [time_budget]")
        sys.exit(1)

    log_file    = sys.argv[1]
    time_budget = float(sys.argv[2]) if len(sys.argv) > 2 else 500.0

    auc, final_cost = compute_auc(log_file, time_budget)
    if auc is None:
        print("NO_DATA,NO_DATA")
    else:
        print(f"{final_cost},{auc}")
