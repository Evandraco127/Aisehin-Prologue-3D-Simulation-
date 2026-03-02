import bge
from mathutils import Vector

def ground_check(cont):
    own = cont.owner
    ray = cont.sensors["GroundRay"]

    lv = own.worldLinearVelocity

    # Only grounded if ray hits AND not moving upward
    if ray.positive and lv.z <= 0.1:
        if not own.get("grounded", True):
            print("Landed")
        own["grounded"] = True
    else:
        own["grounded"] = False

    # --- DEBUG DRAW ---
    start = own.worldPosition.copy()
    end = start - Vector((0, 0, 2.0))  # match your ray length!
    bge.render.drawLine(start, end, [1, 0, 0])  # red line

    if ray.positive:
        own["grounded"] = True
    else:
        own["grounded"] = False
