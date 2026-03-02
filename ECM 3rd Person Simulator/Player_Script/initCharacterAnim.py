import bge

def init(cont):
    own = cont.owner

    # --- Authoritative Action State ---
    if "action_state" not in own:
        own["action_state"] = "idle"

    # --- Core Flags ---
    own["jumping"] = False
    own["grounded"] = True
    own["speed"] = 0.0

    # --- Input memory (prevents first-frame bugs) ---
    own["_prev_light"] = False
    own["_prev_jump"] = False

    # --- Play default animation ---
    own.playAction(
        "LLAidle.001",
        0,
        300,
        layer=0,
        play_mode=bge.logic.KX_ACTION_MODE_LOOP,
        speed=1.0
    )