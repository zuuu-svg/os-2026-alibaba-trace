#Task 1 — Data quality check & peak window (server_usage.csv)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

col_names = ['timestamp', 'machine_id', 'util_cpu', 'util_mem',
             'util_disk', 'load1', 'load5', 'load15']
df = pd.read_csv('data/server_usage.csv', names=col_names)
INTERVAL = 300           # 預期採樣間隔(秒),下面會驗證
print(df.dtypes)


#1. 數值範圍(找異常值、哨兵值如 -1 或 >100)

print(df[['util_cpu', 'util_mem', 'util_disk', 'load1', 'load5', 'load15']].describe().T)
for c in ['util_cpu', 'util_mem', 'util_disk']:
    bad = df[(df[c] < 0) | (df[c] > 100)]
    print(f'{c}: 超出 0-100 的筆數 = {len(bad)}')

#2. 缺失值與重複紀錄

print(df.isnull().sum())
print('含空值的資料列:')
print(df[df.isnull().any(axis=1)])
dup = df.duplicated(subset=['machine_id', 'timestamp']).sum()
print(f'(machine_id, timestamp) 重複筆數 = {dup}')

#3. 時間覆蓋與採樣間隔

ts = np.sort(df['timestamp'].unique())
gaps = np.diff(ts)
print(f'不同時間點數量: {len(ts)}')
print('相鄰時間點間隔(秒)的種類與次數:')
print(pd.Series(gaps).value_counts())
expected_points = int((ts.max() - ts.min()) / INTERVAL) + 1
print(f'依間隔 {INTERVAL}s 預期時間點數: {expected_points}')

#4. 每台機器的紀錄筆數(找缺漏紀錄)

per_machine = df.groupby('machine_id').size()
print(f'機器數: {per_machine.size}')
print(f'預期每台筆數: {expected_points}')
print(f'筆數不足的機器數: {(per_machine < expected_points).sum()}')
print(f'總缺漏筆數: {per_machine.size * expected_points - len(df):,}'
      f' ({1 - len(df) / (per_machine.size * expected_points):.2%})')
print(per_machine.describe())
per_machine.hist(bins=30)
plt.xlabel('Records per machine'); plt.ylabel('Number of machines')
plt.title('Records per Machine in server_usage.csv')
plt.tight_layout(); plt.savefig('week1_records_per_machine.png', dpi=200); plt.show()

# 5.(選用)和 server_event 比對機器數
# 請先對照官方 schema 確認 machine_id 是第幾欄,再調整 usecols。

import os
if os.path.exists('data/server_event.csv'):
    ev = pd.read_csv('data/server_event.csv', header=None)
    ev_ids = set(ev[1].unique())          # 假設 machine_id 在第 2 欄,請依 schema 確認
    use_ids = set(df['machine_id'].unique())
    print(f'server_event 機器數: {len(ev_ids)}, server_usage 機器數: {len(use_ids)}')
    print('只在 server_event、沒有使用紀錄的機器:', sorted(ev_ids - use_ids))
    print('只在 server_usage、沒有 event 的機器:', sorted(use_ids - ev_ids))
else:
    print('data/server_event.csv 不存在,略過')

# 6. 以數據決定「尖峰」:找平均 CPU 最高的連續 4 小時

df['hour'] = (df['timestamp'] - df['timestamp'].min()) / 3600.0
trend = df.groupby('timestamp')[['util_cpu', 'util_mem']].mean().sort_index()
WIN = int(4 * 3600 / INTERVAL)                      # 4 小時 = 48 個點
roll = trend['util_cpu'].rolling(WIN).mean()
end_ts = roll.idxmax()
start_ts = end_ts - (WIN - 1) * INTERVAL
t0 = df['timestamp'].min()
print(f'平均 CPU 最高的 4 小時視窗: {(start_ts - t0)/3600:.2f}h – {(end_ts - t0 + INTERVAL)/3600:.2f}h')

win = trend.loc[start_ts:end_ts]
rest = trend.drop(win.index)
print('視窗內  平均 CPU / MEM: %.1f%% / %.1f%%' % (win.util_cpu.mean(), win.util_mem.mean()))
print('視窗外  平均 CPU / MEM: %.1f%% / %.1f%%' % (rest.util_cpu.mean(), rest.util_mem.mean()))
gap = trend['util_mem'] - trend['util_cpu']
print('記憶體 − CPU 差距(百分點)統計:')
print(gap.describe())

h = (trend.index - t0) / 3600.0
plt.figure(figsize=(10, 5))
plt.plot(h, trend['util_cpu'], label='Average CPU Utilization (%)')
plt.plot(h, trend['util_mem'], label='Average Memory Utilization (%)')
plt.axvspan((start_ts - t0) / 3600, (end_ts - t0 + INTERVAL) / 3600,
            color='gray', alpha=0.2, label='Selected peak window')
plt.ylim(0, 100); plt.grid(True, linestyle='--', alpha=0.6); plt.legend()
plt.xlabel('Hours Since First Usage Record'); plt.ylabel('Utilization (%)')
plt.title('Cluster-Wide Average Utilization with Selected Peak Window')
plt.tight_layout(); plt.savefig('week1_peak_window.png', dpi=200); plt.show()