# Aisehin-Prologue-3D-Simulation-
3rd Person Language Game Application
# 2026 Python 3rd Person Controller System
UPBGE 0.50 | Fully Scripted | State-Driven Architecture
Author: Evan Charles McArthur  

---

Overview

A modular third-person combat framework built in UPBGE 0.50 using Python.

This project focuses on deterministic state control, layered animation authority, and modular combat architecture rather than prototype-level scripting.

The goal was to design a reusable, inspectable, production-oriented controller system that avoids hidden state coupling and animation deadlocks.

# Core Features

2 fully playable characters

25+ animation clips per character

Layered animation system (locomotion + action override)

Lock-on targeting system

Combo-based attack handling

Dodge system with cooldown logic

AI opponent system

12-foot Reptile Oni boss character

Hitbox-driven damage messaging

Collectible + state-based world interaction system

System Architecture

The framework is structured around explicit state authority.

Movement, animation, and combat are resolved in a deterministic order each frame.

Input
  ↓
State Resolution
  ↓
Movement Authority (Character Physics)
  ↓
Animation Controller (Layered)
  ↓
Combat & Hit Detection
  ↓
AI / World Interaction

Each layer has a clear responsibility and avoids cross-coupling.
---

## Project Structure
```
2026 Python 3rd Person Controller System/
│
├── AI_Opponent_Script/
├── Documents/
├── Media/
│ ├── LLAHooks0_48.gif
│ ├── LLAJab0_22.gif
│ ├── LLARearJab0_21.gif
│ ├── LLARun66_95.gif
│ ├── LLARun6695.gif
│ └── LLAWalk4_35.gif
│
├── Player_Script/
│ ├── AttackController.py
│ ├── camControllerA.py
│ ├── Grounded.py
│ ├── handle_inputScript.py
│ ├── MCAnimationController.py
│ └── moveJoyM.py
---
```
