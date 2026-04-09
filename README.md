# DyMAB: Adaptive Neighbourhood Selection for MAPF via Non-Stationary Bandits

> **Accepted for publication in the [Journal of Artificial Intelligence Research (JAIR)](https://www.jair.org/), Special Track on MAPF.**

DyMAB is a novel anytime algorithm for Multi-Agent Path Finding (MAPF) that integrates a non-stationary Multi-Armed Bandit (MAB) framework into Adaptive Large Neighbourhood Search (ALNS). Using a sliding window of size *W* to track recent rewards, DyMAB efficiently adapts neighbourhood selection at each step, ensuring that the most effective destroy heuristic is used at the right time.

Two policies are implemented:
- **DyMAB(α-UCB)** — sliding-window upper confidence bound with logarithmic decay
- **DyMAB(ε-Greedy)** — sliding-window ε-greedy with logarithmic decay

The framework combines three orthogonal destroy heuristics:
- **H_rand** — random neighbourhood selection
- **H_sync** — synchronised random walk targeting delayed agents
- **H_entr** — entropy-guided walk targeting spatially congested regions

---

## Requirements

- C++17 compiler
- [`Boost 1.81.0`](https://www.boost.org/)
- [`Eigen 3.3`](https://eigen.tuxfamily.org/)
- [`CMake`](https://cmake.org)
- Python 3.10+ (for plotting scripts)

---

## Build

```bash
cmake -DCMAKE_BUILD_TYPE=RELEASE .
make -j$(nproc)
```

---

## Run DyMAB

MAPF instances from the [Moving AI Lab benchmark](https://movingai.com/benchmarks/mapf/index.html).

### DyMAB(α-UCB)
```bash
./dymab -m maps/Berlin/Berlin_1_256.map \
        -a maps/Berlin/Berlin_1_256.map-scen-random/Berlin_1_256-random-1.scen \
        -o output -k 500 -t 60 \
        --outputPaths=paths.txt \
        --banditAlgo=AlphaUCB \
        --neighborCandidateSizes=5 \
        --seed=0 \
        --alphaUCB=10000 \
        --decayWindow=100 \
        --lambdaDecay=10
```

### DyMAB(ε-Greedy)
```bash
./dymab -m maps/Berlin/Berlin_1_256.map \
        -a maps/Berlin/Berlin_1_256.map-scen-random/Berlin_1_256-random-1.scen \
        -o output -k 500 -t 60 \
        --outputPaths=paths.txt \
        --banditAlgo=EpsilonGreedy \
        --neighborCandidateSizes=5 \
        --seed=0 \
        --initialEpsilon=0.5 \
        --decayWindow=100 \
        --lambdaDecay=0.01
```

### Key parameters

| Parameter              | Description                                                        |
| :--------------------- | :----------------------------------------------------------------- |
| `-m`                   | Map file (`.map` format from Moving AI benchmark)                  |
| `-a`                   | Scenario file (`.scen`)                                            |
| `-o`                   | Output file prefix                                                 |
| `-k`                   | Number of agents                                                   |
| `-t`                   | Time budget (seconds)                                              |
| `--outputPaths`        | File to write solution paths                                       |
| `--banditAlgo`         | Policy: `AlphaUCB`, `EpsilonGreedy`, or `Random`                  |
| `--neighborCandidateSizes` | Number of neighbourhood size candidates (default: 5)          |
| `--seed`               | Random seed                                                        |
| `--alphaUCB`           | Exploration parameter α for DyMAB(α-UCB) (default: 10000)         |
| `--initialEpsilon`     | Initial ε for DyMAB(ε-Greedy) (default: 0.5)                      |
| `--decayWindow`        | Sliding window size W (default: 100)                               |
| `--lambdaDecay`        | Decay rate λ (default: 10 for α-UCB, 0.01 for ε-Greedy)           |

---

---

## Credits

DyMAB builds on and extends:
- [BALANCE](https://github.com/thomyphan/anytime-mapf) — T. Phan et al., AAAI 2024
- [MAPF-LNS2](https://github.com/Jiaoyang-Li/MAPF-LNS2) — J. Li et al., AAAI 2022
- [MAPF-LNS](https://github.com/Jiaoyang-Li/MAPF-LNS) — J. Li et al., IJCAI 2021

DyMAB is released under the MIT License. See `LICENSE` for details.

---

## References

- [1] A. Sow et al. *"Adaptive Neighbourhood Selection for MAPF via Non-Stationary Bandits"*. **Journal of Artificial Intelligence Research (JAIR)**, accepted 2025.
- [2] T. Phan et al. *"Adaptive Anytime Multi-Agent Path Finding using Bandit-Based Large Neighborhood Search"*. AAAI 2024.
- [3] J. Li et al. *"MAPF-LNS2: Fast Repairing for Multi-Agent Path Finding via Large Neighborhood Search"*. AAAI 2022.
- [4] J. Li et al. *"MAPF-LNS: Anytime Multi-Agent Path Finding via Large Neighborhood Search"*. IJCAI 2021.
- [5] A. Gravier et al. *"On Upper-Confidence Bound Policies for Non-Stationary Bandit Problems"*. HAL 2008.
