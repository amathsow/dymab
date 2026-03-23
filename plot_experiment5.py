#!/usr/bin/env python3
"""
Plot SOD vs Number of Agents for each map (Figure 4).
Layout: 3 maps top row (random, ost003d, dense), 2 maps bottom row (Berlin, NewCity/Linkoping).
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import os

# ── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = "/home/amath/Desktop/dymab"
OUT      = os.path.join(DATA_DIR, "figure4_sod_vs_agents.png")
DPI      = 300

MAPS = [
    ("random",   "Random"),
    ("ost003d",  "ost003d"),
    ("dense",    "dense"),
    ("Berlin",   "Berlin"),
    ("NewCity",  "Linköping"),
]

ALGO_STYLE = {
    "DyMAB-aUCB":        dict(color="#e41a1c", linestyle="-",  marker="o",  linewidth=2.0, label=r"DyMAB($\alpha$-UCB)"),
    "DyMAB-eGreedy":     dict(color="#ff7f00", linestyle="-",  marker="s",  linewidth=2.0, label=r"DyMAB($\epsilon$-Greedy)"),
    "MAPF-LNS2":         dict(color="#4daf4a", linestyle="--", marker="^",  linewidth=1.8, label="MAPF-LNS2"),
    "MAPF-LNS":          dict(color="#984ea3", linestyle="--", marker="D",  linewidth=1.8, label="MAPF-LNS"),
    "BALANCE-UCB1":      dict(color="#377eb8", linestyle=":",  marker="v",  linewidth=1.8, label="BALANCE-UCB1"),
    "BALANCE-Thompson":  dict(color="#a65628", linestyle=":",  marker="P",  linewidth=1.8, label="BALANCE-Thompson"),
}

# ── Load & aggregate ─────────────────────────────────────────────────────────
def load_map(name):
    path = os.path.join(DATA_DIR, f"{name}_sod_vs_agents.csv")
    df = pd.read_csv(path)
    # filter failed/segfault rows
    df = df[df["solved"] == 1].copy()
    return df

def aggregate(df):
    """Mean ± 95% CI of SOD per (num_agents, algorithm)."""
    grp = df.groupby(["num_agents", "algorithm"])["sod"]
    mean = grp.mean()
    ci   = 1.96 * grp.std() / np.sqrt(grp.count())
    return mean.reset_index(name="mean_sod"), ci.reset_index(name="ci_sod")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 9))
gs  = gridspec.GridSpec(
    2, 6,
    figure=fig,
    hspace=0.42,
    wspace=0.35,
)

# top row: 3 subplots spanning 2 cols each
# bottom row: 2 subplots centred (cols 1-2 and 3-4, 0-indexed)
axes = [
    fig.add_subplot(gs[0, 0:2]),   # random
    fig.add_subplot(gs[0, 2:4]),   # ost003d
    fig.add_subplot(gs[0, 4:6]),   # dense
    fig.add_subplot(gs[1, 1:3]),   # Berlin
    fig.add_subplot(gs[1, 3:5]),   # NewCity
]

handles_global = {}

for ax, (map_key, map_title) in zip(axes, MAPS):
    df = load_map(map_key)
    if df.empty:
        ax.set_title(map_title, fontsize=12, fontweight="bold")
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        continue

    mean_df, ci_df = aggregate(df)
    merged = mean_df.merge(ci_df, on=["num_agents", "algorithm"])

    algos_present = merged["algorithm"].unique()
    for algo in ALGO_STYLE:
        if algo not in algos_present:
            continue
        sub = merged[merged["algorithm"] == algo].sort_values("num_agents")
        style = ALGO_STYLE[algo]
        x   = sub["num_agents"].values
        y   = sub["mean_sod"].values
        err = sub["ci_sod"].values

        line, = ax.plot(
            x, y,
            color=style["color"],
            linestyle=style["linestyle"],
            marker=style["marker"],
            linewidth=style["linewidth"],
            markersize=5,
            label=style["label"],
        )
        ax.fill_between(x, y - err, y + err,
                        color=style["color"], alpha=0.12)

        if algo not in handles_global:
            handles_global[algo] = line

    ax.set_title(map_title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Number of agents", fontsize=10)
    ax.set_ylabel("Sum of Delays (SOD)", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    ax.set_xticks(sorted(df["num_agents"].unique()))
    ax.ticklabel_format(axis="y", style="sci", scilimits=(3, 3))

# ── Shared legend below the figure ──────────────────────────────────────────
ordered_keys = [k for k in ALGO_STYLE if k in handles_global]
handles = [handles_global[k] for k in ordered_keys]
labels  = [ALGO_STYLE[k]["label"] for k in ordered_keys]

fig.legend(
    handles, labels,
    loc="lower center",
    ncol=len(labels),
    fontsize=10,
    frameon=True,
    bbox_to_anchor=(0.5, -0.04),
)

fig.suptitle("Sum of Delays vs. Number of Agents", fontsize=14, fontweight="bold", y=1.01)

plt.savefig(OUT, dpi=DPI, bbox_inches="tight")
print(f"Saved: {OUT}")
