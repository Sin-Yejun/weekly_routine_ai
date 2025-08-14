#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
user.parquet에서 workout_days가 7 이하인 사용자 수를 세는 스크립트
"""

import polars as pl
from pathlib import Path

def count_users_with_low_workout_days(threshold: int = 7) -> dict:
    """
    workout_days가 특정 임계값 이하인 사용자 수를 반환합니다.
    
    Args:
        threshold: workout_days 임계값 (기본값: 7)
        
    Returns:
        dict: 통계 정보를 담은 딕셔너리
    """
    user_parquet_path = Path("data/parquet/user.parquet")
    
    if not user_parquet_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {user_parquet_path}")
    
    # 데이터 로드
    df = pl.read_parquet(user_parquet_path)
    
    # 전체 사용자 수
    total_users = len(df)
    
    # workout_days가 null이 아닌 사용자들만 필터링
    df_valid = df.filter(pl.col("workout_days").is_not_null())
    valid_users = len(df_valid)
    
    # workout_days가 threshold 이하인 사용자 필터링
    low_workout_users = df_valid.filter(pl.col("workout_days") <= threshold)
    low_workout_count = len(low_workout_users)
    
    # workout_days 통계
    workout_stats = df_valid.select([
        pl.col("workout_days").min().alias("min_workout_days"),
        pl.col("workout_days").max().alias("max_workout_days"),
        pl.col("workout_days").mean().alias("avg_workout_days"),
        pl.col("workout_days").median().alias("median_workout_days")
    ]).to_dicts()[0]
    
    # 결과 반환
    result = {
        "threshold": threshold,
        "total_users": total_users,
        "valid_users": valid_users,
        "users_with_workout_days_null": total_users - valid_users,
        "low_workout_users": low_workout_count,
        "low_workout_percentage": (low_workout_count / valid_users * 100) if valid_users > 0 else 0,
        "workout_days_stats": workout_stats
    }
    
    return result

def print_detailed_stats(threshold: int = 7):
    """
    상세한 통계 정보를 출력합니다.
    """
    try:
        stats = count_users_with_low_workout_days(threshold)
        
        print(f"=== Workout Days Analysis (threshold: {threshold} days) ===")
        print(f"전체 사용자 수: {stats['total_users']:,}")
        print(f"workout_days 정보가 있는 사용자: {stats['valid_users']:,}")
        print(f"workout_days 정보가 없는 사용자: {stats['users_with_workout_days_null']:,}")
        print()
        print(f"workout_days가 {threshold} 이하인 사용자: {stats['low_workout_users']:,}")
        print(f"비율: {stats['low_workout_percentage']:.2f}%")
        print()
        print("=== Workout Days 통계 ===")
        print(f"최소값: {stats['workout_days_stats']['min_workout_days']}")
        print(f"최대값: {stats['workout_days_stats']['max_workout_days']}")
        print(f"평균: {stats['workout_days_stats']['avg_workout_days']:.2f}")
        print(f"중간값: {stats['workout_days_stats']['median_workout_days']}")
        
    except Exception as e:
        print(f"오류 발생: {e}")

def get_workout_days_distribution():
    """
    workout_days 분포를 보여줍니다.
    """
    user_parquet_path = Path("data/parquet/user.parquet")
    df = pl.read_parquet(user_parquet_path)
    
    # workout_days 분포
    distribution = (
        df.filter(pl.col("workout_days").is_not_null())
        .group_by("workout_days")
        .agg(pl.count().alias("count"))
        .sort("workout_days")
    )
    
    # print("\n=== Workout Days 분포 ===")
    # for row in distribution.iter_rows(named=True):
    #     print(f"workout_days {row['workout_days']:2d}: {row['count']:,} 명")

if __name__ == "__main__":
    # 기본 통계 (7일 이하)
    print_detailed_stats(7)
    
    # 분포 확인
    get_workout_days_distribution()
    
    # 다른 임계값들도 확인
    print("\n" + "="*50)
    for threshold in [1,2,3,4,5,6,7,8,9,10]:
        stats = count_users_with_low_workout_days(threshold)
        print(f"workout_days ≤ {threshold:2d}: {stats['low_workout_users']:,} 명 ({stats['low_workout_percentage']:5.2f}%)")
