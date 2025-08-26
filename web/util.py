import re
from enum import Enum

# _to_number function moved to server.py

class FormattingStyle(Enum):
    HISTORY_SUMMARY = 1  # For [Recent Workout History]
    FORMATTED_ROUTINE = 2 # For Formatted Routine

def _parse_set_triplet(s):
    """
    Parses various formats into a (w, r, t) tuple.
    Handles lists, strings, and nested string/lists.
    """
    if isinstance(s, (list, tuple)):
        if len(s) == 3:
            return [_to_number(s[0]), _to_number(s[1]), _to_number(s[2])]
        if len(s) == 1 and isinstance(s[0], str):
            return _parse_set_triplet(s[0])
        return None

    if isinstance(s, str):
        stripped = s.strip().strip('[](){}')
        parts = [p.strip() for p in stripped.split(',')]
        if len(parts) == 3:
            return [_to_number(parts[0]), _to_number(parts[1]), _to_number(parts[2])]
    return None

def compress_sets(sets: list) -> str:
    """Compresses a list of set dictionaries into a readable string."""
    out = []
    if not sets:
        return ""
    for s in sets:
        if not isinstance(s, dict): continue
        reps, weight, time = s.get("reps"), s.get("weight"), s.get("time")
        if time and time > 0:
            out.append(f"{time}s")
            continue
        
        w_disp = int(weight) if weight is not None and isinstance(weight, (int, float)) and float(weight).is_integer() else weight
        
        base = ""
        if w_disp is not None and w_disp != 0:
            base = f"{w_disp}x{reps}"
        else:
            base = f"{reps}"
        out.append(base)
    return " / ".join(out)

def summarize_user_history(workout_days: list, exercise_name_map: dict, style: FormattingStyle) -> str:
    """
    Formats a routine into a human-readable summary, using a provided exercise map.
    """
    texts = []
    for idx, day in enumerate(workout_days, 1):
        duration = day.get('duration')
        duration_str = f" (Duration: {duration}min)" if duration else ""
        header = f"[Workout #{idx}{duration_str}]"
        lines = [header]
        
        if "session_data" in day and day["session_data"]:
            for ex in day["session_data"]:
                e_text_id = (ex.get('eTextId') or ex.get('e_text_id') or
                             ex.get('eName') or ex.get('e_name') or 'N/A')

                display_name = e_text_id # Default to e_text_id

                if style == FormattingStyle.FORMATTED_ROUTINE:
                    exercise_info = exercise_name_map.get(e_text_id, {})
                    b_name = exercise_info.get('bName')
                    e_name = exercise_info.get('eName')
                    if b_name and e_name:
                        display_name = f"[{b_name}] {e_name}"
                elif style == FormattingStyle.HISTORY_SUMMARY:
                    # For history summary, we just want the eTextId
                    display_name = e_text_id

                sets_data = ex.get('sets') or []
                if not sets_data:
                    continue
                    
                num_sets = len(sets_data)
                compressed_sets_str = compress_sets(sets_data)
                line = f"- {display_name}: {num_sets}sets: {compressed_sets_str}"
                lines.append(line)
                
        if len(lines) > 1:
            texts.append("\n".join(lines))
            
    return "\n\n".join(texts)
