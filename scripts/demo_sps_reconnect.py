import time
import json
import os
import subprocess
import re
import threading
from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions

NUM_STEPS       = 25
STEP_SIZE       = 0.008
HOLD_TIME       = 1.5
NEUTRAL_STEPS   = 30
NEUTRAL_SIZE    = 0.005
GROUP_LOOPS     = 3
RECONNECT_DELAY = 3.0
MAX_RETRIES     = 10
POSES_FILE      = "demo_poses.json"
CONFIG_PATH     = "orca_core/models/v1/orcahand_right/config.yaml"
SERIAL_PORT     = "COM5"
WATCHDOG_INTERVAL = 1.0  # check every second

def pose_from_fractions(hand, fractions):
    pose = dict(hand.config.neutral_position)
    for joint, fraction in fractions.items():
        if joint not in hand.config.joint_roms_dict:
            continue
        joint_min, joint_max = hand.config.joint_roms_dict[joint]
        pose[joint] = joint_min + fraction * (joint_max - joint_min)
    return OrcaJointPositions.from_dict(pose)

def go_to_neutral(hand_ref):
    try:
        hand_ref[0].enable_torque()
        hand_ref[0].set_control_mode('current_based_position')
        hand_ref[0].set_neutral_position(num_steps=NEUTRAL_STEPS, step_size=NEUTRAL_SIZE)
    except Exception as e:
        print(f"\n⚠️  Could not reach neutral: {e}")

def print_status(group, name, cycle, group_loop, total_loops, i, total):
    print(f"\033[2J\033[H", end="")
    print(f"\033[1m  ORCA Hand — Demo\033[0m\n")
    print(f"  Cycle:       {cycle}")
    if total_loops > 1:
        print(f"  Group:       \033[92m{group}\033[0m  (rep {group_loop}/{total_loops})")
    else:
        print(f"  Group:       \033[92m{group}\033[0m  (single pose)")
    print(f"  Pose:        \033[92m{name}\033[0m  ({i+1}/{total})")
    print(f"  Status:      \033[92m● Online\033[0m")

def print_waiting(attempt):
    print(f"\033[2J\033[H", end="")
    print(f"\033[1m  ORCA Hand — Demo\033[0m\n")
    print(f"  Status:      \033[93m⚠ Waiting for connection (attempt {attempt})...\033[0m")
    print(f"\n  Check power supply and USB connection.")
    print(f"  Will resume automatically when ready.")

def group_poses(saved_poses):
    groups = {}
    for name in saved_poses:
        parts = name.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            prefix = parts[0]
            is_sequence = True
        else:
            prefix = name
            is_sequence = False
        if prefix not in groups:
            groups[prefix] = {"poses": [], "is_sequence": is_sequence}
        groups[prefix]["poses"].append(name)
    return groups

def force_close_port(port=SERIAL_PORT):
    try:
        subprocess.run(
            ["powershell", "-Command",
             f"Get-Process | Where-Object {{$_.Modules.FileName -like '*{port}*'}} | Stop-Process -Force"],
            capture_output=True, text=True, timeout=5
        )
    except Exception:
        pass
    try:
        import serial
        s = serial.Serial(port, baudrate=9600, timeout=0.1)
        s.close()
        del s
    except Exception:
        pass
    try:
        subprocess.run(
            ["powershell", "-Command",
             f"$port = New-Object System.IO.Ports.SerialPort '{port}'; "
             f"$port.Open(); $port.Close(); $port.Dispose()"],
            capture_output=True, text=True, timeout=5
        )
    except Exception:
        pass
    time.sleep(1.0)

def try_create_hand(config_path):
    """Tries to create and connect a new hand. Returns hand or None."""
    try:
        new_hand = create_hand(config_path, use_mock=False)
        success, msg = new_hand.connect()
        if not success:
            return None
        # Verify motors respond
        _ = new_hand.get_motor_pos()
        new_hand.enable_torque()
        new_hand.set_control_mode('current_based_position')
        return new_hand
    except Exception:
        return None

def wait_for_recovery(config_path):
    """
    Waits indefinitely until hand is available again.
    Stops all packet sending during wait.
    """
    print(f"\n\033[93m⚠️  Connection lost — stopping packets, waiting for recovery...\033[0m")

    attempt = 0
    while True:
        attempt += 1
        print_waiting(attempt)

        # Try force close first
        force_close_port()

        new_hand = try_create_hand(config_path)
        if new_hand is not None:
            print(f"\n\033[92m✅ Recovered on attempt {attempt}! Resuming demo...\033[0m\n")
            time.sleep(1.0)
            return new_hand

        time.sleep(RECONNECT_DELAY)

class ConnectionWatchdog:
    """
    Background thread that monitors connection health.
    Sets a flag when connection is lost so the main loop can pause.
    """
    def __init__(self, hand_ref, config_path):
        self.hand_ref = hand_ref
        self.config_path = config_path
        self.connection_lost = threading.Event()
        self.recovering = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            time.sleep(WATCHDOG_INTERVAL)
            if self.recovering.is_set():
                continue
            try:
                # Simple health check — read motor positions
                if not self.hand_ref[0].is_connected():
                    raise Exception("Not connected")
                _ = self.hand_ref[0].get_motor_pos()
            except Exception:
                if not self.recovering.is_set():
                    self.connection_lost.set()

def safe_execute(hand_ref, func, config_path, watchdog):
    """
    Executes a function with automatic recovery on connection loss.
    Pauses packet sending while recovering.
    """
    while True:
        # Check if watchdog already detected a problem
        if watchdog.connection_lost.is_set():
            watchdog.recovering.set()
            watchdog.connection_lost.clear()
            new_hand = wait_for_recovery(config_path)
            hand_ref[0] = new_hand
            watchdog.recovering.clear()

        try:
            func()
            return True
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\n⚠️  Error during execution: {e}")
            watchdog.recovering.set()
            watchdog.connection_lost.clear()
            new_hand = wait_for_recovery(config_path)
            if new_hand is None:
                return False
            hand_ref[0] = new_hand
            watchdog.recovering.clear()

# ── Setup ─────────────────────────────────────────────────
if not os.path.exists(POSES_FILE):
    print(f"⚠️  File '{POSES_FILE}' not found. Please run record_poses.py first.")
    exit(1)

try:
    with open(POSES_FILE, 'r') as f:
        content = f.read().strip()
        saved_poses = json.loads(content) if content else {}
except json.JSONDecodeError:
    print(f"⚠️  File '{POSES_FILE}' corrupted.")
    exit(1)

if not saved_poses:
    print("⚠️  No poses found. Please run record_poses.py first.")
    exit(1)

hand = create_hand(CONFIG_PATH, use_mock=False)
connect_hand(hand)
hand.enable_torque()
hand.set_control_mode('current_based_position')

hand_ref = [hand]
groups = group_poses(saved_poses)

watchdog = ConnectionWatchdog(hand_ref, CONFIG_PATH)
watchdog.start()

print(f"\n{'='*50}")
print(f"  DEMO — {len(groups)} groups, {len(saved_poses)} poses total")
print(f"  Sequences repeat {GROUP_LOOPS}x, single poses execute once")
for group, data in groups.items():
    tag = f"x{GROUP_LOOPS}" if data["is_sequence"] else "x1"
    print(f"  • {group} ({tag}): {' → '.join(data['poses'])}")
print(f"  Ctrl+C to stop")
print(f"{'='*50}\n")
time.sleep(1)

try:
    cycle = 0
    while True:
        cycle += 1
        for group, data in groups.items():
            names = data["poses"]
            is_sequence = data["is_sequence"]
            loops = GROUP_LOOPS if is_sequence else 1

            for rep in range(1, loops + 1):
                for i, name in enumerate(names):
                    fractions = saved_poses[name]

                    def move():
                        pose = pose_from_fractions(hand_ref[0], fractions)
                        print_status(group, name, cycle, rep, loops, i, len(names))
                        hand_ref[0].set_joint_positions(
                            pose, num_steps=NUM_STEPS, step_size=STEP_SIZE
                        )

                    ok = safe_execute(hand_ref, move, CONFIG_PATH, watchdog)
                    if not ok:
                        print("❌ Giving up — could not recover.")
                        exit(1)
                    time.sleep(HOLD_TIME)

            def neutral():
                go_to_neutral(hand_ref)

            safe_execute(hand_ref, neutral, CONFIG_PATH, watchdog)

except KeyboardInterrupt:
    print("\n\nDemo stopped.")
finally:
    watchdog.stop()
    go_to_neutral(hand_ref)
    shutdown_hand(hand_ref[0])