# 间歇需求补货回测规则登记

- 规模：中型

## 功能模块

| 模块 | 动作 | 接口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 样例采信 | 预览并定位坏行 | `POST /api/stages/intake` | `app/intake/service.py` | `tests/test_intake.py` |
| M2 样本窗口 | 检查领域约束 | `POST /api/stages/prepare` | `app/modules/prepare.py` | `tests/test_prepare.py` |
| M3 需求与库存模拟 | 查看业务计算结果 | `POST /api/stages/calculate` | `app/modules/calculate.py` | `tests/test_calculate.py` |
| M4 缺货对账 | 查看签收判定 | `POST /api/stages/policy` | `app/modules/policy.py` | `tests/test_policy.py` |
| M5 运行对账 | 对照输入、采信和隔离行 | `POST /api/stages/balance` | `app/modules/reconcile.py` | `tests/test_reconcile.py` |
| M6 批次复核 | 执行批次并签发或暂缓 | `POST /api/runs、PATCH /api/runs/<id>` | `app/review/service.py` | `tests/test_review.py` |
| M7 证据交付 | 下载复核清单 | `GET /api/runs/<id>/evidence` | `app/evidence/render.py` | `tests/test_evidence.py` |
| M8 首日加急 | 全仓挑一笔在途货提前到次日 | `POST /api/stages/<stage>、POST /api/runs`（`critical` 标记） | `app/modules/expedite.py` | `tests/test_expedite.py` |

## 输入陷阱

| 编号 | 规则 | 处理 | 测试 |
|---|---|---|---|
| TRAP-02 | 去除 BOM | `app/intake/reader.py` | `tests/test_intake.py::test_bom_preserves_identifier` |
| TRAP-03 | 按逻辑记录读取引号内换行 | `app/intake/reader.py` | `tests/test_intake.py::test_quoted_newline_is_one_logical_record` |
| TRAP-04 | 重复表头计入忽略行 | `app/intake/service.py` | `tests/test_intake.py::test_repeated_header_is_counted` |
| TRAP-05 | 异常列数隔离 | `app/intake/schema.py` | `tests/test_intake.py::test_extra_column_is_isolated` |
| TRAP-06 | 归一化全角数字和千分位 | `app/intake/numeric.py` | `tests/test_intake.py::test_full_width_and_grouping_are_canonical` |
| TRAP-07 | 空值行隔离 | `app/intake/numeric.py` | `tests/test_intake.py::test_sentinel_keeps_row_out_of_total` |
| TRAP-08 | 记录键保留前导零 | `app/intake/schema.py` | `tests/test_intake.py::test_bom_preserves_identifier` |
| TRAP-14 | 冲突版本都进入隔离 | `app/intake/resolve.py` | `tests/test_intake.py::test_duplicate_conflict_removes_both_copies` |
| TRAP-16 | 引号未闭合时拒收文件 | `app/intake/reader.py` | `tests/test_intake.py::test_unclosed_quote_invalidates_source` |
| TRAP-18 | 区分空文件、全空白和仅表头 | `app/intake/reader.py` | `tests/test_intake.py::test_empty_states_have_distinct_causes` |
| TRAP-26 | 拒绝旧版本复核 | `app/review/store.py` | `tests/test_review.py::test_review_optimistic_lock` |

## 领域反例

历史缺行补零需求，正需求间隔从观测起点算起。用精确分数做 Croston 平滑，再乘 1−α/2。补货点为交期需求向上取整。每天先到货、再消耗、最后补到目标，缺货作为失销。回测固定六天，以未满足量占比核对服务要求。

## 首日加急

首日收盘后，全仓最多把一笔原定第三天或更晚的到货提前到次日。候选到货整笔挪动，原到货日删除，加急件先到货再扣当天需求，与原到货对账只入库一次（在途总量不变）。逐笔回放比较两组分数：先比关键件缺货量，再比全仓缺货量；分数相同按到货日、分组、数量排定。若加急前就无改善，则不加急。

加急后任一备件仍超原缺货上限（`basis_points`）或存在无法模拟的分组时整仓暂缓；来源有隔离行或行数不平也不得签发。签发门槛统一为 `report.signoff.ready`。

`sample_data/ready.csv` 的 0001 组会把第 4 天到货提前到第 2 天，关键件缺货与全仓缺货同时下降。`sample_data/incoming.csv` 的 0003 组无法模拟、0004 组仍超上限，因此整仓暂缓。

`sample_data/incoming.csv` 的 0003 组触发预检异常，0004 组触发业务判定。`tests/test_calculate.py` 还核对逐组结论和证据字段。
