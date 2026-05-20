import time
import json
import os
from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions

NUM_STEPS     = 25
STEP_SIZE     = 0.008
HOLD_TIME     = 1.5
NEUTRAL_STEPS = 30
NEUTRAL_SIZE  = 0.005
GROUP_LOOPS   = 5
POSES_FILE    = "demo_poses.json"

def pose_from_fractions(hand, fractions):
    pose = dict(hand.config.neutral_position)
    for joint, fraction in fractions.items():
        if joint not in hand.config.joint_roms_dict:
            continue
        joint_min, joint_max = hand.config.joint_roms_dict[joint]
        pose[joint] = joint_min + fraction * (joint_max - joint_min)
    return OrcaJointPositions.from_dict(pose)

def go_to_neutral(hand):
    hand.enable_torque()
    hand.set_control_mode('current_based_position')
    hand.set_neutral_position(num_steps=NEUTRAL_STEPS, step_size=NEUTRAL_SIZE)

def print_status(group, name, cycle, group_loop, total_loops, i, total):
    print(f"\033[2J\033[H", end="")
    print(f"\033[1m  ORCA Hand — Demo\033[0m\n")
    print(f"  Cycle:       {cycle}")
    if total_loops > 1:
        print(f"  Group:       \033[92m{group}\033[0m  (rep {group_loop}/{total_loops})")
    else:
        print(f"  Group:       \033[92m{group}\033[0m  (single pose)")
    print(f"  Pose:        \033[92m{name}\033[0m  ({i+1}/{total})")

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

groups = group_poses(saved_poses)

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
                    pose = pose_from_fractions(hand, fractions)
                    print_status(group, name, cycle, rep, loops, i, len(names))
                    hand.set_joint_positions(pose, num_steps=NUM_STEPS, step_size=STEP_SIZE)
                    time.sleep(HOLD_TIME)

            go_to_neutral(hand)

except KeyboardInterrupt:
    print("\n\nDemo stopped.")
finally:
    go_to_neutral(hand)
    shutdown_hand(hand)