"""Reproduce the four-session HW4 analysis and report figures.

Requires matplotlib; raw CSVs are read only. Run from any working directory.
"""
import csv
import json
import statistics as st
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results' / 'analysis'
SOURCES = {
    'hand': 'experiment1_20261106-全部用手.csv',
    'mixed': 'experiment1_20261106-z1z2使用頭_z3z4z5z6使用手.csv',
    'threshold': 'experiment2_20261106-z1z2使用頭_z3z4z5z6使用手.csv',
    'lighting': 'experiment3_20261106-z1z2使用頭_z3z4z5z6使用手.csv',
}
LABELS = {'hand': '全部用手', 'mixed': 'Z1／Z2 用頭，其餘用手', 'threshold': '實驗二', 'lighting': '實驗三'}
COLORS = ['#21867a', '#df8155', '#97a4b5']
ZONES = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']


def load():
    data = {}
    for key, name in SOURCES.items():
        rows = list(csv.DictReader((ROOT / 'results' / name).open(encoding='utf-8-sig')))
        assert len(rows) == {'hand': 30, 'mixed': 30, 'threshold': 27, 'lighting': 18}[key]
        assert len({r['trial_id'] for r in rows}) == len(rows)
        for r in rows:
            for field in ['correct', 'false_trigger', 'missed_trigger']:
                assert r[field] in ['true', 'false']
                r[field] = r[field] == 'true'
            assert sum(r[f] for f in ['correct', 'false_trigger', 'missed_trigger']) == 1
            assert r['correct'] == (r['target_zone'] == r['triggered_zone'])
            assert r['missed_trigger'] == (r['triggered_zone'] == '')
            r['motion_ratio'] = float(r['motion_ratio'])
            r['threshold_value'] = float(r['threshold_value'])
            r['time_s'] = float(r['trigger_time_ms']) / 1000 if r['trigger_time_ms'] else None
            assert 0 <= r['motion_ratio'] <= 1
            assert (r['time_s'] is None) == r['missed_trigger']
        data[key] = rows
    assert Counter(r['target_zone'] for r in data['hand']) == Counter({z: 5 for z in ZONES})
    assert Counter(r['target_zone'] for r in data['mixed']) == Counter({z: 5 for z in ZONES})
    assert Counter((r['threshold_level'], r['target_zone']) for r in data['threshold']) == Counter({(l,z):3 for l in ['Low','Medium','High'] for z in ZONES[:3]})
    assert Counter((r['lighting'], r['target_zone']) for r in data['lighting']) == Counter({(l,z):3 for l in ['Normal Lighting','Dim Lighting'] for z in ZONES[:3]})
    return data


def metrics(rows):
    good = [r for r in rows if r['correct']]
    all_times = [r['time_s'] for r in rows if r['time_s'] is not None]
    times = [r['time_s'] for r in good]
    return dict(n=len(rows), correct=len(good), success_pct=100*len(good)/len(rows),
                false_trigger=sum(r['false_trigger'] for r in rows), missed=sum(r['missed_trigger'] for r in rows),
                mean_all_trigger_s=st.mean(all_times) if all_times else None,
                mean_correct_s=st.mean(times) if times else None, median_correct_s=st.median(times) if times else None,
                mean_correct_motion_pct=100*st.mean(r['motion_ratio'] for r in good) if good else None)


def subset(rows, field, value):
    return [r for r in rows if r[field] == value]


def save(fig, name, note):
    fig.text(.02, .015, note, fontsize=9, color='#566375')
    fig.subplots_adjust(bottom=.2, top=.84, wspace=.35)
    fig.savefig(OUT / (name+'.png'), dpi=220, facecolor='white')
    fig.savefig(OUT / (name+'.svg'), facecolor='white')
    svg_path=OUT / (name+'.svg')
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text().splitlines())+'\n')
    plt.close(fig)


def outcomes(ax, groups, names):
    bottom = np.zeros(len(groups))
    for field, label, color in zip(['correct','false_trigger','missed_trigger'], ['正確','誤觸','漏觸'], COLORS):
        counts = np.array([sum(r[field] for r in a) for a in groups])
        values = np.array([100*c/len(a) for c,a in zip(counts,groups)])
        ax.bar(names, values, bottom=bottom, color=color, label=label, width=.58)
        for i, (value, count) in enumerate(zip(values, counts)):
            if count:
                ax.text(i, bottom[i]+value/2, (f'{value:.1f}%' if value < 10 else f'{value:.1f}%\n({count}/{len(groups[i])})'), ha='center', va='center', fontsize=10, color='white' if field!='missed_trigger' else '#172437')
        bottom += values
    ax.set_ylim(0,100); ax.set_ylabel('試驗比例 (%)'); ax.legend(loc='upper center', bbox_to_anchor=(.5,1.1), ncol=3, frameon=False, fontsize=9)


def success_by_zone(ax, groups, labels, zones):
    x=np.arange(len(zones)); w=.8/len(groups)
    for i,(rows,label) in enumerate(zip(groups,labels)):
        vals=[100*sum(r['correct'] for r in subset(rows,'target_zone',z))/len(subset(rows,'target_zone',z)) for z in zones]
        bars=ax.bar(x+(i-(len(groups)-1)/2)*w, vals, width=w, label=label, color=['#4267a4','#21867a','#df8155'][i])
        ax.bar_label(bars, labels=[f"{sum(r['correct'] for r in subset(rows,'target_zone',z))}/{len(subset(rows,'target_zone',z))}" for z in zones], fontsize=8, padding=3)
    ax.set_xticks(x, zones); ax.set_ylim(0,118); ax.set_yticks([0,25,50,75,100]); ax.set_ylabel('各目標區成功率 (%)'); ax.legend(fontsize=8, frameon=False, loc='lower center', bbox_to_anchor=(.5,-.25))


def times(ax, groups, labels):
    for i,rows in enumerate(groups):
        t=[r['time_s'] for r in rows if r['correct']]
        ax.scatter(i+np.linspace(-.12,.12,len(t)),t,s=23,color='#4267a4',alpha=.7)
        if t:
            ax.hlines(st.mean(t),i-.23,i+.23,color='#df8155',lw=3)
            ax.text(i, st.mean(t)+.13,f'平均 {st.mean(t):.2f}s',ha='center',fontsize=9, bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=1))
    ax.set_xticks(range(len(labels)),labels); ax.set_ylabel('正確試驗觸發時間 (秒)'); ax.set_ylim(0, max(r['time_s'] for group in groups for r in group if r['correct'])*1.28)
    ax.set_title('圓點：各正確試驗；橫線：平均',fontsize=10)


def table(groups):
    lines=['| 條件 | n | 正確 | 成功率 | 誤觸 | 漏觸 | 所有已觸發平均秒 | 正確觸發平均秒 | 正確觸發中位秒 | 正確試驗平均 motion ratio |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for label,rows in groups:
        m=metrics(rows)
        fmt=lambda x: '—' if x is None else f'{x:.3f}'
        lines.append(f"| {label} | {m['n']} | {m['correct']} | {m['success_pct']:.1f}% | {m['false_trigger']} | {m['missed']} | {fmt(m['mean_all_trigger_s'])} | {fmt(m['mean_correct_s'])} | {fmt(m['median_correct_s'])} | {(fmt(m['mean_correct_motion_pct'])+'%') if m['mean_correct_motion_pct'] is not None else '—'} |")
    return '\n'.join(lines)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    font='/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
    if Path(font).exists():
        font_manager.fontManager.addfont(font)
        plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.unicode_minus':False,'svg.fonttype':'path'})
    d=load(); groups=[d['hand'],d['mixed']]; names=['全部用手','頭手混用']
    fig,axs=plt.subplots(1,3,figsize=(15,5.5)); fig.suptitle('實驗一：操作媒介調整後，跨區誤觸減少',fontsize=18)
    outcomes(axs[0],groups,names); success_by_zone(axs[1],groups,names,ZONES); times(axs[2],groups,names)
    save(fig,'01_exp1_input_comparison','每組 30 次，各目標區 5 次；相同正常光線與門檻 5.5961%。時間僅計正確試驗，兩組成功試驗組成不同。')
    fig,axs=plt.subplots(1,2,figsize=(11,5.5)); fig.suptitle('實驗一：目標區與實際觸發區',fontsize=18)
    for ax,rows,label in zip(axs,groups,names):
        matrix=np.array([[sum(r['target_zone']==a and r['triggered_zone']==b for r in rows) for b in ZONES] for a in ZONES])
        ax.imshow(matrix,cmap='Blues',vmin=0,vmax=5)
        for i in range(6):
            for j in range(6): ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>=3 else '#172437')
        ax.set_xticks(range(6),ZONES); ax.set_yticks(range(6),ZONES); ax.set_xlabel('實際觸發區'); ax.set_ylabel('目標區'); ax.set_title(label)
    save(fig,'02_exp1_confusion','格內為次數；對角線為正確觸發。全手操作：Z1 全部觸發 Z3，Z2 觸發 Z6 四次、Z5 一次。')
    levels=['Low','Medium','High']; g=[subset(d['threshold'],'threshold_level',l) for l in levels]; labels=['Low\n4.03%','Medium\n5.60%','High\n17.86%']
    fig,axs=plt.subplots(1,3,figsize=(15,5.5)); fig.suptitle('實驗二：高門檻使成功率下降，漏觸集中於上方操作區',fontsize=18)
    outcomes(axs[0],g,labels); success_by_zone(axs[1],g,levels,ZONES[:3]); times(axs[2],g,labels)
    save(fig,'03_exp2_threshold','各門檻 9 次，各目標區 3 次；全部使用頭手混用。High 的正確試驗只有 Z3，時間比較須連同成功率解讀。')
    g=[subset(d['lighting'],'lighting',l) for l in ['Normal Lighting','Dim Lighting']]; labels=['正常光線','昏暗光線']
    fig,axs=plt.subplots(1,3,figsize=(15,5.5)); fig.suptitle('實驗三：昏暗光線下，Z1 的三次操作均誤觸 Z2',fontsize=18)
    outcomes(axs[0],g,labels); success_by_zone(axs[1],g,labels,ZONES[:3]); times(axs[2],g,labels)
    save(fig,'04_exp3_lighting','每種光線 9 次，各目標區 3 次；頭手混用，固定門檻 5.5961%。昏暗先於正常執行，切換後重設背景。')
    summary=[]
    allgroups=[(LABELS[k],d[k]) for k in d]
    allgroups += [('實驗二 '+l,subset(d['threshold'],'threshold_level',l)) for l in levels]
    allgroups += [('實驗三 '+l,subset(d['lighting'],'lighting',l)) for l in ['Normal Lighting','Dim Lighting']]
    for label,rows in allgroups: summary.append(dict(condition=label,**metrics(rows)))
    with (OUT/'summary_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(summary)
    (OUT/'validation.json').write_text(json.dumps({'total_trials':sum(map(len,d.values())),'sources':SOURCES,'checks':'row counts, unique trial IDs per source, balanced cells, outcome flags, correct-zone agreement, missing-time semantics passed'},ensure_ascii=False,indent=2),encoding='utf-8')
    report = ['# HW4 實驗結果與討論','', '## 資料與指標定義','',
      '四份 CSV 共 105 次試驗：實驗一新增一組操作媒介比較，因此實驗一為 60 次，實驗二 27 次、實驗三 18 次。已核對各組次數、條件格數、trial_id 唯一性與結果旗標，未刪除任何試驗。實驗二與三均採 Z1／Z2 用頭，Z3–Z6 用手。',
      '成功率為正確觸發次數／總試驗次數；誤觸指試驗中第一個觸發區與目標區不同，漏觸指逾時未觸發。誤觸率的分母為正式試驗次數，不代表無操作時的背景誤觸頻率。觸發時間從按下開始計時至偵測觸發，包含人的反應與動作時間，並非純演算法處理延遲。',
      '時間表同時列出所有有觸發試驗（包含誤觸）及正確試驗的平均值。漏觸時間為缺值，不以 0 秒取代，也不當作成功觸發時間。motion ratio 在成功時是目標區觸發當幀的比例，誤觸時屬於錯誤觸發區，漏觸時是目標區在試驗內的最大比例；因此以下平均 motion ratio 僅計正確試驗。',
      '', '## 實驗一：操作媒介的調整','',table([(LABELS[k],d[k]) for k in ['hand','mixed']]),'',
      '兩組均為正常光線、固定門檻 5.5961%、各指令五次。全手操作正確 19/30（63.3%），頭手混用正確 28/30（93.3%），增加 30.0 個百分點。誤觸由 11 次降為 2 次，減少 9 次（相對減少 81.8%）；兩組均無漏觸。',
      '差異主要集中於閱讀區：全手操作的 Z1、Z2 各 0/5；混用後 Z1 為 3/5、Z2 為 5/5。全手操作 Z1 的五次均誤觸 Z3，Z2 的五次分別誤觸 Z6 四次與 Z5 一次，顯示上方目標操作常被下方工具列區域先觸發。',
      '操作過程觀察到，使用手觸及上方 Z1／Z2 時，容易伴隨較大幅度的手臂及身體移動，使其他區域出現前景變化。改以頭部控制上方兩區後，本次記錄的誤觸次數減少。這個機制是測試者的質性觀察；CSV 能支持跨區錯誤的分布，沒有直接測量身體位移或每一幀各區變化，故不能單靠這些資料證明身體移動是唯一原因。',
      '此結果說明背景減除能接受不同動作媒介：系統辨識的是前景變化，並沒有新增頭部或手部偵測。互動方式應配合鏡頭中身體位置、目標區高度與移動路徑設計。',
      '', '### 各指令結果','',table([(f'{LABELS[k]} {z}',subset(d[k],'target_zone',z)) for k in ['hand','mixed'] for z in ZONES]),'',
      '![操作方式比較](01_exp1_input_comparison.png)','![混淆矩陣](02_exp1_confusion.png)',
      '', '## 實驗二：門檻的影響','',table([(l,subset(d['threshold'],'threshold_level',l)) for l in levels]),'',
      'Low（4.03%）與 Medium（5.60%）皆為 9/9 正確、無誤觸與漏觸。High（17.86%）只有 3/9 正確，另有 1 次誤觸及 5 次漏觸；三次正確均為 Z3。Z1 在 High 為兩次漏觸、一次誤觸 Z5，Z2 的三次均漏觸。',
      'High 的五次漏觸，其目標區最大 motion ratio 均低於 17.86%（約 11.41%–17.82%），支持門檻過高會排除本次自然操作的解釋。逐幀 motion ratio 未保存，無法進一步重建連續 K 幀的時間歷程。',
      'Medium 的正確觸發平均時間低於 Low，但兩者各僅九次，這項小差異不足以宣稱 Medium 普遍較快或為最佳門檻；本次資料只能支持 Low／Medium 在目前操作條件下皆可用，而 High 不適合上方兩區。',
      '',table([(f'{l} {z}',[r for r in d['threshold'] if r['threshold_level']==l and r['target_zone']==z]) for l in levels for z in ZONES[:3]]),'',
      '![門檻比較](03_exp2_threshold.png)',
      '', '## 實驗三：光線的影響','',table([(l,subset(d['lighting'],'lighting',l)) for l in ['Normal Lighting','Dim Lighting']]),'',
      '正常光線為 9/9 正確，昏暗光線為 6/9 正確，下降 33.3 個百分點；兩種光線均無漏觸。昏暗的三次失敗皆為 Z1 誤觸 Z2，Z2 與 Z3 各為 3/3 正確，因此錯誤集中在左右閱讀區的區分，不能概括成所有指令都因昏暗而失效。',
      '正確試驗平均觸發時間在昏暗條件較長，但昏暗條件排除了三次 Z1 失敗，兩組成功試驗的命令組成不同。應同時閱讀各指令表，不把整體平均時間當成同一批動作的純光線效果。背景模型在切換光線後重新學習，因此此實驗比較穩定後的正常／昏暗條件，不衡量調光瞬間的干擾。',
      '',table([(f'{l} {z}',[r for r in d['lighting'] if r['lighting']==l and r['target_zone']==z]) for l in ['Normal Lighting','Dim Lighting'] for z in ZONES[:3]]),'',
      '![光線比較](04_exp3_lighting.png)',
      '', '## 結果的適用範圍','',
      '這是同一測試者、同一設備與環境的探索性重複試驗，試驗次數不能視為獨立參與者數。全手組先於頭手混用組，可能存在練習、策略調整與時間順序效應；實驗三昏暗組先於正常組，也有順序效應的可能。未記錄照度、相機曝光參數、K 與 Cooldown 的逐次設定，無法由 CSV 確認其物理光線差異或所有控制變項。',
      '本次新增的操作媒介比較是對發現問題後進行的探索性設計調整，應在報告中明確描述；實驗二與三僅針對調整後的頭手混用方式，結果不宜直接外推到全手操作。未進行顯著性檢定或宣稱普遍因果效果。後續可透過更多測試者、對調操作順序、固定攝影機位置、量測照度及保存逐幀區域數值，檢驗媒介調整能否穩定改善誤觸。',
      '', '## 資料來源與重現','',
      *[f'- [{name}](../{name})' for name in SOURCES.values()],
      '', '執行 `python analyze_experiments.py` 重新產生本報告、summary_metrics.csv 與四組 PNG／SVG 圖表；需安裝 matplotlib。原始 CSV 不會被修改。圖表時間分布只顯示正確試驗，橫線為平均值；各圖均標示分母，未繪製不適當的參與者信賴區間。']
    (OUT/'RESULTS_ANALYSIS.md').write_text('\n\n'.join(report),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
