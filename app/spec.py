COLUMNS = ('day', 'quantity', 'lead_time', 'alpha', 'basis_points')
KINDS = ('history', 'demand', 'receipt', 'scenario')
PROJECT = {'name': '间歇需求补货回测', 'actor': '备件仓计划员', 'stages': [('intake', '样例采信'), ('prepare', '样本窗口'), ('calculate', '需求与库存模拟'), ('policy', '缺货对账'), ('balance', '运行对账')], 'chart': '补货到达日', 'mark': '间'}
