# Respite: Detecting Recording-Station Failures in Robot Training Data

Respite Labs · technical report · {{ meta.generated }} · source commit `{{ meta.source_commit }}`

## Abstract

Robot training data is recorded at stations: a robot, its cameras and a recorder. When one part of a station degrades, every episode it records can look normal on video while the relationships between streams are wrong. We asked whether a trained model detects such station faults better than Respite's existing rules on recording conditions it has not seen. Because no dataset here carries independent fault labels, we wrote six kinds of synthetic fault into real recordings with known onsets, trained and tuned on one team's recordings (two stations, {{ data.dev.episodes | int }} episodes), and tested once, after freezing every model and threshold, on {{ data.test.episodes | int }} episodes of XDOF ABC-130k, a dataset from another company and recorder.

On the external test set the shipped rules detected {{ test.point.rules.recall | pct0 }} of {{ test.point.rules.n_fault_trials | int }} injected faults (95% interval {{ test.ci95.rules.recall | ci_pct0 }}). A simple robust statistical detector with no training detected {{ test.point.robust_z.recall | pct0 }} ({{ test.ci95.robust_z.recall | ci_pct0 }}). The trained model, gradient-boosted trees selected by cross-validation, detected between {{ test.point.model_303.recall | pct0 }} and {{ test.point.model_202.recall | pct0 }} across three training seeds: it did not transfer to the new recorder. The rules missed whole fault types because they read measurements the test format does not carry, or none for that fault. On unmodified test recordings the robust detector raised more alerts than the rules ({{ test.point.robust_z.alerts_per_100h | f0 }} against {{ test.point.rules.alerts_per_100h | f0 }} per 100 station-hours); {{ test.unmodified_alerts.robust_z.documented | int }} of its {{ test.unmodified_alerts.robust_z.alerts | int }} such alerts line up with problems Respite had documented in that data before this study. All detection results are on synthetic faults; none is a production accuracy.

## 1. Problem

A recording station writes several streams: joint states, commanded joints, camera frames, and the recorder's own clock. Each stream can look healthy alone while their relationship is broken. A camera can deliver half the frames the recorder logs, so most rows carry an old image. A recorder can log fewer rows than it declares while a playback clock in the file hides the lost time. Arms can trail their commands by more than before. A camera's clock can drift against the recorder's. These faults usually come from one station and persist until someone fixes it, so every episode the station records in the meantime is affected.

Respite checks recordings for these relationships and points to the station. This study asks two product questions: should the station detector be a trained model, and what does Respite measure that an existing open-source data-quality tool, Hebbian Robotics' HFlow, does not.

## 2. Design

The protocol, the split and the injection code were written down and hashed before any model was trained or any test result existed; the trained models and thresholds were hashed again before the test set was scored. Three amendments were made before any test result existed (file-format fixes and the HFlow comparison design); they are listed in the protocol.

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

## 3. Methods

**Respite rules (shipped).** `respite live` judges each station after every finished episode from its last five episodes: a recorder rule (rows a second against the declared rate, from the median interval), a camera rule (new camera frames against rows, and rows whose frame is older than 150 ms), a delay rule (command-to-motion delay against the station's first episodes) and a motion rule. A problem must hold over three counted episodes before a warning.

**Rules, one episode at a time.** The same thresholds without the cross-episode logic: an ablation of Respite's own design.

**Robust z.** Fifteen measurements (recorder rate, interval spread, gaps, hidden time, camera freshness, frame age, camera message rate, dropped camera frames, camera offset, delay, dispatch offset, number of cameras, missing streams), each against the median and spread of the segment's first eight episodes, one-sided in the direction of a fault. Alert when the median score of the last three episodes passes a threshold; the category is the group of the measurement that moved most. No training.

**Trained model.** A per-episode classifier over the same measurements, their change from the segment's first eight episodes and missing-value flags; classes are "no fault" and the six categories. Station score: mean fault probability over the last three episodes. The recorder's validity flag and episode length are not inputs.

**HFlow 0.2.22.** Hebbian Robotics' open-source data-quality SDK (Apache-2.0), installed from PyPI and run under WSL2. Section 7.6.

## 4. Training

Two families were compared with 4-fold cross-validation grouped by station and week: logistic regression (C in 0.1, 1, 10) and histogram gradient-boosted trees (depth 3 or unlimited, 100 or 300 iterations). The winner was the configuration with the highest out-of-fold station-level recall at an alert rate matched to the rules' rate on development controls ({{ training.target_alerts_per_100h | f0 }} alert events per 100 station-hours). One model per development draw of synthetic faults (seeds 101, 202, 303).

| Draw | Selected | Out-of-fold recall (development) | Threshold | Training episodes | Fit time |
|---|---|---|---|---|---|
| 101 | {{ training.draws.101.selected_text }} | {{ training.draws.101.oof_recall | f3 }} | {{ training.draws.101.threshold | f2 }} | {{ training.draws.101.train_episodes | int }} | {{ training.draws.101.fit_seconds | f1 }} s |
| 202 | {{ training.draws.202.selected_text }} | {{ training.draws.202.oof_recall | f3 }} | {{ training.draws.202.threshold | f2 }} | {{ training.draws.202.train_episodes | int }} | {{ training.draws.202.fit_seconds | f1 }} s |
| 303 | {{ training.draws.303.selected_text }} | {{ training.draws.303.oof_recall | f3 }} | {{ training.draws.303.threshold | f2 }} | {{ training.draws.303.train_episodes | int }} | {{ training.draws.303.fit_seconds | f1 }} s |

Hardware: {{ training.processor }}; {{ training.hardware }}. Python {{ meta.python }}, scikit-learn {{ meta.sklearn }}. Model files are hashed in the freeze record. For comparison, logistic regression (C = 1) reached {{ training.draws.101.cv.1.oof_recall | f3 }} out-of-fold recall on draw 101, against {{ training.draws.101.oof_recall | f3 }} for the selected trees. The robust z threshold was set the same way, to {{ training.robust_z_threshold | f1 }}.

## 5. Results on the external test set (synthetic faults)

### 5.1 Main comparison

| Detector | Detected | Recall (95% CI) | Alert events per 100 h on unmodified recordings (95% CI) | Precision | F1 | Median delay (min) |
|---|---|---|---|---|---|---|
| Respite rules (shipped) | {{ test.point.rules.detected | int }} / {{ test.point.rules.n_fault_trials | int }} | {{ test.point.rules.recall | pct0 }} ({{ test.ci95.rules.recall | ci_pct0 }}) | {{ test.point.rules.alerts_per_100h | f0 }} ({{ test.ci95.rules.alerts_per_100h | ci_f0 }}) | {{ test.point.rules.precision | f2 }} | {{ test.point.rules.f1 | f2 }} | {{ test.point.rules.median_delay_min | f1 }} |
| Rules, one episode at a time | {{ test.point.rules_per_episode.detected | int }} / {{ test.point.rules_per_episode.n_fault_trials | int }} | {{ test.point.rules_per_episode.recall | pct0 }} ({{ test.ci95.rules_per_episode.recall | ci_pct0 }}) | {{ test.point.rules_per_episode.alerts_per_100h | f0 }} ({{ test.ci95.rules_per_episode.alerts_per_100h | ci_f0 }}) | {{ test.point.rules_per_episode.precision | f2 }} | {{ test.point.rules_per_episode.f1 | f2 }} | {{ test.point.rules_per_episode.median_delay_min | f1 }} |
| Robust z | {{ test.point.robust_z.detected | int }} / {{ test.point.robust_z.n_fault_trials | int }} | {{ test.point.robust_z.recall | pct0 }} ({{ test.ci95.robust_z.recall | ci_pct0 }}) | {{ test.point.robust_z.alerts_per_100h | f0 }} ({{ test.ci95.robust_z.alerts_per_100h | ci_f0 }}) | {{ test.point.robust_z.precision | f2 }} | {{ test.point.robust_z.f1 | f2 }} | {{ test.point.robust_z.median_delay_min | f1 }} |
| Model, seed 101 | {{ test.point.model_101.detected | int }} / {{ test.point.model_101.n_fault_trials | int }} | {{ test.point.model_101.recall | pct0 }} ({{ test.ci95.model_101.recall | ci_pct0 }}) | {{ test.point.model_101.alerts_per_100h | f0 }} ({{ test.ci95.model_101.alerts_per_100h | ci_f0 }}) | {{ test.point.model_101.precision | f2 }} | {{ test.point.model_101.f1 | f2 }} | {{ test.point.model_101.median_delay_min | f1 }} |
| Model, seed 202 | {{ test.point.model_202.detected | int }} / {{ test.point.model_202.n_fault_trials | int }} | {{ test.point.model_202.recall | pct0 }} ({{ test.ci95.model_202.recall | ci_pct0 }}) | {{ test.point.model_202.alerts_per_100h | f0 }} ({{ test.ci95.model_202.alerts_per_100h | ci_f0 }}) | {{ test.point.model_202.precision | f2 }} | {{ test.point.model_202.f1 | f2 }} | {{ test.point.model_202.median_delay_min | f1 }} |
| Model, seed 303 | {{ test.point.model_303.detected | int }} / {{ test.point.model_303.n_fault_trials | int }} | {{ test.point.model_303.recall | pct0 }} ({{ test.ci95.model_303.recall | ci_pct0 }}) | {{ test.point.model_303.alerts_per_100h | f0 }} ({{ test.ci95.model_303.alerts_per_100h | ci_f0 }}) | {{ test.point.model_303.precision | f2 }} | {{ test.point.model_303.f1 | f2 }} | {{ test.point.model_303.median_delay_min | f1 }} |

Intervals are 95% bootstrap intervals over the {{ data.test.segments | int }} test segments. Delay is recording time from the start of the first faulty episode to the end of the episode after which the alert came. Precision counts alerts on unmodified recordings as false, which section 5.5 shows is too harsh.

Paired differences against the rules, on the same resampled segments:

| Comparison | Recall difference (95% CI) | Alert-rate difference per 100 h (95% CI) | Better than the rules by the fixed rule? |
|---|---|---|---|
| Robust z | {{ decision.detectors.robust_z.recall | pct0 }} vs {{ decision.detectors.robust_z.rules_recall | pct0 }} ({{ test.paired.robust_z_vs_rules.recall | ci_pp0 }}) | {{ test.paired.robust_z_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.robust_z.better_than_rules | yesno }} |
| Model, seed 101 | {{ decision.detectors.model_101.recall | pct0 }} vs {{ decision.detectors.model_101.rules_recall | pct0 }} ({{ test.paired.model_101_vs_rules.recall | ci_pp0 }}) | {{ test.paired.model_101_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.model_101.better_than_rules | yesno }} |
| Model, seed 202 | {{ decision.detectors.model_202.recall | pct0 }} vs {{ decision.detectors.model_202.rules_recall | pct0 }} ({{ test.paired.model_202_vs_rules.recall | ci_pp0 }}) | {{ test.paired.model_202_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.model_202.better_than_rules | yesno }} |
| Model, seed 303 | {{ decision.detectors.model_303.recall | pct0 }} vs {{ decision.detectors.model_303.rules_recall | pct0 }} ({{ test.paired.model_303_vs_rules.recall | ci_pp0 }}) | {{ test.paired.model_303_vs_rules.alerts_per_100h | ci_f0 }} | {{ decision.detectors.model_303.better_than_rules | yesno }} |

The fixed rule: better only if the recall difference interval is above zero and the alert rate on unmodified recordings is not higher (point estimate, or an interval that includes zero).

![Detection against alert rate](figures/test_recall_vs_alert_rate.png)

### 5.2 By fault type

| Fault | Rules | Rules, one episode | Robust z | Model 101 | Model 202 | Model 303 |
|---|---|---|---|---|---|---|
| Camera frames | {{ test.by_fault.rules.camera.detected | int }}/20 | {{ test.by_fault.rules_per_episode.camera.detected | int }}/20 | {{ test.by_fault.robust_z.camera.detected | int }}/20 | {{ test.by_fault.model_101.camera.detected | int }}/20 | {{ test.by_fault.model_202.camera.detected | int }}/20 | {{ test.by_fault.model_303.camera.detected | int }}/20 |
| Recorder rate | {{ test.by_fault.rules.recorder_rate.detected | int }}/20 | {{ test.by_fault.rules_per_episode.recorder_rate.detected | int }}/20 | {{ test.by_fault.robust_z.recorder_rate.detected | int }}/20 | {{ test.by_fault.model_101.recorder_rate.detected | int }}/20 | {{ test.by_fault.model_202.recorder_rate.detected | int }}/20 | {{ test.by_fault.model_303.recorder_rate.detected | int }}/20 |
| Recorder pause | {{ test.by_fault.rules.recorder_pause.detected | int }}/20 | {{ test.by_fault.rules_per_episode.recorder_pause.detected | int }}/20 | {{ test.by_fault.robust_z.recorder_pause.detected | int }}/20 | {{ test.by_fault.model_101.recorder_pause.detected | int }}/20 | {{ test.by_fault.model_202.recorder_pause.detected | int }}/20 | {{ test.by_fault.model_303.recorder_pause.detected | int }}/20 |
| Command-to-motion delay | {{ test.by_fault.rules.timing_delay.detected | int }}/20 | {{ test.by_fault.rules_per_episode.timing_delay.detected | int }}/20 | {{ test.by_fault.robust_z.timing_delay.detected | int }}/20 | {{ test.by_fault.model_101.timing_delay.detected | int }}/20 | {{ test.by_fault.model_202.timing_delay.detected | int }}/20 | {{ test.by_fault.model_303.timing_delay.detected | int }}/20 |
| Camera clock drift | {{ test.by_fault.rules.sync_drift.detected | int }}/20 | {{ test.by_fault.rules_per_episode.sync_drift.detected | int }}/20 | {{ test.by_fault.robust_z.sync_drift.detected | int }}/20 | {{ test.by_fault.model_101.sync_drift.detected | int }}/20 | {{ test.by_fault.model_202.sync_drift.detected | int }}/20 | {{ test.by_fault.model_303.sync_drift.detected | int }}/20 |
| Missing stream | {{ test.by_fault.rules.missing.detected | int }}/20 | {{ test.by_fault.rules_per_episode.missing.detected | int }}/20 | {{ test.by_fault.robust_z.missing.detected | int }}/20 | {{ test.by_fault.model_101.missing.detected | int }}/20 | {{ test.by_fault.model_202.missing.detected | int }}/20 | {{ test.by_fault.model_303.missing.detected | int }}/20 |

![By fault type](figures/test_by_fault.png)

### 5.3 Diagnosis and attribution

Among detected faults, the robust detector named the right subsystem in {{ test.point.robust_z.subsystem_category | pct0 }} of cases and the rules in {{ test.point.rules.subsystem_category | pct0 }}. When each faulty segment was paired with a healthy segment recorded at the same time, the first alert landed on the faulty station, with the healthy one quiet, in {{ test.attribution.robust_z.attributed_correctly | int }} of {{ test.attribution.robust_z.detected_in_pair_run | int }} detections for robust z and {{ test.attribution.rules.attributed_correctly | int }} of {{ test.attribution.rules.detected_in_pair_run | int }} for the rules. On faults both caught, the robust detector alerted earlier in {{ test.paired_delay.robust_z_vs_rules.detector_faster | int }} and later in {{ test.paired_delay.robust_z_vs_rules.rules_faster | int }} of {{ test.paired_delay.robust_z_vs_rules.n | int }} cases.

### 5.4 With measurements removed

| Removed | Rules recall | Robust z recall | Model 101 recall |
|---|---|---|---|
| nothing | {{ test.point.rules.recall | pct0 }} | {{ test.point.robust_z.recall | pct0 }} | {{ test.point.model_101.recall | pct0 }} |
| camera measurements | {{ test.ablations.camera.rules.recall | pct0 }} | {{ test.ablations.camera.robust_z.recall | pct0 }} | {{ test.ablations.camera.model_101.recall | pct0 }} |
| timestamp measurements | {{ test.ablations.timestamp.rules.recall | pct0 }} | {{ test.ablations.timestamp.robust_z.recall | pct0 }} | {{ test.ablations.timestamp.model_101.recall | pct0 }} |
| action and state measurements | {{ test.ablations.action_state.rules.recall | pct0 }} | {{ test.ablations.action_state.robust_z.recall | pct0 }} | {{ test.ablations.action_state.model_101.recall | pct0 }} |

### 5.5 Alerts on unmodified recordings (exploratory)

Control trials are real recordings, so an alert on one is not automatically false. After the results were in, every such alert was compared with the XDOF findings Respite documented before this study. For robust z, {{ test.unmodified_alerts.robust_z.documented | int }} of {{ test.unmodified_alerts.robust_z.alerts | int }} line up with documented problems (a week the recorder was overloaded, two evaluation episodes whose cameras dropped out for seconds, a step in command-to-motion delay, a day with three times the usual dropped frames); {{ test.unmodified_alerts.robust_z.no_documented_counterpart | int }} do not. The rules raised {{ test.unmodified_alerts.rules.alerts | int }} such alert, in the overloaded week. The earlier findings are Respite's own measurements, recomputed independently at the time; they are not independent labels.

### 5.6 Calibration

The model's per-episode fault probability on test episodes had a Brier score of {{ test.calibration.model_101.brier | f3 }} (seed 101), {{ test.calibration.model_202.brier | f3 }} (202) and {{ test.calibration.model_303.brier | f3 }} (303), with 10-bin expected calibration errors of {{ test.calibration.model_101.ece_10bin | f3 }}, {{ test.calibration.model_202.ece_10bin | f3 }} and {{ test.calibration.model_303.ece_10bin | f3 }}.

HFLOW_SECTION

### 5.8 Real recordings without injected faults (descriptive)

Every detector was replayed over the unmodified recordings of each station in recording order. Without labels this is description, not accuracy, and the team dataset is in-sample for the rules (tuned on it) and the model (trained on faults injected into it).

| Station | Hours | Rules: share of episodes in alert | Robust z | Model 101 | Recorder's own flag below 50% valid |
|---|---|---|---|---|---|
| Station A | {{ retrospective.team.station_a.hours | f1 }} | {{ retrospective.team.station_a.rules.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_a.robust_z.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_a.model_101.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_a.recorder_flag.share_of_episodes_in_alert | pct0 }} |
| Station B | {{ retrospective.team.station_b.hours | f1 }} | {{ retrospective.team.station_b.rules.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_b.robust_z.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_b.model_101.share_of_episodes_in_alert | pct0 }} | {{ retrospective.team.station_b.recorder_flag.share_of_episodes_in_alert | pct0 }} |

Station B's cameras delivered about half the frames its recorder logged from its first recorded episode (an earlier Respite finding). The rules, which compare each episode against fixed lines, were in alert for {{ retrospective.team.station_b.rules.share_of_episodes_in_alert | pct0 }} of its episodes, and the recorder's own validity flag marked most rows invalid in {{ retrospective.team.station_b.recorder_flag.share_of_episodes_in_alert | pct0 }}. The robust detector and the model compare a station with its own start, so a station that is broken from the beginning looks normal to them: robust z raised no camera alert on Station B, and the three models were in alert for at most {{ retrospective.team.station_b.model_303.share_of_episodes_in_alert | pct1 }} of its episodes. By day, over {{ retrospective.day_agreement.rules.days | int }} station-days of the team dataset, the rules were in alert on {{ retrospective.day_agreement.rules.both | int }} of the {{ retrospective.day_agreement.rules.flag_days | int }} days the recorder's flag marked most rows invalid (and on {{ retrospective.day_agreement.rules.detector_only | int }} other days); robust z on {{ retrospective.day_agreement.robust_z.both | int }}; model 101 on {{ retrospective.day_agreement.model_101.both | int }}. (Day agreement counts a station as alerting on every day an alert lasts; the first version of this script counted only the day an alert was raised, which hid persistent alerts, and was corrected before this report.)

On the external XDOF streams, the rules raised {{ retrospective.xdof.proxy_3.rules.alert_events | int }} alert events on the largest stream ({{ retrospective.xdof.proxy_3.hours | f1 }} h) and robust z {{ retrospective.xdof.proxy_3.robust_z.alert_events | int }}; section 5.5 compares such alerts with earlier documented findings.

## 6. Failure analysis

Why the shipped rules missed (test set, counts of fault trials):

- Camera faults: {{ test.failure.rules_misses.camera.absent_in_format | int }} of 20 missed because the rule reads new-frame counts, which need per-row frame sequence numbers. The test format logs camera message times instead, and the rules never look at camera message rate.
- Camera clock drift: {{ test.failure.rules_misses.sync_drift.absent_in_format | int }} of 20, for the same reason (the rule reads frame age, which the format does not carry).
- Recorder pauses and missing streams: {{ test.failure.rules_misses.recorder_pause.no_measurement | int }} and {{ test.failure.rules_misses.missing.no_measurement | int }} of 20. The rules have no measurement for either.
- Recorder rate: {{ test.failure.rules_misses.recorder_rate.median_rate_ok | int }} of 20. The rule estimates the rate from the median interval between rows, which stays at the declared rate until roughly a third of the rows are gone; moderate, irregular drops pass under it.
- Command-to-motion delay: {{ test.failure.rules_misses.timing_delay.below_margin | int }} of 20, smaller increases than the rule's 50 ms margin or not sustained over three episodes.

Why the trained model missed: on test episodes its mean fault probability stayed close to its value on unmodified episodes for camera, recorder and drift faults (seed 101: {{ test.failure.model.101.camera.mean_p_faulty | f3 }} on camera-fault episodes against {{ test.failure.model.101.control.mean_p_unaffected | f3 }} on unmodified ones; threshold {{ training.draws.101.threshold | f2 }}). It learned what faults look like at the development recorder's 10 Hz and with its per-row camera record; the test recorder runs at 30 Hz and carries different camera measurements. Only the faults that look alike in both formats, a missing stream and, for one seed, a delay, came through.

Where robust z struggled: delays were sometimes named as camera-clock drift, because writing state messages later also moves the camera-to-arm offset it measures; missing camera streams were caught less often than missing action streams; and it cannot flag a station that is broken from its first episode, because it compares a station with its own start (section 5.8).

## 7. What differs from HFlow, and the operator workflow

HFLOW_DIFF_SECTION

## 8. Reproducibility

Everything above is produced by scripts in Respite's repository from stored files: `experiments/PROTOCOL.md` (the frozen design and amendments), `experiments/splits/` (split and freeze hashes), `experiments/build_features.py`, `train_model.py`, `benchmark.py`, `decide.py`, `failure_analysis.py`, `adjudicate_controls.py`, `retrospective.py`, `hflow/`, and `export_site.py`, which writes the bundle this report is rendered from (SHA-256 in `data/MANIFEST.json`). The repository is private today; the result tables, per-trial outcomes and the public test dataset are linked from the Reproduce page. Measuring one test episode took a median of {{ test.cost.measurement.seconds_median | f2 }} s on the machine above.

## 9. Limitations

All detection numbers are on synthetic faults. There are no independent labels. The development set shaped the rules and the model. The test set is {{ data.test.segments | int }} segments from one company with bimanual YAM-style arms and no physical station field; intervals are wide. Frozen camera frames cannot be measured in the test format by any detector here. Nothing ran live. The HFlow comparison is episode-level, on 30 files, with decision rules we applied to its measurements. Passing Respite's checks does not show a station is safe or calibrated.

## 10. Conclusion

**Is a trained model better than Respite's existing rules?** Not reliably. Of three training seeds, one met the decision rule fixed before the test run (seed 202: recall {{ test.point.model_202.recall | pct0 }} against {{ test.point.rules.recall | pct0 }}, no alerts on unmodified recordings) and two were worse than the rules (paired recall differences {{ test.paired.model_101_vs_rules.recall | ci_pp0 }} and {{ test.paired.model_303_vs_rules.recall | ci_pp0 }}). A model that is better or worse depending on its random seed, and whose probabilities are miscalibrated on a new recorder (expected calibration error {{ test.calibration.model_202.ece_10bin | f2 }} to {{ test.calibration.model_303.ece_10bin | f2 }}), should not replace the rules. The cause is clear from the failure analysis: with two development stations from one team, the model learned that recorder's format rather than the faults.

**What does improve detection?** Measurements, not learning. A robust per-station change detector over a wider set of measurements, with no training, detected {{ test.point.robust_z.recall | pct0 }} of the synthetic faults against the rules' {{ test.point.rules.recall | pct0 }} and alerted earlier on {{ test.paired_delay.robust_z_vs_rules.detector_faster | int }} of the {{ test.paired_delay.robust_z_vs_rules.n | int }} faults both caught. It met the decision rule, but only because the test set holds too few unmodified hours ({{ data.test.control_hours | f1 }}) to show that its higher alert rate ({{ test.point.robust_z.alerts_per_100h | f0 }} against {{ test.point.rules.alerts_per_100h | f0 }} per 100 station-hours) is real; most of those alerts line up with problems documented earlier, which suggests, without proving, that many are not false. And it cannot see a station that is broken from its first episode, which the rules can.

**Recommendation.** Keep the rules as the primary station check. Give them the measurements they lack for MCAP-style recorders (camera message rate, gaps and pauses, camera-to-arm offsets, stream presence), and run the robust change detector beside them as a second signal behind the same persistence. Do not ship the trained model. Before calling any of this an operator-reliability product, it needs what this study could not provide: a prospective run on live stations with operator-confirmed incidents.
