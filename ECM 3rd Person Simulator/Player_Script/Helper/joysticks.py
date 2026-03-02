import bge

def update(cont):
    joy = bge.logic.joysticks[0]
    if not joy:
        return

    for btn in joy.activeButtons:
        print("BUTTON", btn, "pressed")
        
#    for s in cont.sensors:
#         print("Sensor:", s.name, "Positive:", s.positive)
