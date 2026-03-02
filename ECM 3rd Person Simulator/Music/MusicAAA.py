import bge
import aud
import os
import sys

# Single audio device for the whole game
DEVICE = aud.Device()

def _candidate_paths_for(filename: str):
    """Return a list of candidate absolute paths to try for the given file."""
    cand = []

    # 1) Editor path (relative to .blend)
    try:
        cand.append(bge.logic.expandPath("//music/" + filename))
        # also try the dir directly if expandPath("//music") resolves
        music_dir = bge.logic.expandPath("//music")
        cand.append(os.path.join(music_dir, filename))
    except Exception:
        pass

    # 2) Runtime paths
    exe_path = os.path.abspath(sys.argv[0])
    exe_dir  = os.path.dirname(exe_path)

    # a) Next to the executable (Contents/MacOS/music on macOS)
    cand.append(os.path.join(exe_dir, "music", filename))

    # b) macOS .app root (go up two levels from Contents/MacOS to .app)
    app_root = os.path.abspath(os.path.join(exe_dir, "..", ".."))
    cand.append(os.path.join(app_root, "music", filename))

    # c) macOS Resources
    resources = os.path.join(app_root, "Contents", "Resources")
    cand.append(os.path.join(resources, "music", filename))

    # d) Current working directory (just in case)
    cand.append(os.path.join(os.getcwd(), "music", filename))

    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for p in cand:
        ap = os.path.abspath(p)
        if ap not in seen:
            uniq.append(ap)
            seen.add(ap)
    return uniq

def _resolve_file(filename: str):
    """Return the first existing absolute path for the file, or None. Prints debug."""
    candidates = _candidate_paths_for(filename)
    for p in candidates:
        if os.path.isfile(p):
            print(f"[Music] Found '{filename}' at: {p}")
            return p
    print(f"[Music] Could not find '{filename}'. Tried:")
    for p in candidates:
        print("  -", p)
    return None

def _load_playlist(names):
    """Resolve all filenames to absolute paths. Skips missing ones with a warning."""
    paths = []
    for n in names:
        rp = _resolve_file(n)
        if rp:
            paths.append(rp)
    return paths

# -------------------------------------------------------------
# Main entry (attach to Always sensor with True pulse enabled)
# -------------------------------------------------------------
def player(cont):
    own = cont.owner

    if "songs" not in own:
        # List the files you expect to ship
        filenames = [
            "BPM53Phoenems.mp3",
            "EvangelionofECM.mp3",
            "EveryThingurNevGonna.mp3",
            "SheLovesSheLeaves.mp3"
        ]
        playlist = _load_playlist(filenames)

        if not playlist:
            print("[Music] ERROR: No songs resolved. Check your 'music' folder location.")
            return

        own["songs"] = playlist
        own["current"] = 0
        own["handle"] = None

        _play_current(own)

    # Input
    keyboard = bge.logic.keyboard
    JUST = bge.logic.KX_INPUT_JUST_ACTIVATED

    if keyboard.events[bge.events.NKEY] == JUST:
        _next(own)
    if keyboard.events[bge.events.BKEY] == JUST:
        _prev(own)

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _play_current(own):
    # Stop previous
    if own["handle"]:
        own["handle"].stop()
        own["handle"] = None

    path = own["songs"][own["current"]]
    try:
        snd = aud.Sound(path)      # <- this is the correct type for Device.play
        handle = DEVICE.play(snd)
        handle.loop_count = -1     # loop forever
        own["handle"] = handle
        print(f"[Music] Now playing: {path}")
    except Exception as e:
        print(f"[Music] ERROR playing '{path}': {e}")

def _next(own):
    own["current"] = (own["current"] + 1) % len(own["songs"])
    _play_current(own)

def _prev(own):
    own["current"] = (own["current"] - 1) % len(own["songs"])
    _play_current(own)
