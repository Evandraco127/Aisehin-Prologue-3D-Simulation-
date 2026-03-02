# enemy_ai_clean.py
import bge
import random
from mathutils import Vector, Matrix

# ---------------------------
# Config / Tunables
# ---------------------------
NAVMESH_NAME = "NavMesh"
TARGET_NAME  = "Player.MallHall"

MIN_DISTANCE = 0.893
CHASE_DISTANCE = 3.25
MOVE_SPEED = 0.057
SMOOTH_TURN = 0.15
POST_EVADE_COOLDOWN_FRAMES = 120
KO_SECONDS = 32.5

ANIMATIONS = {
    "idle": "IdleFIghtSaturn",
    "run":  "RunSaturn.001",
    "evade":"Evade.001",
    "block":"Block",
    "ko":"ik.TPoses.Faith",
    "hit":"IdleFIghtSaturn"
}

ATTACK_INFO = {
    "attack1": {"anim": "PunchSaturn",   "attack_type": "SATPunch1", "hb_idx": 0},
    "attack2": {"anim": "TepKickSaturn", "attack_type": "SATKick1",  "hb_idx": 1},
    "attack3": {"anim": "PunchSaturn",   "attack_type": "SATPunch1", "hb_idx": 0},
}

DAMAGE = {
    "LLA_Light_1": 10,
    "LLA_Light_2": 12,
    "LLA_Light_3": 15,
    "LLA_Kick_1": 18,
    "LLA_Kick_2": 20,
    "LLA_Kick_3": 25,
}

DEFAULT_DAMAGE = 10
DAMAGE_COOLDOWN_FRAMES = 6


# ---------------------------
# Helpers
# ---------------------------

def move_to_point(own, target_pos, navmesh):
    """Generic movement logic for NavMesh or Direct Steering"""
    if navmesh:
        # Update path if destination moved significantly
        if "last_path_pos" not in own or (own["last_path_pos"] - target_pos).length > 0.5:
            own["path"] = navmesh.findPath(own.worldPosition, target_pos)
            own["last_path_pos"] = target_pos.copy()

        path = own["path"]
        if path:
            # Draw path for debugging
            for i in range(len(path)-1):
                bge.render.drawLine(path[i], path[i+1], (0, 1, 0))
                
            vec = own.getVectTo(path[0])
            if vec[0] < 0.7: # Threshold to pop next waypoint
                path.pop(0)
            
            if path:
                move_vec = own.getVectTo(path[0])[1]
                own.alignAxisToVect(move_vec, 1, SMOOTH_TURN)
                own.applyMovement(move_vec.normalized() * MOVE_SPEED, False)
    else:
        # Fallback: Direct steering
        vec = own.getVectTo(target_pos)
        own.alignAxisToVect(vec[1], 1, SMOOTH_TURN)
        own.applyMovement(vec[1].normalized() * MOVE_SPEED, False)
        
    own.alignAxisToVect([0,0,1], 2, 1) # Keep Upright
    
def play_animation(own, name, start, end, loop=True, blend=5):
    if not name:
        return
    arm = own.get("armature")
    if not arm:
        return
    if own.get("current_anim") == name:
        return
    mode = bge.logic.KX_ACTION_MODE_LOOP if loop else bge.logic.KX_ACTION_MODE_PLAY
    arm.playAction(name, start, end, layer=0, priority=0, blendin=blend,
                   play_mode=mode, speed=1.0)
    own["current_anim"] = name

def draw_debug_line(a, b, color=(1,1,1)):
    p1 = a.worldPosition if hasattr(a, "worldPosition") else a
    p2 = b.worldPosition if hasattr(b, "worldPosition") else b
    bge.render.drawLine(p1, p2, color)

def toggle_hitbox(hitbox, active):
    if not hitbox:
        return

    hitbox.setVisible(bool(active))
    hitbox["active"] = bool(active)
    hitbox["_sent_attack_message"] = False
    if not active:
        hitbox["Hitbox"] = False
        hitbox["attack_type"] = ""


def auto_find_armature_and_hitbox(own, scene):
    # keep existing if already set
    arm = own.get("armature")
    if not arm:
        # try hardcoded first
        arm = scene.objects.get("ik.Fay.PremiumRig_2024.001")
        if not arm:
            # look among children for something that looks like an armature/rig
            for ch in own.childrenRecursive:
                nm = ch.name.lower()
                if "armature" in nm or nm.startswith("ik.") or "rig" in nm:
                    arm = ch
                    break
        if arm:
            own["armature"] = arm
        else:
            own["state"] = "hit"
            own["hit_timer"] = 18   # stun frames
            own["path"] = []
            try:
                own.worldLinearVelocity = [0,0,0]
                own.worldAngularVelocity = [0,0,0]
            except Exception:
                pass

            hit_anim = ANIMATIONS.get("hit")
            if arm and hit_anim:
                arm.playAction(hit_anim, 0, 20, layer=0,
                               play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=1.0)

            print(f"[AI] Hit stun {attack_type} dmg={dmg} HP {old_hp}->{new_hp}")
            return
    hb = own.get("hitbox")
    if not hb:
        hb = scene.objects.get("SaturnHitbox_R.001")
        if not hb:
            for ch in own.childrenRecursive:
                if "hitbox" in ch.name.lower():
                    hb = ch
                    break
        if hb:
            own["hitbox"] = hb
            for hb in hitboxes:
                toggle_hitbox(hb, False)


# ---------------------------
# Always face Player When Attacking
def face_target(own, target, turn_speed=0.25):
    if not target:
        return

    to_target = target.worldPosition - own.worldPosition
    to_target.z = 0.0

    if to_target.length < 0.0001:
        return

    to_target.normalize()

    own.alignAxisToVect(to_target, 1, turn_speed)
    own.alignAxisToVect([0, 0, 1], 2, 1)

# Main AI tick
# ---------------------------
def main():
    cont = bge.logic.getCurrentController()
    own = cont.owner
    scene = bge.logic.getCurrentScene()
    # -- init on first frame --
    if "init" not in own:
        own["init"] = True
        own["target"] = scene.objects.get(TARGET_NAME)
        own["navmesh"] = scene.objects.get(NAVMESH_NAME)
        own["path"] = []
        own["target_pos"] = None
        own["state"] = "idle"

        own["attack_cd"] = 0
        own["attack_timer"] = 0
        own["evade_timer"] = 0
        own["post_evade_cd"] = 0

        own["current_anim"] = ""
        own["armature"] = scene.objects.get("ik.Fay.PremiumRig_2024.001")
        #own["hitbox"] = scene.objects.get("SaturnHitbox_R.001")
        own["hitboxes"] = []
        
        handRight = scene.objects.get("SaturnHitbox_R.001")
        footRight = scene.objects.get("SaturnFootHitbox_R.001")
        
        if handRight:
            own["hitboxes"].append(handRight)
        if footRight:
            own["hitboxes"].append(footRight)
            
#        auto_find_armature_and_hitbox(own, scene)
#        if own.get("hitbox"):
#            hb = own["hitbox"]
        for hb in own["hitboxes"]:
            hb["Hitbox"] = False
            hb["attack_type"] = ""
            hb.setVisible(False)

        own["max_hp"] = own.get("max_hp", 100)
        own["hp"] = own.get("hp", own["max_hp"])
        own["spawn_pos"] = own.worldPosition.copy()
        own["spawn_ori"] = own.worldOrientation.copy()
        own["ko_timer"] = 0
        own["evade_dir"] = None
        own["damage_cooldown"] = 0

    # quick references
    target = own.get("target")
    navmesh = own.get("navmesh")  # may be None; we now fall back gracefully
    hitboxes  = own.get("hitboxes",[])
    arm = own.get("armature")
    if not target:
        return

    current_frame = arm.getActionFrame(0) if arm else 0

    # -----------------------------
    # Decrement small timers
    # -----------------------------
    for t in ["attack_cd","attack_timer","evade_timer","post_evade_cd","damage_cooldown"]:
        if own.get(t,0) > 0:
            own[t] -= 1

    # -----------------------------
    # Process incoming messages for damage
    msg_sensor = cont.sensors.get("Message")
    if msg_sensor and msg_sensor.positive and own.get("damage_cooldown", 0) <= 0:

        for subject in msg_sensor.subjects:
            if subject in DAMAGE:

                dmg = DAMAGE[subject]
                own["hp"] -= dmg
                own["damage_cooldown"] = 20
                own["hit_timer"] = 18
                own["state"] = "hit"

                print(f"[Enemy] Took {dmg} damage. HP = {own['hp']}")

                # ---- KO CHECK ----
                if own["hp"] <= 0:
                    own["state"] = "ko"

                    fps = bge.logic.getLogicTicRate() or 60
                    own["ko_timer"] = int(KO_SECONDS * fps)

                    own["path"] = []

                    try:
                        own.worldLinearVelocity = [0,0,0]
                        own.worldAngularVelocity = [0,0,0]
                    except:
                        pass

                    print("[AI] KO triggered")

                break

    # KO handling & respawn
    # -----------------------------
    # HIT STUN handling
    # -----------------------------
    if own.get("state") == "hit":
        if own.get("hit_timer",0) > 0:
            own["hit_timer"] -= 1
            for hb in hitboxes:
                toggle_hitbox(hb,false)
            return
        else:
            own["state"] = "idle"
        
    # Hitbox activation + single message per activation
    # -----------------------------
    # --- Inside Main Loop: Hitbox activation ---
    is_attacking = own["state"] in ATTACK_INFO
    
    if is_attacking and 7 <= current_frame <= 9:
        # Get the index for the specific hitbox we want
        idx = ATTACK_INFO[own["state"]]["hb_idx"]
        
        # Safety check to make sure index exists in our list
        if idx < len(hitboxes):
            hb = hitboxes[idx]
            toggle_hitbox(hb, True)
            hb["Hitbox"] = True
            hb["attack_type"] = ATTACK_INFO[own["state"]]["attack_type"]
            
            if not hb.get("_sent_attack_message", False):
                attack_msg = hb["attack_type"]
                if attack_msg:
                    bge.logic.sendMessage(attack_msg, "", "")
                hb["_sent_attack_message"] = True
    else:
        # Turn OFF all hitboxes when not in the active window
        for hb in hitboxes:
            hb["Hitbox"] = False
            hb["attack_type"] = ""
            toggle_hitbox(hb, False)
    # -----------------------------
    # EVADE
    # -----------------------------
    if own["state"] == "evade":
        for hb in hitboxes:
            toggle_hitbox(hb, False)
#        return
#    else:
#        own["state"] = "idle"
        
        evade_speed = 0.08
        if own["evade_dir"] is None:
            to_ai = own.worldPosition - target.worldPosition
            to_ai.z = 0.0
            if to_ai.length > 0.0001:
                to_ai.normalize()
            right_vec = to_ai.cross([0,0,1])
            choice = random.choice(["back","left","right"])
            if choice == "back":
                own["evade_dir"] = to_ai
            elif choice == "left":
                own["evade_dir"] = -right_vec
            else:
                own["evade_dir"] = right_vec
        move_vec = own["evade_dir"] * evade_speed
        own.applyMovement(move_vec, False)
        play_animation(own, ANIMATIONS["evade"], 0, 20, loop=False, blend=2)
        if own["evade_timer"] > 0:
            own["evade_timer"] -= 1
        if own["evade_timer"] <= 0:
            own["post_evade_cd"] = POST_EVADE_COOLDOWN_FRAMES
            own["evade_dir"] = None
            if own.getDistanceTo(target) <= CHASE_DISTANCE:
                own["state"] = "run"
            else:
                own["state"] = "idle"
        return

    # -----------------------------
    # Attacking handling (play animation while timer)
    # -----------------------------
    if is_attacking:
        if own["attack_timer"] > 0:
            # keep playing the chosen attack (one-shot)
            play_animation(own, ATTACK_INFO[own["state"]]["anim"], 0, 30, loop=False, blend=4)
            return
        else:
            own["state"] = "idle"

    # -----------------------------
    # Attack / Evade trigger
    # -----------------------------
    distance = own.getDistanceTo(target)
    # Combat-facing enforcement
    if own["state"] in ATTACK_INFO:
        face_target(own, target, 0.35)
    elif distance <= CHASE_DISTANCE:
        face_target(own, target, 0.25)
    if distance <= MIN_DISTANCE and own["attack_cd"] <= 0:
        own["attack_cd"] = 20
        choice = random.choice(list(ATTACK_INFO.keys()) + ["block","evade"])
        own["state"] = choice
        if choice in ATTACK_INFO:
            print("[AI] Attack chosen:", choice)
            play_animation(own, ATTACK_INFO[choice]["anim"], 0, 30, loop=False, blend=4)
            own["attack_timer"] = 25
        elif choice == "evade":
            play_animation(own, ANIMATIONS["evade"], 0, 30, loop=False, blend=4)
            own["evade_timer"] = 15
            own["evade_dir"] = None
        elif choice == "block":
            play_animation(own, ANIMATIONS["block"], 0, 30, loop=False, blend=4)
        return

 
# -----------------------------
    # Movement / Chase / Return Home
    # -----------------------------
    distance_to_spawn = own.getDistanceTo(own["spawn_pos"])
    
    # CASE 1: Chase the player
    if MIN_DISTANCE < distance <= CHASE_DISTANCE and own["post_evade_cd"] <= 0:
        if own["state"] != "run":
            own["state"] = "run"
            play_animation(own, ANIMATIONS["run"], 0, 27, loop=True, blend=5)
        
        move_to_point(own, target.worldPosition, navmesh)

    # CASE 2: Player out of range - Return to Spawn Position
    elif distance > CHASE_DISTANCE and distance_to_spawn > 1.0:
        if own["state"] != "run":
            own["state"] = "run"
            play_animation(own, ANIMATIONS["run"], 0, 27, loop=True, blend=5)
        
        move_to_point(own, own["spawn_pos"], navmesh)

    # CASE 3: At destination (Player or Spawn) - Idle
    else:
        if own["state"] not in ["idle", "evade", "hit", "ko"] + list(ATTACK_INFO.keys()):
            own["state"] = "idle"
        
        if own["state"] == "idle":
            play_animation(own, ANIMATIONS["idle"], 0, 30, loop=True, blend=5)
            # Face spawn orientation if close to home
            if distance_to_spawn < 1.1:
                own.alignAxisToVect(own["spawn_ori"].col[1], 1, 0.05)

    # -----------------------------
    # Debug (small)
    # -----------------------------
    # Check if ANY hitbox in the list is active for the printout
    any_hit_active = any(hb.get("active", False) for hb in hitboxes)
    print(f"State:{own['state']} Frame:{current_frame:.1f} Dist:{distance:.2f} HP:{own['hp']} Hit:{any_hit_active}")
