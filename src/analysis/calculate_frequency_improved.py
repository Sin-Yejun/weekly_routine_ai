import pandas as pd
import numpy as np
import os

def _drop_outliers(counts: pd.Series,
                   method: str = "iqr",          # "iqr" | "pct" | "mad" | "none"
                   strength: float = 1.5,        # iqr:k, pct:p(0~1), mad:z
                   hard_cap: int | None = None,
                   plan_cap: int | None = None) -> pd.Series:
    if counts.empty:
        return counts
    x = counts.copy().astype(float)
    upper = None
    if method == "iqr":
        q1, q3 = x.quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + strength * iqr
    elif method == "pct":
        upper = x.quantile(float(strength))
    elif method == "mad":
        med = x.median()
        mad = np.median(np.abs(x - med)) or 1e-9
        z = 0.6745 * (x - med) / mad
        return x[np.abs(z) <= float(strength)]
    elif method == "none":
        pass
    else:
        raise ValueError("method must be one of {'iqr','pct','mad','none'}")

    caps = [c for c in [upper, hard_cap, plan_cap] if c is not None and np.isfinite(c)]
    if caps:
        cap = min(caps)
        x = x[x <= cap]
    return x

def calculate_frequency_sliding(input_path: str,
                                output_path: str,
                                window_days: int = 7,
                                min_sessions: int = 10,
                                exclude_zero: bool = True,
                                tie_break: str = "max",
                                outlier_method: str = "iqr",
                                outlier_strength: float = 1.5,
                                hard_cap: int | None = None,
                                plan_cap_map: dict | None = None,
                                plan_buffer: int = 0,
                                low_hist_probs=(0.05, 0.15, 0.25, 0.25, 0.15, 0.10, 0.05),
                                # --- 새 옵션: 통계 저장 ---
                                save_stats: bool = True):
    """
    date 기반 7일 슬라이딩 합계의 모드(최빈값)를 계산.
    assigned_random == True/False 각각에 대해 frequency 분포/요약통계도 저장.
    """

    if not os.path.exists(input_path):
        print(f"❌ Error: Input file not found at {input_path}")
        return

    print(f"🔄 Loading workout data from {input_path}...")
    df = pd.read_parquet(input_path, columns=["user_id", "date"])
    print("✅ Data loaded successfully.")

    if 'date' not in df.columns:
        raise ValueError("Input must contain a 'date' column.")
    df['date'] = pd.to_datetime(df['date'])

    user_session_counts = df['user_id'].value_counts()
    users_lt = user_session_counts[user_session_counts < min_sessions].index
    users_ge = user_session_counts[user_session_counts >= min_sessions].index

    results = []

    # < min_sessions → 확률 랜덤(주1~7)
    if len(users_lt) > 0:
        print(f"🎲 Weighted random for {len(users_lt)} users (< {min_sessions} sessions)")
        freqs = np.random.choice([1,2,3,4,5,6,7], size=len(users_lt), p=np.array(low_hist_probs))
        res_lt = pd.DataFrame({
            'user_id': users_lt,
            'frequency': freqs.astype(int),
            'sessions_total': user_session_counts.loc[users_lt].values,
            'method': f'sliding_{window_days}d_mode',
            'outlier_method': outlier_method,
            'outlier_strength': outlier_strength,
            'tie_break': tie_break,
            'assigned_random': True
        })
        results.append(res_lt)

    # ≥ min_sessions → 슬라이딩 + 이상치 필터링 + tie_break
    if len(users_ge) > 0:
        print(f"⚙️ Sliding-window + outlier filtering for {len(users_ge)} users")
        out_rows = []
        df_ge = df[df['user_id'].isin(users_ge)]

        for uid, g in df_ge.groupby('user_id'):
            s = (
                g.sort_values('date')
                 .set_index('date')
                 .assign(val=1)['val']
                 .groupby(level=0).sum()
            )
            roll = s.rolling(f'{window_days}D').sum().astype(int)
            counts = roll[roll > 0] if exclude_zero else roll

            # 유저별 계획 상한(있다면)
            plan_cap = None
            if plan_cap_map and uid in plan_cap_map:
                plan_cap = int(plan_cap_map[uid]) + int(plan_buffer)

            counts_f = _drop_outliers(
                counts,
                method=outlier_method,
                strength=outlier_strength,
                hard_cap=hard_cap,
                plan_cap=plan_cap
            )

            if counts_f.empty:
                freq = np.random.choice([1,2,3,4,5,6,7], p=np.array(low_hist_probs))
                assigned_random = True
            else:
                vc = counts_f.value_counts()
                top = vc.max()
                modes = sorted(vc[vc == top].index)
                if tie_break == "min":
                    freq = int(min(modes))
                elif tie_break == "median":
                    freq = int(np.median(modes))
                else:  # "max"
                    freq = int(max(modes))
                assigned_random = False

            out_rows.append({
                'user_id': uid,
                'frequency': freq,
                'sessions_total': int(user_session_counts.loc[uid]),
                'method': f'sliding_{window_days}d_mode',
                'outlier_method': outlier_method,
                'outlier_strength': outlier_strength,
                'tie_break': tie_break,
                'assigned_random': assigned_random
            })

        results.append(pd.DataFrame(out_rows))

    if not results:
        print("⚠️ No user data to process.")
        return

    final_df = pd.concat(results, ignore_index=True)
    final_df['frequency'] = final_df['frequency'].astype(int)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_csv(output_path, index=False)

    print(f"\n🎉 Calculated frequencies for {len(final_df)} users.")
    print(f"💾 Saved to {output_path}")
    print(final_df.head())

    # --------- 📊 통계 출력/저장 ---------
    def _summaries(df):
        # 요약통계
        summary = (df.groupby('assigned_random')['frequency']
                     .agg(n_users='count',
                          mean='mean',
                          median='median',
                          std='std',
                          min='min',
                          max='max')
                     .reset_index())
        # 분포(빈도표)
        dist = (df.groupby(['assigned_random','frequency'])
                  .size()
                  .rename('count')
                  .reset_index()
                  .sort_values(['assigned_random','frequency']))
        # 누적비/비율 추가
        dist['ratio'] = dist['count'] / dist.groupby('assigned_random')['count'].transform('sum')
        dist['cum_ratio'] = dist.groupby('assigned_random')['ratio'].cumsum()
        return summary, dist

    summary, dist = _summaries(final_df)

    print("\n=== Summary by assigned_random ===")
    print(summary)
    print("\n=== Distribution by assigned_random & frequency ===")
    print(dist.head(30))

    if save_stats:
        base_dir = os.path.dirname(output_path)
        summary_path = os.path.join(base_dir, "user_frequency_summary_by_assigned_random.csv")
        dist_path = os.path.join(base_dir, "user_frequency_distribution_by_assigned_random.csv")
        summary.to_csv(summary_path, index=False)
        dist.to_csv(dist_path, index=False)
        print(f"\n📄 Stats saved:\n- {summary_path}\n- {dist_path}")
