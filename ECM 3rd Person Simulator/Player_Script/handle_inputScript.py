import bge
from mathutils import Vector

# --- CONFIG ---
PLAYER_NAME = "Player.MallHall"
ENEMY_PREFIX = "Enemy"   # all enemies must start with this in their name
R1_INDEX = 10
TOGGLE_COOLDOWN = 0.2
LOCK_RADIUS = 25.0       # max distance to lock onto enemy
# -------------

def get_closest_enemy(scene, player):
    """Return the closest enemy object to player (within LOCK_RADIUS)."""
    enemies = [obj for obj in scene.objects if obj.name.startswith(ENEMY_PREFIX)]
    if not enemies:
        return None
    
    player_pos = Vector(player.worldPosition)
    closest_enemy = None
    closest_dist = float("inf")
    
    for enemy in enemies:
        dist = (Vector(enemy.worldPosition) - player_pos).length
        if dist < closest_dist and dist <= LOCK_RADIUS:
            closest_enemy = enemy
            closest_dist = dist
    
    return closest_enemy

def toggle_lock_on(cont):
    own = cont.owner
    scene = bge.logic.getCurrentScene()
    kb = bge.logic.keyboard
    joysticks = bge.logic.joysticks

    LKEY = bge.events.LKEY

    player = scene.objects.get(PLAYER_NAME)
    if not player:
        return

    # init cooldown
    if "lock_toggle_cooldown" not in own:
        own["lock_toggle_cooldown"] = 0.0

    # update cooldown
    own["lock_toggle_cooldown"] = max(0.0, own["lock_toggle_cooldown"] - bge.logic.getFrameTime())

    toggled_cam = False
    toggled_player = False

    # Keyboard lock
    if kb.events[LKEY] == bge.logic.KX_INPUT_JUST_ACTIVATED and own["lock_toggle_cooldown"] == 0.0:
        toggled_player = True

    # Joystick lock
    if joysticks and joysticks[0]:
        joy = joysticks[0]
        current_buttons = joy.activeButtons or []
        prev_buttons = own.get("prev_buttons", [])
        newly_pressed = [b for b in current_buttons if b not in prev_buttons]

        if R1_INDEX in newly_pressed and own["lock_toggle_cooldown"] == 0.0:
            toggled_cam = True

        own["prev_buttons"] = current_buttons

    # Apply toggles
    if toggled_cam:
        enemy = get_closest_enemy(scene, player)
        if enemy:
            own["lock_target"] = enemy
            own["lock_on"] = not own.get("lock_on", False)
            own["lock_toggle_cooldown"] = TOGGLE_COOLDOWN
            own["lock_initialized"] = False
            print("[toggle] cam lock ->", own["lock_on"], "target:", enemy.name)
        else:
            print("[toggle] no enemies in range")

    if toggled_player:
        player["lock_on"] = not player.get("lock_on", False)
        player["lock_initialized"] = False
        own["lock_toggle_cooldown"] = TOGGLE_COOLDOWN
        print("[toggle] player lock ->", player["lock_on"])
        
        # Force locomotion to resync
        for child in player.children:
            if "last_state" in child:
                child["locomotion_dirty"] = True
                child["last_state"] = None





