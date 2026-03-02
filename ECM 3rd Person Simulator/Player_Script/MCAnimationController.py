import bge

# ===== CONFIG =====
HITBOX_NAME = "Cube.164"
# ==================

def update(cont):
    own = cont.owner              # armature
    player = own.parent           # movement controller
    scene = bge.logic.getCurrentScene()

    # --------------------------------------------------
       # --------------------------------------------------
    # ACTION OVERRIDE (Attack / Dodge / etc)
    # --------------------------------------------------
    prev_action = own.get("_prev_action_state", None)
    action_state = own.get("action_state")
    own["_prev_action_state"] = action_state

    if action_state:
        print(
    "[LOCO DEBUG]",
    "prev_action:", prev_action,
    "action_state:", action_state,
    "dirty:", own.get("locomotion_dirty"),
    "last:", own.get("last_state"),
    "input_moving:", player.get("input_moving"),
    "fwd:", round(player.get("forward_speed", 0.0), 3),
    "side:", round(player.get("sideways_speed", 0.0), 3),
    "lock:", player.get("lock_on"),
)

        action_anim = own.get("action_anim")
        layer = own.get("action_layer", 1)

        if action_anim and not own.isPlayingAction(layer):
            own.playAction(
                action_anim,
                0, 100,
                layer=layer,
                play_mode=bge.logic.KX_ACTION_MODE_PLAY,
                speed=1.0
            )
        return  # locomotion suppressed DURING action

    # 🔑 action just ended → resync locomotion ONCE
    if prev_action and not action_state:
        if not own.get("combo_active", False):
            own.stopAction(0)   # clear action layer
            own["locomotion_dirty"] = True
            own["last_state"] = None




    # --------------------------------------------------
    # LOCOMOTION STATE DECISION
    # --------------------------------------------------
    grounded = player.get("grounded", True)
    input_moving = player.get("input_moving", False)
    forward = player.get("forward_speed", 0.0)
    sideways = player.get("sideways_speed", 0.0)
    lock_on = player.get("lock_on", False)
    prev_lock = own.get("_prev_lock", False)
    own["_prev_lock"] = lock_on

    if prev_lock != lock_on:
        own["locomotion_dirty"] = True
        own["last_state"] = None
        own["last_state"] = "__FORCE__"

    vel_z = player.worldLinearVelocity.z

    if not grounded:
        if vel_z > 0.1:
            new_state = "jump"
        else:
            new_state = "fall"


    elif input_moving:
        if lock_on:
            if abs(sideways) > 0.02 and abs(forward) < 0.02:
                new_state = "strafe_right" if sideways > 0 else "strafe_left"
            elif forward < -0.02:
                new_state = "back"
            elif forward > 0.025:
                new_state = "run"
            elif forward > 0.006:
                new_state = "walk"
            else:
                new_state = "idle"
        else:
            if abs(forward) > abs(sideways):
                new_state = "run" if abs(forward) > 0.025 else "walk"
            else:
                new_state = "run" if abs(sideways) > 0.025 else "walk"
    else:
        new_state = "idle" if lock_on else "idle2"

    # --------------------------------------------------
    # PLAY LOCOMOTION ANIMATION
    # --------------------------------------------------
    dirty = own.get("locomotion_dirty", False)

    if own.get("last_state") == new_state and not dirty:
        if own.isPlayingAction(0):
            print("[LOCO SKIP]", new_state)
            return



    own.stopAction(0)

    ACTIONS = {
        "idle":       ("LLSEXYIDLE", 275, 600),
        "idle2":      ("LLSEXYIDLE", 275, 600),
        "walk":       ("LLA1stLocomotions", 0, 64),
        "run":        ("LLA1stLocomotions", 66, 95),
        "strafe_left":("LLAStrafeLeft", 66, 95),
        "strafe_right":("LLAStrafeRight",66, 95),
        "back":       ("LLAStrafeBack", 0, 29),
        "jump":       ("LLAJump", 0, 28),
        "fall":       ("LLAJump", 12, 16),
    }

    anim = ACTIONS.get(new_state)
    if anim:
        own.playAction(
            anim[0], anim[1], anim[2],
            layer=0,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP
        )

    own["last_state"] = new_state
    own["locomotion_dirty"] = False
