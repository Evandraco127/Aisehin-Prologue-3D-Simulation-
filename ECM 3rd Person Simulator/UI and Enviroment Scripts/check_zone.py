# check_zone.py

#import bge

#cont = bge.logic.getCurrentController()
#scene = bge.logic.getCurrentScene()

#inventory = bge.logic.globalDict.get("inventory", [])
#print("Inventory:", inventory)

#if "EarthAieshin" in inventory:
#    print("You found the apple!")
#    cont.activate(cont.actuators["Sound"])
#else:
#    print("You haven't found the apple yet.")
#    
#    
#    
# check_zone.py

import bge

cont = bge.logic.getCurrentController()
scene = bge.logic.getCurrentScene()

inventory = bge.logic.globalDict.get("inventory", [])

reward = scene.objects.get("kumako")

if "EarthAieshin" in inventory and reward:
    reward.visible = True
    reward.suspendDynamics(False)
    print("Secret item revealed!")
    cont.activate(cont.actuators["Sound"])
else:
    print("You haven't found the apple yet.")
#