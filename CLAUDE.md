# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace purpose

This workspace has two areas:

1. **Document processing** — Korean-language educational course materials (`.docx` and `.pdf` files for weekly assignments; 주차 = week, 산출물 = deliverables).
2. **`prototype/`** — A Python multi-agent shared memory experiment framework that evaluates conflict detection and resolution strategies with an LLM-based Judge Agent (DeepSeek API).

## Prototype: multi-agent shared memory experiment

### Running

```bash
pip install -r prototype/requirements.txt   # openai>=1.0.0, numpy
python -m prototype.main
```

This runs 8 comparison groups × 3 conflict scenarios × 30 iterations (720 total runs), outputs a console results table, and exports two CSV files (detail + pivot) to `prototype/`.

### Architecture

The experiment compares 8 configurations for resolving shared-memory conflicts between three role-based agents (Planner, Executor, Reviewer). Each configuration toggles structural strategies (timestamp, trust score, leader), the LLM Judge Agent, and a structural pre-filter on/off.

**Data flow per iteration:**
1. `ScenarioGenerator` produces a workload with two agents writing conflicting values to the same memory key
2. Agent writes go through `SharedMemoryStore` (SQLite with WAL mode, two tables: `working_memory` and `long_term_memory`)
3. `ConflictResolver` orchestrates detection → structural pre-filter → Judge Agent → resolution
4. Results flow to `MetricsCollector`, then `print_results()` / `export_csv()`

**Key modules:**

| Module | Role |
|---|---|
| `prototype/agents/` | `BaseAgent` with read/write/trust-score tracking; `PlannerAgent`, `ExecutorAgent`, `ReviewerAgent` extend it. `JudgeAgent` calls DeepSeek API for semantic conflict judgment. |
| `prototype/memory/` | `SharedMemoryStore` — SQLite-backed store with versioned writes. `models.py` defines `MemoryEntry`, `ConflictRecord`, `WriteResult`, and enums. |
| `prototype/conflict/` | `ConflictDetector` detects visibility/ordering conflicts by comparing agent state versions. `ConflictResolver` orchestrates the 3-phase resolution pipeline (structural → Judge → fallback) and is configured by `ResolverConfig`. |
| `prototype/consistency/` | Three consistency models: `StrongConsistency` (lock-based), `EventualConsistency` (non-blocking, last-write-wins), `HierarchicalConsistency` (strong for working memory, eventual for long-term). |
| `prototype/strategies/` | Three structural resolution strategies: timestamp priority, trust-score priority, leader arbitration. |
| `prototype/experiments/` | `ExperimentRunner` main loop, `ScenarioGenerator` (3 scenario types), `build_groups()` (8 `ResolverConfig` presets), `MetricsCollector`, CSV reporter. |

**The 8 comparison groups** (defined in `prototype/experiments/groups.py`):
1. Baseline (last-write-wins only)
2. Strong consistency only
3. Timestamp priority
4. Trust score priority
5. Leader mediation
6. Ablation 1 — hierarchical + structural strategies, no Judge
7. Ablation 2 — hierarchical + all strategies + Judge, no pre-filter
8. Full proposed approach (all components enabled)

**The 3 conflict scenarios:**
- `simultaneous_write` — two agents write to the same key within a tight window (50ms)
- `ordering` — agent with stale version overwrites a newer value
- `semantic` — two agents produce contradictory natural-language conclusions (15 fixed contradictory pairs)

### Configuration

- `prototype/config.py` holds all constants: API key/base URL (DeepSeek), agent count/roles, DB path, iteration count, timing windows, trust score defaults.
- API key is read from the `DEEPSEEK_API_KEY` environment variable. If not set, replace `None` in `config.py` with your key string (do not commit it).
- The SQLite database is `experiment_results.db` in the workspace root.

### Dependencies

- `openai>=1.0.0` (used with DeepSeek's OpenAI-compatible endpoint)
- `numpy>=1.24.0`
- `python-docx` (for document processing scripts)

## Document processing

- Use `python-docx` for reading/writing `.docx` files.
- Use `python3 -c "import docx; ..."` for quick docx inspection.
- For PDF reading, use the Read tool directly (it supports PDF files).

## Environment

- Not a git repository.
- No build system, linter, or test suite.
- PowerShell is the default shell on this Windows machine.
- DeepSeek API is configured as the Anthropic model backend via `.claude/settings.json`.
