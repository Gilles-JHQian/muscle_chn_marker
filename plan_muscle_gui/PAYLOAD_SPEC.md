# Payload 标准格式 — Pipeline ⇄ Muscle 标记工具

> 本文件在 **两个计划包里内容完全一致**（`plan_pipeline/` 与 `plan_muscle_gui/` 各一份），是两个工具之间的硬契约。任何一侧改动都要同步另一侧。

两个工具，三条契约：A、B 是**工具之间**的交接；C 是 Muscle 工具**内部**（dataprep→GUI）的载荷，列在这里是为了让两个计划对同一 schema 达成一致。

占位符：
- `{BIDS_ROOT}` = `/cwork/jq81/cogan_lab_box/CoganLab/BIDS-1.0_{TASK}/BIDS`（Delay 任务即 `.../BIDS-1.0_LexicalDecRepDelay/BIDS`）
- `{COGANLAB_IEEG}` = `{BIDS_ROOT}/coganlab_ieeg`
- `{SAVE_DIR}` = 小波/缩略图输出根（由工具的 env `SAVE_DIR` 指定，见 muscle 计划）
- `{SUBJ}` = BIDS 被试号，如 `D0100`
- `{TASK}` = 任务标签，如 `LexicalDecRepDelay`；`{TASKNOSEP}` = `{TASK}` 去掉下划线（util 用 `task.replace('_','')`）

---

## 契约 A — Clean 衍生数据（Pipeline → Muscle 工具）

Pipeline 的 `denoise` 产出 BIDS "clean" 衍生；Muscle 工具的 dataprep 读它。

**路径**：`{BIDS_ROOT}/derivatives/clean/sub-{SUBJ}/ieeg/`
- 每个 run：`sub-{SUBJ}_task-{TASKNOSEP}_acq-{A}_run-{R}_desc-clean_ieeg.edf`（+ `.json`）、`..._desc-clean_channels.tsv`、`..._desc-clean_events.tsv`
- 每个被试：`sub-{SUBJ}_acq-{A}_space-ACPC_electrodes.tsv`、`..._space-ACPC_coordsystem.json`

**channels.tsv**（制表符分隔，列固定如下）：
```
name  type  units  low_cutoff  high_cutoff  description  sampling_frequency  status  status_description
```
- `status` ∈ {good, bad}；坏道的 `status_description` ∈ {outlier, muscle, ...}
- good 行示例：`LOF1  SEEG  µV  0.0  1024.0  StereoEEG  2048.0  good  `（status_description 为空）
- bad 行示例：`LTMM5  SEEG  µV  0.0  1024.0  StereoEEG  2048.0  bad  outlier`

**clean EDF 语义**：已去线噪（陷波 60/120/180/240 Hz）、已丢掉 EEG 与 Trigger 通道、**未做平均参考（CAR）**。outlier 通道仅在 channels.tsv 里被标 `bad/outlier`，**信号仍保留在 EDF 中、未删除**。

**electrodes.tsv（clean）**：列 `name  x  y  z  size`，MNE 写出、**单位米**、ACPC 系。
- ⚠️ 3D 脑视图**不**用这个文件（改用 ECoG Recon 的 RAS 文件，见契约 C/脑资产）。通道↔电极仅按 `name` 对齐。

---

## 契约 B — Muscle 通道 CSV（Muscle 工具 → Pipeline）

Muscle 工具导出人工标记；Pipeline 的 `apply_muscle` 消费。

**路径**：`{COGANLAB_IEEG}/data/muscle_chans/{SUBJ}_muscle_chans.csv`

**格式**：纯文本 CSV，**无表头，每行一个通道名**。名字必须等于 clean channels.tsv 的 `name`（如 `RPIF6`）。
```
RPIF6
LTMM5
```
- 无 muscle 通道 → 单行 `nan`（沿用 `data/eeg_chans` 约定）或空文件。
- 由 `update_muscle_chs()` 消费：对列出的每个通道，在**每个 run** 的 clean channels.tsv 里置 `status=bad, status_description=muscle`。幂等（重复跑不重复污染）。

---

## 契约 C — Wavelet 载荷（Muscle 工具内部：dataprep → GUI）

Muscle 工具的 `make_spectra` 产出，工具自己的后端/前端消费。两个计划共用此 schema。

**路径根**：`{SAVE_DIR}/{SUBJ}/wavelet/`
- `{tag}-tfr.h5` — MNE `AverageTFR`，跨试次平均、baseline ratio、dB（`log10(ratio)*20`）；形状 `(n_chan, n_freq, n_time)`；`{tag}` ∈ 事件标签（Delay：`Cue/Auditory/Go/Resp`）。
- `thumbs/{tag}/{ch}.png` — 每通道缩略图（~140×90，parula colormap，vlim=(-2,2)），供前端平铺网格。
- `manifest.json`：
  ```json
  {"subject":"D0100","task":"LexicalDecRepDelay",
   "tags":["Cue","Auditory","Go","Resp"],
   "channels":["LOF1","LOF2","..."],
   "vlim":[-2,2],"cmap":"parula","has_recon":true}
  ```
- 后端按通道从 `.h5` 切片，返回 JSON：`{"freqs":[...],"times":[...],"data":[[...]],"vlim":[-2,2]}`。

**脑资产（3D 视图，工具内部）**：
- `brain.glb` — 被试 pial 网格（ECoG Recon `surf/lh.pial`+`rh.pial` 合并），**surfaceRAS** 系。
- `electrodes.json` — `[{ "channel":"LTMM15","x":..,"y":..,"z":..,"hemi":"L" }]`，**surfaceRAS**（= scannerRAS − c_ras）。按 `channel` 名与频谱图通道对齐。
