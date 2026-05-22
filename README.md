# Multi-Agent Shared Memory Experiment

멀티 에이전트 공유 메모리 시스템에서의 계층형 일관성 모델 및 충돌 해소 메커니즘 설계 — 프로토타입 구현 및 실험 코드

## Overview

본 저장소는 석사논문 *"멀티 에이전트 공유 메모리 시스템에서의 계층형 일관성 모델 및 충돌 해소 메커니즘 설계"* 의 프로토타입 구현과 실험 코드를 포함합니다.

3개 역할 기반 에이전트(Planner, Executor, Reviewer)가 공유 메모리에 접근할 때 발생하는 가시성 충돌, 순서성 충돌, 의미적 충돌을 탐지·해소하는 8가지 비교군을 3가지 시나리오에서 평가합니다.

## Requirements

```bash
pip install -r prototype/requirements.txt
```

- Python 3.12+
- openai >= 1.0.0
- numpy >= 1.24.0

## Configuration

DeepSeek API 키를 환경 변수로 설정해야 합니다:

```bash
# Windows (PowerShell)
$env:DEEPSEEK_API_KEY = "your-api-key"

# Linux / macOS
export DEEPSEEK_API_KEY="your-api-key"
```

또는 `prototype/config.py`의 `API_KEY = None` 을 직접 키 문자열로 교체할 수 있습니다.

기타 설정(`AGENT_COUNT`, `ITERATIONS`, `RANDOM_SEED` 등)은 `prototype/config.py`에서 변경 가능합니다.

## Run

```bash
python -m prototype.main
```

실행 결과:
- 콘솔에 8개 비교군 × 3개 시나리오의 정확도, 일관성 유지율, 지연시간 출력
- `prototype/` 디렉토리에 CSV 파일 2종(상세 결과 + 피벗) 자동 저장

## Architecture

```
prototype/
├── main.py              # Entry point
├── config.py            # Experiment parameters
├── agents/              # Agent implementations
│   ├── base.py          # BaseAgent (read/write/trust tracking)
│   ├── roles.py         # Planner, Executor, Reviewer agents
│   └── judge.py         # LLM-based Judge Agent (DeepSeek API)
├── memory/              # Shared memory storage
│   ├── models.py        # Data models (MemoryEntry, ConflictRecord, etc.)
│   └── store.py         # SQLite-backed SharedMemoryStore
├── conflict/            # Conflict detection & resolution
│   ├── detector.py      # Structural conflict detection
│   └── resolver.py      # 3-phase resolution pipeline
├── consistency/         # Consistency models
│   ├── strong.py        # Lock-based strong consistency
│   ├── eventual.py      # Non-blocking eventual consistency
│   └── hierarchical.py  # Two-tier hierarchical consistency
├── strategies/          # Resolution strategies
│   ├── timestamp.py     # Timestamp priority
│   ├── trust_score.py   # Trust score priority
│   └── leader.py        # Leader agent mediation
└── experiments/         # Experiment framework
    ├── runner.py        # Main experiment loop
    ├── groups.py        # 8 comparison group configs
    ├── scenarios.py     # 3 conflict scenario generators
    ├── metrics.py       # Metrics collection
    └── reporter.py      # Console + CSV output
```

## Experiment Design

### 8 Comparison Groups

| Group | Detection | Strategies | Judge Agent | Pre-filter | Consistency |
|-------|-----------|------------|-------------|------------|--------------|
| 1. Baseline | ✗ | ✗ | ✗ | ✗ | none |
| 2. StrongOnly | ✓ | ✗ | ✗ | ✗ | strong |
| 3. TimestampPriority | ✓ | timestamp | ✗ | ✓ | none |
| 4. TrustScorePriority | ✓ | trust score | ✗ | ✓ | none |
| 5. LeaderMediation | ✓ | leader | ✗ | ✓ | none |
| 6. Ablation1 (NoJudge) | ✓ | all structural | ✗ | ✓ | hierarchical |
| 7. Ablation2 (NoPreFilter) | ✓ | all structural | ✓ | ✗ | hierarchical |
| 8. FullProposed | ✓ | all structural | ✓ | ✓ | hierarchical |

### 3 Conflict Scenarios

- **Simultaneous Write**: two agents write to the same key within 50ms window
- **Ordering Conflict**: agent with stale version overwrites newer value
- **Semantic Conflict**: two agents produce contradictory natural-language conclusions (15 fixed pairs)

### Metrics

- Accuracy (%)
- Memory Consistency Rate (%)
- Task Success Rate (%)
- Average Latency (ms)

## Key Results

| Group | Accuracy | Consistency | Avg Latency |
|-------|----------|-------------|-------------|
| 1. Baseline | 71.1% | 0.0% | 4.4ms |
| 8. FullProposed | 93.3% | 100.0% | 478.7ms |

FullProposed achieved 22.2%p accuracy improvement over Baseline while maintaining 100% memory consistency. Judge Agent groups scored 80.0% on semantic conflicts. Structural pre-filtering reduced LLM calls by 3× (30 vs 90) and latency by 3.1× compared to no-filter configuration.

## License

MIT
