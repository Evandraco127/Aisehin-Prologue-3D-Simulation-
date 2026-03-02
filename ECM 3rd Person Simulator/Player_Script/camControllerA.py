import bge
import math
from mathutils import Vector

# -------------------------------------------------------------
# Toggle this to True if you want debug text in the console
# -------------------------------------------------------------
DEBUG = False

def dprint(*msg):
    """Debug print helper."""
    if DEBUG:
        print("[CAMERA]", *msg)


def camera_controller(cont):
    own = cont.owner
    scene = bge.logic.getCurrentScene()

    player = scene.objects.get("Player.MallHall")
    if not player:
        return

    # =============================================================
    #  INITIAL CAMERA RIG SETUP
    # =============================================================
    if "offset" not in own:
        # offset = where the camera pivot sits relative to the player
        # (X sideways, Y forward/back, Z up)
        own["offset"] = (0.0, 0.0, 0.35)

    offx, offy, offz = own["offset"]

    # camera lock 
    if "cam_lock" not in own:
        own["cam_lock"] = False

    # run only once when lock is toggled
    if "cam_lock_initialized" not in own:
        own["cam_lock_initialized"] = False

    # reusable vector for aligning camera during lock-on
    if "_align_dir" not in own:
        own["_align_dir"] = [0.0, 0.0, 0.0]

    # How fast the camera follows the pivot
    follow_speed = 0.15


    # =============================================================
    #  INPUT HELPERS
    # =============================================================
    joysticks = [js for js in bge.logic.joysticks if js]
    keyboard_inputs = bge.logic.keyboard.inputs

    def key_active(keycode):
        k = keyboard_inputs.get(keycode)
        return bool(k and k.active)

    def key_just_pressed(keycode):
        k = keyboard_inputs.get(keycode)
        return bool(k and k.activated)


    # =============================================================
    #  HAT SWITCH (ADJUST CAMERA HEIGHT)
    # =============================================================
    if joysticks:
        buttons = joysticks[0].activeButtons or []
        pivot_offset_speed = 0.025
        
        # Move camera pivot DOWN
        if 13 in buttons:
            offz = max(0.5, offz - pivot_offset_speed)

        # Move camera pivot UP
        if 14 in buttons:
            offz = min(0.85, offz + pivot_offset_speed)

    own["offset"] = (offx, offy, offz)


    # =============================================================
    #  SMOOTH FOLLOW MATH
    # =============================================================
    # target_x = player's position + offset
    # Camera pivot moves toward this using linear interpolation.
    #
    # new = old + (target - old) * speed
    #
    # This creates smooth easing instead of snapping.

    px, py, pz = player.worldPosition
    target_x = px + offx
    target_y = py + offy
    target_z = pz + offz

    ox, oy, oz = own.worldPosition
    own.worldPosition.x = ox + (target_x - ox) * follow_speed
    own.worldPosition.y = oy + (target_y - oy) * follow_speed
    z_follow_speed = 0.0667  # slower than horizontal
    own.worldPosition.z = oz + (target_z - oz) * z_follow_speed

    dprint("Pivot Pos:", own.worldPosition[:])


    # =============================================================
    #  GET CAMERA OBJECT
    # =============================================================
    cam = own.children.get("Camera.001")
    if not cam:
        return

    # =============================================================
    #  ZOOM HANDLING
    # =============================================================
    if "zoom" not in cam:
        # zoom is negative because camera moves backwards on local -Y axis
        cam["zoom"] = -5.0

    zoom_speed = 0.1
    min_zoom, max_zoom = -8.0, -2.0

    # Keyboard zoom
    if key_active(bge.events.ZKEY): cam["zoom"] -= zoom_speed
    if key_active(bge.events.XKEY): cam["zoom"] += zoom_speed

    # Controller zoom
    if joysticks:
        buttons = joysticks[0].activeButtons or []
        if 11 in buttons: cam["zoom"] -= zoom_speed
        if 12 in buttons: cam["zoom"] += zoom_speed

    cam["zoom"] = max(min_zoom, min(max_zoom, cam["zoom"]))
    cam.localPosition.y = cam["zoom"]


    # =============================================================
    #  FREE ROTATION vs LOCK-ON
    # =============================================================
    yaw_speed = 0.03
    pitch_speed = 0.02
    deadzone = 0.2

    axis_h = axis_v = 0.0
    if joysticks:
        axis = joysticks[0].axisValues or []
        # axis[2] = right stick horizontal  
        # axis[3] = right stick vertical
        if len(axis) >= 4:
            axis_h = axis[2] if abs(axis[2]) > deadzone else 0.0
            axis_v = axis[3] if abs(axis[3]) > deadzone else 0.0


    # =============================================================
    #  LOCK-ON TOGGLE
    # =============================================================
    R1_pressed = False
    if joysticks:
        R1_pressed = 10 in (joysticks[0].activeButtons or [])
    if key_active(bge.events.RKEY):
        R1_pressed = True

    if "prev_R1" not in own:
        own["prev_R1"] = False

    # Toggle when freshly pressed
    if R1_pressed and not own["prev_R1"]:
        own["cam_lock"] = not own["cam_lock"]
        own["cam_lock_initialized"] = False
        dprint("Lock Toggled:", own["cam_lock"])

    own["prev_R1"] = R1_pressed


    # =============================================================
    #  GET PIVOT + CAM_BEHIND EMPTY
    # =============================================================
    try:
        pivot = scene.objects["EmptyMallHall"]
        cam_behind = scene.objects["cam_behind.001"]
    except KeyError:
        return


    # =============================================================
    #  RESET TO DEFAULT POSITION
    # =============================================================
    RESET_KEY = bge.events.TKEY

    if key_just_pressed(RESET_KEY):
        default_offset = Vector((0.0, -2.0, 0.65))
        own.worldPosition = player.worldPosition + default_offset
        own.worldOrientation = player.worldOrientation.copy()

        cam["zoom"] = -3.0
        cam["current_cam_distance"] = -3.0
        own["cam_lock_initialized"] = True

        dprint("Camera reset.")


    # =============================================================
    #  LOCK-ON CAMERA BEHAVIOR
    # =============================================================
    if own["cam_lock"]:
        t = player.get("lock_target")
        target = scene.objects.get(t) if isinstance(t, str) else t if t else scene.objects.get("Enemy.003")

        if target:
            tx, ty, tz = target.worldPosition
            ox, oy, oz = own.worldPosition

            # dx,dy = difference between pivot and target
            # dist = 2D distance (we ignore height)
            dx, dy = tx - ox, ty - oy
            dist = math.hypot(dx, dy)  # sqrt(x²+y²)

            if dist > 0.001:
                # UNIT VECTOR pointing toward target
                nx, ny = dx / dist, dy / dist

                ad = own["_align_dir"]
                ad[0], ad[1], ad[2] = nx, ny, 0.0

                # Align pivot to target
                if not own["cam_lock_initialized"]:
                    own.alignAxisToVect(ad, 1, 1.0)     # hard snap
                    own.alignAxisToVect([0,0,1], 2, 1.0)
                    own["cam_lock_initialized"] = True
                else:
                    own.alignAxisToVect(ad, 1, 0.12)    # smoothing
                    own.alignAxisToVect([0,0,1], 2, 1.0)

    else:
        # =========================================================
        #  FREE ROTATION CAMERA
        # =========================================================
        if axis_h != 0.0 or axis_v != 0.0:
            # YAW (Rotate left/right)
            own.applyRotation((0, 0, -axis_h * yaw_speed), False)

            # PITCH (Rotate up/down)
            pitch_e = own.localOrientation.to_euler()
            new_pitch = pitch_e.x + axis_v * pitch_speed

            # Prevent flipping upside-down
            if -0.5 < new_pitch < 1.2:
                own.applyRotation((axis_v * pitch_speed, 0, 0), True)


#    # =============================================================
#    #  CAMERA COLLISION MATH
#    # =============================================================
    # requested_dist = how far camera *wants* to be based on zoom  
    # We adjust this if walls or floor block the line.

    requested_dist = -cam["zoom"]

    # Ray start slightly above pivot to avoid tiny bumps
    ray_start = pivot.worldPosition + Vector((0.0, 0.0, 1.0))

    # Desired camera position (before collisions)
    behind_world = cam_behind.worldPosition
    vec = behind_world - ray_start

    total_len = vec.length
    dir_vec = vec.normalized() if total_len > 0.0001 else Vector((0,0,0))

    desired_dist = min(requested_dist, total_len)
    desired_pos = ray_start + dir_vec * desired_dist

    cam_distance = requested_dist

    hit_obj, hit_pos, hit_norm = pivot.rayCast(
        desired_pos, ray_start, desired_dist, xray=True
    )

    if hit_obj and hit_obj.name not in ["Cube.164","LLAHurtBox", "Player.MallHall","Akiko.Hair.001","LLA.WhiteGLoves.002"]:
        # camera stops 0.15m before hitting wall
        cam_distance = min(cam_distance, (hit_pos - ray_start).length - 0.35)
        dprint("Wall hit:", hit_obj.name)


    # =============================================================
    #  FLOOR RAYCAST (stops camera from sinking too low)
    # =============================================================
    floor_start = Vector((desired_pos.x, desired_pos.y, desired_pos.z + 0.25))
    floor_end   = Vector((desired_pos.x, desired_pos.y, desired_pos.z - 3.0))

    floor_hit, floor_point, floor_norm = pivot.rayCast(floor_end, floor_start, 2.0)

    if floor_hit:
        dist_to_floor = (floor_point - ray_start).length
        cam_distance = max(cam_distance, dist_to_floor + 0.25)
        dprint("Floor hit:", floor_hit.name)

    # =============================================================
    #  APPLY CLAMPED CAMERA DISTANCE
    # =============================================================
    if "current_cam_distance" not in cam:
        cam["current_cam_distance"] = cam_distance

    delta = cam_distance - cam["current_cam_distance"]

    # Smooth change
    cam["current_cam_distance"] += delta * 0.12
    cam.localPosition.y = -cam["current_cam_distance"]

    dprint("Cam Dist:", cam["current_cam_distance"])
