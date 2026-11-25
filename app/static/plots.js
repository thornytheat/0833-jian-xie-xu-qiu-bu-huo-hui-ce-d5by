import {element} from './client.js';

function block(target,className,content) {
  const node=element('div',content,{class:className});
  target.append(node);
  return node;
}
const note=(target,text)=>block(target,'chart-note',text);

export function visualize(report,selected) {
  const target=document.querySelector('#visual');
  target.replaceChildren();
  const measurement=report.cases?.find(row=>row.case===selected)?.measure;
  if (!measurement) {block(target,'chart-note','选择有计算值的分组');return;}
  const e=measurement.evidence;

  const line=block(target,'receipts');
  for(const [day,quantity] of Object.entries(e.orders)) {
    const item=block(line,'receipt',`${day} 日到货`); block(item,'arrival',`${quantity} 件`);
  }
  note(target,`补货点 ${e.reorder} 件 · 未满足 ${e.unserved} 件 · 期末 ${e.closing} 件`);
}
