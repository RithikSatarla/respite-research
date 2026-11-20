# Model card: Respite station-fault classifier (research model, not shipped)

## Decision

Not recommended for use: by the decision rule fixed before the test run, one of three training seeds was better than the shipped rules and two were worse, so the result depends on the seed; its probabilities are also poorly calibrated on a new recorder. On the external test set the trained model detected {{ test.point.model_303.recall | pct0 }} to {{ test.point.model_202.recall | pct0 }} of synthetic station faults across three training seeds, against {{ test.point.rules.recall | pct0 }} for Respite's shipped rules and {{ test.point.robust_z.recall | pct0 }} for a robust statistical baseline that needs no training. Better than the rules by the decision rule fixed before the test run: seed 101 {{ decision.detectors.model_101.better_than_rules | yesno }}; seed 202 {{ decision.detectors.model_202.better_than_rules | yesno }}; seed 303 {{ decision.detectors.model_303.better_than_rules | yesno }}.

## What it is

- **Task:** after each finished episode of one recording station, classify the episode as no fault or one of six fault categories (camera, recorder, timing, sync, missing stream); the station score is the mean fault probability over the last three episodes, and an alert is raised above a fixed threshold.
- **Inputs:** {{ training.draws.101.features_text }} ({{ training.draws.101.n_features | int }} inputs). "abs" is the episode's own measurement; "rel" is its change from the median of the station's first eight episodes. Missing measurements stay missing.
- **Not inputs:** the recorder's own `training_valid` flag, episode length, station or dataset identity.
- **Architectures selected** (one per training seed, by grouped cross-validation): seed 101 {{ training.draws.101.selected_text }}; seed 202 {{ training.draws.202.selected_text }}; seed 303 {{ training.draws.303.selected_text }}. Logistic regression was the other family tried.
- **Thresholds:** {{ training.draws.101.threshold | f2 }}, {{ training.draws.202.threshold | f2 }} and {{ training.draws.303.threshold | f2 }}, set from out-of-fold scores so that the alert rate on unmodified development recordings matched the shipped rules' ({{ training.target_alerts_per_100h | f0 }} per 100 station-hours).

## Training data

- One robotics team's YAM recordings, Station A and Station B (development set only), {{ data.dev.segments | int }} segments of 20 episodes.
- Labels come from synthetic faults written into those recordings: {{ training.draws.101.train_positive | int }} faulty episodes out of {{ training.draws.101.train_episodes | int }} for seed 101 (class counts: camera {{ training.draws.101.class_counts.camera | int }}, recorder {{ training.draws.101.class_counts.recorder | int }}, timing {{ training.draws.101.class_counts.timing | int }}, sync {{ training.draws.101.class_counts.sync | int }}, missing {{ training.draws.101.class_counts.missing | int }}). Real problems already present in the development recordings (for example Station B's slow cameras) are labelled "no fault" because nothing independent marks them.
- Training ran on {{ training.processor }} ({{ training.hardware }}); fit times {{ training.draws.101.fit_seconds | f1 }} s, {{ training.draws.202.fit_seconds | f1 }} s and {{ training.draws.303.fit_seconds | f1 }} s; peak Python memory during the final fit {{ training.draws.101.peak_python_alloc_mb | f1 }} MB (seed 101). No GPU.
- Artifacts: `experiments/results/models/model_draw{101,202,303}.joblib`, SHA-256 `{{ training.draws.101.artifact_sha256 }}`, `{{ training.draws.202.artifact_sha256 }}`, `{{ training.draws.303.artifact_sha256 }}`.

## Evaluation

| Seed | Out-of-fold recall (development) | Test recall (95% CI) | Test alerts per 100 h, unmodified | Brier (episodes) | ECE, 10 bins |
|---|---|---|---|---|---|
| 101 | {{ training.draws.101.oof_recall | f3 }} | {{ test.point.model_101.recall | pct0 }} ({{ test.ci95.model_101.recall | ci_pct0 }}) | {{ test.point.model_101.alerts_per_100h | f0 }} | {{ test.calibration.model_101.brier | f3 }} | {{ test.calibration.model_101.ece_10bin | f3 }} |
| 202 | {{ training.draws.202.oof_recall | f3 }} | {{ test.point.model_202.recall | pct0 }} ({{ test.ci95.model_202.recall | ci_pct0 }}) | {{ test.point.model_202.alerts_per_100h | f0 }} | {{ test.calibration.model_202.brier | f3 }} | {{ test.calibration.model_202.ece_10bin | f3 }} |
| 303 | {{ training.draws.303.oof_recall | f3 }} | {{ test.point.model_303.recall | pct0 }} ({{ test.ci95.model_303.recall | ci_pct0 }}) | {{ test.point.model_303.alerts_per_100h | f0 }} | {{ test.calibration.model_303.brier | f3 }} | {{ test.calibration.model_303.ece_10bin | f3 }} |

The gap between development and test is the main finding about this model: it learned the development recorder's 10 Hz values and per-row camera record, and the test recorder runs at 30 Hz with camera message times instead.

## Intended use and limits

Research only. All labels are synthetic. Two stations from one team trained it; it was tested on one other company's recorder. It must not be used to judge a station, and its probabilities are not calibrated across recorders.
