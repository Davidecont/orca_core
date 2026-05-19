import time
import json
import os
from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions

NUM_STEPS  = 25
STEP_SIZE  = 0.008
HOLD_TIME  = 1.5
POSES_FILE = "demo_poses.json"

def pose_from_fractions(hand, fractions):
    pose = dict(hand.config.neutral_position)
    for joint, fraction in fractions.items():
        if joint not in hand.config.joint_roms_dict:
            continue
        joint_min, joint_max = hand.config.joint_roms_dict[joint]
        pose[joint] = joint_min + fraction * (joint_max - joint_min)
    return OrcaJointPositions.from_dict(pose)

# def print_pose_live(name, fractions):
    print(f"\033[2J\033[H", end="")
    print(f"\033[1m  ORCA Hand — Demo\033[0m\n")
    print(f"  Current pose: \033[92m{name}\033[0m\n")
    groups = {
        "Thumb":  ["thumb_abd", "thumb_mcp", "thumb_pip", "thumb_dip"],
        "Index":  ["index_abd", "index_mcp", "index_pip"],
        "Middle": ["middle_abd", "middle_mcp", "middle_pip"],
        "Ring":   ["ring_abd",   "ring_mcp",   "ring_pip"],
        "Pinky":  ["pinky_abd",  "pinky_mcp",  "pinky_pip"],
        "Wrist":  ["wrist"],
    }
    for finger, joints in groups.items():
        print(f"  \033[2m{finger}\033[0m")
        for joint in joints:
            val = fractions.get(joint, 0.0)
            bar = "█" * int(val * 20)
            spaces = " " * (20 - int(val * 20))
            print(f"    {joint:<16} \033[92m{bar}{spaces}\033[0m {int(val*100):3d}%")
        print()

def go_to_neutral(hand):
    print("\nReturning to neutral position...")
    hand.enable_torque()
    hand.set_control_mode('current_based_position')
    hand.set_neutral_position(num_steps=50, step_size=0.02)
    print("✅ Neutral position reached.")

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

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)
hand.enable_torque()
hand.set_control_mode('current_based_position')

names = list(saved_poses.keys())
print(f"\n{'='*50}")
print(f"  DEMO — {len(names)} poses in cycle")
print(f"  {' → '.join(names)}")
print(f"  Ctrl+C to stop")
print(f"{'='*50}\n")
time.sleep(1)

try:
    cycle = 0
    while True:
        cycle += 1
        for i, name in enumerate(names):
            fractions = saved_poses[name]
            pose = pose_from_fractions(hand, fractions)
            # print_pose_live(f"{name}  (cycle {cycle}, {i+1}/{len(names)})", fractions)
            hand.set_joint_positions(pose, num_steps=NUM_STEPS, step_size=STEP_SIZE)
            time.sleep(HOLD_TIME)

except KeyboardInterrupt:
    print("\n\nDemo stopped.")
finally:
    go_to_neutral(hand)
    shutdown_hand(hand)