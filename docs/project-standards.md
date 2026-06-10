# AKQuant 项目工程规范

> 版本：v1.0  
> 日期：2026-06-10  
> 适用范围：`akquant/`、`tests/`、`docs/` 下的研究、筛选、回测与报告代码。

## 1. 项目定位

AKQuant 是本地 A 股量化研究与回测工具，不是实盘交易系统。

当前稳定方向分为两条主线：

```text
单标的研究回测
  -> 本地 CSV
  -> 自研日频事件引擎
  -> A 股交易规则
  -> Markdown 报告

资产配置/股票筛选研究
  -> AKShare 数据
  -> 领域配置
  -> Backtrader 或 pandas 分析
  -> 可审计报告
```

禁止把研究结论、回测结果或筛选结果表述为投资建议。

## 2. 架构边界

新增功能必须优先放入已有边界，而不是写成单文件脚本。

| 层级 | 模块示例 | 允许职责 | 禁止职责 |
| --- | --- | --- | --- |
| 数据获取/标准化 | `akshare_provider.py`, `fundamentals.py` | 调用 AKShare、标准化字段、记录数据质量 | 策略解释、指标排名、交易决策 |
| 配置/领域对象 | `portfolios.py`, `stock_pool.py`, `screening.py` | 表达配置、筛选规则、股票池、组合 | 直接访问外部网络 |
| 执行引擎 | `engine.py`, `backtrader_engine.py`, `portfolio_runner.py` | 回测执行、调仓、交易模拟 | 数据 fallback 决策、报告渲染 |
| 指标/分析 | `metrics.py`, `comparison.py` | 统一指标、收益曲线、回撤、对比表 | 拉取 AKShare 原始数据 |
| 报告/CLI | `*_reporting.py`, `cli.py` | 参数解析、Markdown/CSV 输出、用户入口 | 隐式改变核心业务逻辑 |

跨层调用方向必须保持单向：

```text
CLI/reporting
  -> config/domain
  -> provider/runner/metrics
```

不要让底层 provider 反向依赖 CLI、报告或具体策略。

## 3. 数据口径规范

### 3.1 ETF/指数回测

- 真实可交易 ETF 优先。
- ETF 覆盖率不足时才 fallback 到指数代理。
- fallback 必须写入运行元数据和报告，不能伪装成真实可交易回测。
- 同一份组合对比报告中的组合必须使用同一日期区间、同一成本模型、同一数据策略。

### 3.2 A 股估值筛选

- 最新截面使用 `stock_zh_a_spot_em` 标准化价格、PE/PB、市值、成交额等字段。
- 个股股息率优先使用 `stock_fhps_em(date)` 的现金分红股息率补全。
- `stock_a_gxl_lg` 是市场/板块股息率，不得作为个股筛选字段。
- 数据质量问题必须进入 `data_quality_flags`，例如：
  - `missing_pe_ttm`
  - `missing_pb`
  - `missing_dividend_yield`
  - `dividend_yield_from_fhps`
  - `extreme_dividend_yield`
- 缓存快照必须保留六位股票代码和列表型质量标记。

### 3.3 历史回测防未来函数

历史估值股票池回测只有在满足以下条件后才允许接入主路径：

- 每个调仓日只能使用当日之前已经可见的数据。
- 财报、分红、估值字段必须有公告日或保守滞后规则。
- 不得用最新截面因子回填历史。
- 调仓股票池必须持久化或可重建，且报告必须展示使用的快照日期。

## 4. 配置优先原则

组合、筛选条件和排序权重应使用配置表达，避免把研究逻辑硬编码在回测函数里。

可接受：

```python
ScreenConfig(
    id="value_screen",
    filters=[ScreeningRule("pe_ttm", ">", 0)],
    ranking=[RankingSpec("pe_ttm", ascending=True, weight=1.0)],
)
```

不可接受：

```python
if symbol == "000001":
    buy()
```

配置对象必须做基础校验：

- 权重合计要求明确。
- 权重不得为负。
- `top_n` 必须为正数。
- 缺失字段应清晰失败或产生 warning，不能静默生成误导结果。

## 5. 测试规范

所有行为变更必须先写失败测试，再实现修复。

标准验证命令：

```bash
uv run --with pytest pytest -q
```

合并前最低门禁：

```bash
uv run python -m compileall -q akquant
uv run --with pytest pytest -q
```

新增模块至少覆盖：

- 正常路径。
- 数据缺失或异常路径。
- 配置错误路径。
- CLI 入口或报告输出路径，如果该能力暴露给用户。

测试命名必须描述业务行为，例如：

```python
def test_factor_store_roundtrips_list_quality_flags(...)
```

不要只写：

```python
def test_store(...)
```

## 6. CLI 规范

- 新命令必须挂在 `akquant.cli:main` 下。
- CLI 只负责参数解析、加载配置、调用领域服务和写报告。
- CLI 不应直接实现指标计算、筛选排序或交易模拟。
- 会产生文件的参数必须明确，例如 `--out`、`--csv-out`、`--factor-cache-dir`。
- 支持缓存读取时，必须避免无意调用网络数据源。

## 7. 报告规范

报告必须回答三个问题：

1. 这次用了什么配置？
2. 实际选中了什么资产/股票？
3. 有哪些数据质量、fallback 或覆盖率警告？

报告中的配置快照必须使用 JSON 或 YAML 等稳定格式，不使用 Python repr 作为长期审计格式。

Markdown 报告允许中文标题；CSV 输出必须保留股票代码前导零。

## 8. 文档规范

新增面向用户的能力必须同步更新：

- `README.md`：放最小可运行命令。
- `docs/`：放设计背景、边界和口径。
- 如果某功能没有实现，必须明确写在“未实现”或“当前边界”中。

不得把未来计划写成已经可用的功能。

## 9. 代码风格

- 默认使用 Python 3.11+ 类型标注。
- 文件编辑默认 ASCII；已有中文文档和中文报告可使用 UTF-8 中文。
- provider 层字段映射要集中管理，不在 CLI 或报告里临时转换。
- 不引入额外依赖，除非能减少真实复杂度并补齐测试。
- 注释只解释非显然业务规则，例如数据口径或防未来函数约束。

## 10. Review 清单

每次较大修改完成后，按以下顺序自查：

- 架构边界是否清晰，是否出现跨层职责混杂。
- 数据口径是否可解释，是否记录 fallback/warning。
- 是否存在未来函数或把不可交易代理伪装成真实交易。
- 配置对象是否有必要校验。
- 报告是否能审计配置、输入、输出和警告。
- CLI 是否只是入口，不承载核心业务逻辑。
- 新增行为是否有失败测试证明。
- `uv run --with pytest pytest -q` 是否通过。
