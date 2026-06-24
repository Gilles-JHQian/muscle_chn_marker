# 计划包 ② — Muscle Channel 标记工具（Web GUI）

> 独立计划包，可在本服务器任意工作区执行。配套：本目录 `PAYLOAD_SPEC.md`（与 Pipeline 的硬契约）、`refs/`（参考文件）。
> 姊妹计划：`../plan_pipeline/`（生成 clean 的管线）。两者通过 `PAYLOAD_SPEC.md` 解耦。

## Context

加速 muscle channel 的人工标记。现状（`refs/readme.md` Step 5）要人肉翻 `Baishen_Figs/{SUBJ}/wavelet/*.jpg` 网格图、再人工写 CSV。本工具把"小波频谱数据准备 + 可视化标记 + 导出"做成一个规范的独立工程：

- **左**：被试 3D 皮层面（pial surface）+ 电极，高亮当前选中通道的位置。
- **右**：当前事件标签下所有通道的小波频谱图平铺；点一个 → 看该通道 4 个阶段的可缩放/平移热图；勾选 muscle yes/no；导出。
- **导出**：写契约 B 的 CSV 到 `data/muscle_chans/`，并回写 clean/channels.tsv（调 `update_muscle_chs`）。

输入来自 Pipeline 的 **契约 A**（`derivatives/clean`）；输出 **契约 B**（muscle CSV）回喂 Pipeline。工具内部用 **契约 C**（小波 `.h5` + 缩略图 + manifest）。三者定义见本目录 `PAYLOAD_SPEC.md`。

### 范围
- 先支持 `LexicalDecRepDelay` + `LexicalDecRepNoDelay`；为 `UniquenessPoint` 预留（事件窗口/baseline 待补，见末尾清单）。
- 左脑**仅 3D 皮层面**（不做 2D T1 切片）。大多数被试无 ECoG Recon → 脑面板降级、纯频谱标记仍可用。

### 复用
- 小波/CAR 逻辑：`refs/batch_preproc.py` wavelet 段 L234-343（含 `wavelet_scaleogram/crop_pad/rescale/chan_grid` 用法、事件窗口、baseline）。
- 导出回写：`refs/utils_batch.py` 的 `update_muscle_chs`（= `coganlab_ieeg/utils/batch.py`）。
- `ieeg`：`raw_from_layout, trial_ieeg, outliers_to_nan, wavelet_scaleogram, crop_pad, rescale`；`ieeg.viz.parula.parula_map`；`ieeg.viz.mri.{plot_subj, subject_to_info}`（坐标处理参考）。
- 环境：conda `Lexical_NoDelay`（含 ieeg/mne 1.10.1/nibabel/numpy；**缺 fastapi、uvicorn 需装**）。Node `/opt/apps/rhel8/node-v18.14.2-linux-x64/bin`。
- ECoG Recon：`/cwork/jq81/cogan_lab_box/ECoG_Recon/D{NNN}/`（`D0100`→`D100`）；有 recon 的被试：D100,D121,D128,D133,D134,D137,D138,D139,D140。

### 参考实现（**不拷贝，按约定仅写路径**）
- Web app 模板（React18+Vite5+three.js0.170+@react-three/fiber/drei+react-plotly）：
  `/hpc/home/jq81/cogan_lab/jq81/avalon/lexical_access/brain_viewer/viewer_react`
  - 关键文件：`src/App.jsx`（布局+选择态）、`src/components/brain/{BrainViewer,AverageBrainMesh,ElectrodePoint,ElectrodeInstances}.jsx`、`src/components/waveform/`（react-plotly）、`scripts/{serve.sh,dev.sh}`、`vite.config.js`、`package.json`。
- mesh→glb 工具：`/hpc/home/jq81/cogan_lab/jq81/avalon/lexical_access/brain_viewer/build_viewer_assets.py`（`write_glb`、mesh-merge），与 `export/export_average_brain_mesh.py`（pial→glb）、`export/phase_overlap_geometry.py`（电极坐标变换）。

---

## 目标结构

```
coganlab_ieeg/webui/
  dataprep/make_spectra.py        # clean → CAR + wavelet → {tag}-tfr.h5 + thumbs + manifest（sbatch 重）
  backend/app.py                  # FastAPI：服务频谱/脑/电极 + 写 muscle
  frontend/                       # React+Vite（拷 viewer_react 的栈与组件骨架）
  export/export_subject_brain.py  # ECoG Recon → brain.glb + electrodes.json
  scripts/{serve.sh, dev.sh}
  sbatch/sbatch_spectra.sh        # make_spectra array（重）
```
`config.TASK_EVENTS`（事件查询、时间窗、baseline）与 wavelet 参数（`WAVELET_DECIM_HZ=200, WAVELET_VLIM=(-2,2), BASELINE_WIN=(-0.5,0)`）放共享 `preproc/config.py`，逐字对照 `refs/batch_preproc.py` L268-310。Delay：`Cue(-0.5,3,base)/Auditory_stim(-0.5,3)/Go(-0.5,1)/Resp(-0.5,1)`；NoDelay：`Cue/Repeat(-0.5,3,base)/Auditory_stim/Repeat(-0.5,1)/Resp/Repeat(-0.5,1)`。

### 数据准备 `dataprep/make_spectra.py`（sbatch 重）
CLI：`python -m webui.dataprep.make_spectra --subject D0100 --task ...`，拆 `refs/batch_preproc.py` L234-343：
1. `raw=raw_from_layout(derivatives/clean,desc='clean',preload=False)` → `drop_channels(raw.info['bads'])` → `load_data()` → `set_eeg_reference("average")`（内存 CAR）。
2. for `(epoch,(t0,t1),bsl)` in `TASK_EVENTS[task]`：`trial_ieeg`→`outliers_to_nan(10)`→`wavelet_scaleogram(decim=sfreq/200)`→`crop_pad("0.5s")`→(bsl 段 crop(-0.5,0) 作 base)→`average(nanmean)`→`rescale(ratio)`→`log10×20`；`write_tfrs({tag}-tfr.h5)`。
3. **GUI 载荷（契约 C）**：每通道每 tag 出 `thumbs/{tag}/{ch}.png`（~140×90，parula，vlim）；写 `manifest.json`。
- 输出根 `{SAVE_DIR}/{SUBJ}/wavelet/`。后端**直接读 `.h5`** 按通道切片（按 subject LRU 缓存）。

### 脑资产 `export/export_subject_brain.py`（坐标对齐，关键）
- pial（`mne.read_surface(lh/rh.pial)`）在 **surfaceRAS/tkrRAS**；`D{NNN}_elec_locations_RAS_brainshifted.txt` 在 **scanner RAS(mm)**。差一个纯平移 `c_ras`，从 `orig.mgz` 头取：`c_ras=(vox2ras @ inv(vox2ras_tkr))[:3,3]`（D100 ≈ [+1.82,−10.03,+6.69]mm）。
- `elec_surf = elec_scanner − c_ras` 即与 mesh 同系 → three.js 直接对齐、无需再变换。复用 `build_viewer_assets.write_glb` + mesh-merge。用 `_brainshifted.txt`（与 `plot_subj` 一致，触点贴向表面）。
- 通道名：clean EDF 道名（`LTMM15`）= recon `NAME+IDX`（`LTMM`+`15`）；对不上的道无脑标记但仍可在网格里标。无 recon → 脑面板降级。

### 后端 `backend/app.py`（FastAPI，路径全从 env `LAB_ROOT/SAVE_DIR/RECON_DIR` 解析；`StaticFiles` 同端口托管前端 `dist/`）
```
GET  /api/subjects                            -> [{subject,has_recon,tags,n_channels}]
GET  /api/subjects/{s}/manifest               -> manifest.json
GET  /api/subjects/{s}/thumbs/{tag}/{ch}.png  -> 缩略图（StaticFiles）
GET  /api/subjects/{s}/spectra/{tag}/{ch}     -> {freqs,times,data[[..]],vlim}（读 .h5 切片）
GET  /api/subjects/{s}/brain.glb              -> 皮层面 mesh
GET  /api/subjects/{s}/electrodes.json        -> [{channel,x,y,z,hemi}]
GET  /api/subjects/{s}/muscle                 -> 已标记通道（读 CSV，续标）
POST /api/subjects/{s}/muscle {channels:[..]} -> 写 data/muscle_chans/{s}_muscle_chans.csv + 调 update_muscle_chs 回写 channels.tsv
```

### 前端（镜像 `viewer_react`）
```
App.jsx state:{subject,tag,selectedChannel,muscleSet,hovered}
 ├─ SubjectDropdown + TagSelector(Cue/Auditory/Go/Resp)
 ├─ 左 BrainPanel → BrainViewer.jsx(R3F Canvas;useGLTF 载 brain.glb)
 │     └─ ElectrodeInstances/ElectrodePoint.jsx // selectedChannel 高亮；muscle 已标异色；无 recon 提示
 └─ 右 SpectrogramPanel
     ├─ SpectrogramGrid.jsx   // 当前 tag 所有通道缩略图平铺，点击选道
     ├─ SpectrogramDetail.jsx // 选中道 4 阶段 plotly Heatmap(parula+vlim)，自带 zoom/pan/box-zoom
     ├─ MarkingControls.jsx   // muscle yes/no 勾选框 ↔ muscleSet；readme 7 条判定标准帮助面板
     └─ ExportButton          // POST muscleSet
```
工作流：选 tag → 网格点一道 → 右看 4 阶段交互热图 + 左脑高亮 → 勾 muscle → 导出（写 CSV + 回写 tsv）。双向选择（点脑/点网格选同一道）；进入时 `GET /muscle` 回填续标。

### 启动（改自 `viewer_react/scripts`）
- `serve.sh`（SLURM 生产，单端口）：`conda activate Lexical_NoDelay`；缺则 `npm run build`；`export LAB_ROOT/SAVE_DIR/RECON_DIR=/cwork/jq81/cogan_lab_box/ECoG_Recon`；`uvicorn backend.app:app --host 0.0.0.0 --port 8082`；打印 `ssh -L 8082:<node>:8082 jq81@dcc-login.oit.duke.edu`。
- `dev.sh`（双进程）：Node 上 PATH；`npm ci`；后台 `uvicorn --reload --port 8001`；`npm run dev`（Vite :5173，`vite.config.js` proxy `/api`→`:8001`）。本地隧道后开 `http://localhost:<port>/`。
- **前置安装**：`conda run -n Lexical_NoDelay pip install fastapi "uvicorn[standard]"`（+ `pygltflib`/`trimesh` 视 `build_viewer_assets.write_glb` 而定，实现时先看那份文件）。

---

## Payload 契约（详见本目录 `PAYLOAD_SPEC.md`）

本工具**消费契约 A**、**产出契约 B**、**内部用契约 C**：

**A — Clean 衍生（消费）**：`{BIDS_ROOT}/derivatives/clean/sub-{SUBJ}/ieeg/` 的 `*_desc-clean_ieeg.edf` + channels.tsv（`bads` 来自 status=bad）。dataprep 读 EDF、按 bads 丢道后 CAR。

**B — Muscle CSV（产出）**：`{COGANLAB_IEEG}/data/muscle_chans/{SUBJ}_muscle_chans.csv`，无表头、每行一名（须等于 channels.tsv 的 `name`）。导出时同时调 `update_muscle_chs` 回写 channels.tsv 的 `bad/muscle`。

**C — Wavelet 载荷（内部）**：`{SAVE_DIR}/{SUBJ}/wavelet/{tag}-tfr.h5` + `thumbs/{tag}/{ch}.png` + `manifest.json{subject,task,tags,channels,vlim,cmap,has_recon}`；后端按通道切片为 `{freqs,times,data,vlim}`。脑资产 `brain.glb`(surfaceRAS) + `electrodes.json`(surfaceRAS)。

> 完整字段与示例见 `PAYLOAD_SPEC.md`。

---

## 本计划需要一起拷贝的参考文件（已放入 `refs/`）
| 文件 | 用途 |
|---|---|
| `refs/batch_preproc.py` | 小波/CAR 源逻辑（L234-343），事件窗口/baseline/参数照搬 |
| `refs/utils_batch.py` | 导出回写复用 `update_muscle_chs`（= `coganlab_ieeg/utils/batch.py`） |
| `refs/readme.md` | Step 5 的 muscle 判定 7 条标准（做 GUI 帮助面板）+ 背景 |

> **不拷贝、仅写路径**（按约定）：`viewer_react` 整个 app 及 `build_viewer_assets.py`/`export/*.py`（路径见上"参考实现"）。
> **不拷贝**：muscle 相关数据（`data/muscle_chans/`）。

---

## Uniqueness point 待补信息（小波侧）
1. events.tsv `trial_type` 取值：对应 Cue/听觉刺激/Go/Resp 的确切字符串；条件切分与 `CORRECT` 编码。
2. 每个画 wavelet 事件的时间窗 `(t0,t1)` 与作 baseline 的事件（现状 Cue −0.5~0s）。
3. 采样率、被试列表、有 recon 的被试。
（BIDS 目录/Trigger/EEG 等 denoise 侧信息见姊妹计划 `../plan_pipeline/`。）

---

## 验证（端到端）
1. **数据准备**：`conda run -n Lexical_NoDelay python -m webui.dataprep.make_spectra --subject D0100 --task LexicalDecRepDelay` → `{SAVE_DIR}/D0100/wavelet/` 出 4 个 `{tag}-tfr.h5` + `thumbs/` + `manifest.json`；抽一个 `.h5` 与旧产物数值对比。
2. **脑资产**：`python -m webui.export.export_subject_brain --subject D0100` → `brain.glb` + `electrodes.json`；抽查电极落在皮层附近（c_ras 对齐正确）。
3. **GUI**：`bash webui/scripts/dev.sh` → 本地隧道 `:5173`；选 D0100 → 网格出缩略图 → 点一道出 4 阶段可缩放热图 + 左脑高亮该电极 → 勾 muscle → 导出 → 确认 `data/muscle_chans/D0100_muscle_chans.csv` 生成且 `clean/channels.tsv` 对应道变 `bad/muscle`。无 recon 被试（如 D0023）确认脑面板降级、频谱标记可用。
