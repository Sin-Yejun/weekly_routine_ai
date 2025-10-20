# -*- coding: utf-8 -*-
from prompts import common_prompt, detail_prompt_abstract, SPLIT_RULES, LEVEL_GUIDE, LEVEL_SETS, LEVEL_PATTERN, LEVEL_WORKING_SETS, DUMBBELL_GUIDE
import random
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Constants from calculation_prompt.py ---
M_ratio_weight = {
    "Leg Press": 1.8229,
    "Horizontal Leg Press": 1.315,
    "Reverse V Squat": 1.2341,
    "Conventional Deadlift": 1.1549,
    "Sumo Deadlift": 1.1459,
    "Barbell Box Squat": 1.1,
    "V Squat": 1.0988,
    "Romanian Deadlift": 1.022,
    "Rack Pull": 1.0,
    "Back Squat": 1.0,
    "Hack Squat Machine": 0.9899,
    "Chest Supported T-bar Row": 0.9,
    "Linear Hack Squat Machine": 0.85,
    "Smith Machine Deadlift": 0.8463,
    "Smith Machine Squat": 0.8349,
    "Smith Machine Hip Thrust": 0.8,
    "Middle Row Machine": 0.8,
    "Smith Machine Shrug": 0.7959,
    "Barbell Bench Press": 0.7902,
    "Barbell Sumo Squat": 0.7897,
    "Barbell Shrug": 0.7781,
    "Hip Abduction Machine": 0.7777,
    "Dumbbell Front Squat": 0.75,
    "Leg Extension": 0.7483,
    "Barbell Row": 0.7466,
    "Stiff Leg Deadlift": 0.7409,
    "Incline Dumbbell Pull Over": 0.73,
    "Barbell Hip Thrust": 0.7297,
    "Pendlay Row": 0.7172,
    "Chest Press Machine": 0.7088,
    "Hip Adduction Machine": 0.7,
    "Smith Machine Bench Press": 0.6954,
    "Seated Cable Row": 0.6947,
    "Seated Row Machine": 0.6924,
    "Lat Pull Down": 0.6914,
    "Cable Crunch": 0.6882,
    "Barbell Split Squat": 0.68,
    "Smith Machine Row": 0.6799,
    "Incline Bench Press Machine": 0.6773,
    "Lateral Wide Pull Down": 0.6765,
    "Decline Chest Press Machine": 0.6737,
    "Hip Thrust Machine": 0.6729,
    "High Row Machine": 0.6565,
    "Smith Machine Incline Bench Press": 0.6542,
    "Barbell Incline Bench Press": 0.6502,
    "Low Row Machine": 0.6409,
    "Front Squat": 0.6408,
    "Incline Dumbbell Shoulder Press": 0.63,
    "Abdominal Crunch Machine": 0.6242,
    "Close-grip Bench Press": 0.6167,
    "Barbell Jump Squat": 0.6091,
    "Assisted Pull Up Machine": 0.6077,
    "Smith Machine Bulgarian Split Squat": 0.6,
    "Seated Barbell Tricep Extension": 0.6,
    "Leg Curl": 0.5817,
    "Pec Deck Fly Machine": 0.5811,
    "Incline Chest Press Machine": 0.5767,
    "Assisted Dip Machine": 0.5752,
    "Incline Barbell Front Raise": 0.57,
    "Barbell Incline Front Raise": 0.55,
    "EZ Bar Incline Front Raise": 0.55,
    "Incline EZ Bar Front Raise": 0.55,
    "Chest Fly Machine": 0.55,
    "EZ Bar Lying Tricep Extension": 0.55,
    "EZ Bar Tricep Extension": 0.55,
    "Bicep Curl Machine": 0.55,
    "Shoulder Press Machine": 0.5301,
    "Dumbbell Skull Crusher": 0.52,
    "Barbell Lunge": 0.5143,
    "T-bar Row Machine": 0.5141,
    "Smith Machine Split Squat": 0.5131,
    "Incline Dumbbell Front Raise": 0.5,
    "Dumbbell Incline Front Raise": 0.5,
    "Kettlebell Shoulder Press": 0.5,
    "Dumbbell Lying Tricep Extension": 0.5,
    "EZ Bar Reverse Curl": 0.5,
    "Seated Barbell Shoulder Press": 0.4962,
    "Reverse Pec Deck Fly Machine": 0.4944,
    "Cable Push Down": 0.4898,
    "Overhead Press": 0.4825,
    "Cable Upright Row": 0.48,
    "Cable Straight Arm Pulldown": 0.47,
    "Barbell Bulgarian Split Squat": 0.4683,
    "Barbell Incline Row": 0.4526,
    "Weighted Decline Sit Up": 0.45,
    "Smith Machine Calf Raise": 0.45,
    "Bentover Cable Lateral Raise": 0.45,
    "Concentration Curl": 0.45,
    "Jumping Jack": 0.443,
    "Barbell Lateral Lunge": 0.4403,
    "Push Press": 0.4306,
    "Seated Dumbbell Lateral Raise": 0.43,
    "Face Pull": 0.4263,
    "Seated Knee Up": 0.42,
    "Cable Curl": 0.4065,
    "Cable Hammer Curl": 0.4057,
    "Plate Shoulder Press": 0.4,
    "Dumbbell Standing Calf Raise": 0.4,
    "Arm Curl Machine": 0.3758,
    "Knee Push Ups": 0.368,
    "Weighted Dips": 0.3672,
    "Barbell Upright Row": 0.3605,
    "Dumbbell Burpee": 0.35,
    "Torso Rotation Machine": 0.35,
    "Weighted Chin Up": 0.3467,
    "Cable Crossover": 0.3397,
    "EZ Bar Upright Row": 0.3278,
    "Cable Pull Through": 0.3257,
    "Barbell Bicep Curl": 0.3213,
    "Incline Dumbbell Bench Press": 0.3196,
    "EZ Bar Curl": 0.3194,
    "Dumbbell Bench Press": 0.3174,
    "Dumbbell Shrug": 0.3102,
    "Dumbbell Sumo Deadlift": 0.2935,
    "Lying Tricep Extension": 0.2917,
    "Dumbbell Squat": 0.29,
    "Weighted Pull Up": 0.2899,
    "One Arm Dumbbell Row": 0.2895,
    "Dumbbell Sumo Squat": 0.2838,
    "Dumbbell Row": 0.2832,
    "EZ Bar Preacher Curl": 0.2832,
    "Standing Cable Fly": 0.281,
    "Decline Dumbbell Bench Press": 0.28,
    "Kettlebell Sumo Deadlift": 0.2684,
    "Barbell Preacher Curl": 0.2667,
    "Bodyweight Calf Raise": 0.2621,
    "Dumbbell Goblet Squat": 0.2617,
    "Seated Dumbbell Shoulder Press": 0.2613,
    "Crunch": 0.2587,
    "Dumbbell Incline Row": 0.2581,
    "Incline Cable Fly": 0.2571,
    "Barbell Wrist Curl": 0.2546,
    "Sit Up": 0.2497,
    "Dumbbell Shoulder Press": 0.2494,
    "Mountain Climber": 0.2475,
    "Kettlebell Deadlift": 0.2437,
    "Air Squat": 0.2422,
    "Heel Touch": 0.2412,
    "Cable Front Raise": 0.2389,
    "Kettlebell Sumo Squat": 0.2359,
    "Dumbbell Bulgarian Split Squat": 0.2326,
    "EZ Bar Wrist Curl": 0.2312,
    "Dumbbell Pullover": 0.2306,
    "Dumbbell Lunge": 0.2274,
    "Decline Sit Up": 0.221,
    "Kettlebell Goblet Squat": 0.2193,
    "Dumbbell Split Squat": 0.2186,
    "Incline Dumbbell Fly": 0.2176,
    "Push Ups": 0.2146,
    "Barbell Front Raise": 0.2126,
    "Dumbbell Tricep Extension": 0.2117,
    "Dumbbell Side Bend": 0.2103,
    "Dumbbell Fly": 0.2069,
    "Weight Hyperextension": 0.2052,
    "EZ Bar Front Raise": 0.1995,
    "Leg Raise": 0.1957,
    "Dumbbell Upright Row": 0.1937,
    "Sumo Air Squat": 0.1912,
    "Cable Reverse Fly": 0.1869,
    "Decline Push Ups": 0.185,
    "Lunge": 0.1781,
    "Jump Squat": 0.1778,
    "Dumbbell Preacher Curl": 0.177,
    "Bench Dips": 0.1763,
    "V-up": 0.1729,
    "Donkey Kick": 0.1716,
    "Hanging Leg Raise": 0.1716,
    "Bodyweight Lateral Lunge": 0.1659,
    "Dumbbell Lateral Lunge": 0.1641,
    "Dumbbell Bicep Curl": 0.164,
    "Dumbbell Hammer Curl": 0.1636,
    "Incline Push Ups": 0.1595,
    "Hanging Knee Raise": 0.1576,
    "Abs Roll Out": 0.1559,
    "Incline Dumbbell Curl": 0.1545,
    "Burpee": 0.1541,
    "Back Extension": 0.151,
    "Hip Thrust": 0.1503,
    "Hyperextension": 0.1497,
    "Dumbbell Wrist Curl": 0.1463,
    "Russian Twist": 0.1387,
    "Dumbbell Lateral Raise": 0.1375,
    "Bentover Dumbbell Lateral Raise": 0.1355,
    "Dumbbell Front Raise": 0.1309,
    "Dips": 0.1306,
    "Cable Lateral Raise": 0.1275,
    "Inverted Row": 0.1245,
    "Dumbbell Kickback": 0.1224,
    "Seated Dumbbell Rear Lateral Raise": 0.1197,
    "Pistol Box Squat": 0.1161,
    "Hindu Push Ups": 0.1152,
    "Weighted Hanging Knee Raise": 0.1124,
    "Toes To Bar": 0.1118,
    "Pull Up": 0.1045,
    "Chin Up": 0.0941,
}
F_ratio_weight = {
    "Leg Press": 1.6973,
    "Horizontal Leg Press": 1.5644,
    "Assisted Pull Up Machine": 1.4466,
    "Assisted Dip Machine": 1.4091,
    "Hip Abduction Machine": 1.3618,
    "Conventional Deadlift": 1.2049,
    "Sumo Deadlift": 1.204,
    "Barbell Box Squat": 1.08,
    "Rack Pull": 1.06,
    "Romanian Deadlift": 1.035,
    "Back Squat": 1.0,
    "Linear Hack Squat Machine": 0.95,
    "Hip Adduction Machine": 0.9211,
    "Reverse V Squat": 0.9211,
    "Smith Machine Hip Thrust": 0.92,
    "Barbell Hip Thrust": 0.9139,
    "Cable Crunch": 0.8788,
    "V Squat": 0.8447,
    "Barbell Split Squat": 0.82,
    "Dumbbell Front Squat": 0.82,
    "Hack Squat Machine": 0.8127,
    "Jumping Jack": 0.7993,
    "Hip Thrust Machine": 0.7823,
    "Smith Machine Bulgarian Split Squat": 0.78,
    "Smith Machine Deadlift": 0.7775,
    "Smith Machine Shrug": 0.7451,
    "Smith Machine Squat": 0.7429,
    "Stiff Leg Deadlift": 0.7339,
    "Chest Supported T-bar Row": 0.72,
    "Lat Pull Down": 0.7087,
    "Leg Extension": 0.7024,
    "Seated Cable Row": 0.6993,
    "Barbell Shrug": 0.6957,
    "Barbell Sumo Squat": 0.6916,
    "Abdominal Crunch Machine": 0.6869,
    "Middle Row Machine": 0.68,
    "Seated Row Machine": 0.6671,
    "Barbell Bench Press": 0.6451,
    "Pendlay Row": 0.6433,
    "High Row Machine": 0.6314,
    "Barbell Row": 0.6122,
    "Barbell Jump Squat": 0.6074,
    "Low Row Machine": 0.5995,
    "Close-grip Bench Press": 0.5944,
    "Front Squat": 0.5918,
    "Lateral Wide Pull Down": 0.5871,
    "Leg Curl": 0.5807,
    "Knee Push Ups": 0.5793,
    "Smith Machine Row": 0.5744,
    "Cable Pull Through": 0.5693,
    "Barbell Lunge": 0.5611,
    "Weighted Decline Sit Up": 0.55,
    "Crunch": 0.5473,
    "Chest Press Machine": 0.536,
    "Seated Knee Up": 0.5327,
    "Face Pull": 0.5263,
    "Cable Straight Arm Pulldown": 0.5193,
    "Smith Machine Split Squat": 0.5182,
    "Barbell Incline Bench Press": 0.5043,
    "Mountain Climber": 0.4942,
    "Smith Machine Bench Press": 0.4867,
    "Sit Up": 0.4794,
    "Barbell Bulgarian Split Squat": 0.4765,
    "Pec Deck Fly Machine": 0.4763,
    "Air Squat": 0.4735,
    "Cable Push Down": 0.4664,
    "Incline Dumbbell Pull Over": 0.46,
    "Heel Touch": 0.4523,
    "Decline Chest Press Machine": 0.4514,
    "Smith Machine Incline Bench Press": 0.4362,
    "Reverse Pec Deck Fly Machine": 0.4327,
    "Donkey Kick": 0.4309,
    "Kettlebell Deadlift": 0.4307,
    "Bodyweight Calf Raise": 0.4281,
    "Overhead Press": 0.4274,
    "Leg Raise": 0.4267,
    "Cable Upright Row": 0.42,
    "Push Press": 0.4148,
    "Incline Dumbbell Shoulder Press": 0.41,
    "Barbell Incline Row": 0.4091,
    "Incline Bench Press Machine": 0.4034,
    "Dumbbell Burpee": 0.4,
    "Seated Barbell Shoulder Press": 0.3983,
    "Cable Hammer Curl": 0.3977,
    "Barbell Upright Row": 0.3968,
    "EZ Bar Upright Row": 0.3968,
    "T-bar Row Machine": 0.3919,
    "Kettlebell Sumo Deadlift": 0.3895,
    "V-up": 0.3893,
    "Lunge": 0.3891,
    "Burpee": 0.3882,
    "Jump Squat": 0.3878,
    "Cable Curl": 0.3818,
    "Toes To Bar": 0.3814,
    "Kettlebell Shoulder Press": 0.38,
    "Sumo Air Squat": 0.3785,
    "Decline Dumbbell Bench Press": 0.3781,
    "Barbell Preacher Curl": 0.3712,
    "Decline Sit Up": 0.3712,
    "Hanging Leg Raise": 0.3708,
    "Chest Fly Machine": 0.37,
    "Bodyweight Lateral Lunge": 0.3648,
    "Incline Chest Press Machine": 0.3644,
    "Hip Thrust": 0.3622,
    "Dumbbell Sumo Squat": 0.3604,
    "Hanging Knee Raise": 0.3576,
    "Barbell Lateral Lunge": 0.3573,
    "Shoulder Press Machine": 0.3554,
    "Hyperextension": 0.3543,
    "Smith Machine Calf Raise": 0.35,
    "Abs Roll Out": 0.3459,
    "Cable Crossover": 0.345,
    "Kettlebell Sumo Squat": 0.3446,
    "Dumbbell Sumo Deadlift": 0.3437,
    "EZ Bar Curl": 0.3402,
    "EZ Bar Preacher Curl": 0.3399,
    "Barbell Bicep Curl": 0.336,
    "Incline Push Ups": 0.3358,
    "Arm Curl Machine": 0.3344,
    "Standing Cable Fly": 0.3314,
    "Back Extension": 0.3305,
    "Seated Barbell Tricep Extension": 0.33,
    "Dumbbell Shrug": 0.3269,
    "Plate Shoulder Press": 0.32,
    "Dumbbell Standing Calf Raise": 0.32,
    "EZ Bar Lying Tricep Extension": 0.32,
    "Push Ups": 0.3166,
    "Bench Dips": 0.315,
    "Barbell Incline Front Raise": 0.31,
    "Incline Barbell Front Raise": 0.31,
    "EZ Bar Tricep Extension": 0.31,
    "Dumbbell Skull Crusher": 0.31,
    "Dumbbell Squat": 0.3011,
    "Dumbbell Lying Tricep Extension": 0.3,
    "Bicep Curl Machine": 0.3,
    "Weighted Dips": 0.3,
    "Pistol Box Squat": 0.2972,
    "EZ Bar Wrist Curl": 0.2968,
    "Dips": 0.2904,
    "EZ Bar Incline Front Raise": 0.29,
    "Incline EZ Bar Front Raise": 0.29,
    "Dumbbell Goblet Squat": 0.2882,
    "Dumbbell Incline Row": 0.2849,
    "Kettlebell Goblet Squat": 0.2842,
    "Barbell Wrist Curl": 0.2811,
    "Incline Dumbbell Front Raise": 0.28,
    "Dumbbell Incline Front Raise": 0.28,
    "EZ Bar Reverse Curl": 0.28,
    "Inverted Row": 0.2765,
    "Lying Tricep Extension": 0.2758,
    "Decline Push Ups": 0.275,
    "Hindu Push Ups": 0.2721,
    "Seated Dumbbell Lateral Raise": 0.27,
    "EZ Bar Front Raise": 0.2675,
    "Dumbbell Row": 0.2664,
    "Pull Up": 0.2613,
    "Concentration Curl": 0.26,
    "Barbell Front Raise": 0.2589,
    "Cable Reverse Fly": 0.2586,
    "Chin Up": 0.2516,
    "Bentover Cable Lateral Raise": 0.25,
    "Weighted Chin Up": 0.25,
    "Incline Dumbbell Bench Press": 0.2483,
    "Dumbbell Bench Press": 0.2472,
    "Cable Front Raise": 0.2445,
    "One Arm Dumbbell Row": 0.2397,
    "Dumbbell Split Squat": 0.234,
    "Dumbbell Bulgarian Split Squat": 0.232,
    "Dumbbell Lunge": 0.2241,
    "Incline Cable Fly": 0.2225,
    "Weight Hyperextension": 0.2216,
    "Dumbbell Preacher Curl": 0.2194,
    "Dumbbell Side Bend": 0.2163,
    "Dumbbell Lateral Lunge": 0.2111,
    "Dumbbell Pullover": 0.208,
    "Seated Dumbbell Shoulder Press": 0.2078,
    "Dumbbell Upright Row": 0.2062,
    "Torso Rotation Machine": 0.2,
    "Weighted Pull Up": 0.2,
    "Dumbbell Shoulder Press": 0.1915,
    "Incline Dumbbell Fly": 0.1848,
    "Dumbbell Wrist Curl": 0.1771,
    "Dumbbell Fly": 0.1769,
    "Dumbbell Tricep Extension": 0.1661,
    "Dumbbell Hammer Curl": 0.1659,
    "Dumbbell Bicep Curl": 0.1615,
    "Incline Dumbbell Curl": 0.1604,
    "Russian Twist": 0.1604,
    "Cable Lateral Raise": 0.1595,
    "Dumbbell Front Raise": 0.126,
    "Dumbbell Lateral Raise": 0.1245,
    "Seated Dumbbell Rear Lateral Raise": 0.1192,
    "Bentover Dumbbell Lateral Raise": 0.1183,
    "Dumbbell Kickback": 0.1095,
    "Weighted Hanging Knee Raise": 0.1022,
}
LEVEL_CODE = {"Beginner":"B","Novice":"N","Intermediate":"I","Advanced":"A","Elite":"E"}

SPLIT_MUSCLE_GROUPS = {
    "UPPER": "(Upper Chest, Middle Chest, Lower Chest, Upper Back, Lower Back, Lats, Anterior Deltoid, Lateral Deltoid, Posterior Deltoid, Traps, Biceps, Triceps, Forearms)",
    "LOWER": "(Glutes, Quads, Hamstrings, Adductors, Abductors, Calves)",
    "PUSH": "(Upper Chest, Middle Chest, Lower Chest, Anterior Deltoid, Lateral Deltoid, Posterior Deltoid, Triceps)",
    "PULL": "(Upper Back, Lower Back, Lats, Traps, Biceps)",
    "LEGS": "(Glutes, Quads, Hamstrings, Adductors, Abductors, Calves)",
    "CHEST": "(Upper Chest, Middle Chest, Lower Chest)",
    "BACK": "(Upper Back, Lower Back, Lats)",
    "SHOULDERS": "(Anterior Deltoid, Lateral Deltoid, Posterior Deltoid, Traps)",
    "ARM": "(Biceps, Triceps, Forearms)",
    "Abs": "(Upper Abs, Lower Abs, Obliques, Core)",
    "ARM+ABS": "(Biceps, Triceps, Forearms, Upper Abs, Lower Abs, Obliques, Core)"
}

# --- Helper Functions ---

SPLIT_CONFIGS = {
    "2": [
        {"id": "SPLIT", "name": "(Upper/Lower)", "days": ["UPPER", "LOWER"], "rule_key": 2},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B"], "rule_key": "FB_2"}
    ],
    "3": [
        {"id": "SPLIT", "name": "(Push/Pull/Legs)", "days": ["PUSH", "PULL", "LEGS"], "rule_key": 3},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B", "FULLBODY_C"], "rule_key": "FB_3"}
    ],
    "4": [
        {"id": "SPLIT", "name": "(4-Day Split)", "days": ["CHEST", "BACK", "SHOULDERS", "LEGS"], "rule_key": 4},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B", "FULLBODY_C", "FULLBODY_D"], "rule_key": "FB_4"}
    ],
    "5": [
        {"id": "SPLIT", "name": "(5-Day Split)", "days": ["CHEST", "BACK", "LEGS", "SHOULDERS", "ARM+ABS"], "rule_key": 5},
        {"id": "FB", "name": "(Full Body)", "days": ["FULLBODY_A", "FULLBODY_B", "FULLBODY_C", "FULLBODY_D", "FULLBODY_E"], "rule_key": "FB_5"}
    ]
}

L = {
    "M": {"BP":{"B":0.6,"N":1.0,"I":1.3,"A":1.6,"E":2.0},
        "SQ":{"B":0.8,"N":1.2,"I":1.6,"A":2.0,"E":2.5},
        "DL":{"B":1.0,"N":1.5,"I":2.0,"A":2.5,"E":3.0},
        "OHP":{"B":0.4,"N":0.7,"I":0.9,"A":1.1,"E":1.4}},
    
    "F": {"BP":{"B":0.39,"N":0.65,"I":0.845,"A":1.04,"E":1.3},
        "SQ":{"B":0.52,"N":0.78,"I":1.04,"A":1.3,"E":1.625},
        "DL":{"B":0.65,"N":0.975,"I":1.3,"A":1.625,"E":1.95},
        "OHP":{"B":0.26,"N":0.455,"I":0.585,"A":0.715,"E":0.91}}
}
ANCHOR_PCTS = [0.55, 0.60, 0.65, 0.70]
@dataclass
class User:
    gender: str
    weight: float
    level: str
    freq: int
    duration: int
    intensity: str
    tools: List[str]

def parse_duration_bucket(bucket: str) -> int:
    if not isinstance(bucket, str): return 60
    numbers = re.findall(r'\d+', bucket)
    return int(numbers[-1]) if numbers else 60

def round_to_step(x: float, step: int = 5) -> int:
    return int(round(x / step) * step)

def compute_tm(gender: str, bodyweight: float, level: str, step: int = 5) -> dict:
    """TM = round( 0.9 * (bodyweight * L[gender][lift][level_code]) , step )"""
    code = LEVEL_CODE.get(level)
    if not code or gender not in L:  # 안전장치
        return {"BP":0,"SQ":0,"DL":0,"OHP":0}
    coeffs = L[gender]
    tm = {}
    for lift in ("BP","SQ","DL","OHP"):
        raw = 0.9 * (bodyweight * coeffs[lift][code])
        tm[lift] = round_to_step(raw, step)
    return tm

def build_load_row(tm_val: int, pcts=ANCHOR_PCTS, step: int = 5) -> str:
    # "55%:xx, 60%:yy, 65%:zz, 70%:aa" 형태 문자열
    parts = []
    for p in pcts:
        kg = round_to_step(tm_val * p, step)
        parts.append(f"{int(p*100)}%:{kg}")
    return ", ".join(parts)

def _parse_reps_pattern(level: str) -> list[int]:
    """
    prompts.LEVEL_PATTERN[level]에서 숫자 배열만 뽑기.
    예: "- Novice: [15,12,10,9,8]" -> [15,12,10,9,8]
    """
    pat = LEVEL_PATTERN.get(level, "")
    nums = re.findall(r'\d+', pat)
    return [int(n) for n in nums] if nums else [12, 10, 8, 8]

def _parse_working_pct_bounds(level: str) -> tuple[float, float]:
    """
    prompts.LEVEL_WORKING_SETS[level]에서 퍼센트 범위를 추출해 (low, high) 반환.
    - Beginner: "65–70% of TM" -> (0.65, 0.70)
    - Novice: "70% of TM"      -> (0.70, 0.70)
    """
    text = LEVEL_WORKING_SETS.get(level, "")
    m_range = re.search(r'(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\s*%', text)
    if m_range:
        low, high = float(m_range.group(1))/100.0, float(m_range.group(2))/100.0
        return (min(low, high), max(low, high))
    m_single = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if m_single:
        v = float(m_single.group(1))/100.0
        return (v, v)
    return (0.70, 0.70)

def _linspace(a: float, b: float, n: int) -> list[float]:
    if n <= 1: 
        return [a]
    step = (b - a) / (n - 1)
    return [a + i*step for i in range(n)]

def _round_by_tool(kg: float, tool: str) -> int:
    """Dumbbell=2kg, 그 외=5kg 배수 반올림."""
    step = 2 if (tool or '').lower() == 'dumbbell' else 5
    return round_to_step(kg, step)

def build_example_sets_by_level(tm_val: int, level: str, tool: str = 'Barbell') -> str:
    """
    Warm-up 2세트 + Working (레벨 범위 등분)
    - 세트 수: LEVEL_PATTERN 기반 → 서버 스키마(4/5/6)와 자연 일치
    - 1세트: 바벨이면 무조건 20kg(빈봉), 덤벨/머신이면 규칙적용
    - 2세트: TM의 50%
    - 3세트+: LEVEL_WORKING_SETS의 범위를 등분
    """
    reps = _parse_reps_pattern(level)
    total_sets = max(4, len(reps))  # 안전장치
    # Warm-up
    warmup_pcts = [0.25, 0.50]  # ~25% (빈봉 대체), 50%
    # Working
    work_low, work_high = _parse_working_pct_bounds(level)
    work_sets = max(0, total_sets - 2)
    work_pcts = _linspace(work_low, work_high, work_sets) if work_sets > 0 else []

    pcts = warmup_pcts + work_pcts
    pcts = pcts[:total_sets]
    reps = reps[:total_sets] + [reps[-1]]*(total_sets - len(reps)) if len(reps) < total_sets else reps[:total_sets]

    out = []
    for idx, (r, p) in enumerate(zip(reps, pcts), 1):
        if idx == 1 and (tool or '').lower() == 'barbell':
            kg = 20  # 빈봉 고정(서버 스키마도 바벨 최소 20kg과 일치)
        else:
            kg = _round_by_tool(tm_val * p, tool)
        out.append(f"[{r},{kg},0]")
    return ", ".join(out)

def _filter_catalog(catalog: list, user: User, allowed_names: dict) -> list:
    """Filters the catalog based on user's tools and level."""
    
    # 1. Filter by selected tools
    if hasattr(user, 'tools') and user.tools:
        selected_tools_set = {t.lower() for t in user.tools}
        pullupbar_exercises = set(allowed_names.get("TOOL", {}).get("PullUpBar", []))
        
        filtered_list = []
        for item in catalog:
            tool_en = item.get('tool_en', '').lower()
            e_name = item.get('eName', '')
            is_pullupbar_exercise = e_name in pullupbar_exercises

            include = False
            if is_pullupbar_exercise:
                if "pullupbar" in selected_tools_set:
                    include = True
            else:
                if tool_en in selected_tools_set:
                    include = True
            
            if include:
                filtered_list.append(item)
        catalog = filtered_list

    # 2. Filter by level (Beginner/Novice)
    if user.level in ['Beginner', 'Novice'] and allowed_names:
        level_key = 'MBeginner' if user.gender == 'M' else 'FBeginner' if user.level == 'Beginner' else 'MNovice' if user.gender == 'M' else 'FNovice'
        level_exercise_set = set(allowed_names.get(level_key, []))
        catalog = [item for item in catalog if item.get('eName') in level_exercise_set]
    
    return catalog

def _group_catalog_by_split(catalog: list, split_days: List[str]) -> Dict[str, list]:
    """Groups the catalog by split days based on the provided day tags."""
    is_full_body_split = any(day.startswith("FULLBODY") for day in split_days)

    # For full body, create one unified catalog. For splits, create one for each day.
    if is_full_body_split:
        grouped_catalog = {"FULLBODY": []}
    else:
        grouped_catalog = {day: [] for day in split_days}

    for item in catalog:
        # Common processing for all items
        bName = item.get('bName')
        eName = item.get('eName')
        mg_num = item.get('MG_num', 1)
        micro_en_raw = item.get('MG', "")
        micro_en_parts = [p.strip() for p in micro_en_raw.split('/')] if isinstance(micro_en_raw, str) and micro_en_raw.strip() else []
        scores = item.get('musle_point', [])
        formatted_micro_parts = []
        if len(micro_en_parts) == len(scores):
            for i in range(len(micro_en_parts)):
                part = micro_en_parts[i]
                score = scores[i]
                formatted_micro_parts.append(f"{part}({score})")
        else:
            formatted_micro_parts = micro_en_parts
        muscle_group = {"micro": formatted_micro_parts}
        category = item.get('category')
        main_ex = item.get('main_ex', False)
        processed_item = [
            bName.upper() if isinstance(bName, str) else bName,
            eName,
            category,
            mg_num,
            muscle_group,
            main_ex,
        ]

        if is_full_body_split:
            grouped_catalog["FULLBODY"].append(processed_item)
        else:
            # Refactored logic for split workouts
            freq = len(split_days)
            target_day_tag = None

            if freq == 2:
                target_day_tag = item.get('body_region', '').upper()
            elif freq == 3:
                target_day_tag = item.get('movement_type', '').upper()
            elif freq in [4, 5]:
                bName_upper = item.get('bName', '').upper()
                
                if bName_upper == 'CHEST': target_day_tag = 'CHEST'
                elif bName_upper == 'BACK': target_day_tag = 'BACK'
                elif bName_upper == 'LEG': target_day_tag = 'LEGS'
                elif bName_upper == 'SHOULDER': target_day_tag = 'SHOULDERS'
                elif bName_upper == 'ARM' or bName_upper == 'ABS':
                    if 'ARM+ABS' in split_days:
                        target_day_tag = 'ARM+ABS'
                    elif bName_upper == 'ARM' and 'ARMS' in split_days:
                        target_day_tag = 'ARM'
                    elif bName_upper == 'ABS' and 'ABS' in split_days:
                        target_day_tag = 'ABS'
            
            if target_day_tag and target_day_tag in grouped_catalog:
                grouped_catalog[target_day_tag].append(processed_item)

    return grouped_catalog

def _apply_special_ordering(grouped_catalog: Dict[str, list], split_days: List[str]):
    """Applies special ordering for 2 and 3-day splits."""
    for group_list in grouped_catalog.values():
        random.shuffle(group_list)

    def get_ordered_list(exercises, order):
        sub_groups = {key: [] for key in order}
        sub_groups['ETC'] = []
        for exercise_item in exercises:
            bName = exercise_item[0]
            sub_groups.get(bName, sub_groups['ETC']).append(exercise_item)
        
        final_list = []
        for key in order:
            final_list.extend(sub_groups[key])
        final_list.extend(sub_groups['ETC'])
        return final_list

    freq = len(split_days)
    is_full_body_split = any(day.startswith("FULLBODY") for day in split_days)

    if not is_full_body_split:
        if freq == 2 and 'UPPER' in grouped_catalog:
            chest_back_order = ['CHEST', 'BACK'] if random.random() < 0.5 else ['BACK', 'CHEST']
            upper_order = chest_back_order + ['SHOULDER', 'ARM']
            grouped_catalog['UPPER'] = get_ordered_list(grouped_catalog['UPPER'], upper_order)

        if freq == 3:
            if 'PUSH' in grouped_catalog:
                grouped_catalog['PUSH'] = get_ordered_list(grouped_catalog['PUSH'], ['CHEST', 'SHOULDER', 'ARM'])
            if 'PULL' in grouped_catalog:
                grouped_catalog['PULL'] = get_ordered_list(grouped_catalog['PULL'], ['BACK', 'ARM'])
    
    return grouped_catalog

def _build_catalog_string(grouped_catalog: Dict[str, list], split_days: List[str], catalog: list) -> str:
    """Builds the final catalog string for the prompt with nested grouping."""
    catalog_lines = []
    eName_to_tool_map = {item.get('eName'): item.get('tool_en', 'Etc') for item in catalog}
    is_full_body_split = any(day.startswith("FULLBODY") for day in split_days)

    if is_full_body_split:
        # For full body, print a single unified catalog
        catalog_lines.append("FULL BODY (All exercises available for all days)")
        exercises_for_day = grouped_catalog.get("FULLBODY", [])
        if exercises_for_day:
            category_groups = {}
            for exercise in exercises_for_day:
                category = exercise[2] if exercise[2] else "(Uncategorized)"
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(exercise)

            for category in sorted(category_groups.keys()):
                cat_exercises = category_groups[category]
                catalog_lines.append(f"  {category}:")
                for i, exercise in enumerate(cat_exercises):
                    tool = eName_to_tool_map.get(exercise[1], 'Etc')
                    line_end = "," if i < len(cat_exercises) - 1 else ""
                    bName = exercise[0]
                    eName = exercise[1]
                    is_main = exercise[5]
                    display_bName = f"{bName} (main)" if is_main else bName
                    prompt_item = [display_bName, eName, tool, exercise[3], exercise[4]]
                    catalog_lines.append("    " + json.dumps(prompt_item, ensure_ascii=False) + line_end)
    else:
        # Existing logic for split workouts
        for day in split_days:
            muscle_group_info = SPLIT_MUSCLE_GROUPS.get(day, "")
            catalog_lines.append(f"{day} {muscle_group_info}".strip())
            exercises_for_day = grouped_catalog.get(day, [])

            if exercises_for_day:
                category_groups = {}
                for exercise in exercises_for_day:
                    category = exercise[2] if exercise[2] else "(Uncategorized)"
                    if category not in category_groups:
                        category_groups[category] = []
                    category_groups[category].append(exercise)

                for category in sorted(category_groups.keys()):
                    cat_exercises = category_groups[category]
                    catalog_lines.append(f"  {category}:")
                    for i, exercise in enumerate(cat_exercises):
                        tool = eName_to_tool_map.get(exercise[1], 'Etc')
                        line_end = "," if i < len(cat_exercises) - 1 else ""
                        bName = exercise[0]
                        eName = exercise[1]
                        is_main = exercise[5]
                        display_bName = f"{bName} (main)" if is_main else bName
                        prompt_item = [display_bName, eName, tool, exercise[3], exercise[4]]
                        catalog_lines.append("    " + json.dumps(prompt_item, ensure_ascii=False) + line_end)

    return "\n".join(catalog_lines)

def build_prompt(user: User, catalog: list, duration_str: str, min_ex: int, max_ex: int, split_config: dict, allowed_names: dict = None) -> str:
    prompt_template = common_prompt

    split_days = split_config["days"]
    split_name = split_config["name"]
    rule_key = split_config["rule_key"]

    filtered_catalog = _filter_catalog(catalog, user, allowed_names)
    grouped_catalog = _group_catalog_by_split(filtered_catalog, split_days)
    ordered_grouped_catalog = _apply_special_ordering(grouped_catalog, split_days)
    catalog_str = _build_catalog_string(ordered_grouped_catalog, split_days, filtered_catalog)

    split_rules = SPLIT_RULES.get(rule_key, "")
    level_guide = LEVEL_GUIDE.get(user.level, "")

    return prompt_template.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        freq=user.freq,
        duration=user.duration,
        intensity=user.intensity,
        split_name=split_name,
        split_days=" / ".join(split_days),
        level_guide=level_guide,
        split_rules=split_rules,
        catalog_json=catalog_str
    )

def format_new_routine(plan_json: dict, name_map: dict, enable_sorting: bool = False, show_b_name: bool = True) -> str:
    import logging
    import random
    import json
    logging.basicConfig(level=logging.INFO)

    if not isinstance(plan_json, dict) or "days" not in plan_json:
        return "Invalid plan format."
    out = []
    for i, day in enumerate(plan_json["days"], 1):
        if not isinstance(day, list):
            continue

        if enable_sorting:
            bname_priority_map = {
                'CHEST': 1, 'BACK': 1, 'LEG': 1, 'SHOULDER': 2, 'ARM': 3, 'ABS': 4
            }
            random_bname_order = {bname: random.random() for bname in bname_priority_map.keys()}

            def get_randomized_sort_key(entry):
                exercise_name = None
                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list):
                    exercise_name = entry[0]
                elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str):
                    exercise_name = entry[1]
                else:
                    return (99, 0.5, 0, 0)

                exercise_info = name_map.get(exercise_name, {})
                b_name = exercise_info.get('bName', 'ETC').upper()
                mg_num = exercise_info.get('MG_num', 0)
                muscle_point_sum = exercise_info.get('musle_point_sum', 0)
                prio = bname_priority_map.get(b_name, 5)
                random_prio = random_bname_order.get(b_name, 0.5)
                try: mg_num = int(mg_num)
                except (ValueError, TypeError): mg_num = 0
                try: muscle_point_sum = int(muscle_point_sum)
                except (ValueError, TypeError): muscle_point_sum = 0
                return (prio, random_prio, -mg_num, -muscle_point_sum)
            day.sort(key=get_randomized_sort_key)

        # --- Conditional Formatting ---
        if show_b_name:
            # LOGIC FOR INITIAL ROUTINE (with b_name and padding)
            day_display_data = []
            micro_sums = {}
            max_b_name_width = 0
            max_k_name_width = 0

            for entry in day:
                data = {"b_name": "", "k_name": "", "details": ""}
                exercise_name = None
                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list): exercise_name = entry[0]
                elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str): exercise_name = entry[1]
                if not exercise_name: continue

                exercise_info = name_map.get(exercise_name, {})
                b_name = exercise_info.get("bName", "N/A")
                is_main = exercise_info.get("main_ex", False)
                data["b_name"] = f"{b_name} (main)" if is_main else b_name
                data["k_name"] = exercise_info.get("kName", exercise_name)
                data["details"] = f"({exercise_info.get('category', 'N/A')})"

                b_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["b_name"])
                k_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["k_name"])
                if b_name_width > max_b_name_width: max_b_name_width = b_name_width
                if k_name_width > max_k_name_width: max_k_name_width = k_name_width
                day_display_data.append(data)

                micro_groups_raw = exercise_info.get("MG_ko")
                micro_groups = []
                if isinstance(micro_groups_raw, str): micro_groups = [m.strip() for m in micro_groups_raw.split('/') if m.strip()]
                elif isinstance(micro_groups_raw, list): micro_groups = [str(m).strip() for m in micro_groups_raw if str(m).strip()]
                try: muscle_point = int(exercise_info.get("musle_point_sum", 0))
                except (ValueError, TypeError): muscle_point = 0
                if muscle_point > 0:
                    for group in micro_groups:
                        micro_sums[group] = micro_sums.get(group, 0) + muscle_point

            day_header = f"## Day{i} (운동개수: {len(day)})"
            if micro_sums:
                sorted_micro_sums = sorted(micro_sums.items(), key=lambda item: item[1], reverse=True)
                micro_sum_str = ", ".join([f"{group}: {point}" for group, point in sorted_micro_sums])

            lines = [day_header]
            for data in day_display_data:
                b_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["b_name"])
                k_name_width = sum(2 if '\uac00' <= c <= '\ud7a3' else 1 for c in data["k_name"])
                padding1 = " " * (max_b_name_width - b_name_width + 2)
                padding2 = " " * (max_k_name_width - k_name_width + 3)
                line = f'{data["b_name"]}{padding1}{data["k_name"]}{padding2}{data["details"]}'
                lines.append(line)

            if len(lines) > 1:
                out.append("\n".join(lines))

        else:
            # LOGIC FOR DETAILED ROUTINE (no b_name, single space)
            day_display_data = []
            micro_sums = {}
            for entry in day:
                data = {"k_name": "", "details": ""}
                exercise_name = None
                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list): exercise_name = entry[0]
                elif isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], str): exercise_name = entry[1]
                if not exercise_name: continue

                exercise_info = name_map.get(exercise_name, {})
                data["k_name"] = exercise_info.get("kName", exercise_name)

                if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], list):
                    sets = entry[1:]
                    set_parts = []
                    for s in sets:
                        if isinstance(s, list) and len(s) == 3:
                            reps, weight, time = s
                            if reps > 0 and weight > 0: set_parts.append(f"{reps}x{weight}")
                            elif reps > 0: set_parts.append(f"{reps}회")
                            elif time > 0 and weight > 0: set_parts.append(f"{weight}kg {time}초")
                            elif time > 0: set_parts.append(f"{time}초")
                    data["details"] = " / ".join(set_parts)
                else:
                    data["details"] = f"({exercise_info.get('category', 'N/A')})"
                
                day_display_data.append(data)
                
                micro_groups_raw = exercise_info.get("MG_ko")
                micro_groups = []
                if isinstance(micro_groups_raw, str): micro_groups = [m.strip() for m in micro_groups_raw.split('/') if m.strip()]
                elif isinstance(micro_groups_raw, list): micro_groups = [str(m).strip() for m in micro_groups_raw if str(m).strip()]
                try: muscle_point = int(exercise_info.get("musle_point_sum", 0))
                except (ValueError, TypeError): muscle_point = 0
                if muscle_point > 0:
                    for group in micro_groups:
                        micro_sums[group] = micro_sums.get(group, 0) + muscle_point

            day_header = f"## Day{i} (운동개수: {len(day)})"
            if micro_sums:
                sorted_micro_sums = sorted(micro_sums.items(), key=lambda item: item[1], reverse=True)
                micro_sum_str = ", ".join([f"{group}: {point}" for group, point in sorted_micro_sums])

            lines = [day_header]
            for data in day_display_data:
                line = f'{data["k_name"]} {data["details"]}'
                lines.append(line)

            if len(lines) > 1:
                out.append("\n".join(lines))

    formatted_routine = "\n\n".join(out)
    if not show_b_name:
        raw_output_str = json.dumps(plan_json, ensure_ascii=False)
        return f"{formatted_routine}\n\n--- Raw Model Output ---\n{raw_output_str}"
    
    return formatted_routine

def create_detail_prompt(user: User, initial_routine: dict, name_to_exercise_map: dict) -> str:
    """Generates the prompt for the detailed routine generation API."""
    all_exercises_for_prompt = []
    for day_exercises in initial_routine.get("days", []):
        for bp, e_name in day_exercises:
            exercise_details = name_to_exercise_map.get(e_name)
            if exercise_details:
                tool = exercise_details.get('tool_en', 'Etc')
                all_exercises_for_prompt.append({"ename": e_name, "tool": tool})
    
    if not all_exercises_for_prompt:
        return "No exercises found in the initial routine to generate a details prompt."

    tm = compute_tm(user.gender, user.weight, user.level)
    bp_loads = build_load_row(tm['BP'])
    sq_loads = build_load_row(tm['SQ'])
    dl_loads = build_load_row(tm['DL'])
    ohp_loads = build_load_row(tm['OHP'])

    # ★ 레벨/툴 반영 예시 세트 (Barbell & Dumbbell)
    bp_example    = build_example_sets_by_level(tm['BP'], user.level, tool='Barbell')
    sq_example    = build_example_sets_by_level(tm['SQ'], user.level, tool='Barbell')
    dl_example    = build_example_sets_by_level(tm['DL'], user.level, tool='Barbell')
    ohp_example   = build_example_sets_by_level(tm['OHP'], user.level, tool='Barbell')
    bp_example_db = build_example_sets_by_level(tm['BP'], user.level, tool='Dumbbell')
    sq_example_db = build_example_sets_by_level(tm['SQ'], user.level, tool='Dumbbell')

    prompt = detail_prompt_abstract.format(
        gender="male" if user.gender == "M" else "female",
        weight=int(round(user.weight)),
        level=user.level,
        intensity=user.intensity,
        exercise_list_with_einfotype_json=json.dumps(all_exercises_for_prompt, ensure_ascii=False),
        TM_BP=tm['BP'],
        TM_SQ=tm['SQ'],
        TM_DL=tm['DL'],
        TM_OHP=tm['OHP'],
        BP_loads=bp_loads,
        SQ_loads=sq_loads,
        DL_loads=dl_loads,
        OHP_loads=ohp_loads,
        level_sets=LEVEL_SETS[user.level],
        level_pattern=LEVEL_PATTERN[user.level],
        level_working_sets=LEVEL_WORKING_SETS[user.level],
        dumbbell_weight_guide=DUMBBELL_GUIDE[user.level],
        BP_example=bp_example, SQ_example=sq_example,
        DL_example=dl_example, OHP_example=ohp_example,
        BP_example_db=bp_example_db, SQ_example_db=sq_example_db
    )
    
    return prompt
