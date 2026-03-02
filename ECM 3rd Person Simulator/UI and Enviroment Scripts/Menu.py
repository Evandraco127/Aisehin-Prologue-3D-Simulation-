import bge

# --- Scene names ---
START_SCENE  = "StartGame"
GAME_SCENE   = "Game"
#GAME_SCENE2  = "MallHall"
#END_SCENE    = "PauseMenu"
QUIT_SCENE   = "QuitScreen"

# --- Objects ---
PLAYER_OBJECT_NAME = "Player"

# --- Timer settings ---
END_DELAY = 5.0  # seconds until auto end

def menu_controller(cont):
    scene  = bge.logic.getCurrentScene()
    kb     = bge.logic.keyboard
    inputs = kb.inputs

    # Debug print player transforms
    for obj in scene.objects:
        if "Player.MallHall" in obj.name:
            print(obj.name, obj.worldPosition, obj.worldOrientation.to_euler())

    # --- Persistent flags using globalDict ---
    gd = bge.logic.globalDict
    gd.setdefault("game_started", False)
    gd.setdefault("end_timer", 0.0)

    # --- START GAME (T key) ---
    if inputs[bge.events.TKEY].activated and not gd["game_started"]:
        try:
            scene.replace(GAME_SCENE)
            gd["game_started"] = True
            gd["end_timer"] = 0.0
            print("[Menu] Game started (T)")
        except Exception as e:
            print("[Menu] Failed to start game:", e)

    # --- START GAME2 (O key) ---
#    if inputs[bge.events.OKEY].activated and not gd["game_started"]:
#        try:
#            scene.replace(GAME_SCENE2)
#            gd["game_started"] = True
#            gd["end_timer"] = 0.0
#            print("[Menu] Game started (O)")
#        except Exception as e:
#            print("[Menu] Failed to start game2:", e)

    # --- RETURN TO START MENU (P key) ---
#    if inputs[bge.events.PKEY].activated and gd["game_started"]:
#        try:
#            scene.replace(START_SCENE)
#            gd.clear()  # reset state completely
#            print("[Menu] Returned to Start Scene")
#        except Exception as e:
#            print("[Menu] Failed to return to start:", e)

#    

    # --- AUTO END SCENE ---
#    if bge.logic.globalDict["game_started"]:
#        dt = 1.0 / 60.0  # assume 60 FPS
#        bge.logic.globalDict["end_timer"] += dt

#        if bge.logic.globalDict["end_timer"] >= END_DELAY:
#            try:
#                scene.replace(END_SCENE)
#                print(f"[Menu] {END_SCENE} loaded automatically after {END_DELAY} seconds")
#                bge.logic.globalDict["game_started"] = False
#                bge.logic.globalDict["end_timer"] = 0.0
#            except Exception as e:
#                print(f"[Menu] Failed to load {END_SCENE} automatically:", e)
