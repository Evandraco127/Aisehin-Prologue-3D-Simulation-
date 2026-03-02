import bge

HITBOX_NAME = "Cube.001"
ACTION_LAYER = 1
INPUT_BUFFER = 8

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


# -------------------------
# CONTROLLER
# -------------------------

def update(cont):
    own = cont.owner
    scene = bge.logic.getCurrentScene()

    # ---------------- HITBOX ----------------

    if "hitbox" not in own:
        own["hitbox"] = scene.objects.get(HITBOX_NAME)
    hitbox = own["hitbox"]

    # ---------------- INPUT BUFFER INIT ----------------

    if "light_buffer" not in own:
        own["light_buffer"] = 0

    if "medium_buffer" not in own:
        own["medium_buffer"] = 0

    # Input flags (these must be set elsewhere)
    light_pressed = own.get("light_pressed", False)
    medium_pressed = own.get("medium_pressed", False)

    # Buffer input
    if light_pressed:
        own["light_buffer"] = INPUT_BUFFER

    if medium_pressed:
        own["medium_buffer"] = INPUT_BUFFER

    # Count down buffer
    if own["light_buffer"] > 0:
        own["light_buffer"] -= 1

    if own["medium_buffer"] > 0:
        own["medium_buffer"] -= 1

    light_buffered = own["light_buffer"] > 0
    medium_buffered = own["medium_buffer"] > 0

    # ---------------- STATE INIT ----------------

    if "attack_state" not in own:
        own["attack_state"] = None
        own["combo_index"] = 0
        own["combo_type"] = None
        own["queued"] = False

    # ---------------- IDLE ----------------

    if own["attack_state"] is None:

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

    # ---------------- ATTACK STATE ----------------

    combo_type = own["combo_type"]
    combo = COMBOS[combo_type]
    step = combo[own["combo_index"]]

    frame = int(own.getActionFrame(ACTION_LAYER))

    # ---- HIT WINDOW ----
    if step["active"][0] <= frame <= step["active"][1]:
        toggle_hitbox(hitbox, True)
    else:
        toggle_hitbox(hitbox, False)

    # ---- CANCEL WINDOW ----
    if step["cancel"][0] <= frame <= step["cancel"][1] and not own["queued"]:

        if combo_type == "light" and light_buffered:
            own["queued"] = True
            own["light_buffer"] = 0

        elif combo_type == "medium" and medium_buffered:
            own["queued"] = True
            own["medium_buffer"] = 0

    # ---- END ANIMATION ----
    if frame >= step["length"] - 1:

        if own["queued"] and own["combo_index"] + 1 < len(combo):
            start_attack(own, combo_type, own["combo_index"] + 1)
        else:
            reset_attack(own)


# -------------------------
# HELPERS
# -------------------------

def start_attack(own, combo_name, index):

    step = COMBOS[combo_name][index]

    own["attack_state"] = "ATTACK"
    own["combo_type"] = combo_name
    own["combo_index"] = index
    own["queued"] = False

    print(f"[PLAY] {step['anim']}")

    own.playAction(
        step["anim"],
        0,
        step["length"],
        layer=ACTION_LAYER,
        play_mode=bge.logic.KX_ACTION_MODE_PLAY,
        speed=1.0,
        blendin=2
    )


def reset_attack(own):

    own.stopAction(ACTION_LAYER)

    own["attack_state"] = None
    own["combo_index"] = 0
    own["combo_type"] = None
    own["queued"] = False
