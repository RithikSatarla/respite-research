# Respite: Detecting Recording-Station Failures in Robot Training Data

Respite Labs · technical report · {{ meta.generated }} · source commit `{{ meta.source_commit }}`

## Abstract

Robot training data is recorded at stations: a robot, its cameras and a recorder. When one part of a station degrades, every episode it records can look normal on video while the relationships between streams are wrong. We asked whether a trained model detects such station faults better than Respite's existing rules on recording conditions it has not seen. Because no dataset here carries independent fault labels, we wrote six kinds of synthetic fault into real recordings with known onsets, trained and tuned on one team's recordings (two stations, {{ data.dev.episodes | int }} episodes), and tested once, after freezing every model and threshold, on {{ data.test.episodes | int }} episodes of XDOF ABC-130k, a dataset from another company and recorder.

On the external test set the shipped rules detected {{ test.point.rules.recall | pct0 }} of {{ test.point.rules.n_fault_trials | int }} injected faults (95% interval {{ test.ci95.rules.recall | ci_pct0 }}). A simple robust statistical detector with no training detected {{ test.point.robust_z.recall | pct0 }} ({{ test.ci95.robust_z.recall | ci_pct0 }}). The trained model, gradient-boosted trees selected by cross-validation, detected between {{ test.point.model_303.recall | pct0 }} and {{ test.point.model_202.recall | pct0 }} across three training seeds: it did not transfer to the new recorder. The rules missed whole fault types because they read measurements the test format does not carry, or none for that fault. On unmodified test recordings the robust detector raised more alerts than the rules ({{ test.point.robust_z.alerts_per_100h | f0 }} against {{ test.point.rules.alerts_per_100h | f0 }} per 100 station-hours); {{ test.unmodified_alerts.robust_z.documented | int }} of its {{ test.unmodified_alerts.robust_z.alerts | int }} such alerts line up with problems Respite had documented in that data before this study. On {{ hflow.n_original | int }} episodes run through both Respite and HFlow 0.2.22, an open-source data-quality tool, both tools' measurements caught every recorder pause and missing stream. At matched flag rates, HFlow's caught command-to-motion delays no more often than chance, against {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.timing_delay | pct0 }} for Respite's. That is exploratory, after a correction to how we scored HFlow's measurement names. All detection results are on synthetic faults; none is a production accuracy.

## 1. Problem

A recording station writes several streams: joint states, commanded joints, camera frames, and the recorder's own clock. Each stream can look healthy alone while their relationship is broken. A camera can deliver half the frames the recorder logs, so most rows carry an old image. A recorder can log fewer rows than it declares while a playback clock in the file hides the lost time. Arms can trail their commands by more than before. A camera's clock can drift against the recorder's. These faults usually come from one station and persist until someone fixes it, so every episode the station records in the meantime is affected.

Respite checks recordings for these relationships and points to the station. This study asks two product questions: should the station detector be a trained model, and what does Respite measure that an existing open-source data-quality tool, Hebbian Robotics' HFlow, does not.

## 2. Method

**Respite rules (shipped).** `respite live` judges each station after every finished episode from its last five episodes: a recorder rule (rows a second against the declared rate, from the median interval), a camera rule (new camera frames against rows, and rows whose frame is older than 150 ms), a delay rule (command-to-motion delay against the station's first episodes) and a motion rule. A problem must hold over three counted episodes before a warning.

**Rules, one episode at a time.** The same thresholds without the cross-episode logic: an ablation of Respite's own design.

**Robust z.** Fifteen measurements (recorder rate, interval spread, gaps, hidden time, camera freshness, frame age, camera message rate, dropped camera frames, camera offset, delay, dispatch offset, number of cameras, missing streams), each against the median and spread of the segment's first eight episodes, one-sided in the direction of a fault. Alert when the median score of the last three episodes passes a threshold; the category is the group of the measurement that moved most. No training.

**Trained model.** A per-episode classifier over the same measurements, their change from the segment's first eight episodes and missing-value flags; classes are "no fault" and the six categories. Station score: mean fault probability over the last three episodes. The recorder's validity flag and episode length are not inputs.

**Recorder's own flag.** The development recorder writes a per-row validity flag. A station counts as flagged when the median share of valid rows over its last three episodes is below half. It is a reference for the real-data replay (section 6.8), not a detector on the test set, whose format has no such flag.

**HFlow 0.2.22.** Hebbian Robotics' open-source data-quality SDK (Apache-2.0), installed from PyPI and run under WSL2. Sections 6.7 and 8.

## 3. Datasets

### Data

| Set | Source | Stations | Segments | Episodes | Role |
|---|---|---|---|---|---|
| Development | one robotics team's YAM recordings (owner not named; licence not recorded) | Station A, Station B | {{ data.dev.segments | int }} | {{ data.dev.episodes | int }} | training, selection, thresholds |
| External test | XDOF ABC-130k sample (Apache-2.0, gated download) | four recording streams used as proxy stations | {{ data.test.segments | int }} | {{ data.test.episodes | int }} | scored once |

Respite's shipped rules were tuned on the development set, so it is never used as test data. Each station's episodes are sorted by recording start and cut into 20-episode segments; a segment is the experimental unit. No episode is in both sets.

### Labels

There are no independent, human-checked labels of station faults in any dataset here. The development set's per-row `training_valid` flag is written by its own recorder. Earlier Respite findings on these datasets are Respite's own measurements. So every detection number comes from faults written into real recordings, where fault, onset and affected episodes are known by construction.

### Synthetic faults

| Fault | Category | What changes | Range |
|---|---|---|---|
| camera | camera | one camera delivers fewer new frames | 35% to 85% kept |
| recorder_rate | recorder | the recorder logs fewer rows than it claims | 50% to 95% of its rate |
| recorder_pause | recorder | the recorder stops logging inside episodes | 1 to 3 pauses, 0.3 to 3.0 s |
| timing_delay | timing | the arms trail their commands by more | 40 to 200 ms |
| sync_drift | sync | one camera's clock drifts against the recorder | 0.1 to 0.6 s by episode end |
| missing | missing | a camera stream or the action stream is absent | camera or action |

Each segment has one control trial and one trial per fault, starting at the same episode (between the 11th and 14th). Three in ten trials are intermittent. Development faults are applied in memory to the recorded episodes; test faults are written into copies of the MCAP files at the message level, so every tool reads identical bytes. The test set has {{ data.test.fault_trials | int }} fault trials and {{ data.test.control_trials | int }} control trials ({{ data.test.control_hours | f1 }} station-hours of unmodified recording).

## 4. Training

Two families were compared with 4-fold cross-validation grouped by station and week: logistic regression (C in 0.1, 1, 10) and histogram gradient-boosted trees (depth 3 or unlimited, 100 or 300 iterations). The winner was the configuration with the highest out-of-fold station-level recall at an alert rate matched to the rules' rate on development controls ({{ training.target_alerts_per_100h | f0 }} alert events per 100 station-hours). One model per development draw of synthetic faults (seeds 101, 202, 303).

| Draw | Selected | Out-of-fold recall (development) | Threshold | Training episodes | Fit time |
|---|---|---|---|---|---|
| 101 | {{ training.draws.101.selected_text }} | {{ training.draws.101.oof_recall | f3 }} | {{ training.draws.101.threshold | f2 }} | {{ training.draws.101.train_episodes | int }} | {{ training.draws.101.fit_seconds | f1 }} s |
| 202 | {{ training.draws.202.selected_text }} | {{ training.draws.202.oof_recall | f3 }} | {{ training.draws.202.threshold | f2 }} | {{ training.draws.202.train_episodes | int }} | {{ training.draws.202.fit_seconds | f1 }} s |
| 303 | {{ training.draws.303.selected_text }} | {{ training.draws.303.oof_recall | f3 }} | {{ training.draws.303.threshold | f2 }} | {{ training.draws.303.train_episodes | int }} | {{ training.draws.303.fit_seconds | f1 }} s |

Hardware: {{ training.processor }}; {{ training.hardware }}. Python {{ meta.python }}, scikit-learn {{ meta.sklearn }}. Model files are hashed in the freeze record. For comparison, logistic regression (C = 1) reached {{ training.draws.101.cv.1.oof_recall | f3 }} out-of-fold recall on draw 101, against {{ training.draws.101.oof_recall | f3 }} for the selected trees. The robust z threshold was set the same way, to {{ training.robust_z_threshold | f1 }}.

## 5. Experiments

The protocol, the split and the injection code were written down and hashed before any model was trained or any test result existed; the trained models and thresholds were hashed again before the test set was scored, and the test set was scored once. Three amendments were made before any test result existed (file-format fixes and the HFlow comparison design); they are listed in the protocol. Scoring follows it:

- **Detection.** An alert event is a step at which a detector goes from no alert to alert, or changes category. A fault counts as detected if an alert event comes at or after its first affected episode. A detector that was already alerting when the fault began and raises no new event misses it.
- **Alerts on unmodified recordings.** Alert events on control trials, per 100 station-hours. They are not called false alarms, because real recordings can hold real faults; precision still counts them as false.
- **Delay.** Recording time from the start of the first faulty episode to the end of the episode after which the alert came.
- **Diagnosis and attribution.** Among detected faults, whether the alert named the right category, strictly and by subsystem (camera and clock drift together; recorder; timing; missing). For attribution each fault trial is paired with the control trial of the next segment, standing in for a second station recording at the same time; it is correct when the first alert after onset is on the faulty station and the other station stays quiet.
- **Missing measurements.** Every detector rerun with the camera, timestamp, or action and state measurements removed.
- **Calibration** (model only). Brier score and 10-bin expected calibration error of the episode-level fault probability.
- **Uncertainty.** 95% percentile bootstrap over segments (2,000 resamples); differences between detectors are paired on the same resampled segments.
- **Thresholds.** The robust z and model thresholds were set on development data so that their rate of alert events on development controls matched the rules' rate there, then frozen.
- **Decision rule, fixed in advance.** A detector is better than the rules only if the paired 95% interval of its recall difference is above zero and its alert rate on unmodified recordings is not higher (point estimate, or a paired interval that includes zero).

## 6. Results on the external test set (synthetic faults)

### 6.1 Main comparison

| Detector | Detected | Recall (95% CI) | Alert events per 100 h on unmodified recordings (95% CI) | Precision | F1 | Median delay (min) |
|---|---|---|---|---|---|---|
| Respite rules (shipped) | {{ test.point.rules.detected | int }} / {{ test.point.rules.n_fault_trials | int }} | {{ test.point.rules.recall | pct0 }} ({{ test.ci95.rules.recall | ci_pct0 }}) | {{ test.point.rules.alerts_per_100h | f0 }} ({{ test.ci95.rules.alerts_per_100h | ci_f0 }}) | {{ test.point.rules.precision | f2 }} | {{ test.point.rules.f1 | f2 }} | {{ test.point.rules.median_delay_min | f1 }} |
| Rules, one episode at a time | {{ test.point.rules_per_episode.detected | int }} / {{ test.point.rules_per_episode.n_fault_trials | int }} | {{ test.point.rules_per_episode.recall | pct0 }} ({{ test.ci95.rules_per_episode.recall | ci_pct0 }}) | {{ test.point.rules_per_episode.alerts_per_100h | f0 }} ({{ test.ci95.rules_per_episode.alerts_per_100h | ci_f0 }}) | {{ test.point.rules_per_episode.precision | f2 }} | {{ test.point.rules_per_episode.f1 | f2 }} | {{ test.point.rules_per_episode.median_delay_min | f1 }} |
| Robust z | {{ test.point.robust_z.detected | int }} / {{ test.point.robust_z.n_fault_trials | int }} | {{ test.point.robust_z.recall | pct0 }} ({{ test.ci95.robust_z.recall | ci_pct0 }}) | {{ test.point.robust_z.alerts_per_100h | f0 }} ({{ test.ci95.robust_z.alerts_per_100h | ci_f0 }}) | {{ test.point.robust_z.precision | f2 }} | {{ test.point.robust_z.f1 | f2 }} | {{ test.point.robust_z.median_delay_min | f1 }} |
| Model, seed 101 | {{ test.point.model_101.detected | int }} / {{ test.point.model_101.n_fault_trials | int }} | {{ test.point.model_101.recall | pct0 }} ({{ test.ci95.model_101.recall | ci_pct0 }}) | {{ test.point.model_101.alerts_per_100h | f0 }} ({{ test.ci95.model_101.alerts_per_100h | ci_f0 }}) | {{ test.point.model_101.precision | f2 }} | {{ test.point.model_101.f1 | f2 }} | {{ test.point.model_101.median_delay_min | f1 }} |
| Model, seed 202 | {{ test.point.model_202.detected | int }} / {{ test.point.model_202.n_fault_trials | int }} | {{ test.point.model_202.recall | pct0 }} ({{ test.ci95.model_202.recall | ci_pct0 }}) | {{ test.point.model_202.alerts_per_100h | f0 }} ({{ test.ci95.model_202.alerts_per_100h | ci_f0 }}) | {{ test.point.model_202.precision | f2 }} | {{ test.point.model_202.f1 | f2 }} | {{ test.point.model_202.median_delay_min | f1 }} |
| Model, seed 303 | {{ test.point.model_303.detected | int }} / {{ test.point.model_303.n_fault_trials | int }} | {{ test.point.model_303.recall | pct0 }} ({{ test.ci95.model_303.recall | ci_pct0 }}) | {{ test.point.model_303.alerts_per_100h | f0 }} ({{ test.ci95.model_303.alerts_per_100h | ci_f0 }}) | {{ test.point.model_303.precision | f2 }} | {{ test.point.model_303.f1 | f2 }} | {{ test.point.model_303.median_delay_min | f1 }} |

Intervals are 95% bootstrap intervals over the {{ data.test.segments | int }} test segments. Delay is recording time from the start of the first faulty episode to the end of the episode after which the alert came. Precision counts alerts on unmodified recordings as false, which section 6.5 shows is too harsh.

Paired differences against the rules, on the same resampled segments:

| Comparison | Recall difference (95% CI) | Alert-rate difference per 100 h (95% CI) | Better than the rules by the fixed rule? |
|---|---|---|---|
| Robust z | {{ decision.detectors.robust_z.recall | pct0 }} vs {{ decision.detectors.robust_z.rules_recall | pct0 }} ({{ test.paired.robust_z_vs_rules.recall | ci_pp0 }}) | {{ test.paired.robust_z_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.robust_z.better_than_rules | yesno }} |
| Model, seed 101 | {{ decision.detectors.model_101.recall | pct0 }} vs {{ decision.detectors.model_101.rules_recall | pct0 }} ({{ test.paired.model_101_vs_rules.recall | ci_pp0 }}) | {{ test.paired.model_101_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.model_101.better_than_rules | yesno }} |
| Model, seed 202 | {{ decision.detectors.model_202.recall | pct0 }} vs {{ decision.detectors.model_202.rules_recall | pct0 }} ({{ test.paired.model_202_vs_rules.recall | ci_pp0 }}) | {{ test.paired.model_202_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.model_202.better_than_rules | yesno }} |
| Model, seed 303 | {{ decision.detectors.model_303.recall | pct0 }} vs {{ decision.detectors.model_303.rules_recall | pct0 }} ({{ test.paired.model_303_vs_rules.recall | ci_pp0 }}) | {{ test.paired.model_303_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.model_303.better_than_rules | yesno }} |

The fixed rule: better only if the recall difference interval is above zero and the alert rate on unmodified recordings is not higher (point estimate, or an interval that includes zero).

![Detection against alert rate](figures/test_recall_vs_alert_rate.png)

### 6.2 By fault type

| Fault | Rules | Rules, one episode | Robust z | Model 101 | Model 202 | Model 303 |
|---|---|---|---|---|---|---|
| Camera frames | {{ test.by_fault.rules.camera.detected | int }}/20 | {{ test.by_fault.rules_per_episode.camera.detected | int }}/20 | {{ test.by_fault.robust_z.camera.detected | int }}/20 | {{ test.by_fault.model_101.camera.detected | int }}/20 | {{ test.by_fault.model_202.camera.detected | int }}/20 | {{ test.by_fault.model_303.camera.detected | int }}/20 |
| Recorder rate | {{ test.by_fault.rules.recorder_rate.detected | int }}/20 | {{ test.by_fault.rules_per_episode.recorder_rate.detected | int }}/20 | {{ test.by_fault.robust_z.recorder_rate.detected | int }}/20 | {{ test.by_fault.model_101.recorder_rate.detected | int }}/20 | {{ test.by_fault.model_202.recorder_rate.detected | int }}/20 | {{ test.by_fault.model_303.recorder_rate.detected | int }}/20 |
| Recorder pause | {{ test.by_fault.rules.recorder_pause.detected | int }}/20 | {{ test.by_fault.rules_per_episode.recorder_pause.detected | int }}/20 | {{ test.by_fault.robust_z.recorder_pause.detected | int }}/20 | {{ test.by_fault.model_101.recorder_pause.detected | int }}/20 | {{ test.by_fault.model_202.recorder_pause.detected | int }}/20 | {{ test.by_fault.model_303.recorder_pause.detected | int }}/20 |
| Command-to-motion delay | {{ test.by_fault.rules.timing_delay.detected | int }}/20 | {{ test.by_fault.rules_per_episode.timing_delay.detected | int }}/20 | {{ test.by_fault.robust_z.timing_delay.detected | int }}/20 | {{ test.by_fault.model_101.timing_delay.detected | int }}/20 | {{ test.by_fault.model_202.timing_delay.detected | int }}/20 | {{ test.by_fault.model_303.timing_delay.detected | int }}/20 |
| Camera clock drift | {{ test.by_fault.rules.sync_drift.detected | int }}/20 | {{ test.by_fault.rules_per_episode.sync_drift.detected | int }}/20 | {{ test.by_fault.robust_z.sync_drift.detected | int }}/20 | {{ test.by_fault.model_101.sync_drift.detected | int }}/20 | {{ test.by_fault.model_202.sync_drift.detected | int }}/20 | {{ test.by_fault.model_303.sync_drift.detected | int }}/20 |
| Missing stream | {{ test.by_fault.rules.missing.detected | int }}/20 | {{ test.by_fault.rules_per_episode.missing.detected | int }}/20 | {{ test.by_fault.robust_z.missing.detected | int }}/20 | {{ test.by_fault.model_101.missing.detected | int }}/20 | {{ test.by_fault.model_202.missing.detected | int }}/20 | {{ test.by_fault.model_303.missing.detected | int }}/20 |

![By fault type](figures/test_by_fault.png)

### 6.3 Diagnosis and attribution

Among detected faults, the robust detector named the right subsystem in {{ test.point.robust_z.subsystem_category | pct0 }} of cases and the rules in {{ test.point.rules.subsystem_category | pct0 }}. When each faulty segment was paired with a healthy segment recorded at the same time, the first alert landed on the faulty station, with the healthy one quiet, in {{ test.attribution.robust_z.attributed_correctly | int }} of {{ test.attribution.robust_z.detected_in_pair_run | int }} detections for robust z and {{ test.attribution.rules.attributed_correctly | int }} of {{ test.attribution.rules.detected_in_pair_run | int }} for the rules. On faults both caught, the robust detector alerted earlier in {{ test.paired_delay.robust_z_vs_rules.detector_faster | int }} and later in {{ test.paired_delay.robust_z_vs_rules.rules_faster | int }} of {{ test.paired_delay.robust_z_vs_rules.n | int }} cases.

### 6.4 With measurements removed

| Removed | Rules recall | Robust z recall | Model 101 recall |
|---|---|---|---|
| nothing | {{ test.point.rules.recall | pct0 }} | {{ test.point.robust_z.recall | pct0 }} | {{ test.point.model_101.recall | pct0 }} |
| camera measurements | {{ test.ablations.camera.rules.recall | pct0 }} | {{ test.ablations.camera.robust_z.recall | pct0 }} | {{ test.ablations.camera.model_101.recall | pct0 }} |
| timestamp measurements | {{ test.ablations.timestamp.rules.recall | pct0 }} | {{ test.ablations.timestamp.robust_z.recall | pct0 }} | {{ test.ablations.timestamp.model_101.recall | pct0 }} |
| action and state measurements | {{ test.ablations.action_state.rules.recall | pct0 }} | {{ test.ablations.action_state.robust_z.recall | pct0 }} | {{ test.ablations.action_state.model_101.recall | pct0 }} |

### 6.5 Alerts on unmodified recordings (exploratory)

Control trials are real recordings, so an alert on one is not automatically false. After the results were in, every such alert was compared with the XDOF findings Respite documented before this study. For robust z, {{ test.unmodified_alerts.robust_z.documented | int }} of {{ test.unmodified_alerts.robust_z.alerts | int }} line up with documented problems (a week the recorder was overloaded, two evaluation episodes whose cameras dropped out for seconds, a step in command-to-motion delay, a day with three times the usual dropped frames); {{ test.unmodified_alerts.robust_z.no_documented_counterpart | int }} do not. The rules raised {{ test.unmodified_alerts.rules.alerts | int }} such alert, in the overloaded week. The earlier findings are Respite's own measurements, recomputed independently at the time; they are not independent labels.

### 6.6 Calibration

The model's per-episode fault probability on test episodes had a Brier score of {{ test.calibration.model_101.brier | f3 }} (seed 101), {{ test.calibration.model_202.brier | f3 }} (202) and {{ test.calibration.model_303.brier | f3 }} (303), with 10-bin expected calibration errors of {{ test.calibration.model_101.ece_10bin | f3 }}, {{ test.calibration.model_202.ece_10bin | f3 }} and {{ test.calibration.model_303.ece_10bin | f3 }}.

### 6.7 HFlow on the same files (episode level)

HFlow 0.2.22 re-encodes every video stream when it ingests a file and refuses files without video data, and most of the stored test files had been downloaded without video. So HFlow was compared on {{ hflow.n_original | int }} test episodes that kept their video, each as the original and with five of the faults written at the message level (the camera fault is left out: dropping frames from an H.264 stream breaks the stream instead of lowering its rate). Both tools read exactly the same files. HFlow ran its default duration and content-digest checks plus four opt-in checks, given the configuration a user must supply: timestamp regularity at the declared 30 Hz per stream (which also reports camera-to-arm start and end offsets), camera frame-rate conformance at 30 fps, the stream's required topics, and the action rate. Its checks that decode video were not run.

HFlow ships measurements and leaves the pass/fail decision to the user, so the same decision rules were applied to both tools' measurements. An episode is flagged when any measurement is more than 1.645 standard deviations from the mean of the original episodes (HFlow's documented cohort pattern; each original is compared with the other originals, each faulty file with all of them). Each tool's own fixed rules are reported separately. HFlow's fixed rules flag a camera frame rate that does not match nominal, or a required topic missing. Respite's flag its per-episode recorder rule (a rate below 95% of the declared rate) or a missing stream. This is an episode-level comparison of measurements. Respite's station logic, which needs a sequence of episodes, is not part of it.

**Pre-specified scoring.** Under the scoring fixed before any HFlow result existed, all {{ hflow.tools.hflow.originals_infinite_z | int }} untouched originals got an infinite score from HFlow's measurements. So the z rule flagged every file, faulty or not, and no threshold separated them. The cause was our scoring, not HFlow's measurements. HFlow names each camera's start and end offset after the stream it used as reference in that file, and that stream differs between files. So every file lacked names that other files carried, and the scoring counted each missing name as infinitely unusual. Under the same scoring, Respite's measurements flagged {{ hflow.tools.respite.flag_rate_originals_doc_z | pct0 }} of the originals and every faulty file.

**Amended scoring (post hoc, protocol amendment 4).** Each camera's offsets get one name, and an absent measurement counts as infinitely unusual only when at least 90% of the originals carry it. Both changes apply to both tools and change nothing for Respite's measurements. The tables below use this scoring, which was chosen after HFlow's results were seen. The fixed rules do not depend on the scoring.

| Fault | Respite, z rule | HFlow, z rule | Respite, fixed rules | HFlow, fixed rules |
|---|---|---|---|---|
| Recorder rate | {{ hflow.amended_tools.respite.recall_doc_z.recorder_rate | pct0 }} | {{ hflow.amended_tools.hflow.recall_doc_z.recorder_rate | pct0 }} | {{ hflow.amended_tools.respite.recall_fixed.recorder_rate | pct0 }} | {{ hflow.amended_tools.hflow.recall_fixed.recorder_rate | pct0 }} |
| Recorder pause | {{ hflow.amended_tools.respite.recall_doc_z.recorder_pause | pct0 }} | {{ hflow.amended_tools.hflow.recall_doc_z.recorder_pause | pct0 }} | {{ hflow.amended_tools.respite.recall_fixed.recorder_pause | pct0 }} | {{ hflow.amended_tools.hflow.recall_fixed.recorder_pause | pct0 }} |
| Command-to-motion delay | {{ hflow.amended_tools.respite.recall_doc_z.timing_delay | pct0 }} | {{ hflow.amended_tools.hflow.recall_doc_z.timing_delay | pct0 }} | {{ hflow.amended_tools.respite.recall_fixed.timing_delay | pct0 }} | {{ hflow.amended_tools.hflow.recall_fixed.timing_delay | pct0 }} |
| Camera clock drift | {{ hflow.amended_tools.respite.recall_doc_z.sync_drift | pct0 }} | {{ hflow.amended_tools.hflow.recall_doc_z.sync_drift | pct0 }} | {{ hflow.amended_tools.respite.recall_fixed.sync_drift | pct0 }} | {{ hflow.amended_tools.hflow.recall_fixed.sync_drift | pct0 }} |
| Missing stream | {{ hflow.amended_tools.respite.recall_doc_z.missing | pct0 }} | {{ hflow.amended_tools.hflow.recall_doc_z.missing | pct0 }} | {{ hflow.amended_tools.respite.recall_fixed.missing | pct0 }} | {{ hflow.amended_tools.hflow.recall_fixed.missing | pct0 }} |
| Originals flagged (no fault written) | {{ hflow.amended_tools.respite.flag_rate_originals_doc_z | pct0 }} | {{ hflow.amended_tools.hflow.flag_rate_originals_doc_z | pct0 }} | {{ hflow.amended_tools.respite.flag_rate_originals_fixed | pct0 }} | {{ hflow.amended_tools.hflow.flag_rate_originals_fixed | pct0 }} |

Shares of the {{ hflow.n_original | int }} files per row. At 1.645 standard deviations both tools flag many untouched originals, so the next table moves each tool's threshold until both flag the same number of originals. Each cell shows Respite / HFlow.

| Fault | 1 of 30 originals flagged | 2 of 30 | 3 of 30 | 6 of 30 |
|---|---|---|---|---|
| Recorder rate | {{ hflow.amended_tools.respite.matched_rate_sweep.1.recall.recorder_rate | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.1.recall.recorder_rate | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.recorder_rate | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.2.recall.recorder_rate | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.3.recall.recorder_rate | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.3.recall.recorder_rate | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.4.recall.recorder_rate | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.recorder_rate | pct0 }} |
| Recorder pause | {{ hflow.amended_tools.respite.matched_rate_sweep.1.recall.recorder_pause | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.1.recall.recorder_pause | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.recorder_pause | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.2.recall.recorder_pause | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.3.recall.recorder_pause | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.3.recall.recorder_pause | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.4.recall.recorder_pause | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.recorder_pause | pct0 }} |
| Command-to-motion delay | {{ hflow.amended_tools.respite.matched_rate_sweep.1.recall.timing_delay | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.1.recall.timing_delay | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.timing_delay | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.2.recall.timing_delay | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.3.recall.timing_delay | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.3.recall.timing_delay | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.4.recall.timing_delay | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.timing_delay | pct0 }} |
| Camera clock drift | {{ hflow.amended_tools.respite.matched_rate_sweep.1.recall.sync_drift | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.1.recall.sync_drift | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.sync_drift | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.2.recall.sync_drift | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.3.recall.sync_drift | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.3.recall.sync_drift | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.4.recall.sync_drift | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.sync_drift | pct0 }} |
| Missing stream | {{ hflow.amended_tools.respite.matched_rate_sweep.1.recall.missing | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.1.recall.missing | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.missing | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.2.recall.missing | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.3.recall.missing | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.3.recall.missing | pct0 }} | {{ hflow.amended_tools.respite.matched_rate_sweep.4.recall.missing | pct0 }} / {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.missing | pct0 }} |
| Untouched originals flagged (chance level) | {{ hflow.amended_tools.hflow.matched_rate_sweep.1.originals_flagged_share | pct0 }} | {{ hflow.amended_tools.hflow.matched_rate_sweep.2.originals_flagged_share | pct0 }} | {{ hflow.amended_tools.hflow.matched_rate_sweep.3.originals_flagged_share | pct0 }} | {{ hflow.amended_tools.hflow.matched_rate_sweep.4.originals_flagged_share | pct0 }} |

![Respite and HFlow measurements on the same episodes](figures/hflow_episode_level.png)

Both tools' measurements caught every recorder pause and every missing stream. The clear difference is command-to-motion delay. At matched flag rates, HFlow's measurements flagged {{ hflow.amended_tools.hflow.matched_rate_sweep.1.recall.timing_delay | pct0 }} to {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.timing_delay | pct0 }} of the delayed files, no more than the share of untouched originals flagged at the same threshold. Different measurements were behind each of those flags, so they are the chance rate, not a response to the delay. Respite's measurements flagged {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.timing_delay | pct0 }} of delayed files with two originals flagged. Recorder-rate drops went the other way at the lowest flag rates: HFlow flagged {{ hflow.amended_tools.hflow.matched_rate_sweep.2.recall.recorder_rate | pct0 }} against Respite's {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.recorder_rate | pct0 }} with two originals flagged. At six originals flagged it was {{ hflow.amended_tools.hflow.matched_rate_sweep.4.recall.recorder_rate | pct0 }} against {{ hflow.amended_tools.respite.matched_rate_sweep.4.recall.recorder_rate | pct0 }}. Camera clock drift was mixed. With 30 originals, a difference of one or two files is within chance.

HFlow's fixed rules caught every missing stream, because it was given the list of topics to expect, and nothing else. Respite's fixed rules caught {{ hflow.amended_tools.respite.missing_by_stream.action.fixed_flagged | int }} of the {{ hflow.amended_tools.respite.missing_by_stream.action.n | int }} removed action streams but only {{ hflow.amended_tools.respite.missing_by_stream.camera.fixed_flagged | int }} of the {{ hflow.amended_tools.respite.missing_by_stream.camera.n | int }} removed cameras, and that one came from an episode whose untouched original was flagged too. They also caught {{ hflow.amended_tools.respite.recall_fixed.recorder_rate | pct0 }} of recorder-rate drops and almost none of the other faults.

Respite's measurements took a median {{ hflow.amended_tools.respite.median_seconds_per_file | f1 }} s per file; HFlow took {{ hflow.amended_tools.hflow.median_seconds_per_file | f0 }} s. The jobs differ: HFlow also re-encodes the video and stores a transformed copy. The host disk filled during HFlow's first run, so 44 of its 180 runs were repeated with the same version and checks (`experiments/hflow/RUN_NOTES.md`).

### 6.8 Real recordings without injected faults (descriptive)

Every detector was replayed over the unmodified recordings of each station in recording order. Without labels this is description, not accuracy, and the team dataset is in-sample for the rules (tuned on it) and the model (trained on faults injected into it).

| Station | Hours | Rules: share of episodes in alert | Robust z | Model 101 | Recorder's own flag below 50% valid |
|---|---|---|---|---|---|
| Station A | {{ retrospective.team.station_a.hours | f1 }} | {{ retrospective.team.station_a.rules.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_a.robust_z.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_a.model_101.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_a.recorder_flag.share_of_episodes_in_alert | pct0 }} |
| Station B | {{ retrospective.team.station_b.hours | f1 }} | {{ retrospective.team.station_b.rules.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_b.robust_z.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_b.model_101.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_b.recorder_flag.share_of_episodes_in_alert | pct0 }} |

Station B's cameras delivered about half the frames its recorder logged from its first recorded episode (an earlier Respite finding). The rules, which compare each episode against fixed lines, were in alert for {{ retrospective.team.station_b.rules.share_of_episodes_in_alert | pct0 }} of its episodes, and the recorder's own validity flag marked most rows invalid in {{ retrospective.team.station_b.recorder_flag.share_of_episodes_in_alert | pct0 }}. The robust detector and the model compare a station with its own start, so a station that is broken from the beginning looks normal to them: robust z raised no camera alert on Station B, and the three models were in alert for at most {{ retrospective.team.station_b.model_303.share_of_episodes_in_alert | pct1 }} of its episodes. By day, over {{ retrospective.day_agreement.rules.days | int }} station-days of the team dataset, the rules were in alert on {{ retrospective.day_agreement.rules.both | int }} of the {{ retrospective.day_agreement.rules.flag_days | int }} days the recorder's flag marked most rows invalid (and on {{ retrospective.day_agreement.rules.detector_only | int }} other days); robust z on {{ retrospective.day_agreement.robust_z.both | int }}; model 101 on {{ retrospective.day_agreement.model_101.both | int }}. (Day agreement counts a station as alerting on every day an alert lasts; the first version of this script counted only the day an alert was raised, which hid persistent alerts, and was corrected before this report.)

On the external XDOF streams, the rules raised {{ retrospective.xdof.proxy_3.rules.alert_events | int }} alert events on the largest stream ({{ retrospective.xdof.proxy_3.hours | f1 }} h) and robust z {{ retrospective.xdof.proxy_3.robust_z.alert_events | int }}; section 6.5 compares such alerts with earlier documented findings.

## 7. Failure analysis

Why the shipped rules missed (test set, counts of fault trials):

- Camera faults: {{ test.failure.rules_misses.camera.absent_in_format | int }} of 20 missed because the rule reads new-frame counts, which need per-row frame sequence numbers. The test format logs camera message times instead, and the rules never look at camera message rate.
- Camera clock drift: {{ test.failure.rules_misses.sync_drift.absent_in_format | int }} of 20, for the same reason (the rule reads frame age, which the format does not carry).
- Recorder pauses and missing streams: {{ test.failure.rules_misses.recorder_pause.no_measurement | int }} and {{ test.failure.rules_misses.missing.no_measurement | int }} of 20. The rules have no measurement for either.
- Recorder rate: {{ test.failure.rules_misses.recorder_rate.median_rate_ok | int }} of 20. The rule estimates the rate from the median interval between rows, which stays at the declared rate until roughly a third of the rows are gone; moderate, irregular drops pass under it.
- Command-to-motion delay: {{ test.failure.rules_misses.timing_delay.below_margin | int }} of 20, smaller increases than the rule's 50 ms margin or not sustained over three episodes.

Why the trained model missed: on test episodes its mean fault probability stayed close to its value on unmodified episodes for camera, recorder and drift faults (seed 101: {{ test.failure.model.101.camera.mean_p_faulty | f3 }} on camera-fault episodes against {{ test.failure.model.101.control.mean_p_unaffected | f3 }} on unmodified ones; threshold {{ training.draws.101.threshold | f2 }}). It learned what faults look like at the development recorder's 10 Hz and with its per-row camera record; the test recorder runs at 30 Hz and carries different camera measurements. Only the faults that look alike in both formats, a missing stream and, for one seed, a delay, came through.

Where robust z struggled: delays were sometimes named as camera-clock drift, because writing state messages later also moves the camera-to-arm offset it measures; missing camera streams were caught less often than missing action streams; and it cannot flag a station that is broken from its first episode, because it compares a station with its own start (section 6.8).

## 8. What differs from HFlow, and the operator workflow

HFlow and Respite overlap more than either's description suggests. Both read MCAP recordings and measure the timing of each stream: HFlow's timestamp check reports gaps, intervals against a declared rate and camera start and end offsets, and its frame-rate check compares each camera's message rate with nominal. On the 30 files both could read, both tools' measurements caught every recorder pause and every missing stream, and HFlow's did better on recorder-rate drops at low flag rates (section 6.7).

The differences that matter for a vendor, with what this study could and could not test:

- **Command-to-motion delay.** Respite finds the time shift that best lays each arm's measured joints over its commanded path, which is how far motion trails commands. None of the sixteen checks in HFlow 0.2.22's `hflow/checks.py` compares a command stream with a state stream over time; the only timing it reports between streams is the camera start and end offsets (source read on 2026-11-19). On the delayed files, HFlow's measurements flagged no more than chance, and Respite's flagged {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.timing_delay | pct0 }} at the same flag rate (section 6.7).
- **Stations over time.** Respite judges a station across its consecutive episodes, against the station's own first episodes, with persistence before a warning and a cross-station check for delay, and points to the station. HFlow judges episodes. A failing check marked critical quarantines the episode, and its catalog can group episodes by task, operator and embodiment, but we found no reference to a recording station in its source. This study measured the value of Respite's station logic only against its own per-episode version (section 6.1); HFlow was not run over station sequences, because most stored test files lack the video it requires.
- **Per-row camera freshness.** Where a recorder logs each row's camera frame number or age, as the development recorder does, Respite measures how many rows carry a new frame and how old the frames are. The test format has no such record, so neither tool was compared on it.
- **What happens after an alert.** Respite writes a cleaned copy of the batch with a script that applies it. New in this study is a local incident ledger. `respite ops sync` opens one incident per new station alert. `show` prints the measurements behind it, and `ack` and `action` record who looked and what they changed on the station. `recheck` reruns the same checks on fresh episodes from that station, and `close` ends the incident. Everything stays in one file next to the station status file; Respite never sends commands to a robot. HFlow's re-run clears a quarantine tag when the check passes again, which is about the episode, not the station. The workflow is tested on synthetic batches only and has not been used by a station operator.

A pass does not prove much. When a recheck passes, Respite says that the recorder, cameras and arms logged in step on the episodes checked, and that this does not show every physical part of the station is safe or calibrated.

## 9. Reproducibility

Everything above is produced by scripts in Respite's repository from stored files: `experiments/PROTOCOL.md` (the frozen design and amendments), `experiments/splits/` (split and freeze hashes), `experiments/build_features.py`, `train_model.py`, `benchmark.py`, `decide.py`, `failure_analysis.py`, `adjudicate_controls.py`, `retrospective.py`, `hflow/`, and `export_site.py`, which writes the bundle this report is rendered from (SHA-256 in `data/MANIFEST.json`). The repository is private today; the result tables, per-trial outcomes and the public test dataset are linked from the Reproduce page. Measuring one test episode took a median of {{ test.cost.measurement.seconds_median | f2 }} s on the machine above. The frozen models give the same probabilities, to 12 decimal places, on all {{ model_versions.0.episodes | int }} test episodes under scikit-learn {{ model_versions.0.sklearn }} (the study's) and {{ model_versions.1.sklearn }} (`experiments/check_model_versions.py`), so a reader with either version gets the same model outputs.

## 10. Limitations

All detection numbers are on synthetic faults. There are no independent labels. The development set shaped the rules and the model. The test set is {{ data.test.segments | int }} segments from one company with bimanual YAM-style arms and no physical station field; intervals are wide. Frozen camera frames cannot be measured in the test format by any detector here. Nothing ran live. The HFlow comparison is episode-level, on 30 files, with decision rules we applied to its measurements, a check set chosen by us (its video checks were not run), and a scoring amended after its results were seen; someone who knows HFlow well could configure it better. Passing Respite's checks does not show a station is safe or calibrated.

## 11. Conclusion

**Is a trained model better than Respite's existing rules?** Not reliably. Of three training seeds, one met the decision rule fixed before the test run (seed 202: recall {{ test.point.model_202.recall | pct0 }} against {{ test.point.rules.recall | pct0 }}, no alerts on unmodified recordings) and two were worse than the rules (paired recall differences {{ test.paired.model_101_vs_rules.recall | ci_pp0 }} and {{ test.paired.model_303_vs_rules.recall | ci_pp0 }}). A model that is better or worse depending on its random seed, and whose probabilities are miscalibrated on a new recorder (expected calibration error {{ test.calibration.model_202.ece_10bin | f2 }} to {{ test.calibration.model_303.ece_10bin | f2 }}), should not replace the rules. The cause is clear from the failure analysis: with two development stations from one team, the model learned that recorder's format rather than the faults.

**What does improve detection?** Measurements, not learning. A robust per-station change detector over a wider set of measurements, with no training, detected {{ test.point.robust_z.recall | pct0 }} of the synthetic faults against the rules' {{ test.point.rules.recall | pct0 }} and alerted earlier on {{ test.paired_delay.robust_z_vs_rules.detector_faster | int }} of the {{ test.paired_delay.robust_z_vs_rules.n | int }} faults both caught. It met the decision rule, but only because the test set holds too few unmodified hours ({{ data.test.control_hours | f1 }}) to show that its higher alert rate ({{ test.point.robust_z.alerts_per_100h | f0 }} against {{ test.point.rules.alerts_per_100h | f0 }} per 100 station-hours) is real; most of those alerts line up with problems documented earlier, which suggests, without proving, that many are not false. And it cannot see a station that is broken from its first episode, which the rules can.

**What does Respite show that HFlow does not already provide?** Less than a feature list would suggest. On the same files, HFlow's timing and topic measurements caught recorder pauses and missing streams as well as Respite's, and recorder-rate drops better at low flag rates. Three things are Respite's alone in this comparison, and one was tested. First, the command-to-motion delay: HFlow 0.2.22 has no measurement of it, and on delayed files its measurements flagged no more than chance, while Respite's caught {{ hflow.amended_tools.respite.matched_rate_sweep.2.recall.timing_delay | pct0 }} at the same flag rate (exploratory). Second, judging a station over its episodes and pointing to it, which was not compared with HFlow. Third, the incident ledger from alert to recheck, which has only been tested on synthetic batches.

**Recommendation.** Keep the rules as the primary station check. Give them the measurements they lack for MCAP-style recorders (camera message rate, gaps and pauses, camera-to-arm offsets, stream presence), and run the robust change detector beside them as a second signal behind the same persistence. Do not ship the trained model. Before calling any of this an operator-reliability product, it needs what this study could not provide: a prospective run on live stations with operator-confirmed incidents.
