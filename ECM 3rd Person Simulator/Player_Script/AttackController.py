import bge

HITBOX_NAME = "Cube.164"
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

        if not active:
            hitbox["_already_hit"] = False   # reset for next swing

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

    if "action_state" not in own:
        own["action_state"] = None
        own["combo_index"] = 0
        own["combo_type"] = None
        own["queued"] = False

    # ---------------- IDLE ----------------

#    if own["action_state"] is None:

#        toggle_hitbox(hitbox, False)

#        if light_buffered:
#            own["light_buffer"] = 0
#            start_attack(own, "light", 0)
#            return

#        elif medium_buffered:
#            own["medium_buffer"] = 0
#            start_attack(own, "medium", 0)
#            return

#        return
    # ---------------- STATE FLOW ----------------

    state = own.get("action_state")

    if state is None:
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

    # 🔴 If not in ATTACK, do nothing here
    if state != "ATTACK":
        toggle_hitbox(hitbox, False)
        return
    # ---------------- ATTACK STATE ----------------

    combo_type = own.get("combo_type")
    combo = COMBOS[combo_type]
    step = combo[own["combo_index"]]
    frame = int(own.getActionFrame(ACTION_LAYER))

    # ---- HIT WINDOW ----
    # ---- HIT WINDOW ----
# ---- HIT WINDOW (Player Script) ----
    if step["active"][0] <= frame <= step["active"][1]:
        toggle_hitbox(hitbox, True)
        
        # Ensure the hitbox tells the enemy WHAT hit it
        # You can use the animation name or a specific ID
        hitbox["attack_type"] = step["anim"] 

        if not own.get("hit_sent", False):
            #bge.logic.sendMessage(step["anim"], "", "SaturnHurtBox.001")
            bge.logic.sendMessage(step["anim"])
            own["hit_sent"] = True
            print(f"[ATTACK] Sent {step['anim']}")
    else:
        toggle_hitbox(hitbox, False)
        hitbox["attack_type"] = "" # Clear it when not active

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
    player = own.parent
    if player:
        player["movement_locked"] = True

    own["action_state"] = "ATTACK"
    own["combo_type"] = combo_name
    own["combo_index"] = index
    own["queued"] = False
    own["hit_sent"] = False

    own["action_anim"] = step["anim"]
    own["action_layer"] = ACTION_LAYER

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
    player = own.parent
    if player:
        player["movement_locked"] = False

    own["action_state"] = None
    own["combo_index"] = 0
    own["combo_type"] = None
    own["queued"] = False
