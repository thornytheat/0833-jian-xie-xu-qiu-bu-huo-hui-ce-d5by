# 阶段接口

`POST /api/stages/<stage>` 接收 `multipart/form-data`。字段 `sample=dirty`、`sample=clean` 或 `file=<CSV>` 三选一。阶段为 `intake`、`prepare`、`calculate`、`policy`、`balance`。预览不入库。

可选字段 `critical` 标记关键备件（业务分组编号），可重复或逗号分隔。`balance` 及后续阶段的响应含 `expedite`（本批加急选择和前后缺货）与 `signoff`（签发结论及阻止原因）。

`POST /api/runs` 接收同样的输入（含 `critical`），执行全批并返回运行报告。相同来源和相同关键件标记复用同一批次；标记不同视为新批次。`GET /api/runs` 返回最近 50 批。`GET /api/runs/<id>` 查询一批和当前复核状态。

`PATCH /api/runs/<id>` 接收 `revision`、`status` 和 `note`。状态使用 `APPROVED` 或 `HELD`。只有 `report.signoff.ready` 为真时才能签发，否则返回 409 `UNRESOLVED_ISSUES`。冲突返回 409 `STALE_REVIEW`，客户端读取新版本后重试。

`GET /api/runs/<id>/evidence` 下载内含运行清单、行号隔离、业务证据、加急选择、签发结论和复核信息的 JSON。
