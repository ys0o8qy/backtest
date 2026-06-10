# A 股估值筛选与股票池研究设计文档

> 版本：v1.0  
> 日期：2026-06-10  
> 项目：AKQuant  
> 目标：为“全 A 股按 PE / PB / 股息率排序和过滤”设计稳定的数据分析与后续回测能力。

## 1. 背景与目标

AKQuant 当前已经具备：

- AKShare 数据接入。
- ETF/指数价格数据标准化。
- Backtrader 多资产组合回测。
- 多组合对比报告。
- YAML/JSON 组合配置。

下一阶段需要补齐的是 **A 股股票筛选与股票池生成能力**。用户希望对全 A 股股票按照 PE、PB、股息率进行排序、过滤，并将结果用于数据分析和后续回测。

本功能的核心定位不是“买卖策略”，而是：

```text
全市场基础数据
  -> 估值/股息因子快照
  -> 过滤与排序
  -> 股票池
  -> 分析报告
  -> 可选接入股票池回测
```

一句话目标：

> 在最新交易日或已缓存/可重建的指定日期，对全 A 股生成可审计的估值截面，基于 PE / PB / 股息率等规则筛选股票，输出可解释的股票池，并为未来历史截面回测留出接口。

## 2. 用户真正想实现的功能

### 2.1 当前截面筛选

用户可以基于最新 A 股截面数据进行筛选；指定日期筛选只有在已有因子快照缓存，或使用历史估值数据重建截面时才启用：

```text
PE(TTM) > 0
PE(TTM) <= 15
PB <= 1.5
股息率 >= 3%
总市值 >= 50 亿
成交额 >= 5000 万
排除 ST
排除停牌
取综合得分前 50
```

输出：

- 筛选后股票列表。
- 每只股票的 PE / PB / 股息率 / 市值 / 成交额 / 行业。
- 排序原因和因子排名。
- 被过滤股票数量和过滤原因汇总。
- Markdown / CSV 报告。

### 2.2 多因子排序

支持单因子排序：

```text
PE 从低到高
PB 从低到高
股息率从高到低
```

支持多因子打分：

```text
value_score =
  pe_rank_score * 0.4
  + pb_rank_score * 0.3
  + dividend_yield_rank_score * 0.3
```

排序要求：

- PE/PB 越低越好，但负 PE 和极端异常值不能简单排到最前。
- 股息率越高越好，但必须识别一次性高分红和异常股息率。
- 每个因子都要保留原始值和标准化排名，避免报告不可解释。

### 2.3 股票池生成

筛选结果不只是报告，也应成为可复用对象：

```text
ScreenResult
  -> StockPool
  -> EqualWeightPortfolioConfig
  -> Backtrader 回测
  -> ComparisonReport
```

股票池需要包含：

- `pool_id`
- `as_of_date`
- `screen_config`
- `selected_symbols`
- `factor_snapshot`
- `filter_summary`
- `ranking_summary`
- `data_warnings`

### 2.4 历史截面回测

如果只是做“今天哪些股票便宜”，使用最新截面即可。

如果要做“PE/PB/股息率策略历史回测”，必须使用历史截面：

```text
每个调仓日：
  1. 取当时已经可见的数据
  2. 计算当时 PE / PB / 股息率
  3. 按配置筛选和排序
  4. 生成 Top N 股票池
  5. 等权或按因子权重持有到下个调仓日
```

关键约束：

- 不能用今天的财务数据筛过去的股票。
- 不能用未来分红计算过去的股息率。
- 必须记录财报公告日或至少使用滞后规则。

## 3. 数据源与口径设计

### 3.1 可用 AKShare 数据

根据 AKShare 官方股票数据文档：

- `stock_info_a_code_name` 可获取沪深京 A 股股票代码和简称。
- `stock_zh_a_spot_em` 可获取沪深京 A 股实时行情，字段包含最新价、成交额、换手率、动态市盈率、市净率、总市值、流通市值等。
- `stock_value_em(symbol)` 可获取指定股票的历史估值数据，字段包含 PE(TTM)、PE(静)、市净率、总市值、流通市值等。
- `stock_fhps_em(date)` 可获取指定报告期的分红配送数据，字段包含现金分红股息率，可用于最新截面的个股股息率补全。
- `stock_a_gxl_lg(symbol)` 是 A 股市场/板块股息率数据，输入为上证 A 股、深证 A 股、创业板、科创板，不是个股级股息率。

资料来源：

- AKShare 股票数据文档：`https://akshare.akfamily.xyz/data/stock/stock.html`

### 3.2 数据口径决策

| 指标 | 当前截面口径 | 历史回测口径 | 说明 |
| --- | --- | --- | --- |
| PE | 优先 PE(TTM)，备选动态 PE | `stock_value_em` 历史 PE(TTM) | 负 PE 不进入低估排序 |
| PB | 市净率 | `stock_value_em` 历史市净率 | PB <= 0 视为异常 |
| 股息率 | 优先 `stock_fhps_em` 个股现金分红股息率，缺失时标记缺失 | 历史分红按可见日期计算 | 不直接使用 `stock_a_gxl_lg` 作为个股股息率 |
| 价格 | 最新价或指定日收盘价 | 调仓日前一交易日收盘价 | 避免未来函数 |
| 市值 | 总市值/流通市值 | 历史估值表市值 | 用于流动性和规模过滤 |
| 成交额 | 实时行情成交额 | 历史行情成交额滚动均值 | 避免选入不可交易股票 |

指定日期口径：

- `latest`：直接使用全市场实时行情和当前可获得估值数据。
- `cached date`：读取 `factor_store.py` 已保存的因子快照。
- `rebuilt date`：基于逐股历史估值、历史行情、分红可见性规则重建，成本高，放在历史回测阶段。

当前实现状态：

- `--as-of latest` 会通过 AKShare 获取最新截面。
- `--factor-cache-dir` 配合 `latest` 会保存当日因子快照。
- `--as-of YYYY-MM-DD --factor-cache-dir PATH` 会读取缓存中不晚于该日期的快照，不再调用 AKShare。
- `rebuilt date` 暂未实现，不能将最新财务数据倒灌到历史回测。

### 3.3 股息率计算原则

个股股息率定义为：

```text
dividend_yield = trailing_cash_dividend_per_share / close_price
```

第一阶段支持两种口径：

1. **当前截面简化口径**
   - 优先读取最近可用报告期的 `stock_fhps_em(date)`。
   - 使用“现金分红-股息率”补全个股 `dividend_yield`。
   - 补全来源写入 `data_quality_flags`，标记为 `dividend_yield_from_fhps`。
   - 如果无法补全，则保留缺失并标记为 `missing_dividend_yield`。

2. **历史回测严格口径**
   - 只使用调仓日前已经公告的分红。
   - 分红归属窗口为过去 12 个月或最近完整年度。
   - 报告中记录可见性规则。

第一阶段不允许把市场整体股息率字段当作个股股息率。

## 4. 架构设计

### 4.1 新增模块

建议新增以下模块：

```text
akquant/
  equity_universe.py        # 全 A 股股票池、ST/停牌/市场板过滤
  fundamentals.py           # PE/PB/分红/股息率数据获取与标准化
  factor_store.py           # 估值因子快照缓存
  screening.py              # 过滤、排序、打分、Top N
  stock_pool.py             # 股票池领域对象
  stock_pool_backtest.py    # 基于股票池的定期调仓回测
  screening_reporting.py    # 筛选报告
```

与现有架构的关系：

```text
AKShare provider
  -> equity_universe
  -> fundamentals
  -> factor_store
  -> screening
  -> stock_pool
  -> stock_pool_backtest
  -> Backtrader / ComparisonReport
```

### 4.2 模块职责

| 模块 | 职责 | 不负责 |
| --- | --- | --- |
| `equity_universe.py` | 获取股票列表、交易板、ST、停牌、新股过滤 | 计算 PE/PB/股息率 |
| `fundamentals.py` | 获取和标准化估值、分红、价格、市值数据 | 排序、打分 |
| `factor_store.py` | 保存和读取每日因子快照 | 解释策略好坏 |
| `screening.py` | 执行过滤、排序、打分、Top N | 拉取 AKShare 原始数据 |
| `stock_pool.py` | 表达股票池结果和元数据 | 交易撮合 |
| `stock_pool_backtest.py` | 定期调仓股票池回测 | 生成基础因子数据 |
| `screening_reporting.py` | 输出 Markdown/CSV 报告 | 修改筛选结果 |

### 4.3 核心领域模型

#### ValuationSnapshot

```python
ValuationSnapshot:
    as_of_date: date
    data_date: date
    symbol: str
    name: str
    close: float
    pe_ttm: float | None
    pe_dynamic: float | None
    pe_static: float | None
    pb: float | None
    dividend_yield: float | None
    market_cap: float | None
    float_market_cap: float | None
    turnover_amount: float | None
    industry: str | None
    is_st: bool
    is_suspended: bool
    listing_age_days: int | None
    data_quality_flags: list[str]
```

#### ScreeningRule

```python
ScreeningRule:
    field: str
    operator: ">" | ">=" | "<" | "<=" | "==" | "between" | "not_null"
    value: float | str | tuple
```

#### RankingSpec

```python
RankingSpec:
    field: str
    ascending: bool
    weight: float
    null_policy: "exclude" | "worst" | "neutral"
```

#### ScreenConfig

```python
ScreenConfig:
    id: str
    name: str
    as_of_date: date | "latest"
    universe: UniverseConfig
    filters: list[ScreeningRule]
    ranking: list[RankingSpec]
    top_n: int
    output_fields: list[str]
```

#### StockPool

```python
StockPool:
    pool_id: str
    as_of_date: date
    config_snapshot: dict
    selected: DataFrame
    rejected_summary: DataFrame
    warnings: list[str]
```

## 5. 功能设计

### 5.1 当前截面筛选

CLI 目标形态：

```bash
uv run python -m akquant.cli screen \
  --as-of latest \
  --pe-max 15 \
  --pb-max 1.5 \
  --dividend-yield-min 0.03 \
  --market-cap-min 5000000000 \
  --turnover-amount-min 50000000 \
  --exclude-st \
  --top 50 \
  --out /tmp/value-screen.md
```

`--as-of` 第一阶段默认只承诺 `latest`。如果传入具体日期，系统必须先查找因子快照缓存；缓存不存在时返回明确错误，而不是静默使用最新数据替代。

输出报告包含：

1. 筛选条件。
2. 数据日期和数据源。
3. 入选股票列表。
4. 因子原始值和排名。
5. 过滤漏斗：
   - 全 A 股数量。
   - 去除 ST 后数量。
   - 去除停牌/低成交额后数量。
   - PE/PB/股息率过滤后数量。
   - 最终 Top N。
6. 数据质量警告。

### 5.2 配置文件筛选

推荐支持 YAML：

```yaml
id: low_valuation_high_dividend
name: 低估值高股息
as_of_date: latest
universe:
  market: all_a
  exclude_st: true
  exclude_suspended: true
  min_listing_days: 180
filters:
  - { field: pe_ttm, operator: ">", value: 0 }
  - { field: pe_ttm, operator: "<=", value: 15 }
  - { field: pb, operator: "<=", value: 1.5 }
  - { field: dividend_yield, operator: ">=", value: 0.03 }
  - { field: market_cap, operator: ">=", value: 5000000000 }
ranking:
  - { field: pe_ttm, ascending: true, weight: 0.4, null_policy: exclude }
  - { field: pb, ascending: true, weight: 0.3, null_policy: exclude }
  - { field: dividend_yield, ascending: false, weight: 0.3, null_policy: exclude }
top_n: 50
```

### 5.3 股票池回测

历史回测 CLI 目标形态：

```bash
uv run python -m akquant.cli stock-pool-backtest \
  --screen-config configs/low_valuation_high_dividend.yaml \
  --start 2016-01-01 \
  --end 2026-06-10 \
  --rebalance quarterly \
  --weight equal \
  --out /tmp/value-factor-backtest.md
```

回测规则：

- 每个调仓日重新生成股票池。
- 默认等权。
- 单只股票最大权重可配置，例如 5%。
- 股票池数量不足时，现金留存或按剩余股票等权，默认现金留存。
- 使用现有 Backtrader 执行层，但需要支持动态股票池。

## 6. 数据质量与风险控制

### 6.1 必须显式处理的问题

| 问题 | 处理方式 |
| --- | --- |
| 负 PE | 不作为“低 PE”优势，默认过滤 |
| PB <= 0 | 视为异常，默认过滤 |
| 股息率缺失 | 可过滤，也可排名时置为最差，默认过滤 |
| 极端股息率 | 超过阈值进入异常标记，例如 > 20% |
| ST 股票 | 默认排除 |
| 停牌股票 | 默认排除 |
| 新股 | 默认排除上市未满 180 日 |
| 低流动性 | 默认用成交额过滤 |
| 财报可见性 | 历史回测必须使用滞后或公告日 |
| 幸存者偏差 | 历史版本必须保留退市和当时股票池，第一阶段报告中披露限制 |

### 6.2 当前阶段限制

第一阶段只承诺：

- 当前截面筛选。
- 最新估值快照。
- 已缓存日期的估值快照读取。
- 报告和 CSV 输出。
- 为未来回测保留数据结构。

第一阶段不承诺：

- 自动重建任意历史日期的全市场估值截面。
- 严格历史财报公告日回测。
- 完整退市股票历史。
- 高频或分钟级回测。
- 实盘交易。

## 7. 与当前项目的集成方式

### 7.1 与 AKShare provider 集成

当前 `akshare_provider.py` 主要负责 ETF/指数价格。

建议扩展为两个 provider：

```text
MarketDataProvider
  - ETF/指数/股票行情
  - price feed
  - return matrix

FundamentalDataProvider
  - 股票列表
  - 实时估值
  - 历史估值
  - 分红数据
```

这样可以避免价格数据和财务数据混在一个类里。

### 7.2 与 PortfolioConfig 集成

筛选模块不直接修改 `PortfolioConfig`。

正确路径是：

```text
ScreenConfig
  -> StockPool
  -> StockPoolPortfolioConfig
  -> Backtrader
```

原因：

- `PortfolioConfig` 适合静态资产配置。
- PE/PB/股息率筛选是动态股票池生成逻辑。
- 两者强行合并会让组合配置变得不可维护。

### 7.3 与 ComparisonReport 集成

未来应支持：

```text
低 PE 组合
低 PB 组合
高股息组合
低 PE + 低 PB + 高股息组合
沪深300基准
```

统一进入 `ComparisonReport`，比较收益、回撤、波动率、夏普、年度收益。

## 8. 推荐实现顺序

### Phase 1：当前截面筛选

1. 新增 `equity_universe.py`。
2. 新增 `fundamentals.py`。
3. 新增 `screening.py`。
4. 新增 `stock_pool.py`。
5. 新增 `screening_reporting.py`。
6. 新增 `screen` CLI。
7. 用 fake AKShare 数据写单元测试。

验收标准：

- 能基于 mock 全 A 股数据筛出 Top N。
- 能正确处理负 PE、缺失 PB、缺失股息率、ST、低成交额。
- 能输出 Markdown 和 CSV。

### Phase 2：因子快照缓存

1. 新增 `factor_store.py`。
2. 每日快照保存为 Parquet。
3. 支持读取指定日期最近可用快照。
4. 支持数据质量摘要。

验收标准：

- 同一日期重复运行优先读缓存。
- 缓存中包含数据源、生成时间、字段版本。

### Phase 3：历史股票池回测

1. 新增 `stock_pool_backtest.py`。
2. 支持月度/季度调仓。
3. 支持等权。
4. 支持单股最大权重。
5. 接入 `ComparisonReport`。

验收标准：

- 能比较低 PE、低 PB、高股息、混合因子四类股票池。
- 报告披露未来函数防护和数据缺失限制。

## 9. 成功标准

一个版本可以交付时，用户应能完成：

```text
1. 获取全 A 股估值截面
2. 设置 PE/PB/股息率过滤条件
3. 设置多因子排序权重
4. 得到 Top N 股票池
5. 查看筛选漏斗和数据警告
6. 导出 Markdown/CSV
7. 后续可把股票池交给回测模块
```

最低可用命令：

```bash
uv run python -m akquant.cli screen \
  --as-of latest \
  --pe-max 15 \
  --pb-max 1.5 \
  --dividend-yield-min 0.03 \
  --top 50 \
  --out /tmp/value-screen.md
```

## 10. 交替审查与修订记录

本节记录本文档完成后的交替审查过程。每一轮发现的问题都已合并进正文。

### 第 1 轮：资深架构师视角

发现问题：

- 初稿容易把 PE/PB/股息率筛选直接塞进现有 `PortfolioConfig`，会让静态资产配置和动态股票池生成混在一起。

修订：

- 增加 `ScreenConfig -> StockPool -> StockPoolPortfolioConfig -> Backtrader` 路径。
- 明确 `PortfolioConfig` 继续服务静态资产配置，筛选模块单独建模。

### 第 2 轮：资深产品经理视角

发现问题：

- 初稿只描述了技术模块，用户无法判断第一阶段到底能用什么。

修订：

- 增加“当前截面筛选”作为 Phase 1。
- 增加 `screen` CLI 示例和报告输出内容。
- 明确第一阶段不承诺严格历史回测。

### 第 3 轮：资深架构师视角

发现问题：

- 股息率口径如果不明确，容易误用 AKShare 的市场级股息率接口。

修订：

- 增加“个股股息率 = trailing cash dividend per share / close price”。
- 明确 `stock_a_gxl_lg` 是市场/板块口径，不作为个股股息率。

### 第 4 轮：资深产品经理视角

发现问题：

- 用户关心“排序和过滤”，但初稿没有解释为什么某些股票被过滤。

修订：

- 增加筛选漏斗。
- 增加过滤原因汇总。
- 要求报告展示被排除数量和原因。

### 第 5 轮：资深架构师视角

发现问题：

- 历史回测没有强调未来函数风险。

修订：

- 增加历史截面回测的可见性约束。
- 增加财报公告日或滞后规则要求。
- 在风险控制中加入幸存者偏差和分红可见性。

### 第 6 轮：资深产品经理视角

发现问题：

- 只做 PE/PB/股息率可能太窄，实际用户还需要基本流动性和规模过滤。

修订：

- 增加总市值、流通市值、成交额过滤。
- 默认排除低流动性股票。

### 第 7 轮：资深架构师视角

发现问题：

- 数据层职责容易膨胀，当前 `akshare_provider.py` 已经承担 ETF/指数价格，如果继续加财务数据会变成大而全模块。

修订：

- 增加 `MarketDataProvider` 与 `FundamentalDataProvider` 分离建议。
- 明确 `fundamentals.py` 负责估值与分红数据。

### 第 8 轮：资深产品经理视角

发现问题：

- 用户需要的是可落地的研究工作流，不只是数据表。

修订：

- 增加从 `ScreenResult` 到 `StockPool` 到回测的链路。
- 增加未来对比低 PE、低 PB、高股息、混合因子的使用场景。

### 第 9 轮：资深架构师视角

发现问题：

- 没有定义缓存和字段版本，后续会导致同一筛选条件跑出不同结果且不可复现。

修订：

- 增加 `factor_store.py`。
- 要求缓存保存数据源、生成时间、字段版本。

### 第 10 轮：资深产品经理视角

发现问题：

- 用户可能误以为第一阶段可以直接做严格十年历史回测。

修订：

- 在“当前阶段限制”和“推荐实现顺序”中明确 Phase 1 只做当前截面筛选。
- 将历史股票池回测放到 Phase 3。

### 第 11 轮：资深架构师视角

审查结果：

- 模块边界清晰。
- 数据口径可追踪。
- 当前截面与历史回测范围分离。
- 与现有 Backtrader / ComparisonReport 集成路径明确。

结论：

- 未发现新的架构性问题。

### 第 12 轮：资深产品经理视角

审查结果：

- 第一阶段用户价值明确。
- 输出报告可解释。
- CLI 示例可执行意图清晰。
- 风险和限制没有过度承诺。

结论：

- 未发现新的产品定义问题。

### 第 13 轮：资深架构师视角

发现问题：

- 文档中“指定日期估值快照”的表述可能被理解为 Phase 1 可以任意重建历史截面，但 AKShare 全市场实时估值更适合 latest，历史日期需要缓存或逐股重建。

修订：

- 将目标改为“最新交易日或已缓存/可重建的指定日期”。
- 明确 `--as-of` 第一阶段默认只承诺 `latest` 和已缓存日期。
- 将任意历史日期重建放到历史回测阶段。

### 第 14 轮：资深产品经理视角

审查结果：

- 第一阶段承诺边界已经清楚。
- 指定日期能力不会误导用户。
- 文档仍保留未来历史回测的演进路线。

结论：

- 未发现新的产品定义问题。

## 11. 最终结论

本文档经过 14 轮交替审查，其中 11 轮发现并修订了问题，第 14 轮未发现新的实质问题，因此停止迭代，未继续到 20 轮。

最终建议：

1. 先实现当前截面筛选。
2. 再实现因子快照缓存。
3. 最后实现历史股票池回测。

这样可以最快让用户拿到可用的数据分析能力，同时为后续严肃回测保留正确架构。
