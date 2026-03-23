import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import rc
import platform
from datetime import datetime
from scipy import stats

# =============================================
# 0. 환경 설정
# =============================================
plt.rcParams['axes.unicode_minus'] = False
if platform.system() == 'Darwin':    rc('font', family='AppleGothic')
elif platform.system() == 'Windows': rc('font', family='Malgun Gothic')
else: plt.rcParams['font.family'] = 'sans-serif'

# =============================================
# 1. v11 유니버스
# =============================================
tickers_map = {
    "K Nuclear":      "434730.KS",
    "JP Semi Mat":    "464920.KS",
    "Global Obesity": "476070.KS",
    "US AI Power":    "487230.KS",
    "Global Defense": "478150.KS",
    "AI Cybersec":    "418670.KS",
    "Gold Miners":    "473640.KS",
    "US Energy":      "474800.KS",
    "US Semi(Phlx)":  "381180.KS",
    "Quantum":        "498270.KS",
    "US TechTop10":   "381170.KS",
}
GOLD_CODE = "411060.KS"
TIPS_CODE = "468370.KS"
BOND_CODE = "308620.KS"
CASH_CODE = "456610.KS"
BM_TICKER = "069500.KS"
DEFENSE_POOL  = {GOLD_CODE, TIPS_CODE, BOND_CODE, CASH_CODE}
ATTACK_TICKERS = [t for t in tickers_map.values()]

# =============================================
# 2. 데이터 다운로드 (일별)
# =============================================
data_start     = "2020-01-01"
backtest_start = "2022-01-01"
end_date       = datetime.today().strftime('%Y-%m-%d')
all_codes = list(set(
    ATTACK_TICKERS +
    [GOLD_CODE, TIPS_CODE, BOND_CODE, CASH_CODE, BM_TICKER]
))
print(f"일별 데이터 다운로드: {data_start} ~ {end_date}")
raw = yf.download(all_codes, start=data_start, end=end_date,
                  progress=False, auto_adjust=True)
if isinstance(raw.columns, pd.MultiIndex):
    data = raw['Close'] if 'Close' in raw.columns.get_level_values(0) \
           else raw['Adj Close']
else:
    data = raw
data = data.ffill()

# 200일 이동평균 (일별)
ma200_daily = data.rolling(200).mean()
print(f"데이터 로드 완료: {len(data)}일 x {len(data.columns)}종목")

# =============================================
# 3. 리밸런싱 날짜 생성
# =============================================
def get_rebal_dates(data, mode):
    """
    mode:
      'end'   = 매월 마지막 영업일 (신호 생성일 = 집행일)
      'begin' = 매월 첫 번째 영업일 (전월말 신호 → 당월초 집행)
      'mid'   = 매월 10~12번째 영업일 (월중 집행)
    """
    biz_days = data.index
    if mode == 'end':
        # 매월 마지막 영업일 = 신호+집행 동일
        dates = biz_days.to_series().groupby(
            biz_days.to_period('M')).last()
        return list(dates)
    elif mode == 'begin':
        # 매월 첫 번째 영업일
        dates = biz_days.to_series().groupby(
            biz_days.to_period('M')).first()
        return list(dates)
    elif mode == 'mid':
        # 매월 10~12번째 영업일 (월 중순)
        result = []
        for period, group in biz_days.to_series().groupby(biz_days.to_period('M')):
            days = list(group)
            # 10번째 영업일 (인덱스 9), 없으면 마지막
            idx = min(9, len(days) - 1)
            result.append(days[idx])
        return result
    return []

dates_end   = get_rebal_dates(data, 'end')
dates_begin = get_rebal_dates(data, 'begin')
dates_mid   = get_rebal_dates(data, 'mid')

# backtest_start 이후만
dates_end   = [d for d in dates_end   if d >= pd.Timestamp(backtest_start)]
dates_begin = [d for d in dates_begin if d >= pd.Timestamp(backtest_start)]
dates_mid   = [d for d in dates_mid   if d >= pd.Timestamp(backtest_start)]
print(f"\n리밸런싱 날짜 수: 월말={len(dates_end)}, 월초={len(dates_begin)}, 월중={len(dates_mid)}")

# =============================================
# 4. 모멘텀·방어 유틸
# =============================================
def check_200dma_daily(code, signal_date):
    """signal_date 기준 200DMA 통과 여부 (T-1 원칙)"""
    if code not in data.columns:
        return False
    # signal_date 이전 마지막 유효 날짜
    prev_dates = data.index[data.index < signal_date]
    if len(prev_dates) == 0:
        return False
    t1 = prev_dates[-1]
    prc = data.loc[t1, code]
    ma  = ma200_daily.loc[t1, code]
    return pd.notna(prc) and pd.notna(ma) and prc >= ma

def get_momentum_daily(signal_date, lookback_days_map=None):
    """
    signal_date T-1 기준 복합 모멘텀
    lookback_days_map = {3M: 63, 6M: 126, 12M: 252} 영업일 근사
    """
    prev_dates = data.index[data.index < signal_date]
    if len(prev_dates) < 252:
        return {}
    t1 = prev_dates[-1]
    scores = {}
    for ticker in ATTACK_TICKERS:
        if ticker not in data.columns:
            continue
        prc_t1 = data.loc[t1, ticker]
        if pd.isna(prc_t1):
            continue
        ret_3m = ret_6m = ret_12m = np.nan
        for days, attr in [(63, '3m'), (126, '6m'), (252, '12m')]:
            idx = max(0, len(prev_dates) - days - 1)
            t_back = prev_dates[idx]
            prc_back = data.loc[t_back, ticker]
            if pd.notna(prc_back) and prc_back > 0:
                ret = prc_t1 / prc_back - 1
                if attr == '3m':  ret_3m  = ret
                if attr == '6m':  ret_6m  = ret
                if attr == '12m': ret_12m = ret
        if not any(np.isnan(x) for x in [ret_3m, ret_6m, ret_12m]):
            scores[ticker] = ret_3m*0.20 + ret_6m*0.30 + ret_12m*0.50
    return scores

def get_defense_daily(signal_date, skip_gold=False):
    if not skip_gold and check_200dma_daily(GOLD_CODE, signal_date):
        return GOLD_CODE, "Gold"
    if check_200dma_daily(TIPS_CODE, signal_date):
        return TIPS_CODE, "TIPS"
    if check_200dma_daily(BOND_CODE, signal_date):
        return BOND_CODE, "T-Bond"
    if CASH_CODE in data.columns:
        return CASH_CODE, "SOFR"
    return "RAW_CASH", "Cash"

# =============================================
# 5. 백테스트 엔진 (날짜 리스트 기반)
# =============================================
def run_backtest_daily(rebal_dates, label):
    """
    rebal_dates: 리밸런싱 집행일 리스트
    신호는 집행일 T-1 기준 (T-1 원칙)
    수익률은 집행일 D → 다음 집행일 D+1 사이 일별 수익률 합산
    """
    returns      = []
    prev_holdings = []
    prev_holdings_set = set()
    history      = {}

    for i in range(len(rebal_dates) - 1):
        signal_date = rebal_dates[i]    # 신호 생성 (T-1 원칙 내장)
        hold_from   = rebal_dates[i]    # 보유 시작
        hold_to     = rebal_dates[i+1]  # 다음 리밸런싱 직전

        # 신호 생성
        mom_scores = get_momentum_daily(signal_date)
        sorted_t = sorted(mom_scores, key=mom_scores.get, reverse=True)

        # 2% 버퍼룰
        if len(sorted_t) >= 4:
            r3, r4 = sorted_t[2], sorted_t[3]
            if (r4 in prev_holdings) and (r3 not in prev_holdings):
                diff = mom_scores.get(r3, 0) - mom_scores.get(r4, 0)
                final_top3 = sorted_t[:2] + ([r4] if diff < 0.02 else [r3])
            else:
                final_top3 = sorted_t[:3]
        else:
            final_top3 = sorted_t[:3]

        # 절대모멘텀 + 4단계 방어
        actual_holdings = []
        for k in range(3):
            if k < len(final_top3):
                asset = final_top3[k]
                if check_200dma_daily(asset, signal_date):
                    actual_holdings.append(asset)
                else:
                    d, _ = get_defense_daily(signal_date,
                                             skip_gold=(asset == GOLD_CODE))
                    actual_holdings.append(d)
            else:
                actual_holdings.append(BM_TICKER)

        # 거래비용
        curr_set = set(x for x in actual_holdings if x not in ('RAW_CASH',))
        cost = (len(curr_set - prev_holdings_set) / 3) * 0.0015

        # 보유 기간 일별 수익률 합산 (동일가중 1/3씩)
        hold_days = data.index[(data.index >= hold_from) &
                               (data.index < hold_to)]
        if len(hold_days) < 2:
            continue
        period_ret = 0.0
        for asset in actual_holdings:
            if asset == 'RAW_CASH' or asset not in data.columns:
                continue
            sub = data.loc[hold_days, asset].pct_change().fillna(0)
            period_ret += (1 + sub).prod() - 1
        period_ret = period_ret / 3 - cost

        returns.append({
            'Date':    hold_to,
            'Return':  period_ret,
            'N_days':  len(hold_days),
        })
        history[signal_date.strftime('%Y-%m-%d')] = actual_holdings
        prev_holdings = actual_holdings
        prev_holdings_set = curr_set

    if not returns:
        return pd.DataFrame(), {}

    res = pd.DataFrame(returns).set_index('Date')

    # BM 수익률
    bm_ret = []
    for i in range(len(rebal_dates) - 1):
        hf = rebal_dates[i]
        ht = rebal_dates[i+1]
        hd = data.index[(data.index >= hf) & (data.index < ht)]
        if len(hd) < 2 or BM_TICKER not in data.columns:
            bm_ret.append(0.0)
        else:
            sub = data.loc[hd, BM_TICKER].pct_change().fillna(0)
            bm_ret.append((1 + sub).prod() - 1)
    res['BM_Return'] = bm_ret[:len(res)]
    res['Cum']    = (1 + res['Return']).cumprod()
    res['BM_Cum'] = (1 + res['BM_Return']).cumprod()
    res['DD']     = res['Cum'] / res['Cum'].cummax() - 1
    return res, history

# =============================================
# 6. 3개 타이밍 실행
# =============================================
print("\n백테스트 실행 중 (3개 타이밍 × 일별 데이터)...")
print("  [1/3] 월말 리밸런싱...")
r_end,   h_end   = run_backtest_daily(dates_end,   "월말")
print("  [2/3] 월초 리밸런싱...")
r_begin, h_begin = run_backtest_daily(dates_begin, "월초")
print("  [3/3] 월중 리밸런싱...")
r_mid,   h_mid   = run_backtest_daily(dates_mid,   "월중(10번째 영업일)")
print("  완료!")

# =============================================
# 7. 성과 지표 계산
# =============================================
def calc_stats(res, label):
    if len(res) == 0:
        return {}
    years   = (res.index[-1] - res.index[0]).days / 365.25
    cagr    = res['Cum'].iloc[-1] ** (1/years) - 1
    mdd     = res['DD'].min()
    sharpe  = res['Return'].mean() / res['Return'].std() * np.sqrt(12) \
              if res['Return'].std() > 0 else np.nan
    neg_std = res['Return'][res['Return'] < 0].std()
    sortino = res['Return'].mean() / neg_std * np.sqrt(12) \
              if neg_std > 0 else np.nan
    calmar  = cagr / abs(mdd) if mdd != 0 else np.nan
    win     = (res['Return'] > 0).mean() * 100
    bm_cagr = res['BM_Cum'].iloc[-1] ** (1/years) - 1
    vol     = res['Return'].std() * np.sqrt(12)
    skew    = stats.skew(res['Return'].dropna())
    kurt    = stats.kurtosis(res['Return'].dropna())
    return {
        'label': label, 'years': years,
        'cum':   res['Cum'].iloc[-1] - 1,
        'cagr':  cagr, 'mdd': mdd,
        'sharpe': sharpe, 'sortino': sortino,
        'calmar': calmar, 'win': win,
        'alpha':  cagr - bm_cagr, 'bm_cagr': bm_cagr,
        'vol': vol, 'skew': skew, 'kurt': kurt,
    }

m_end   = calc_stats(r_end,   "월말")
m_begin = calc_stats(r_begin, "월초")
m_mid   = calc_stats(r_mid,   "월중")

# =============================================
# 8. 성과 출력
# =============================================
W = 82
print()
print("=" * W)
print("  리밸런싱 타이밍 비교 — 월말 / 월초 / 월중(10번째 영업일)")
print(f"  기간: {r_end.index[0].date()} ~ {r_end.index[-1].date()}")
print(f"  모멘텀: 3M×20%+6M×30%+12M×50% | TOP3 | 2%버퍼 | 4단계방어 | T-1신호")
print("=" * W)
print(f"  {'지표':<18} {'월말':>12} {'월초':>12} {'월중':>12} {'KOSPI200':>10}")
print("-" * W)

metrics_list = [
    ("누적수익률(%)",  'cum',     100),
    ("CAGR(%)",       'cagr',    100),
    ("MDD(%)",        'mdd',     100),
    ("변동성(%,연)",  'vol',     100),
    ("Sharpe",        'sharpe',    1),
    ("Sortino",       'sortino',   1),
    ("Calmar",        'calmar',    1),
    ("월승률(%)",     'win',       1),
    ("Alpha(%p)",     'alpha',   100),
    ("왜도(Skew)",    'skew',      1),
    ("첨도(Kurt)",    'kurt',      1),
]

for name, key, mult in metrics_list:
    ve = m_end.get(key, np.nan)   * mult
    vb = m_begin.get(key, np.nan) * mult
    vm = m_mid.get(key, np.nan)   * mult
    bm = (m_end.get('bm_cagr', np.nan) * mult
          if key in ('cagr', 'cum', 'alpha') else None)
    vals = [v for v in [ve, vb, vm] if not np.isnan(v)]
    if not vals: continue
    if 'MDD' in name:
        best = max(vals)
    else:
        best = max(vals)
    def fmt(v):
        if np.isnan(v): return f"{'N/A':>11}"
        star = "★" if abs(v - best) < abs(best) * 0.01 + 0.005 else " "
        return f"{star}{v:>10.2f}"
    bm_s = f"{bm:>9.2f}" if bm is not None else f"{'—':>9}"
    print(f"  {name:<18} {fmt(ve)} {fmt(vb)} {fmt(vm)} {bm_s}")

print("=" * W)
print("  ★ = 해당 지표 최고값  |  MDD는 0에 가까울수록(덜 음수) ★")

# =============================================
# 9. 연도별 수익률
# =============================================
print(f"\n[연도별 수익률]")
print(f"  {'연도':<6} {'월말':>10} {'월초':>10} {'월중':>10} {'KOSPI200':>12} {'최고':>6}")
print("  " + "-" * 56)
all_years = sorted(set(r_end.index.year) |
                   set(r_begin.index.year) |
                   set(r_mid.index.year))
for yr in all_years:
    def yr_ret(res):
        mask = res.index.year == yr
        if mask.sum() == 0: return np.nan
        return (1 + res.loc[mask, 'Return']).prod() - 1
    def yr_bm(res):
        mask = res.index.year == yr
        if mask.sum() == 0: return np.nan
        return (1 + res.loc[mask, 'BM_Return']).prod() - 1
    re = yr_ret(r_end)   * 100
    rb = yr_ret(r_begin) * 100
    rm = yr_ret(r_mid)   * 100
    bm = yr_bm(r_end)    * 100
    vals = {v: n for v, n in [(re,'월말'),(rb,'월초'),(rm,'월중')]
            if not np.isnan(v)}
    best_name = max(vals, key=lambda x: x) if vals else "?"
    best_label = vals.get(best_name, "?")
    print(f"  {yr:<6} {re:>9.2f}% {rb:>9.2f}% {rm:>9.2f}% "
          f"{bm:>11.2f}%  {best_label}")

# =============================================
# 10. 월별 수익률 차이 통계 (t-검정)
# =============================================
print(f"\n[타이밍 간 차이 통계 유의성 — Paired t-test]")
print(f"  H0: 두 타이밍의 수익률 분포에 유의미한 차이 없음")
common_idx = r_end.index.intersection(r_begin.index).intersection(r_mid.index)
r_e = r_end.loc[common_idx, 'Return']
r_b = r_begin.loc[common_idx, 'Return']
r_m = r_mid.loc[common_idx, 'Return']
pairs = [
    ("월말 vs 월초", r_e, r_b),
    ("월말 vs 월중", r_e, r_m),
    ("월초 vs 월중", r_b, r_m),
]
for pname, s1, s2 in pairs:
    t_stat, p_val = stats.ttest_rel(s1.dropna(), s2.dropna())
    sig = "※유의" if p_val < 0.05 else "비유의"
    avg_diff = (s1 - s2).mean() * 100
    print(f"  {pname:<18}: t={t_stat:>6.3f}, p={p_val:.4f}  "
          f"평균차이={avg_diff:>+7.4f}%p  [{sig}]")

# =============================================
# 11. 리밸런싱 일수 분포
# =============================================
print(f"\n[리밸런싱 주기 (보유 일수) 통계]")
for res, lbl in [(r_end,'월말'),(r_begin,'월초'),(r_mid,'월중')]:
    if 'N_days' in res.columns:
        nd = res['N_days']
        print(f"  {lbl}: 평균={nd.mean():.1f}일  "
              f"최소={nd.min()}일  최대={nd.max()}일  "
              f"표준편차={nd.std():.1f}일")

# =============================================
# 12. 시각화
# =============================================
fig = plt.figure(figsize=(14, 16))
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.40, wspace=0.28)
CE   = '#378ADD'   # 월말 파랑
CB2  = '#1D9E75'   # 월초 녹색
CM   = '#D85A30'   # 월중 주황
CBM2 = '#9E9E9E'   # 벤치마크

# 패널 1: 누적 수익률
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(r_end['Cum'],   color=CE,   linewidth=2.0,
         label=f"월말  CAGR {m_end['cagr']*100:.1f}%  MDD {m_end['mdd']*100:.1f}%")
ax1.plot(r_begin['Cum'], color=CB2,  linewidth=2.0,
         label=f"월초  CAGR {m_begin['cagr']*100:.1f}%  MDD {m_begin['mdd']*100:.1f}%")
ax1.plot(r_mid['Cum'],   color=CM,   linewidth=2.0,
         label=f"월중  CAGR {m_mid['cagr']*100:.1f}%  MDD {m_mid['mdd']*100:.1f}%")
ax1.plot(r_end['BM_Cum'], color=CBM2, linewidth=1.2, linestyle='--',
         label=f"KOSPI200 CAGR {m_end['bm_cagr']*100:.1f}%")
ax1.set_title('누적 수익률 비교', fontsize=13, fontweight='bold')
ax1.legend(fontsize=10); ax1.grid(True, alpha=0.25); ax1.set_ylabel('배')

# 패널 2: MDD
ax2 = fig.add_subplot(gs[1, :])
ax2.fill_between(r_end.index,   r_end['DD']*100,   0,
                 color=CE,  alpha=0.30, label=f"월말  MDD {m_end['mdd']*100:.1f}%")
ax2.fill_between(r_begin.index, r_begin['DD']*100, 0,
                 color=CB2, alpha=0.30, label=f"월초  MDD {m_begin['mdd']*100:.1f}%")
ax2.fill_between(r_mid.index,   r_mid['DD']*100,   0,
                 color=CM,  alpha=0.30, label=f"월중  MDD {m_mid['mdd']*100:.1f}%")
ax2.set_title('드로우다운', fontsize=13, fontweight='bold')
ax2.legend(fontsize=10); ax2.grid(True, alpha=0.25); ax2.set_ylabel('DD (%)')

# 패널 3·4: 월간 수익률 분포
for ax, res, lbl, clr in [
    (fig.add_subplot(gs[2, 0]), r_end,   "월말", CE),
    (fig.add_subplot(gs[2, 1]), r_begin, "월초", CB2),
]:
    ax.hist(res['Return']*100, bins=25, color=clr, edgecolor='white', alpha=0.8)
    ax.axvline(0, color='red', linestyle='--', linewidth=1.2)
    ax.axvline(res['Return'].mean()*100, color='orange', linestyle=':',
               linewidth=1.5, label=f"평균 {res['Return'].mean()*100:.2f}%")
    mn = calc_stats(res, lbl)
    ax.set_title(f"{lbl} 수익률 분포  (승률 {mn['win']:.1f}%  Sharpe {mn['sharpe']:.2f})",
                 fontsize=11, fontweight='bold')
    ax.set_xlabel('Period Return (%)')
    ax.legend(fontsize=9); ax.grid(True, alpha=0.25)

fig.suptitle(
    f"리밸런싱 타이밍 비교: 월말 vs 월초 vs 월중(10번째 영업일)\n"
    f"기간: {r_end.index[0].date()} ~ {r_end.index[-1].date()} "
    f"| 3M×20%+6M×30%+12M×50% | TOP3 | 2%버퍼 | 4단계방어 | T-1신호원칙",
    fontsize=11, y=0.998
)

out = '/home/claude/rebal_timing_result.png'
plt.savefig(out, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n그래프 저장: {out}")
print("""
[결과 해석 가이드]
1. t-test p < 0.05 → 타이밍 간 차이가 통계적으로 유의미
   p ≥ 0.05       → 차이가 통계적 노이즈 수준
2. MDD 차이 주목
   리밸런싱 타이밍은 수익률보다 MDD(리스크)에 더 큰 영향을 줄 수 있음
   특히 월말 결산일 주변 변동성 vs 월중 안정구간 비교
3. 왜도(Skew) 해석
   양(+): 이익 꼬리가 두꺼움 → 선호
   음(-): 손실 꼬리가 두꺼움 → 비선호
4. 신호 시차
   월말: 신호생성=집행 (당일) → 슬리피지 최소, 단 월말변동성 노출
   월초: 전월말 신호 → 당월초 집행 (1~3일 시차) → 신호 품질 약간 저하
   월중: 전월말 신호 → 10일 후 집행 (최대 시차) → 신호 품질 가장 낮음
""")
