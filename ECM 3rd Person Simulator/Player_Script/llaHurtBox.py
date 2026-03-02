import bge

def hurt_hit(cont):
    sensor = cont.sensors[0]
    
    if sensor.positive:
        print("COLLISION DETECTED")
        print("Objects:", sensor.hitObjectList)
        
#import bge
#from mathutils import Vector

#INVULN_FRAMES = 10

#def hurt_hit(cont):

#    hurtbox = cont.owner
#    armature = hurtbox.parent
#    player = armature.parent

#    if not player:
#        return

#    scene = bge.logic.getCurrentScene()
#    sensor = cont.sensors["MessagesLLA"]

#    # -------------------------
#    # INVULNERABILITY TIMER
#    # -------------------------
#    if "_hit_cooldown" not in hurtbox:
#        hurtbox["_hit_cooldown"] = 0

#    if hurtbox["_hit_cooldown"] > 0:
#        hurtbox["_hit_cooldown"] -= 1
#        return

#    # -------------------------
#    # GET MESSAGES
#    # -------------------------
#    if not sensor.positive:
#        return

#    messages = sensor.bodies
#    subjects = sensor.subjects

#    if not messages:
#        return

#    # Only process ONE hit per frame
#    attack_type = messages[0]
#    attacker_name = subjects[0] if subjects else None

#    armature["last_attack"] = attack_type

#    # -------------------------
#    # PLAY REACTION
#    # -------------------------
#    if armature.isPlayingAction(2):
#        armature.stopAction(2)

#    armature.playAction(
#        "LLASEXIDLE",
#        647,
#        660,
#        layer=2,
#        play_mode=bge.logic.KX_ACTION_MODE_PLAY,
#        speed=1.0
#    )

#    armature["reaction_cooldown"] = 5

#    # -------------------------
#        damage_table = {
#        "LLAPunch1": 25,
#        "SATPunch1": 15,
#        "SATKick1": 20,
#    }
#    DEFAULT_DAMAGE = 10

#    dmg = damage_table.get(attack_type, DEFAULT_DAMAGE)

#    old_hp = player.get("hp", 100)
#    new_hp = max(0, old_hp - dmg)
#    player["hp"] = new_hp

#    print(f"[PLAYER] {attack_type} {old_hp}->{new_hp}")
#    
#    if new_hp <= 0:
#        player["state"] = "ko"
#        armature.playAction("LLSEXYIDLE", 675, 750, layer=0)
#        return
#    # KNOCKBACK (CORRECT SOURCE)
#    # -------------------------
#    blocking = armature.get("blocking", False)
#    knockback_strength = 0.05 if blocking else 0.15

#    attacker = scene.objects.get(attacker_name) if attacker_name else None

#    if attacker:
#        knock_dir = player.worldPosition - attacker.worldPosition
#    else:else:
#    own["state"] = "hit"
#    own["hit_timer"] = 18   # stun frames
#    own["path"] = []
#    try:
#        own.worldLinearVelocity = [0,0,0]
#        own.worldAngularVelocity = [0,0,0]
#    except Exception:
#        pass

#    hit_anim = ANIMATIONS.get("hit")
#    if arm and hit_anim:
#        arm.playAction(hit_anim, 0, 20, layer=0,
#                       play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=1.0)

#    print(f"[AI] Hit stun {attack_type} dmg={dmg} HP {old_hp}->{new_hp}")
#    return
#        knock_dir = Vector((0, -1, 0))  # fallback

#    knock_dir.z = 0

#    if knock_dir.length > 0:
#        knock_dir.normalize()

#    player.applyMovement(knock_dir * knockback_strength, True)

#    # -------------------------
#    # SET INVULN
#    # -------------------------
#    hurtbox["_hit_cooldown"] = INVULN_FRAMES

#    print("Took damage from:", attack_type)