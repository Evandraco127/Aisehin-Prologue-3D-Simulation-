import bge

# -------------------------
# CONFIG
# -------------------------
# HITBOX_NAME = "Cube.164"
ACTION_LAYER = 1
INPUT_BUFFER = 20

# -------------------------
# COMBO DATA
# -------------------------
COMBOS = {
    "light": [
        {"anim": "LLA_Light_1", "length": 23, "active": (15, 19), "cancel": (17, 21)},
        {"anim": "LLA_Light_2", "length": 22, "active": (6, 12),  "cancel": (10, 15)},
        {"anim": "LLA_Light_3", "length": 20, "active": (10, 16), "cancel": (14, 19)},
    ],
    "medium": [
        {"anim": "LLA_Kick_1", "length": 26, "active": (14, 20), "cancel": (18, 26)},
        {"anim": "LLA_Kick_2", "length": 24, "active": (8, 14),  "cancel": (12, 18)},
        {"anim": "LLA_Kick_3", "length": 24, "active": (14, 18), "cancel": (15, 24)},
    ]
}

# -------------------------
# HITBOX
# -------------------------
def toggle_hitbox(hitbox, active):
    if not hitbox:
        return
    if hitbox.visible != active:
        hitbox.visible = active
        hitbox.suspendDynamics(not active)
        hitbox["active"] = active
        print(f"[HITBOX] {'ON' if active else 'OFF'}")
        hitbox["active"] = active
# -------------------------
# START ATTACK
# -------------------------
def start_attack(own, combo_type, index):
    if combo_type not in COMBOS:
        print("Invalid combo type:", combo_type)
        return

    if index >= len(COMBOS[combo_type]):
        print("Combo index out of range")
        return

    step = COMBOS[combo_type][index]

    own["action_state"] = "ATTACK"
    own["combo_type"] = combo_type
    own["combo_index"] = index
    own["queued"] = False
    own["queued_type"] = None 
    own["combo_active"] = True   # 🔥 ADD THIS

    own.playAction(
        step["anim"],
        0,
        step["length"],
        layer=ACTION_LAYER,
        play_mode=bge.logic.KX_ACTION_MODE_PLAY,
        speed=1.0,
        blendin=0
    )

# -------------------------
# RESET ATTACK
# -------------------------
def reset_attack(own):
    own.stopAction(ACTION_LAYER)
    own["action_state"] = None
    own["combo_index"] = 0
    own["combo_type"] = None
    own["queued"] = False
    own["queued_type"] = None
    own["combo_active"] = False   # 🔥 ADD THIS
    toggle_hitbox(own.get("hitbox", None), False)

# -------------------------
# UPDATE CONTROLLER
# -------------------------
def update(cont):
    own = cont.owner
    scene = bge.logic.getCurrentScene()
    
    # ---- HITBOX INIT ----
    if "hitbox" not in own:
        own["hitbox"] = own.children.get("Cube.164")
        
    hitbox = own["hitbox"]

    # ---- INPUT BUFFER ----
    if "light_buffer" not in own: own["light_buffer"] = 0
    if "medium_buffer" not in own: own["medium_buffer"] = 0

    # Input flags (set externally in your main movement script)
    light_pressed = own.get("light_pressed", False)
    medium_pressed = own.get("medium_pressed", False)

    # --- EDGE DETECTION (just pressed) ---
    prev_light = own.get("_prev_light", False)
    prev_medium = own.get("_prev_medium", False)

    just_pressed_light = light_pressed and not prev_light
    just_pressed_medium = medium_pressed and not prev_medium

    own["_prev_light"] = light_pressed
    own["_prev_medium"] = medium_pressed

    # --- Fill buffer only on press, not hold ---
    if just_pressed_light:
        if just_pressed_light:
            print("LIGHT JUST PRESSED")
            own["pending_light"] = True
            print("LIGHT INTENT STORED")

    if just_pressed_medium:
        own["medium_buffer"] = INPUT_BUFFER

    if own["light_buffer"] > 0: own["light_buffer"] -= 1
    if own["medium_buffer"] > 0: own["medium_buffer"] -= 1

    light_buffered = own["light_buffer"] > 0
    medium_buffered = own["medium_buffer"] > 0

    # ---- STATE INIT ----
    if "action_state" not in own:
        own["action_state"] = None
        own["combo_index"] = 0
        own["combo_type"] = None
        own["queued"] = False
        own["queued_type"] = None

    # ---- IDLE / START NEW ATTACK ----
    if own["action_state"] is None:
        toggle_hitbox(hitbox, False)
        if light_buffered:
            own["light_buffer"] = 0
            start_attack(own, "light", 0)
            return
        elif medium_buffered:
            own["medium_buffer"] = 0
            start_attack(own, "medium", 0)
            return
        return

    # ---- ATTACK STATE ----
    combo_type = own["combo_type"]
    combo = COMBOS[combo_type]
    step = combo[own["combo_index"]]
    frame = int(own.getActionFrame(ACTION_LAYER))
    print("L1 playing:", own.isPlayingAction(1), "Frame:", own.getActionFrame(1))

    # --- HIT WINDOW ---
    active = step["active"][0] <= frame <= step["active"][1]
    toggle_hitbox(hitbox, active)

    # send hit message only once per activation
    if active and not own.get("hit_sent", False):
        bge.logic.sendMessage("LLAPunch1", "", "")
        own["hit_sent"] = True
        print("Sent LLAPunch1")

    if not active:
        own["hit_sent"] = False

    # --- CANCEL WINDOW ---
    if step["cancel"][0] <= frame <= step["cancel"][1] and not own["queued"]:
        print("Frame:", frame, "Cancel:", step["cancel"])
        print("light_buffer:", own["light_buffer"])
        if light_buffered:
            own["queued"] = True
            own["queued_type"] = "light"
            own["pending_light"] = False
            print("COMBO QUEUED")
        elif medium_buffered:
            own["queued"] = True
            own["queued_type"] = "medium"
            own["medium_buffer"] = 0

    # --- END OF ANIMATION ---
    if frame >= step["length"] - 1:
        if own["queued"]:
            if own["queued_type"] == combo_type:
                next_index = own["combo_index"] + 1
            else:
                next_index = 0

            if next_index >= len(COMBOS[own["queued_type"]]):
                reset_attack(own)
            else:
                start_attack(own, own["queued_type"], next_index)
        else:
            reset_attack(own)