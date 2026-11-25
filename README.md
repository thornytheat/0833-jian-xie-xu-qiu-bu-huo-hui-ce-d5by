# 间歇需求补货回测

备件仓计划员可在工作台上传来源 CSV，对照规则判断差异，签发合格批次或记录暂缓意见。

用 SBA 修正间歇需求预测，以逐日库存模拟交期和断货。首日收盘后可全仓挑一笔在途货加急到次日，先保关键件、再保全仓，任一备件仍超原缺货上限则整仓暂缓。

## 启动

```sh
docker compose up --build -d --wait
```

打开 <http://localhost:18332>。页面预览带异常样例。选中阶段查看计算证据，在“首日加急选择”里标记关键件并查看加急结论，选择可签发样例并执行批次，然后提交复核意见。

## 核验

```sh
docker compose exec -T app pytest -q
```

[输入字段](docs/DATA-DICTIONARY.md) · [阶段接口](docs/HTTP.md) · [操作步骤](docs/OPERATIONS.md) · [规则与测试](docs/DEPTH.md)
