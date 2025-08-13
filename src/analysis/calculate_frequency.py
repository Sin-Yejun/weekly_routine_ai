import pandas as pd
import numpy as np
import os
import random

def calculate_frequency_sliding(input_path: str,
                                output_path: str,
                                window_days: int = 7,
                                min_sessions: int = 10,
                                exclude_zero: bool = True,
                                random_choices=(3, 4),
                                tie_break: str = "min"):  # "min" | "max" | "median"
    """
    7일 슬라이딩 윈도우 기반 주당 빈도(최빈값) 계산.

    - 세션 수 >= min_sessions:
        각 유저의 7일 rolling('7D') 합계 시계열에서 최빈값(모드)을 산출
        exclude_zero=True이면 0은 제외 후 모드 계산
        모드 동률 시 tie_break 규칙으로 결정
    - 세션 수 <  min_sessions:
        random_choices 중 하나를 랜덤 할당 (기존 정책 유지)
    """

    if not os.path.exists(input_path):
        print(f"❌ Error: Input file not found at {input_path}")
        return

    print(f"🔄 Loading workout data from {input_path}...")
    df = pd.read_parquet(input_path)
    print("✅ Data loaded successfully.")

    # --- 날짜 컬럼 확인/정리 ---
    if 'date' not in df.columns:
        raise ValueError("Input must contain a 'date' column.")
    df['date'] = pd.to_datetime(df['date'])

    # --- 유저별 총 세션 수 ---
    user_session_counts = df['user_id'].value_counts()

    users_lt = user_session_counts[user_session_counts < min_sessions].index
    users_ge = user_session_counts[user_session_counts >= min_sessions].index

    results = []

    # < min_sessions → 랜덤 3/4
    if len(users_lt) > 0:
        print(f"🔄 Processing {len(users_lt)} users with < {min_sessions} sessions...")
        freq_lt = [int(random.choice(random_choices)) for _ in users_lt]
        res_lt = pd.DataFrame({
            'user_id': users_lt,
            'frequency': freq_lt,
            'sessions_total': user_session_counts.loc[users_lt].values,
            'method': [f'sliding_{window_days}d_mode' for _ in users_lt],
            'window_days': window_days,
            'exclude_zero': exclude_zero,
            'tie_break': tie_break,
            'min_sessions': min_sessions,
            'assigned_random': [True] * len(users_lt)
        })
        results.append(res_lt)
        print("✅ Done (random assign).")

    # >= min_sessions → 7D 슬라이딩 모드
    if len(users_ge) > 0:
        print(f"🔄 Processing {len(users_ge)} users with ≥ {min_sessions} sessions (sliding {window_days}D)...")
        out_rows = []

        df_ge = df[df['user_id'].isin(users_ge)]

        for uid, g in df_ge.groupby('user_id'):
            # 날짜별 세션 개수(같은 날짜 여러 세션이 있으면 합)
            s = (g.sort_values('date')
                  .set_index('date')
                  .assign(val=1)['val']
                  .groupby(level=0).sum())

            # 7일 롤링 합계
            rolling_counts = s.rolling(f'{window_days}D').sum()
            counts = rolling_counts.astype(int)

            if exclude_zero:
                counts = counts[counts > 0]

            # 모드 계산 + tie-break
            if counts.empty:
                # 전부 0이거나 너무 듬성듬성 → 폴백: 랜덤
                freq = int(random.choice(random_choices))
                assigned_random = True
            else:
                vc = counts.value_counts()
                top = vc.max()
                modes = sorted(vc[vc == top].index)  # 오름차순
                if tie_break == "max":
                    freq = int(max(modes))
                elif tie_break == "median":
                    freq = int(np.median(modes))
                else:  # "min" (기본)
                    freq = int(min(modes))
                assigned_random = False

            out_rows.append({
                'user_id': uid,
                'frequency': freq,
                'sessions_total': int(user_session_counts.loc[uid]),
                'method': f'sliding_{window_days}d_mode',
                'window_days': window_days,
                'exclude_zero': exclude_zero,
                'tie_break': tie_break,
                'min_sessions': min_sessions,
                'assigned_random': assigned_random
            })

        results.append(pd.DataFrame(out_rows))
        print("✅ Done (sliding-window mode).")

    if not results:
        print("⚠️ No user data to process.")
        return

    final_df = pd.concat(results, ignore_index=True)
    final_df['frequency'] = final_df['frequency'].astype(int)

    # 저장
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    final_df.to_csv(output_path, index=False)

    print(f"\n🎉 Successfully calculated frequencies for {len(final_df)} users.")
    print(f"💾 Results saved to {output_path}")
    print("\n--- Sample of the Results ---")
    print(final_df.head())


if __name__ == '__main__':
    # 스크립트 기준 경로(기존 구조 유지)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))

    input_file = os.path.join(project_root, 'data', 'parquet', 'workout_session.parquet')
    output_file = os.path.join(project_root, 'data', 'analysis_results', 'user_frequency_sliding.csv')

    # 파라미터는 필요에 맞게 조정 가능
    calculate_frequency_sliding(
        input_path=input_file,
        output_path=output_file,
        window_days=7,         # 슬라이딩 기간(일)
        min_sessions=10,       # 이보다 적으면 랜덤 할당
        exclude_zero=True,     # 0을 모드 계산에서 제외(권장)
        random_choices=(3, 4), # 랜덤 할당 후보
        tie_break="max"        # 모드 동률 시 min/max/median 중 선택
    )
