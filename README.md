# recycle-cost 使用说明手册

`recycle-cost` 是对 `EverBatt 2023.xlsm` 的 Python/Streamlit 迁移版本，用于计算电池回收与制造过程中的成本、收入、能耗、水耗和温室气体排放。项目保留原始 Excel 工作簿作为参数来源和回归校验基准，但用户侧计算、导出和批量场景运行已经转向 Python 公式路径。

## 1. 项目能做什么

当前工具支持：

- 在 Streamlit 页面中配置电池制造、回收物料、回收工艺、正极生产和运输距离。
- 运行内置场景预设，包括黑粉湿法回收、NMC622 电池包火法/湿法/直接回收、制造废料直接回收。
- 查看流程阶段、回收工艺、正极生产、电芯与电池包制造、参数表和综合输出。
- 导出当前场景 JSON、单表 CSV，以及包含场景和全部结果表的 ZIP。
- 在非 Streamlit 环境下用 CLI 批量运行场景并导出结果。
- 对 Python 结果和 LibreOffice 重算后的 Excel 结果做一致性验证。

## 2. 环境准备

项目使用 Python 3.13 和 `uv` 管理依赖。

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync
```

如需进入已有虚拟环境：

```bash
source /home/zhouzhq/recycle_cost/.venv/bin/activate
```

项目根目录需要保留原始工作簿：

```text
EverBatt 2023.xlsm
```

该工作簿仍作为部分参数表、快照表和回归校验来源。

## 3. 启动 Streamlit 应用

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run streamlit run app.py --server.port 8502
```

启动后访问：

```text
http://localhost:8502
```

页面主要区域：

- `结果总览 / Overview`：核心成本、能耗、GHG 和流程汇总。
- `回收流程 / Recycling process`：运输、拆解、预处理、黑粉回收、材料转换。
- `正极与制造 / Cathode and Manufacturing`：正极生产、电芯制造、电池包制造。
- `参数表 / Parameters`：当前场景使用的参数和参考表。
- `导出 / Export`：导出场景 JSON、CSV 或完整 ZIP。

## 4. Streamlit 使用流程

1. 在侧边栏选择语言和场景预设。
2. 修改生产场景：
   - 电池类型：Pack / Module / Cell
   - 制造化学体系：如 `NMC(622)`、`NMC(811)`、`NCA`、`LFP`
   - 制造地点
3. 修改回收物料：
   - 物料类型：黑粉、EOL pack/module/cell、制造废料等
   - 物料化学体系
   - 年处理量
4. 选择回收工艺：
   - `Pyro`
   - `Hydro`
   - `Direct`
   - `Custom` 目前主要保留为工作簿兼容/审计路径
5. 修改正极生产和运输距离参数。
6. 查看结果表，并在导出页下载结果。

上传由本工具导出的 `scenario.json` 可以恢复场景输入。

## 5. CLI 批量运行场景

使用 `scripts/run_scenario.py` 可以在非 Streamlit 环境下批量跑场景：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_scenario.py \
  --preset default \
  --preset pack_pyro \
  --preset pack_hydro \
  --preset pack_direct \
  --preset scrap_direct \
  --out-dir scenario_runs \
  --include-parameters
```

常用参数：

- `--preset`：内置场景名，可重复传入。
- `--scenario-json`：从应用导出的场景 JSON，可重复传入。
- `--process`：覆盖流程表使用的工艺，可选 `Pyro`、`Hydro`、`Direct`、`Custom`。
- `--out-dir`：输出目录。
- `--include-parameters`：同时导出当前参数表。

每个场景会生成独立目录，包含：

```text
scenario.json
summary.json
stage_summary.csv
process_stage.csv
cost_breakdown.csv
recycling_revenue.csv
manufacturing_summary.csv
output_summary.csv
report_results.csv
parameters/*.csv    # 仅在 --include-parameters 时生成
```

`summary.json` 会给出所选回收工艺的核心指标，例如：

- recycling cost
- recycling revenue
- recycling margin
- recycling total energy
- recycling water
- recycling GHG

## 6. 如何解读输出

`output_summary.csv` 是最接近 Excel `Output` 页的用户侧汇总表。

主要指标包括：

- `Cell manufacturing cost`
- `Cell manufacturing total energy`
- `Cell manufacturing water`
- `Cell manufacturing GHGs`
- `Collection and transport cost`
- `Collection and transport total energy`
- `Recycling cost`
- `Recycling total energy`
- `Recycling water`
- `Recycling revenue`
- `Recycling GHGs`

列含义：

- `Virgin`：原生制造或运输基准。
- `Pyro`：火法回收路线。
- `Hydro`：湿法回收路线。
- `Direct`：直接回收路线。
- `Custom`：自定义/兼容路线。

注意：`Cell manufacturing cost` 的 recycled route 目前显示为空值。这不是漏算为 0，而是因为原 Excel 在这些 route 上会产生 `#DIV/0!`、`#N/A` 或 `#NAME?`。Python 版本已改为显式空值，避免误导用户把错误路径解释成“成本为 0”。

## 7. 我们是怎么做迁移的

迁移不是简单读取 Excel 单元格，而是分层把工作簿逻辑移植到 Python。

### 7.1 工作簿侦察

使用 `scripts/analyze_everbatt.py` 提取：

- worksheet 元信息
- 公式依赖关系
- VBA 文本
- 跨 sheet 公式引用

生成的分析文件位于：

```text
docs/analysis/everbatt_logic.md
docs/analysis/everbatt_analysis.json
docs/analysis/vba_olevba.txt
```

### 7.2 场景模型 typed 化

Excel 的 `Input` 页被迁移为 typed Python 对象：

- `Scenario`
- `FeedstockInput`
- `TransportDistances`
- `ScenarioOptions`

这样运行路径不再到处散落 `Input!E9`、`Input!E49` 这类单元格地址，而是通过场景对象传参。

### 7.3 参数访问收敛

工作簿参数读取集中到 `src/recycle_cost/parameters.py`。部分复杂运行参数继续收敛成 typed parameter objects，例如：

- CM recovery throughput 语义被拆成 material-flow tonnes、routed tonnes、cost-design tonnes。
- recycled manufacturing 使用 `RecycledManufacturingParameters` 管理 chemistry、recycled share 和转换因子。

### 7.4 公式模块化迁移

已迁移的主要模块包括：

- Collection and transport
- Disassembly
- Preprocessing
- CM recovery
- Material conversion
- Cathode production
- Cell and pack manufacturing
- Output summary
- Report summary

每个模块尽量保留：

- Python 计算值
- workbook 快照值
- delta
- status/audit 字段

UI 默认隐藏 audit 字段，但测试和开发路径仍能看到。

### 7.5 快照作为 oracle

原始 Excel 不再是用户侧计算引擎，而是回归 oracle：

- `reporting_snapshots.py` 保留读取 workbook 快照的能力。
- Python 用户路径优先使用迁移后的公式。
- 测试中保留 workbook delta，防止迁移过程偏离原模型。

### 7.6 LibreOffice 矩阵校验

为了验证 Python 与 Excel 在非默认场景下的一致性，我们生成并用 LibreOffice/soffice 重算了 15 个工作簿场景，覆盖：

- 黑粉
- EOL pack/module/cell
- 制造废料 rejected cells/electrode
- 混合 feedstock
- `NMC(622)`、`NMC(811)`、`NCA`、`LFP`
- `Pyro`、`Hydro`、`Direct`

校验报告见：

```text
docs/analysis/scenario_matrix_comparison.md
```

## 8. 迁移之后效果如何

当前全量测试：

```text
104 passed
```

关键 parity 结果：

- 15 场景矩阵中，selected-route recycling 的成本、收入、能耗、水耗、GHG 已和 LibreOffice 重算结果达到浮点精度一致。
- `scrap_direct` 的 GHG 差异已修复，Direct 路径使用 feedstock-specific preprocessing GHG。
- `LFP`、`NCA`、`NMC(811)` 的 virgin cell manufacturing 输出已对齐 Excel：
  - cost
  - total energy
  - water
  - GHG
- Direct regenerated manufacturing environment 已覆盖并对齐测试场景：
  - `NMC(622)`
  - `LFP`
  - `NCA`
  - `NMC(811)`
- CLI 可在无 Streamlit 环境下批量导出场景结果。
- 用户侧导出不再把 workbook 错误路径显示成假 0。

selected-route recycling 的矩阵摘要：

| metric | points | max_abs_delta |
| --- | ---: | ---: |
| Recycling GHGs | 15 | 6.54836e-11 |
| Recycling total energy | 15 | 3.97904e-13 |
| Recycling cost | 14 | 9.23706e-14 |
| Recycling water | 15 | 2.84217e-14 |
| Recycling revenue | 15 | 1.77636e-15 |

## 9. 已知边界

当前仍需注意：

- `recycled manufacturing cost` 路径在 Excel 中本身会输出错误值，因此 Python 当前显示为空。若业务上需要这个值，应新增 Python-only estimate，并明确它不是 Excel parity 值。
- `Custom` route 仍以兼容/审计为主，作为真实可配置路线还需要进一步定义边界。
- 部分 output-parity 常量仍在 `reporting.py` / `manufacturing.py` 中，应继续收敛到 typed parameter objects 或参数表。
- UI 当前主要编辑单一 feedstock stream；底层 `Scenario.feedstocks` 已支持多 stream，后续可以扩展页面输入。
- 某些详细 audit 表保留 scenario-derived 计算，而 public `Output` summary 为了 Excel parity 会使用 workbook-style 汇总缓存逻辑。

## 10. 开发与测试

运行全量测试：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

运行分析脚本：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/analyze_everbatt.py
```

运行一组常用 CLI 场景：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_scenario.py \
  --preset default \
  --preset pack_pyro \
  --preset pack_hydro \
  --preset pack_direct \
  --preset scrap_direct \
  --out-dir /tmp/everbatt_runs
```

维护原则：

- 用户侧优先使用 Python-calculated tables。
- workbook snapshots 作为 regression oracle，而不是运行时主计算路径。
- 新迁移公式需要至少覆盖默认场景测试；如果受用户输入影响，应增加非默认场景测试。
- 已知偏差必须记录在 `docs/analysis/migration_checklist.md` 或 `docs/analysis/scenario_matrix_comparison.md`。

## 11. 项目结构

```text
app.py                         Streamlit 入口
scripts/run_scenario.py         CLI 批量场景 runner
scripts/analyze_everbatt.py     Excel 工作簿侦察脚本
src/recycle_cost/model.py       typed scenario model
src/recycle_cost/parameters.py  工作簿参数集中读取
src/recycle_cost/app_services.py UI/导出/场景服务层
src/recycle_cost/reporting.py   Output/Report 汇总逻辑
src/recycle_cost/*.py           各 workbook 模块的 Python 迁移
tests/                          回归测试和场景测试
docs/analysis/                  迁移分析、清单和 parity 报告
```

## 12. 快速排查

如果 Streamlit 启动失败：

- 确认依赖已同步：`UV_CACHE_DIR=/tmp/uv-cache uv sync`
- 确认当前目录是项目根目录。
- 确认 `EverBatt 2023.xlsm` 存在。

如果 LibreOffice 对比失败：

- 确认系统已安装 `soffice` / LibreOffice。
- headless 转换建议使用独立 profile，避免配置锁冲突。

如果输出中 recycled manufacturing cost 为空：

- 这是当前预期行为。
- 原 workbook 对这些 route 的成本公式会返回错误值。
- Python 版本用空值表示“不可用”，避免误报为 0。
