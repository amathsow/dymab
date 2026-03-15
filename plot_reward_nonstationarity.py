#!/usr/bin/env python3
"""
Plot per-heuristic reward time-series from reward_log.csv to visualise
piecewise non-stationarity during an ALNS run.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

WINDOW = 20          # rolling mean window for smoothing
CSV    = "reward_log.csv"
OUT    = "reward_nonstationarity.png"

COLORS = {
    "H_rand": "#1f77b4",
    "H_sync": "#ff7f0e",
    "H_entr": "#2ca02c",
}
LABELS = {
    "H_rand": r"$H_{\mathrm{rand}}$",
    "H_sync": r"$H_{\mathrm{sync}}$",
    "H_entr": r"$H_{\mathrm{entr}}$",
}

df = pd.read_csv(CSV)

fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
heuristics = ["H_rand", "H_sync", "H_entr"]

for ax, h in zip(axes, heuristics):
    sub = df[df["heuristic"] == h].copy().reset_index(drop=True)
    if sub.empty:
        ax.set_ylabel(LABELS[h], fontsize=11)
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color="grey")
        continue

    iters   = sub["iteration"].values
    rewards = sub["reward"].values

    # Raw scatter (faded)
    ax.scatter(iters, rewards, s=4, alpha=0.25, color=COLORS[h])

    # Rolling mean
    smooth = pd.Series(rewards).rolling(WINDOW, min_periods=1).mean().values
    ax.plot(iters, smooth, color=COLORS[h], linewidth=1.8,
            label=f"Rolling mean (w={WINDOW})")

    ax.axhline(0, color="black", linewidth=0.6, linestyle="--")
    ax.set_ylabel(f"Reward\n{LABELS[h]}", fontsize=11)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, linewidth=0.4, alpha=0.5)

axes[-1].set_xlabel("Iteration", fontsize=12)
fig.suptitle("Per-heuristic reward over time (piecewise non-stationarity)",
             fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT}")
