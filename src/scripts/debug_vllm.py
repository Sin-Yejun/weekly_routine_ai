
import openai
from openai import OpenAI
import json

# This schema is copied from web/server.py
schema = {
  "type": "object",
  "properties": {
    "days": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "anyOf": [
            {
              "type": "array",
              "prefixItems": [
                { "type": "string", "enum": ["Abs","Cardio","etc"] },
                { "type": "string", "enum": ["TREADMIL","CYCLE","ROW_MACH","PLANK","CLIMB_STAIRS","ASSAULT_BIKE","BAT_ROPE","STEPMILL_MAC","ELLIP_MC","WALKING","RUNNING"] },
                {
                  "type": "array",
                  "items": {
                    "type": "array",
                    "prefixItems": [ { "const": 0 }, { "const": 0 }, { "type": "integer", "minimum": 300, "maximum": 1800, "multipleOf": 300} ],
                    "items": False,
                    "minItems": 3,
                    "maxItems": 3
                  }
                }
              ],
              "items": False
            },
            {
              "type": "array",
              "prefixItems": [
                { "type": "string", "enum": ["Cardio"] },
                { "type": "string", "enum": ["FARMER_WALK"] },
                {
                  "type": "array",
                  "items": {
                    "type": "array",
                    "prefixItems": [ { "const": 0 }, { "type": "integer", "minimum": 5, "maximum": 500, "multipleOf": 5 }, { "type": "integer", "minimum": 1, "maximum": 1800 } ],
                    "items": False,
                    "minItems": 3,
                    "maxItems": 3
                  }
                }
              ],
              "items": False
            },
            {
              "type": "array",
              "prefixItems": [
                { "type": "string", "enum": ["Abs","Arm","Back","Cardio","Chest","Leg","Shoulder","etc"] },
                { "type": "string", "enum": ["PUSH_UP","SIT_UP","LEG_RAISE","BURPEE","AIR_SQT","JUMP_SQT","HINDU_PUSH_UP","V-UP","PULL_UP","DIPS","MOUNT_CLIMB","LUNGE","CHIN_UP","STEP_UP","INVT_ROW","HIP_THRUST","HPET","BACK_ET","CRUNCH","HEEL_TOUCH","HANG_LEG_RAIGE","ABS_ROLL_OUT","ABS_AIR_BIKE","TOES_TO_BAR","BOX_JUMP","JUMPING_JACK","HANG_KNEE_RAISE","HIGH_KNEE_SKIP","DOUBLE_UNDER","INCHWORM","CLAP_PUSH_UP","INC_PUSH_UP","BW_CALF_RAISE","PISTOL_BOX_SQT","GLUTE_BRDG","BENCH_DIPS","BW_LAT_LUNGE","KB_SM_AIR_SQT","PISTOL_SQT","Y_RAISE","DONK_KICK","DEC_SIT_UP","SEAT_KNEE_UP","DEC_PUSH_UP","DONK_CALF_RAISE","KNEE_PU"] },
                {
                  "type": "array",
                  "items": {
                    "type": "array",
                    "prefixItems": [ { "type": "integer", "minimum": 1, "maximum": 20 }, { "const": 0 }, { "const": 0 } ],
                    "items": False,
                    "minItems": 3,
                    "maxItems": 3
                  }
                }
              ],
              "items": False
            },
            {
              "type": "array",
              "prefixItems": [
                { "type": "string", "enum": ["Abs","Arm","Back","Cardio","Chest","Leg","Lifting","Shoulder","etc"] },
                { "type": "string", "enum": ["BB_BSQT","BB_DL","BB_FSQ","LEG_PRESS","LEG_CURL","LGE_EXT","BB_BP","BB_INC_PRESS","DB_BP","DB_FLY","CROSS_OVER","BB_LOW","DB_LOW","LAT_PULL_DOWN","BB_PRESS","DB_SHD_PRESS","DB_LAT_RAISE","DB_F_RAISE","DB_SHRUG","BB_BC_CURL","DB_BC_CURL","DB_TRI_EXT","DB_KICKBACK","DB_WRIST_CURL","THRUSTER","DB_BO_LAT_RAISE","WEI_PULL_UP","RUS_TWIST","PENDLAY_ROW","MC_LOW","WEI_DIPS","SM_BB_DL","EZB_CURL","SEATED_CABLE_ROW","CABLE_PUSH_DOWN","INN_THIGH_MC","GOOD_MORN","BB_SPLIT_SQT","DB_BULSPLIT_SQT","DB_SPLIT_SQT","GOBLET_SQT","KB_GOBLET_SQT","RM_BB_DL","DB_LUNGE","WEI_HIP_THRUST","DB_INC_FLY","DB_INC_BP","CHEST_PRESS_MC","PEC_DECK_MC","INC_BP_MAC","DB_PULLOVER","WEI_CHIN_UP","INC_BB_ROW","INC_DB_ROW","OA_DB_ROW","WEI_HPET","SHD_PRESS_MAC","BB_SHRUG","FACE_PULL","CABLE_REV_FLY","BB_UPRIGHT_ROW","DB_UPRIGHT_ROW","EZB_UPRIGHT_ROW","DB_HAM_CURL","CABLE_CURL","CG_BB_BP","BB_WRIST_CURL","EZB_WRIST_CURL","LYING_TRI_EXT","DB_SIDE_BEND","PUSH_PRESS","KB_SWING","WB_SHOT","V_SQT","REV_V_SQT","T_BAR_ROW_MAC","DB_PREA_CURL","BB_PREA_CURL","EZ_PREA_CURL","REV_PEC_DECK_MC","HIP_ABD_MC","KB_SNATCH","CABLE_CRUNCH","ARM_CURL_MC","SM_SQT","HACK_SQT","CABLE_LAT_RAISE","ABS_CRUNCH_MC","PAUSE_SQT","SM_SPLIT_SQT","SM_ROW","CABLE_ARM_PULL_DOWN","PAUSE_BB_ROW","PAUSE_SM_DL","SM_DL","PAUSE_DL","SM_BP","CABLE_HAM_CURL","SM_SHRUG","CABLE_FRONT_RAISE","DB_SNATCH","SM_INC_PRESS","BB_LUNGE","DB_SM_SQT","ASS_PULLUP_MC","BB_LAT_LUNGE","DB_DEC_FLY","WEI_HANG_KNEE_RAISE","ASS_DIP_MC","BB_SPLIT_SQT_REAL","DB_SQT","BB_BOX_SQT","DB_BURPEE","BB_FLOOR_PRESS","BB_STD_CALF_RAISE","DB_LEG_CURL","BB_DEC_BP","DB_THRUSTER","EZB_FRONT_RAISE","STIFF_DL","DB_REAR_LAT_RAISE","BB_FR_LUNGE","BB_FRONT_RAISE","BB_HACK_SQT","BB_JUMP_SQT","SUMO_DEAD_HIGH","LAT_WIDE_PULL","HANG_CLEAN","HANG_SNATCH","DEC_DB_BP","HIP_THRUST_MAC","INC_DB_CURL","DEC_CHEST_MAC","INC_CABLE_FLY","STD_CABLE_FLY","KB_DL","KB_SM_DL","DB_SM_DL","DB_LAT_LUNGE","HZ_LEG_PRESS","NOR_HAM_CURL","BB_SM_SQT","KB_SM_SQT","SEAT_BB_SHD_PRESS","SEAT_DB_SHD_PRESS","PLATE_SHD_PRESS","DB_Y_RAISE","LOW_ROW_MC","HIGH_ROW_MC","WEI_DEC_SIT_UP","DEFICIT_DL","TURKISH_GET_UP","INC_CHEST_PRESS_MC","CABLE_PULL_THRU","CABLE_BO_LAT_RAISE","CABLE_UPRIGHT_ROW","TORSO_ROT_MC","RACK_PULL","KB_SHD_PRESS","INC_DB_SHD_PRESS","LIN_HACK_SQT_MC","SM_CALF_RAISE","DB_STD_CALF_RAISE","MID_ROW_MC","CONCENT_CURL","INC_BB_FR_RAISE","INC_EZ_FRONT_RAISE"] },
                {
                  "type": "array",
                  "items": {
                    "type": "array",
                    "prefixItems": [ { "type": "integer", "minimum": 1, "maximum": 20 }, { "type": "integer", "minimum": 5, "maximum": 500, "multipleOf": 5 }, { "const": 0 } ],
                    "items": False,
                    "minItems": 3,
                    "maxItems": 3
                  }
                }
              ],
              "items": False
            }
          ]
        }
      }
    }
  },
  "required": ["days"],
  "additionalProperties": False
}

# --- Model & API Configuration --
VLLM_BASE_URL = "http://127.0.0.1:8000/v1"
VLLM_MODEL    = "google/gemma-3-4b-it"

# A sample prompt. You can replace this with a real prompt that causes issues.
# You can get a real prompt by running the web server and copying the logged prompt.
sample_prompt = """
**Objective:** Generate a comprehensive and logically structured 3-day weekly workout routine tailored to the user's profile and goals.

**User Profile:**
*   **Gender:** M
*   **Weight:** 70.0 kg
*   **Experience Level:** Intermediate
*   **Workout Frequency:** 3 days/week
*   **Workout Duration:** 60 minutes/session
*   **Workout Intensity:** Normal

**Instructions:**
1.  **Format:** The output MUST be a single, valid JSON object. Do not include any text or formatting before or after the JSON object.
2.  **Structure:** The JSON object must have a single root key named "days". The value of "days" must be an array containing exactly 3 arrays, where each inner array represents a workout day.
3.  **Content:** Each "day" array must contain multiple "exercise" arrays. Each "exercise" array must have the following structure: `["bName", "eTextId", [sets, reps, weight_or_duration]]`.
4.  **Exercise Selection:**
    *   Choose exercises from the provided catalog that are appropriate for the user's profile.
    *   Ensure a balanced routine that targets different muscle groups across the week.
    *   Follow the specified `eInfoType` to determine the correct format for `[sets, reps, weight_or_duration]`:
        *   `eInfoType: 1` (Cardio/Duration): `[0, 0, duration_in_seconds]` (e.g., `[0, 0, 900]`).
        *   `eInfoType: 2` (Bodyweight/Reps): `[sets, 0, 0]` (e.g., `[3, 0, 0]`).
        *   `eInfoType: 5` (Carries/Distance & Time): `[0, distance_in_meters, time_in_seconds]` (e.g., `[0, 100, 120]`).
        *   `eInfoType: 6` (Weight Training/Sets & Reps): `[sets, reps, 0]` (e.g., `[4, 10, 0]`).
5.  **Constraints:**
    *   The total number of exercises per day should be reasonable for a 60-minute session.
    *   The `eTextId` and `bName` must correspond to an entry in the exercise catalog.
    *   The values for sets, reps, and duration must be within realistic and safe limits for an intermediate user.

**Exercise Catalog:**
*   `eInfoType: 1`: TREADMIL, CYCLE, ROW_MACH, PLANK, CLIMB_STAIRS, ASSAULT_BIKE, BAT_ROPE, STEPMILL_MAC, ELLIP_MC, WALKING, RUNNING
*   `eInfoType: 2`: PUSH_UP, SIT_UP, LEG_RAISE, BURPEE, AIR_SQT, JUMP_SQT, HINDU_PUSH_UP, V-UP, PULL_UP, DIPS, MOUNT_CLIMB, LUNGE, CHIN_UP, STEP_UP, INVT_ROW, HIP_THRUST, HPET, BACK_ET, CRUNCH, HEEL_TOUCH, HANG_LEG_RAIGE, ABS_ROLL_OUT, ABS_AIR_BIKE, TOES_TO_BAR, BOX_JUMP, JUMPING_JACK, HANG_KNEE_RAISE, HIGH_KNEE_SKIP, DOUBLE_UNDER, INCHWORM, CLAP_PUSH_UP, INC_PUSH_UP, BW_CALF_RAISE, PISTOL_BOX_SQT, GLUTE_BRDG, BENCH_DIPS, BW_LAT_LUNGE, KB_SM_AIR_SQT, PISTOL_SQT, Y_RAISE, DONK_KICK, DEC_SIT_UP, SEAT_KNEE_UP, DEC_PUSH_UP, DONK_CALF_RAISE, KNEE_PU
*   `eInfoType: 5`: FARMER_WALK
*   `eInfoType: 6`: BB_BSQT, BB_DL, BB_FSQ, LEG_PRESS, LEG_CURL, LGE_EXT, BB_BP, BB_INC_PRESS, DB_BP, DB_FLY, CROSS_OVER, BB_LOW, DB_LOW, LAT_PULL_DOWN, BB_PRESS, DB_SHD_PRESS, DB_LAT_RAISE, DB_F_RAISE, DB_SHRUG, BB_BC_CURL, DB_BC_CURL, DB_TRI_EXT, DB_KICKBACK, DB_WRIST_CURL, THRUSTER, DB_BO_LAT_RAISE, WEI_PULL_UP, RUS_TWIST, PENDLAY_ROW, MC_LOW, WEI_DIPS, SM_BB_DL, EZB_CURL, SEATED_CABLE_ROW, CABLE_PUSH_DOWN, INN_THIGH_MC, GOOD_MORN, BB_SPLIT_SQT, DB_BULSPLIT_SQT, DB_SPLIT_SQT, GOBLET_SQT, KB_GOBLET_SQT, RM_BB_DL, DB_LUNGE, WEI_HIP_THRUST, DB_INC_FLY, DB_INC_BP, CHEST_PRESS_MC, PEC_DECK_MC, INC_BP_MAC, DB_PULLOVER, WEI_CHIN_UP, INC_BB_ROW, INC_DB_ROW, OA_DB_ROW, WEI_HPET, SHD_PRESS_MAC, BB_SHRUG, FACE_PULL, CABLE_REV_FLY, BB_UPRIGHT_ROW, DB_UPRIGHT_ROW, EZB_UPRIGHT_ROW, DB_HAM_CURL, CABLE_CURL, CG_BB_BP, BB_WRIST_CURL, EZB_WRIST_CURL, LYING_TRI_EXT, DB_SIDE_BEND, PUSH_PRESS, KB_SWING, WB_SHOT, V_SQT, REV_V_SQT, T_BAR_ROW_MAC, DB_PREA_CURL, BB_PREA_CURL, EZ_PREA_CURL, REV_PEC_DECK_MC, HIP_ABD_MC, KB_SNATCH, CABLE_CRUNCH, ARM_CURL_MC, SM_SQT, HACK_SQT, CABLE_LAT_RAISE, ABS_CRUNCH_MC, PAUSE_SQT, SM_SPLIT_SQT, SM_ROW, CABLE_ARM_PULL_DOWN, PAUSE_BB_ROW, PAUSE_SM_DL, SM_DL, PAUSE_DL, SM_BP, CABLE_HAM_CURL, SM_SHRUG, CABLE_FRONT_RAISE, DB_SNATCH, SM_INC_PRESS, BB_LUNGE, DB_SM_SQT, ASS_PULLUP_MC, BB_LAT_LUNGE, DB_DEC_FLY, WEI_HANG_KNEE_RAISE, ASS_DIP_MC, BB_SPLIT_SQT_REAL, DB_SQT, BB_BOX_SQT, DB_BURPEE, BB_FLOOR_PRESS, BB_STD_CALF_RAISE, DB_LEG_CURL, BB_DEC_BP, DB_THRUSTER, EZB_FRONT_RAISE, STIFF_DL, DB_REAR_LAT_RAISE, BB_FR_LUNGE, BB_FRONT_RAISE, BB_HACK_SQT, BB_JUMP_SQT, SUMO_DEAD_HIGH, LAT_WIDE_PULL, HANG_CLEAN, HANG_SNATCH, DEC_DB_BP, HIP_THRUST_MAC, INC_DB_CURL, DEC_CHEST_MAC, INC_CABLE_FLY, STD_CABLE_FLY, KB_DL, KB_SM_DL, DB_SM_DL, DB_LAT_LUNGE, HZ_LEG_PRESS, NOR_HAM_CURL, BB_SM_SQT, KB_SM_SQT, SEAT_BB_SHD_PRESS, SEAT_DB_SHD_PRESS, PLATE_SHD_PRESS, DB_Y_RAISE, LOW_ROW_MC, HIGH_ROW_MC, WEI_DEC_SIT_UP, DEFICIT_DL, TURKISH_GET_UP, INC_CHEST_PRESS_MC, CABLE_PULL_THRU, CABLE_BO_LAT_RAISE, CABLE_UPRIGHT_ROW, TORSO_ROT_MC, RACK_PULL, KB_SHD_PRESS, INC_DB_SHD_PRESS, LIN_HACK_SQT_MC, SM_CALF_RAISE, DB_STD_CALF_RAISE, MID_ROW_MC, CONCENT_CURL, INC_BB_FR_RAISE, INC_EZ_FRONT_RAISE

**Generate the JSON output now.**
"""

def test_vllm_stability():
    """
    Sends the same request to the vLLM server twice to check for stability issues.
    """
    try:
        client = OpenAI(base_url=VLLM_BASE_URL, api_key="token-1234")
    except Exception as e:
        print(f"Error creating OpenAI client: {e}")
        return

    for i in range(2):
        print(f"--- Sending request #{i + 1} ---")
        try:
            resp = client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[{"role": "user", "content": sample_prompt}],
                temperature=0.0,
                extra_body={"guided_json": schema, "xgrammar_options": {"coerce_one_of": True}},
                max_tokens=4096
            )
            raw_response_text = resp.choices[0].message.content
            print(f"Request #{i + 1} successful. Response length: {len(raw_response_text)}")
            # print(raw_response_text) # Uncomment to see the full response
        except openai.APIStatusError as e:
            print(f"Request #{i + 1} failed with APIStatusError: {e.status_code}")
            print(f"Response body: {e.response.text}")
        except Exception as e:
            print(f"Request #{i + 1} failed with an unexpected error: {e}")

if __name__ == "__main__":
    test_vllm_stability()
