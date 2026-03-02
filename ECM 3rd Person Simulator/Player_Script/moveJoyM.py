import bge
import math
import mathutils
from mathutils import Vector, Euler

# -----------------------------
# Utility (movejoyM.py)
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
def respawn_player(own, arm, start_pos, start_rot):
    # Stop all motion
    own.worldLinearVelocity = [0,0,0]
    own.worldAngularVelocity = [0,0,0]
    
    # Reset player position
    own.worldPosition = start_pos
    own.worldOrientation = start_rot
    
    # Reset HP & state
    own["hp"] = 100
    own["hit_timer"] = 0
    own["hit"] = False
    own["ko_triggered"] = False
    own["damage_cooldown"] = 0
    own["velocity"] = 0.0
    own["forward_speed"] = 0.0
    own["sideways_speed"] = 0.0
    
    # Reset armature state
    if arm:
        arm["action_state"] = "IDLE"
        for child in own.children:
            child.localPosition = child.get("bind_pos", child.localPosition.copy())
            child.localOrientation = child.get("bind_rot", child.localOrientation.copy())
            
# --- KO / Respawn Handler (frame-based) ---
def handle_ko(own, arm, scene):
    """
    Check if the player is KO'd and handle respawn automatically.
    """
    # Only proceed if KO has been triggered
    if not own.get("ko_triggered", False):
        return

    # Initialize KO timer if missing
    if "ko_timer" not in own:
        own["ko_timer"] = 60  # ~1 second at 60fps

    # Countdown timer
    own["ko_timer"] -= 1

    if own["ko_timer"] <= 0:
        # Respawn position object
        start_obj = scene.objects.get("EmptyStartPlayer")
        if start_obj:
            respawn_player(own, arm, start_obj.worldPosition.copy(), start_obj.worldOrientation.copy())
            print("[Player] Respawned!")

        # Reset KO state
        own["ko_triggered"] = False
        own["ko_timer"] = 0
        if arm:
            arm["action_state"] = "IDLE"
            

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
    own = cont.owner
    scene = bge.logic.getCurrentScene()
    arm = scene.objects.get("Armature.029")
    
    start_pos = scene.objects.get("EmptyStartPlayer").worldPosition.copy()
    start_rot = scene.objects.get("EmptyStartPlayer").worldOrientation.copy()
    handle_ko(own, arm, scene)
    
    dodge_pressed = False

    attacking = False
    if arm and "action_state" in arm:
        attacking = arm["action_state"] == "ATTACK"

    cam = scene.objects.get("Camera.001") or scene.active_camera
      
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
    # --- Camera vectors projected to XY plane (FIXED) ---
    # 1. Get the Right vector (this is always horizontal)
    cam_right = cam.worldOrientation.col[0].copy()
    cam_right.z = 0.0
    if cam_right.length > 0.001:
        cam_right.normalize()
    else:
        cam_right = Vector((1, 0, 0))

    # 2. Derive Forward by crossing Right with the World Up [0,0,1]
    # This ensures "Forward" is always relative to the horizon, not the lens pitch
    cam_fwd = Vector((0, 0, 1)).cross(cam_right)
    cam_fwd.normalize()
    
#    cam_fwd = cam.worldOrientation.col[1].copy()
#    cam_fwd.z = 0.0
#    cam_fwd = cam_fwd.normalized() if cam_fwd.length > 0.0001 else Vector((0,1,0))

#    cam_right = cam.worldOrientation.col[0].copy()
#    cam_right.z = 0.0
#    cam_right = cam_right.normalized() if cam_right.length > 0.0001 else Vector((1,0,0))
#    if attacking:
#        # --- Stop horizontal movement ---
#        #own.setLinearVelocity([0,0,own.worldLinearVelocity.z], False)
#        # --- Allow turning during attack ---
##        move_dir = cam_fwd * axis_y + cam_right * axis_x
##        if move_dir.length > 0.001:
##            move_dir.normalize()
##            own.alignAxisToVect(move_dir, 1, 0.2)
##            own.alignAxisToVect([0,0,1], 2, 1.0)
#        # --- Maintain animation stability ---
#        own.worldLinearVelocity = [0,0,0]
#        own.worldAngularVelocity = [0,0,0]
#        own.localLinearVelocity = [0,0,0]
#        
#    
#        own["input_moving"] = False
#        own["velocity"] = 0.0
#        own["forward_speed"] = 0.0
#        own["sideways_speed"] = 0.0
#        
#        own["jump_prev"] = dodge_pressed
#        own["damage_cooldown"] = max(0, own["damage_cooldown"] - 1)
#        own["dodge_cd"] = max(0, own["dodge_cd"] - 1)

#        return

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
    hard_lock = state == "ATTACK"
    dodging = (state == "DODGE")
    
    

    # ATTACK INPUT (READ EARLY)
    # -----------------------------
    if arm:
        arm["light_pressed"]  = joy and (2 in joy.activeButtons)
        print("Punch owner:", own.name)
        print("State:", own.get("action_state"))
        arm["medium_pressed"] = joy and (3 in joy.activeButtons)
        print("Punch owner:", own.name)
        print("State:", own.get("action_state"))

    # DODGE INPUT (Button 0)
    # -----------------------------
    dodge_pressed = False
    try:
        dodge_pressed = joy and (0 in joy.activeButtons)
        print("Punch owner:", own.name)
        print("State:", own.get("action_state"))
    except:
        dodge_pressed = False
        
    prev_jump = own.get("jump_prev", False)
    jump_just_pressed = dodge_pressed and not prev_jump


    if dodge_pressed and attacking and arm:
        arm["cancel_attack"] = True

    # -----------------------------
    # DODGE TRIGGER (STATE TRANSITION ONLY)
    # -----------------------------
    if arm:
        lock_on = own.get("lock_on", False)

        if (
            jump_just_pressed
            and not hard_lock
            and own.get("dodge_cd", 0) == 0
            and own.get("grounded", True)
        ):
 
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
                
                # --- Directional intent ---
                # --- Directional intent ---
                forward_threshold = 0.4
                side_threshold = 0.3

                if axis_y > forward_threshold:
                    # Forward dodge → toward enemy
                    dodge_dir = to_enemy

                elif axis_y < -forward_threshold:
                    # Back dodge → away from enemy
                    dodge_dir = -to_enemy

                elif abs(axis_x) > side_threshold:
                    # Side dodge
                    dodge_dir = right * math.copysign(1.0, axis_x)

                else:
                    # No strong input → default backward
                    dodge_dir = -to_enemy

                dodge_dir.normalize()
      

                # Build dodge direction relative to enemy
#                dodge_dir = to_enemy * axis_y + right * axis_x

#                # If no stick input → roll backward away from enemy
#                if dodge_dir.length < 0.01:
#                    dodge_dir = -to_enemy

#                dodge_dir.normalize()


                own["dodge_vec"] = dodge_dir * 0.23
                own["dodge_timer"] = 12
                own["dodge_cd"] = 20

                arm["action_state"] = "DODGE"
                own["locomotion_dirty"] = True

            else:
                print("JUMP TRIGGERED")
                own.applyMovement((0, 0, 4), False)


                own["grounded"] = False
                arm["action_state"] = "JUMP"
                own["locomotion_dirty"] = True



        state = arm.get("action_state")
        hard_lock = state == "ATTACK"
        dodging = (state == "DODGE")
        jumping = (state == "JUMP")
  
    # -----------------------------
    # HARD ATTACK LOCK
    # -----------------------------
    # --- DODGE TIMER ---
#    if arm and arm.get("action_state") == "DODGE":
#        if own["dodge_timer"] <= 0:
#            arm["action_state"] = "IDLE"
#            own["locomotion_dirty"] = True   # 🔴 THIS IS CRITICAL


    # HARD ATTACK LOCK (Fixed)
    # ----------------------------
    if (
        arm.get("action_state") == "JUMP"
        and own.get("grounded")
        and own.worldLinearVelocity.z <= 0.1
    ):
        arm["action_state"] = None
        own["locomotion_dirty"] = True 

        
    
    if hard_lock:
        # stop horizontal movement
        own.worldLinearVelocity.x = 0
        own.worldLinearVelocity.y = 0
        own.localLinearVelocity.x = 0
        own.localLinearVelocity.y = 0

        # --- Allow turning during attack ---
        move_dir = cam_fwd * axis_y + cam_right * axis_x
        if move_dir.length > 0.001:
            move_dir.normalize()
            own.alignAxisToVect(move_dir, 1, 0.2)  # turn toward input
            own.alignAxisToVect([0,0,1], 2, 1.0)   # keep upright

        own["input_moving"] = False
        own["velocity"] = 0.0
        own["forward_speed"] = 0.0
        own["sideways_speed"] = 0.0

        return
            
    # --- HIT STUN ---
    if own.get("hit_timer", 0) > 0:
        own["hit_timer"] -= 1

        # Freeze movement
        own.setLinearVelocity([0,0,own.worldLinearVelocity.z], False)

        if own["hit_timer"] <= 0:
            own["hit"] = False
            arm["action_state"] = None
            own["locomotion_dirty"] = True

        
    # --- Initialize HP ---
    if "hp" not in own:
        own["hp"] = 100
    # --- Listen for HIT messages ---
    if "damage_cooldown" not in own:
        own["damage_cooldown"] = 0
    # --- Listen for HIT messages ---
    msg_sensor = cont.sensors.get("MessageSensor")

    if msg_sensor and msg_sensor.positive:
        DAMAGE = {
            "SATPunch1": 15,
            "SATKick1": 20,
        }

        for subject in msg_sensor.subjects:
            if own["damage_cooldown"] > 0:
                break  # already hit recently
            if subject in DAMAGE:
                dmg = DAMAGE[subject]
                attacker = own.get("lock_target")  # temporary solution
                # --- KNOCKBACK ---
                if attacker:
                    knock_dir = own.worldPosition - attacker.worldPosition
                    knock_dir.z = 0.0

                    if knock_dir.length > 0.001:
                        knock_dir.normalize()
                    else:
                        knock_dir = -own.worldOrientation.col[1]

                    knock_strength = 0.35   # <-- tweak this value
                    own.worldLinearVelocity = [
                        knock_dir.x * knock_strength,
                        knock_dir.y * knock_strength,
                        own.worldLinearVelocity.z
                    ]
                    own["knock_vec"] = knock_dir * 0.25
                    own["knock_timer"] = 10
                 # Play reaction animation
                arm.playAction("LLSEXYIDLE", 640, 657, layer=2,
                                    play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=0.75)
             
                own["hp"] -= dmg
                own["damage_cooldown"] = 20  # ~0.3 sec at 60fps

                print(f"[Player] Took {dmg} damage. HP = {own['hp']}")
                # --- TRIGGER HIT STATE ---
                own["hit"] = True
                own["hit_timer"] = 20  # frames of hit stun
                arm["action_state"] = "HIT"
                

                # --- KO / Game Restart ---
                if own["hp"] <= 0:
                    if not own.get("ko_triggered", False):
                        print("[Player] KO! Respawning...")
                        own["ko_triggered"] = True
                          # Delay before restart (frames)
                        own["ko_timer"] = 60 # 30 frames ~0.5 sec at 60fps
                        # Play death/fall animation if armature exists
                        if arm:
                            arm["action_state"] = "KO"
                            arm.playAction("LLSEXYIDLE", 645, 700, layer=1,
                                           play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=1.0)           

                
            # --- LOCKED-ON MOVEMENT ---
    if own.get("lock_target"):
        target = own["lock_target"]
        #if target.invalid or  target.get("hp", 1) <= 0:
        if not target or target.invalid or target.get("state") == "ko":
        
                own["lock_on"] = False
                own["lock_target"] = None


    if (own.get("lock_on", False) 
        and own.get("lock_target") 
        and not hard_lock 
        and not dodging
        and not jumping):

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
            forward_speed = 0.0
            sideways_speed = 0.0

        own["forward_speed"] = forward_speed
        own["sideways_speed"] = sideways_speed
        own["last_locked_on_state"] = True
    else:
        if dodging:
            own.applyMovement(own["dodge_vec"], True)
            own["dodge_timer"] -= 1

            if own["dodge_timer"] <= 0:
                arm["action_state"] = None
                # HARD RESET MOVEMENT STATE
                own["input_moving"] = False
                own["velocity"] = 0.0
                own["forward_speed"] = 0.0
                own["sideways_speed"] = 0.0

                own["locomotion_dirty"] = True
        # FREE MOVEMENT
        if own.get("last_locked_on_state", False):
            own.alignAxisToVect(cam_fwd, 1, 1.0)  # snap to camera dir
            own.alignAxisToVect([0,0,1], 2, 1.0)
            own["last_locked_on_state"] = False
            
        if not attacking and not hard_lock and not dodging and not jumping:
            move_free(own, axis_x, axis_y, cam_fwd, cam_right, 0.08)
        

    if "dodge_cd" not in own:
        own["dodge_cd"] = 0

    own["dodge_cd"] = max(0, own["dodge_cd"] - 1)
    own["jump_prev"] = dodge_pressed
    own["damage_cooldown"] = max(0, own["damage_cooldown"] - 1)
    
    if own.get("knock_timer", 0) > 0:
        own.applyMovement(own["knock_vec"], True)
        own["knock_timer"] -= 1

  


    