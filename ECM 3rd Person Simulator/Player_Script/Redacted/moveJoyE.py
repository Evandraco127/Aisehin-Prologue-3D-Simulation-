import bge
import math
import mathutils
from mathutils import Vector, Euler

# -----------------------------
# Utility (movejoyF.py)
# -----------------------------

def _norm_axis(v):
    """
    Normalize joystick axis values.
    Some controllers give huge int values (e.g., 32767).
    Reference: https://upbge.org/docs/latest/api/bge.types.SCA_JoystickSensor.html#bge.types.SCA_JoystickSensor.axis
    This clamps it into [-1.0, 1.0].
    """
    try:
        fv = float(v)
    except:
        return 0.0
    return fv / 32767.0 if abs(fv) > 1.0 else fv
    

def toggle_hitbox(hitbox, active):
    """
    Toggle hitbox visibility and physics state.
    """
    if not hitbox:
        return
    if active and not hitbox.visible:
        hitbox.visible = True
        hitbox.suspendDynamics(False)
        hitbox["active"] = True
    elif not active and hitbox.visible:
        hitbox.visible = False
        hitbox.suspendDynamics(True)
        hitbox["active"] = False

# -----------------------------
# Lock-on toggle
# -----------------------------
def update_lock_on(own, joy):
    kb = bge.logic.keyboard

    # Keyboard 'L'
    if kb.events[bge.events.LKEY] == bge.logic.KX_INPUT_JUST_ACTIVATED:
        own["lock_on"] = not own.get("lock_on", False)
        own["lock_initialized"] = False

        # Pick closest target only when locking on
        if own["lock_on"]:
            scene = bge.logic.getCurrentScene()
            enemies = [obj for obj in scene.objects if "Enemy" in obj.name]
            if enemies:
                closest = min(enemies, key=lambda e: (e.worldPosition - own.worldPosition).length)
                own["lock_target"] = closest
                print(f"[Lock-On] Locked to {closest.name}")
            else:
                own["lock_target"] = None

    # Joystick button
    btn_index = 9
    prev = own.get("lock_button_prev", False)
    cur = False
    try:
        cur = joy and (btn_index in joy.activeButtons)
    except:
        cur = False
    if cur and not prev:
        own["lock_on"] = not own.get("lock_on", False)
        own["lock_initialized"] = False

        # Pick closest target only when locking on
        if own["lock_on"]:
            scene = bge.logic.getCurrentScene()
            enemies = [obj for obj in scene.objects if "Enemy" in obj.name]
            if enemies:
                closest = min(enemies, key=lambda e: (e.worldPosition - own.worldPosition).length)
                own["lock_target"] = closest
                print(f"[Lock-On] Locked to {closest.name}")
            else:
                own["lock_target"] = None

    own["lock_button_prev"] = cur


# -----------------------------
# Free movement
# -----------------------------
def move_free(own, axis_x, axis_y, cam_forward, cam_right, max_speed):
    move_dir = cam_forward * axis_y + cam_right * axis_x
    if move_dir.length > 0.001:
        move_dir.normalize()
        speed = max_speed * min(1.0, (abs(axis_x) + abs(axis_y)) / 2)
        vel = Vector((move_dir.x * speed, move_dir.y * speed, own.worldLinearVelocity.z))
        own.applyMovement((vel.x, vel.y, vel.z), False)
        own.alignAxisToVect(move_dir, 1, 0.2)  # face movement dir
        own.alignAxisToVect([0,0,1], 2, 1.0)   # keep upright

        # --- projection for animation ---
        forward_speed = vel.dot(cam_forward)
        sideways_speed = vel.dot(cam_right)
        own["forward_speed"] = forward_speed
        own["sideways_speed"] = sideways_speed

        own["velocity"] = vel.length
        own["input_moving"] = True
    else:
        lv = own.worldLinearVelocity
        own.applyMovement((lv.x * 0.85, lv.y * 0.85, lv.z), False)
        own["velocity"] = Vector((lv.x, lv.y, lv.z)).length
        own["input_moving"] = False
        own["forward_speed"] = 0.0
        own["sideways_speed"] = 0.0

# -----------------------------
# Main movement function
# -----------------------------
def move(cont):
    own = cont.owner #The player controller Mesh
    scene = bge.logic.getCurrentScene()
    arm = scene.objects.get("Armature.029")
    attacking = False
    if arm and "action_state" in arm:
        attacking = arm["action_state"] == "ATTACK"   
    cam = scene.objects.get("EmptyMallHall") or scene.active_camera 
      
    # freeze when menu open
    if own.get("menu_open", False):
        # optional: zero velocities to ensure immediate stoppage
        try:
            own.worldLinearVelocity = [0.0,0.0,0.0]
            own.worldAngularVelocity = [0.0,0.0,0.0]
        except Exception:
            pass
        own["input_moving"] = False
        return
    # --- Read joystick safely ---
    joy = None
    try:
        joy = bge.logic.joysticks[0]
    except:
        joy = None

    # --- Camera vectors projected to XY plane (RUN EVERY FRAME) ---
    cam_fwd = cam.worldOrientation.col[1].copy()
    cam_fwd.z = 0.0
    cam_fwd = cam_fwd.normalized() if cam_fwd.length > 0.0001 else Vector((0,1,0))

    cam_right = cam.worldOrientation.col[0].copy()
    cam_right.z = 0.0
    cam_right = cam_right.normalized() if cam_right.length > 0.0001 else Vector((1,0,0))

    # --- Update lock toggle ---
    update_lock_on(own, joy)

    # --- Initialize player properties ---
    if "velocity" not in own:
        own["velocity"] = 0.0
        own["jumping"] = False
        own["grounded"] = True
        own["lock_on"] = False
        own["lock_target"] = None
        own["lock_button_prev"] = False
        own["last_locked_on_state"] = False
        own["locomotion_dirty"] = True

    # Axis input
    axis_x = axis_y = 0.0
    try:
        axis_x = _norm_axis(joy.axisValues[0]) #the _norm_axis() method wrap is being called from line 10 def declration
        axis_y = -_norm_axis(joy.axisValues[1])
    except:
        axis_x = axis_y = 0.0

    # Deadzone (prevents stick drift)
    if abs(axis_x) < 0.015: axis_x = 0.0
    if abs(axis_y) < 0.015: axis_y = 0.0
    
    own["axis_x"]=axis_x
    own["axis_y"]=axis_y
    
    # -----------------------------
    # --- STATE GATE (single source of truth) ---
    state = arm.get("action_state") if arm else None
    hard_lock = state in ("ATTACK", "DODGE")
    dodging = (state == "DODGE")


    if hard_lock:
        own["input_moving"] = False
        own["velocity"] = 0.0
        own["forward_speed"] = 0.0
        own["sideways_speed"] = 0.0

    # ATTACK INPUT (READ EARLY)
    # -----------------------------
    if arm:
        arm["light_pressed"]  = joy and (2 in joy.activeButtons)
        arm["medium_pressed"] = joy and (3 in joy.activeButtons)

    # DODGE INPUT (Button 0)
    # -----------------------------
    dodge_pressed = False
    try:
        dodge_pressed = joy and (0 in joy.activeButtons)
    except:
        dodge_pressed = False

    if dodge_pressed and attacking and arm:
        arm["cancel_attack"] = True

    # -----------------------------
    # DODGE TRIGGER (STATE TRANSITION ONLY)
    # -----------------------------
    if arm:

        lock_on = own.get("lock_on", False)

        if (
            dodge_pressed
            and not hard_lock
            and own.get("dodge_cd", 0) == 0
            and own.get("grounded", True)
        ):

#            if lock_on:
#                # dodge relative to character facing (cleaner for lock-on)
#                forward = own.worldOrientation.col[1].copy()
#                right = own.worldOrientation.col[0].copy()
#                forward.z = 0.0
#                right.z = 0.0
#                forward.normalize()
#                right.normalize()
#                dodge_dir = forward * axis_y + right * axis_x

#                if dodge_dir.length < 0.01:
#                    dodge_dir = -forward  # backstep if no input
#                dodge_dir.normalize()
#                own["dodge_vec"] = dodge_dir * 0.23
#                own["dodge_timer"] = 12
#                own["dodge_cd"] = 20

#                arm["action_state"] = "DODGE"
#                own["locomotion_dirty"] = True
            if lock_on and own.get("lock_target"):

                target = own["lock_target"]
                # Vector from player to enemy
                to_enemy = (target.worldPosition - own.worldPosition).copy()
                to_enemy.z = 0.0

                if to_enemy.length < 0.001:
                    to_enemy = own.worldOrientation.col[1].copy()
                    to_enemy.z = 0.0
                    to_enemy.normalize()
                else:
                    to_enemy.normalize()

                # Right vector relative to enemy
                right = to_enemy.cross(Vector((0,0,1)))
                right.normalize()

                # Build dodge direction relative to enemy
                dodge_dir = to_enemy * axis_y + right * axis_x

                # If no stick input → roll backward away from enemy
                if dodge_dir.length < 0.01:
                    dodge_dir = -to_enemy

                dodge_dir.normalize()

                own["dodge_vec"] = dodge_dir * 0.23
                own["dodge_timer"] = 12
                own["dodge_cd"] = 20

                arm["action_state"] = "DODGE"
                own["locomotion_dirty"] = True

            else:
                own["jumping"] = True
                print("JUMP TRIGGERED")


        state = arm.get("action_state")
        hard_lock = state in ("ATTACK", "DODGE")
        dodging = (state == "DODGE")

  


       
    # -----------------------------
    # HARD ATTACK LOCK
    # -----------------------------
    # --- DODGE TIMER ---
    if arm and arm.get("action_state") == "DODGE":
        if own["dodge_timer"] <= 0:
            arm["action_state"] = "IDLE"
            own["locomotion_dirty"] = True   # 🔴 THIS IS CRITICAL


    # HARD ATTACK LOCK (Fixed)
    # -----------------------------
    

    if attacking:

        # --- Stop horizontal movement ---
        own.setLinearVelocity([0,0,own.worldLinearVelocity.z], False)

        # --- Allow turning during attack ---
        move_dir = cam_fwd * axis_y + cam_right * axis_x

        if move_dir.length > 0.001:
            move_dir.normalize()
            own.alignAxisToVect(move_dir, 1, 0.2)
            own.alignAxisToVect([0,0,1], 2, 1.0)

        # --- Maintain animation stability ---
        own["input_moving"] = False
        own["velocity"] = 0.0
        own["forward_speed"] = 0.0
        own["sideways_speed"] = 0.0


    
   
    # --- Initialize HP ---
    if "hp" not in own:
        own["hp"] = 100
     # --- Listen for HIT messages ---
    msg_sensor = cont.sensors.get("MessageSensor")
    if msg_sensor:
        for msg in msg_sensor.bodies:
            if msg.isdigit():
                dmg = int(msg)
                own["hp"] -= dmg
                print(f"[Player] Took {dmg} damage. HP = {own['hp']}")
                if own["hp"] <= 0:
                    print("[Player] KO! Restarting scene...")
                    bge.logic.restartGame()

#    # --- BLOCK CHECK ---
#    blocking = False
#    try:
#        blocking = joy and (1 in joy.activeButtons)
#    except:
#        blocking = False
#    own["blocking"] = blocking
#     # Play block animation
#    if arm and arm.get("action_state") != "ATTACK":
#        if blocking:
#            if not arm.isPlayingAction(3):
#                arm.playAction(
#                    "LLABlock", 0, 20,
#                    layer=3,
#                    play_mode=bge.logic.KX_ACTION_MODE_LOOP,
#                    speed=1.0
#                )
#        else:
#            if arm.isPlayingAction(3):
#                arm.stopAction(3)

# --- LOCKED-ON MOVEMENT ---
    if own.get("lock_target"):
        target = own["lock_target"]

        if target.invalid or  target.get("hp", 1) <= 0:
                own["lock_on"] = False
                own["lock_target"] = None


    if (own.get("lock_on", False) 
        and own.get("lock_target") 
        and not hard_lock 
        and not dodging):
        target = own["lock_target"]
        to_target = (target.worldPosition - own.worldPosition).copy()
        to_target.z = 0.0
        if to_target.length > 0.0001:
            to_target.normalize()
            own.alignAxisToVect(to_target, 1, 0.2)   # face enemy
            own.alignAxisToVect([0,0,1], 2, 1.0)

        # Movement relative to camera
        move_dir = cam_fwd * axis_y + cam_right * axis_x
        forward_speed = 0.0
        sideways_speed = 0.0

        if move_dir.length > 0.001:
            move_dir.normalize()
            speed = 0.08 * min(1.0, (abs(axis_x) + abs(axis_y)) / 2)
            vel = Vector((move_dir.x * speed, move_dir.y * speed, own.worldLinearVelocity.z))
            own.applyMovement((vel.x, vel.y, vel.z), False)
            own["velocity"] = vel.length
            own["input_moving"] = True

            # project velocity onto camera axes for animation
            forward_speed = vel.dot(cam_fwd)
            sideways_speed = vel.dot(cam_right)
        else:
            # slow down when no input
            lv = own.worldLinearVelocity
            own.applyMovement((lv.x * 0.85, lv.y * 0.85, lv.z), False)
            own["velocity"] = Vector((lv.x, lv.y, lv.z)).length
            own["input_moving"] = False

        own["forward_speed"] = forward_speed
        own["sideways_speed"] = sideways_speed
        own["last_locked_on_state"] = True
    else:
        if dodging:
            own.applyMovement(own["dodge_vec"], True)
            own["dodge_timer"] -= 1

            if own["dodge_timer"] <= 0:
                arm["action_state"] = "IDLE"
                own["locomotion_dirty"] = True
        # FREE MOVEMENT
#        if own.get("last_locked_on_state", False) and not blocking:
#            own.alignAxisToVect(cam_fwd, 1, 1.0)  # snap to camera dir
#            own.alignAxisToVect([0,0,1], 2, 1.0)
#            own["last_locked_on_state"] = False
            
        if not attacking and not hard_lock and not dodging:
            move_free(own, axis_x, axis_y, cam_fwd, cam_right, 0.08)
        

    if "dodge_cd" not in own:
        own["dodge_cd"] = 0

    own["dodge_cd"] = max(0, own["dodge_cd"] - 1)
  


    