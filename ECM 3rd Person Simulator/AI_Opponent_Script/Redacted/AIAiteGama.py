# enemy_ai_clean.py
import bge
import random
from mathutils import Vector, Matrix

# ---------------------------
# Config / Tunables
# ---------------------------
NAVMESH_NAME = "NavMesh"
TARGET_NAME  = "Player.MallHall"

MIN_DISTANCE = 0.5
CHASE_DISTANCE = 3.25
MOVE_SPEED = 0.057
SMOOTH_TURN = 0.15
POST_EVADE_COOLDOWN_FRAMES = 64
KO_SECONDS = 7.0

ANIMATIONS = {
    "idle": "IdleFIghtSaturn",
    "run":  "RunSaturn.001",
    "evade":"Evade.001",
    "block":"Block",
    "ko":"ik.TPoses.Faith",
    "hit":"IdleFIghtSaturn"
}

ATTACK_INFO = {
    "attack1": {"anim": "PunchSaturn",   "attack_type": "SATPunch1"},
    "attack2": {"anim": "TepKickSaturn", "attack_type": "SATKick1"},
    "attack3": {"anim": "PunchSaturn",   "attack_type": "SATPunch1"},
}

DAMAGE = {
    "LLAPunch1": 25,
    "SATPunch1": 15,
    "SATKick1": 20,
}
DEFAULT_DAMAGE = 10
DAMAGE_COOLDOWN_FRAMES = 6


# ---------------------------
# Helpers
# ---------------------------
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

def collect_messages(cont):
    msgs = []
    for sensor in cont.sensors:
        if not getattr(sensor, "positive", False):
            continue
        if hasattr(sensor, "subjects"):
            msgs.extend(list(sensor.subjects))
        if hasattr(sensor, "bodies"):
            msgs.extend(list(sensor.bodies))
    return msgs

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
            toggle_hitbox(hb, False)


# ---------------------------
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
        own["hitbox"] = scene.objects.get("SaturnHitbox_R.001")
        auto_find_armature_and_hitbox(own, scene)
        if own.get("hitbox"):
            hb = own["hitbox"]
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
    hitbox = own.get("hitbox")
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
    # -----------------------------
    incoming = collect_messages(cont)
    if incoming and own.get("damage_cooldown",0) <= 0 and own.get("state") != "ko":
        for msg in incoming:
            attack_type = str(msg) if msg else ""
            if not attack_type:
                continue
            dmg = DAMAGE.get(attack_type, DEFAULT_DAMAGE)
            old_hp = own.get("hp", own.get("max_hp",100))
            new_hp = old_hp - dmg
            own["hp"] = new_hp
            own["damage_cooldown"] = DAMAGE_COOLDOWN_FRAMES
            if arm and arm.isPlayingAction(2):
                arm.stopAction(2)
            if new_hp <= 0:
                own["state"] = "ko"
                fps = bge.logic.getLogicTicRate() or 60
                own["ko_timer"] = int(KO_SECONDS * fps)
                own["path"] = []
                try:
                    own.worldLinearVelocity = [0.0,0.0,0.0]
                    own.worldAngularVelocity = [0.0,0.0,0.0]
                except Exception:
                    pass
                toggle_hitbox(hitbox, False)
                if hitbox:
                    hitbox["Hitbox"] = False
                    hitbox["attack_type"] = ""
                ko_anim = ANIMATIONS.get("ko")
                if arm and ko_anim:
                    arm.playAction(ko_anim, 0, 30, layer=0,
                                   play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=1.0)
                print("[AI] KO via message:", attack_type)
                return
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
    # -----------------------------
    # Collision-based damage (optional)
    # -----------------------------
    if own.get("damage_cooldown",0) <= 0 and own.get("state") != "ko":
        for sensor in cont.sensors:
            if not getattr(sensor, "positive", False):
                continue
            if not hasattr(sensor, "hitObjectList"):
                continue
            for hit_obj in list(sensor.hitObjectList):
                attack_type = hit_obj.get("attack_type") or hit_obj.get("AttackType") or hit_obj.get("attack", "")
                if not attack_type and hit_obj.get("Hitbox", False):
                    attack_type = hit_obj.name
                if not attack_type:
                    continue
                dmg = DAMAGE.get(attack_type, DEFAULT_DAMAGE)
                old_hp = own.get("hp", own.get("max_hp",100))
                new_hp = old_hp - dmg
                own["hp"] = new_hp
                own["damage_cooldown"] = DAMAGE_COOLDOWN_FRAMES
                if arm and arm.isPlayingAction(2):
                    arm.stopAction(2)
                if new_hp <= 0:
                    own["state"] = "ko"
                    fps = bge.logic.getLogicTicRate() or 60
                    own["ko_timer"] = int(KO_SECONDS * fps)
                    own["path"] = []
                    try:
                        own.worldLinearVelocity = [0.0,0.0,0.0]
                        own.worldAngularVelocity = [0.0,0.0,0.0]
                    except Exception:
                        pass
                    toggle_hitbox(hitbox, False)
                    if hitbox:
                        hitbox["Hitbox"] = False
                        hitbox["attack_type"] = ""
                    ko_anim = ANIMATIONS.get("ko")
                    if arm and ko_anim:
                        arm.playAction(ko_anim, 0, 30, layer=0,
                                       play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=1.0)
                    print("[AI] KO via collision:", attack_type)
                    return
                else:
                    print(f"[AI] Hit via collision {attack_type} dmg={dmg} HP {old_hp}->{new_hp}")
                break

    # -----------------------------
    # KO handling & respawn
    # -----------------------------
    if own.get("state") == "ko":
        toggle_hitbox(hitbox, False)
        try:
            own.worldLinearVelocity = [0.0,0.0,0.0]
            own.worldAngularVelocity = [0.0,0.0,0.0]
        except Exception:
            pass
        if own.get("ko_timer",0) > 0:
            own["ko_timer"] -= 1
            return
        else:
            own["hp"] = own.get("max_hp",100)
            own["state"] = "idle"
            if own.get("spawn_pos"):
                own.worldPosition = own["spawn_pos"].copy()
            if own.get("spawn_ori") is not None:
                own.worldOrientation = own["spawn_ori"].copy()
            try:
                own.worldLinearVelocity = [0.0,0.0,0.0]
                own.worldAngularVelocity = [0.0,0.0,0.0]
            except Exception:
                pass
            own["attack_cd"] = 0
            own["attack_timer"] = 0
            own["evade_timer"] = 0
            own["post_evade_cd"] = 0
            own["path"] = []
            toggle_hitbox(hitbox, False)
            if hitbox:
                hitbox["Hitbox"] = False
                hitbox["attack_type"] = ""
            print("[AI] Respawned. HP reset to", own["hp"])

    # -----------------------------
    # -----------------------------
    # HIT STUN handling
    # -----------------------------
    if own.get("state") == "hit":
        if own.get("hit_timer",0) > 0:
            own["hit_timer"] -= 1
            toggle_hitbox(hitbox, False)
            return
        else:
            own["state"] = "idle"
        
    # Hitbox activation + single message per activation
    # -----------------------------
    is_attacking = own["state"] in ATTACK_INFO
    if is_attacking and 7 <= current_frame <= 11:
        toggle_hitbox(hitbox, True)
        if hitbox:
            hitbox["Hitbox"] = True
            hitbox["attack_type"] = ATTACK_INFO[own["state"]]["attack_type"]
            if not hitbox.get("_sent_attack_message", False):
                attack_msg = hitbox["attack_type"]
                if attack_msg:
                    bge.logic.sendMessage(attack_msg, "", "")
                hitbox["_sent_attack_message"] = True
    else:
        if hitbox:
            hitbox["Hitbox"] = False
            hitbox["attack_type"] = ""
        toggle_hitbox(hitbox, False)

    # -----------------------------
    # EVADE
    # -----------------------------
    if own["state"] == "evade":
        toggle_hitbox(hitbox, False)
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
    # Movement / Chase
    # -----------------------------
    should_chase = (MIN_DISTANCE < distance <= CHASE_DISTANCE) and (own["post_evade_cd"] <= 0)
    if should_chase:
        if own["state"] != "run":
            own["state"] = "run"
            play_animation(own, ANIMATIONS["run"], 0, 27, loop=True, blend=5)

        if navmesh:
            if own.get("target_pos") != target.worldPosition:
                own["target_pos"] = target.worldPosition.copy()
                own["path"] = navmesh.findPath(own.worldPosition, own["target_pos"])

            path = own["path"]
            if path:
                if len(path) > 1:
                    for i in range(len(path)-1):
                        draw_debug_line(path[i], path[i+1], (0,0.5,1))
                vec = own.getVectTo(path[0])
                if vec[0] < 0.5 + MIN_DISTANCE/2.0:
                    path.pop(0)
                if path:
                    vec = own.getVectTo(path[0])
                    own.alignAxisToVect(vec[1], 1, SMOOTH_TURN)
                    own.alignAxisToVect([0,0,1], 2, 1)
                    own.applyMovement(vec[1].normalized() * MOVE_SPEED, False)
                else:
                    to_player = target.worldPosition - own.worldPosition
                    to_player.z = 0.0
                    if to_player.length > 0.05:
                        own.alignAxisToVect(to_player.normalized(), 1, 0.2)
                        own.applyMovement(to_player.normalized() * MOVE_SPEED, True)
        else:
            # FIX: fallback when there is NO navmesh object
            to_player = target.worldPosition - own.worldPosition
            to_player.z = 0.0
            if to_player.length > 0.001:
                own.alignAxisToVect(to_player.normalized(), 1, SMOOTH_TURN)
                own.alignAxisToVect([0,0,1], 2, 1)
                own.applyMovement(to_player.normalized() * MOVE_SPEED, False)
    else:
        if own["state"] not in ["idle","evade"] + list(ATTACK_INFO.keys()):
            own["state"] = "idle"
            play_animation(own, ANIMATIONS["idle"], 0, 30, loop=True, blend=5)

    # -----------------------------
    # Debug (small)
    # -----------------------------
    hit_active = bool(hitbox.get("active", False)) if hitbox else False
    print(f"State:{own['state']} Frame:{current_frame:.1f} Dist:{distance:.2f} HP:{own['hp']} Hit:{hit_active}")
