# -*- coding: utf-8 -*-
from prompts import common_prompt, detail_prompt_abstract, SPLIT_RULES, LEVEL_GUIDE, LEVEL_SETS, LEVEL_PATTERN, LEVEL_WORKING_SETS, DUMBBELL_GUIDE
import random
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Constants from calculation_prompt.py ---
M_ratio_weight = {
    "ABS_CRUNCH_MC": 0.6242,
    "ABS_ROLL_OUT": 0.1559,
    "AIR_SQT": 0.2422,
    "ARM_CURL_MC": 0.3758,
    "ASS_DIP_MC": 0.5752,
    "ASS_PULLUP_MC": 0.6077,
    "BACK_ET": 0.151,
    "BB_BC_CURL": 0.3213,
    "BB_BP": 0.7902,
    "BB_BSQT": 1.0,
    "BB_DL": 1.1549,
    "BB_FR_LUNGE": 0.5322,
    "BB_FRONT_RAISE": 0.2126,
    "BB_FSQ": 0.6408,
    "BB_INC_PRESS": 0.6502,
    "BB_JUMP_SQT": 0.6091,
    "BB_LAT_LUNGE": 0.4403,
    "BB_LOW": 0.7466,
    "BB_LUNGE": 0.5143,
    "BB_PREA_CURL": 0.2667,
    "BB_PRESS": 0.4825,
    "BB_SHRUG": 0.7781,
    "BB_SM_SQT": 0.7897,
    "BB_SPLIT_SQT": 0.4683,
    "BB_STD_CALF_RAISE": 0.7794,
    "BB_UPRIGHT_ROW": 0.3605,
    "BB_WRIST_CURL": 0.2546,
    "BENCH_DIPS": 0.1763,
    "BURPEE": 0.1541,
    "BW_CALF_RAISE": 0.2621,
    "BW_LAT_LUNGE": 0.1659,
    "CABLE_ARM_PULL_DOWN": 0.47,
    "CABLE_CRUNCH": 0.6882,
    "CABLE_CURL": 0.4065,
    "CABLE_FRONT_RAISE": 0.2389,
    "CABLE_HAM_CURL": 0.4057,
    "CABLE_LAT_RAISE": 0.1275,
    "CABLE_PULL_THRU": 0.3257,
    "CABLE_PUSH_DOWN": 0.4898,
    "CABLE_REV_FLY": 0.1869,
    "CG_BB_BP": 0.6167,
    "CHEST_PRESS_MC": 0.7088,
    "CHIN_UP": 0.0941,
    "CROSS_OVER": 0.3397,
    "CRUNCH": 0.2587,
    "DB_BC_CURL": 0.164,
    "DB_BO_LAT_RAISE": 0.1355,
    "DB_BP": 0.3174,
    "DB_BULSPLIT_SQT": 0.2326,
    "DB_DEC_FLY": 0.2368,
    "DB_FLY": 0.2069,
    "DB_F_RAISE": 0.1309,
    "DB_HAM_CURL": 0.1636,
    "DB_INC_BP": 0.3196,
    "DB_INC_FLY": 0.2176,
    "DB_KICKBACK": 0.1224,
    "DB_LAT_LUNGE": 0.1641,
    "DB_LAT_RAISE": 0.1375,
    "DB_LOW": 0.2832,
    "DB_LUNGE": 0.2274,
    "DB_PREA_CURL": 0.177,
    "DB_PULLOVER": 0.2306,
    "DB_REAR_LAT_RAISE": 0.1197,
    "DB_SHD_PRESS": 0.2494,
    "DB_SHRUG": 0.3102,
    "DB_SIDE_BEND": 0.2103,
    "DB_SM_DL": 0.2935,
    "DB_SM_SQT": 0.2838,
    "DB_SPLIT_SQT": 0.2186,
    "DB_THRUSTER": 0.1911,
    "DB_TRI_EXT": 0.2117,
    "DB_UPRIGHT_ROW": 0.1937,
    "DB_WRIST_CURL": 0.1463,
    "DB_Y_RAISE": 0.1019,
    "DEC_CHEST_MAC": 0.6737,
    "DEC_DB_BP": 0.28,
    "DEC_SIT_UP": 0.221,
    "DIPS": 0.1306,
    "DONK_KICK": 0.1716,
    "EZB_CURL": 0.3194,
    "EZB_FRONT_RAISE": 0.1995,
    "EZB_UPRIGHT_ROW": 0.3278,
    "EZB_WRIST_CURL": 0.2312,
    "EZ_PREA_CURL": 0.2832,
    "FACE_PULL": 0.4263,
    "GOBLET_SQT": 0.2617,
    "HACK_SQT": 0.9899,
    "HANG_KNEE_RAISE": 0.1576,
    "HANG_LEG_RAIGE": 0.1716,
    "HEEL_TOUCH": 0.2412,
    "HIGH_ROW_MC": 0.6565,
    "HINDU_PUSH_UP": 0.1152,
    "HIP_ABD_MC": 0.7777,
    "HIP_THRUST": 0.1503,
    "HIP_THRUST_MAC": 0.6729,
    "HPET": 0.1497,
    "HZ_LEG_PRESS": 1.315,
    "INC_BB_ROW": 0.4526,
    "INC_BP_MAC": 0.6773,
    "INC_CABLE_FLY": 0.2571,
    "INC_CHEST_PRESS_MC": 0.5767,
    "INC_DB_CURL": 0.1545,
    "INC_DB_ROW": 0.2581,
    "INC_PUSH_UP": 0.1595,
    "INN_THIGH_MC": 0.7,
    "INVT_ROW": 0.1245,
    "JUMPING_JACK": 0.443,
    "JUMP_SQT": 0.1778,
    "KB_DL": 0.2437,
    "KB_GOBLET_SQT": 0.2193,
    "KB_SM_AIR_SQT": 0.1912,
    "KB_SM_DL": 0.2684,
    "KB_SM_SQT": 0.2359,
    "LAT_PULL_DOWN": 0.6914,
    "LAT_WIDE_PULL": 0.6765,
    "LEG_CURL": 0.5817,
    "LEG_PRESS": 1.8229,
    "LEG_RAISE": 0.1957,
    "LGE_EXT": 0.7483,
    "LOW_ROW_MC": 0.6409,
    "LUNGE": 0.1781,
    "LYING_TRI_EXT": 0.2917,
    "MC_LOW": 0.6924,
    "MOUNT_CLIMB": 0.2475,
    "OA_DB_ROW": 0.2895,
    "PEC_DECK_MC": 0.5811,
    "PENDLAY_ROW": 0.7172,
    "PISTOL_BOX_SQT": 0.1161,
    "PULL_UP": 0.1045,
    "PUSH_PRESS": 0.4306,
    "PUSH_UP": 0.2146,
    "REV_PEC_DECK_MC": 0.4944,
    "REV_V_SQT": 1.2341,
    "RM_BB_DL": 1.022,
    "RUS_TWIST": 0.1387,
    "SEAT_BB_SHD_PRESS": 0.4962,
    "SEAT_DB_SHD_PRESS": 0.2613,
    "SEATED_CABLE_ROW": 0.6947,
    "SHD_PRESS_MAC": 0.5301,
    "SIT_UP": 0.2497,
    "SM_BB_DL": 1.1459,
    "SM_BP": 0.6954,
    "SM_DL": 0.8463,
    "SM_ROW": 0.6799,
    "SM_SHRUG": 0.7959,
    "SM_SPLIT_SQT": 0.5131,
    "SM_SQT": 0.8349,
    "STD_CABLE_FLY": 0.281,
    "STIFF_DL": 0.7409,
    "T_BAR_ROW_MAC": 0.5141,
    "TOES_TO_BAR": 0.1118,
    "TURKISH_GET_UP": 0.1261,
    "V_SQT": 1.0988,
    "V-UP": 0.1729,
    "WEI_CHIN_UP": 0.3467,
    "WEI_DIPS": 0.3672,
    "WEI_HANG_KNEE_RAISE": 0.1124,
    "WEI_HIP_THRUST": 0.7297,
    "WEI_HPET": 0.2052,
    "WEI_PULL_UP": 0.2899,
    "DB_FRONT_SQT": 0.75,
    "LIN_HACK_SQT_MC": 0.85,
    "SM_BULSPLIT_SQT": 0.6,
    "SM_HIP_THRUSTER": 0.8,
    "SM_CALF_RAISE": 0.45,
    "DB_STD_CALF_RAISE": 0.4,
    "RACK_PULL": 1.0,
    "CHEST_SUP_T_ROW": 0.9,
    "MID_ROW_MC": 0.8,
    "INC_DB_PULL_OVER": 0.73,
    "CABLE_UPRIGHT_ROW": 0.48,
    "CABLE_BO_LAT_RAISE": 0.45,
    "SEAT_DB_LAT_RAISE": 0.43,
    "BB_INC_FRONT_RAISE": 0.55,
    "EZ_INC_FRONT_RAISE": 0.55,
    "INC_BB_FR_RAISE": 0.57,
    "INC_DB_FRONT_RAISE": 0.5,
    "INC_EZ_FRONT_RAISE": 0.55,
    "DB_INC_FRONT_RAISE": 0.5,
    "INC_DB_SHD_PRESS": 0.63,
    "KB_SHD_PRESS": 0.5,
    "CHEST_FLY_MC": 0.55,
    "DEC_PUSH_UP": 0.185,
    "KNEE_PU": 0.368,
    "DB_LYING_TRI_EXT": 0.5,
    "EZ_LYING_TRI_EXT": 0.55,
    "EZ_TRI_EXT": 0.55,
    "SEAT_BB_TRI_EXT": 0.6,
    "DB_SKULL_CRUSH": 0.52,
    "CONCENT_CURL": 0.45,
    "EZ_REVERSE_CURL": 0.5,
    "BICEP_CURL_MC": 0.55,
    "TORSO_ROT_MC": 0.35,
    "SEAT_KNEE_UP": 0.42
}
F_ratio_weight = {
    "ABS_CRUNCH_MC": 0.6869,
    "ABS_ROLL_OUT": 0.3459,
    "AIR_SQT": 0.4735,
    "ARM_CURL_MC": 0.3344,
    "ASS_DIP_MC": 1.4091,
    "ASS_PULLUP_MC": 1.4466,
    "BACK_ET": 0.3305,
    "BB_BC_CURL": 0.336,
    "BB_BP": 0.6451,
    "BB_BSQT": 1.0,
    "BB_DL": 1.2049,
    "BB_FR_LUNGE": 0.473,
    "BB_FRONT_RAISE": 0.2589,
    "BB_FSQ": 0.5918,
    "BB_INC_PRESS": 0.5043,
    "BB_JUMP_SQT": 0.6074,
    "BB_LAT_LUNGE": 0.3573,
    "BB_LOW": 0.6122,
    "BB_LUNGE": 0.5611,
    "BB_PREA_CURL": 0.3712,
    "BB_PRESS": 0.4274,
    "BB_SHRUG": 0.6957,
    "BB_SM_SQT": 0.6916,
    "BB_SPLIT_SQT": 0.4765,
    "BB_STD_CALF_RAISE": 0.6889,
    "BB_UPRIGHT_ROW": 0.3968,
    "BB_WRIST_CURL": 0.2811,
    "BENCH_DIPS": 0.315,
    "BURPEE": 0.3882,
    "BW_CALF_RAISE": 0.4281,
    "BW_LAT_LUNGE": 0.3648,
    "CABLE_ARM_PULL_DOWN": 0.5193,
    "CABLE_CRUNCH": 0.8788,
    "CABLE_CURL": 0.3818,
    "CABLE_FRONT_RAISE": 0.2445,
    "CABLE_HAM_CURL": 0.3977,
    "CABLE_LAT_RAISE": 0.1595,
    "CABLE_PULL_THRU": 0.5693,
    "CABLE_PUSH_DOWN": 0.4664,
    "CABLE_REV_FLY": 0.2586,
    "CG_BB_BP": 0.5944,
    "CHEST_PRESS_MC": 0.536,
    "CHIN_UP": 0.2516,
    "CROSS_OVER": 0.345,
    "CRUNCH": 0.5473,
    "DB_BC_CURL": 0.1615,
    "DB_BO_LAT_RAISE": 0.1183,
    "DB_BP": 0.2472,
    "DB_BULSPLIT_SQT": 0.232,
    "DB_DEC_FLY": 0.2639,
    "DB_FLY": 0.1769,
    "DB_F_RAISE": 0.126,
    "DB_HAM_CURL": 0.1659,
    "DB_INC_BP": 0.2483,
    "DB_INC_FLY": 0.1848,
    "DB_KICKBACK": 0.1095,
    "DB_LAT_LUNGE": 0.2111,
    "DB_LAT_RAISE": 0.1245,
    "DB_LOW": 0.2664,
    "DB_LUNGE": 0.2241,
    "DB_PREA_CURL": 0.2194,
    "DB_PULLOVER": 0.208,
    "DB_REAR_LAT_RAISE": 0.1192,
    "DB_SHD_PRESS": 0.1915,
    "DB_SHRUG": 0.3269,
    "DB_SIDE_BEND": 0.2163,
    "DB_SM_DL": 0.3437,
    "DB_SM_SQT": 0.3604,
    "DB_SPLIT_SQT": 0.234,
    "DB_THRUSTER": 0.1848,
    "DB_TRI_EXT": 0.1661,
    "DB_UPRIGHT_ROW": 0.2062,
    "DB_WRIST_CURL": 0.1771,
    "DB_Y_RAISE": 0.0978,
    "DEC_CHEST_MAC": 0.4514,
    "DEC_DB_BP": 0.3781,
    "DEC_SIT_UP": 0.3712,
    "DIPS": 0.2904,
    "DONK_KICK": 0.4309,
    "EZB_CURL": 0.3402,
    "EZB_FRONT_RAISE": 0.2675,
    "EZB_UPRIGHT_ROW": 0.3968,
    "EZB_WRIST_CURL": 0.2968,
    "EZ_PREA_CURL": 0.3399,
    "FACE_PULL": 0.5263,
    "GOBLET_SQT": 0.2882,
    "HACK_SQT": 0.8127,
    "HANG_KNEE_RAISE": 0.3576,
    "HANG_LEG_RAIGE": 0.3708,
    "HEEL_TOUCH": 0.4523,
    "HIGH_ROW_MC": 0.6314,
    "HINDU_PUSH_UP": 0.2721,
    "HIP_ABD_MC": 1.3618,
    "HIP_THRUST": 0.3622,
    "HIP_THRUST_MAC": 0.7823,
    "HPET": 0.3543,
    "HZ_LEG_PRESS": 1.5644,
    "INC_BB_ROW": 0.4091,
    "INC_BP_MAC": 0.4034,
    "INC_CABLE_FLY": 0.2225,
    "INC_CHEST_PRESS_MC": 0.3644,
    "INC_DB_CURL": 0.1604,
    "INC_DB_ROW": 0.2849,
    "INC_PUSH_UP": 0.3358,
    "INN_THIGH_MC": 0.9211,
    "INVT_ROW": 0.2765,
    "JUMPING_JACK": 0.7993,
    "JUMP_SQT": 0.3878,
    "KB_DL": 0.4307,
    "KB_GOBLET_SQT": 0.2842,
    "KB_SM_AIR_SQT": 0.3785,
    "KB_SM_DL": 0.3895,
    "KB_SM_SQT": 0.3446,
    "LAT_PULL_DOWN": 0.7087,
    "LAT_WIDE_PULL": 0.5871,
    "LEG_CURL": 0.5807,
    "LEG_PRESS": 1.6973,
    "LEG_RAISE": 0.4267,
    "LGE_EXT": 0.7024,
    "LOW_ROW_MC": 0.5995,
    "LUNGE": 0.3891,
    "LYING_TRI_EXT": 0.2758,
    "MC_LOW": 0.6671,
    "MOUNT_CLIMB": 0.4942,
    "OA_DB_ROW": 0.2397,
    "PEC_DECK_MC": 0.4763,
    "PENDLAY_ROW": 0.6433,
    "PISTOL_BOX_SQT": 0.2972,
    "PULL_UP": 0.2613,
    "PUSH_PRESS": 0.4148,
    "PUSH_UP": 0.3166,
    "REV_PEC_DECK_MC": 0.4327,
    "REV_V_SQT": 0.9211,
    "RM_BB_DL": 1.035,
    "RUS_TWIST": 0.1604,
    "SEAT_BB_SHD_PRESS": 0.3983,
    "SEAT_DB_SHD_PRESS": 0.2078,
    "SEATED_CABLE_ROW": 0.6993,
    "SHD_PRESS_MAC": 0.3554,
    "SIT_UP": 0.4794,
    "SM_BB_DL": 1.204,
    "SM_BP": 0.4867,
    "SM_DL": 0.7775,
    "SM_ROW": 0.5744,
    "SM_SHRUG": 0.7451,
    "SM_SPLIT_SQT": 0.5182,
    "SM_SQT": 0.7429,
    "STD_CABLE_FLY": 0.3314,
    "STIFF_DL": 0.7339,
    "T_BAR_ROW_MAC": 0.3919,
    "TOES_TO_BAR": 0.3814,
    "TURKISH_GET_UP": 0.1747,
    "V_SQT": 0.8447,
    "V-UP": 0.3893,
    "WEI_CHIN_UP": 0.9905,
    "WEI_DIPS": 1.2891,
    "WEI_HANG_KNEE_RAISE": 0.1022,
    "WEI_HIP_THRUST": 0.9139,
    "WEI_HPET": 0.2216,
    "WEI_PULL_UP": 1.1324,
    "DB_FRONT_SQT": 0.82,
    "LIN_HACK_SQT_MC": 0.95,
    "SM_BULSPLIT_SQT": 0.78,
    "SM_HIP_THRUSTER": 0.92,
    "SM_CALF_RAISE": 0.35,
    "DB_STD_CALF_RAISE": 0.32,
    "RACK_PULL": 1.06,
    "CHEST_SUP_T_ROW": 0.72,
    "MID_ROW_MC": 0.68,
    "INC_DB_PULL_OVER": 0.46,
    "CABLE_UPRIGHT_ROW": 0.42,
    "CABLE_BO_LAT_RAISE": 0.25,
    "SEAT_DB_LAT_RAISE": 0.27,
    "BB_INC_FRONT_RAISE": 0.31,
    "EZ_INC_FRONT_RAISE": 0.29,
    "INC_BB_FR_RAISE": 0.31,
    "INC_DB_FRONT_RAISE": 0.28,
    "INC_EZ_FRONT_RAISE": 0.29,
    "DB_INC_FRONT_RAISE": 0.28,
    "INC_DB_SHD_PRESS": 0.41,
    "KB_SHD_PRESS": 0.38,
    "CHEST_FLY_MC": 0.37,
    "DEC_PUSH_UP": 0.275,
    "KNEE_PU": 0.5793,
    "DB_LYING_TRI_EXT": 0.3,
    "EZ_LYING_TRI_EXT": 0.32,
    "EZ_TRI_EXT": 0.31,
    "SEAT_BB_TRI_EXT": 0.33,
    "DB_SKULL_CRUSH": 0.31,
    "CONCENT_CURL": 0.26,
    "EZ_REVERSE_CURL": 0.28,
    "BICEP_CURL_MC": 0.3,
    "TORSO_ROT_MC": 0.2,
    "SEAT_KNEE_UP": 0.5327
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
