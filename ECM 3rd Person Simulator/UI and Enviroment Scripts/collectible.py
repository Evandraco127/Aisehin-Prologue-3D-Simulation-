# collectible.py

import bge

cont = bge.logic.getCurrentController()
own = cont.owner
scene = bge.logic.getCurrentScene()

for obj in scene.objects:
    if obj.name == "Player.MallHall":
        player = obj

# Store global inventory
if "inventory" not in bge.logic.globalDict:
    bge.logic.globalDict["inventory"] = []

# Add item
item_name = own.name
bge.logic.globalDict["inventory"].append(item_name)

# Turn off object
own.endObject()