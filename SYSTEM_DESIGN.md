# Future-Ready System Design: Cricket Player Classification, Rating, and Team Selection

## 1) Goals
- Classify player role dynamically (`batter`, `bowler`, `allrounder`)
- Compute explainable ratings from multi-season history
- Recommend best XI given team composition constraints
- Enable future features (match context, opponent fit, injury risk, forecasted performance)

## 2) High-level architecture

1. Data ingestion layer
- Sources: historical scorecards, ball-by-ball feeds, fitness/injury feeds
- Interfaces: batch CSV/Parquet ingestion + streaming events (Kafka/PubSub)
- Validation: schema checks, anomaly detection, missing-value handling

2. Feature store
- Offline store for model training features
- Online store for low-latency inference
- Examples: batting form trend, bowling phase effectiveness, venue split, pressure-index performance

3. Role classifier service
- Baseline rules engine (current implementation)
- Future ML classifier (gradient boosting / shallow neural model)
- Output: role probabilities + confidence

4. Rating engine service
- Hybrid score architecture:
  - Rule-based weighted metrics (transparent)
  - ML forecast score (future expected contribution)
- Final rating = weighted blend of explainable score + forecast score
- Calibration pipeline ensures rating comparability across seasons/formats

5. Team selection optimizer
- Inputs: rating table, role constraints, budget/overseas constraints, captain strategy
- Solver: Integer Linear Programming (ILP) or CP-SAT
- Objective options:
  - maximize expected wins
  - maximize role balance + downside risk control
  - scenario-based objective (powerplay-heavy pitch, spin-friendly pitch)

6. Explainability + audit
- Per-player score card with feature contribution
- Why-selected / why-not-selected explanations
- Model and data lineage for each recommendation

7. API layer
- `POST /ratings/recompute`
- `GET /players/{id}/profile`
- `POST /team/select`
- `GET /team/explain/{request_id}`

8. UI/Workflow layer
- Analyst dashboard for weights, scenarios, and what-if simulation
- Selector UI for editing constraints and comparing squads

## 3) Data model extensions
- Player entity: handedness, bowling type, fitness status
- Match context: venue, opposition, pitch profile, phase splits
- Time-series snapshots: rolling form (last N matches), fatigue indicators
- Availability constraints: injuries, workload caps, rest windows

## 4) Team-selection when structure is provided
Given input structure, e.g.:
```json
{"batter": 4, "bowler": 3, "allrounder": 4}
```

Optimizer constraints:
- exact role counts
- optional min/max spin/pace mix
- optional batting depth threshold
- optional bowling economy ceiling

Output:
- selected XI ordered by expected impact
- alternates (bench) with confidence intervals
- explanation report for each decision

## 5) ML roadmap
- Phase 1: deterministic ratings + simple selector (implemented)
- Phase 2: train role probability and forecast contribution models
- Phase 3: optimization with simulation (Monte Carlo match outcomes)
- Phase 4: closed-loop learning using real match outcomes and drift monitoring

## 6) Production concerns
- Retraining cadence: weekly or post-series
- Drift monitoring: distribution shift in pitch/opponent conditions
- SLO: rating API p95 latency < 250ms, selector API p95 < 1.5s
- Reliability: cache latest ratings, fallback to deterministic rules engine
- Security: role-based access, audit logs for selection decisions

## 7) Suggested folder split for scale
- `ingestion/`
- `features/`
- `models/role_classifier/`
- `models/rating_forecast/`
- `optimization/`
- `services/api/`
- `monitoring/`

This keeps the current CLI tool as a fast baseline while allowing a path to enterprise-grade selection intelligence.
