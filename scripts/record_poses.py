import time
import json
import os
from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions

POSES_FILE = "demo_poses.json"

def read_fractions(hand):
    joint_pos = hand._get_joint_positions().as_dict()
    result = {}
    for joint, pos in joint_pos.items():
        if pos is None:
            continue
        rom = hand.config.joint_roms_dict.get(joint)
        if rom is None:
            continue
        joint_min, joint_max = rom
        rom_range = joint_max - joint_min
        if rom_range == 0:
            continue
        fraction = (pos - joint_min) / rom_range
        result[joint] = round(float(max(0.0, min(1.0, fraction))), 3)
    return result

# def print_pose_live(name, fractions):
    print(f"\033[2J\033[H", end="")
    print(f"\033[1m  ORCA Hand — Pose: {name}\033[0m\n")
    groups = {
        "Thumb":  ["thumb_abd", "thumb_mcp", "thumb_pip", "thumb_dip"],
        "Index":  ["index_abd", "index_mcp", "index_pip"],
        "Middle": ["middle_abd", "middle_mcp", "middle_pip"],
        "Ring":   ["ring_abd",   "ring_mcp",   "ring_pip"],
        "Pinky":  ["pinky_abd",  "pinky_mcp",  "pinky_pip"],
    }
    for finger, joints in groups.items():
        print(f"  \033[2m{finger}\033[0m")
        for joint in joints:
            val = fractions.get(joint, 0.0)
            bar = "█" * int(val * 20)
            spaces = " " * (20 - int(val * 20))
            print(f"    {joint:<16} \033[92m{bar}{spaces}\033[0m {int(val*100):3d}%")
        print()

def print_pose_code(name, fractions):
    print(f"\n# ── {name} ──")
    print('pose = pose_from_fractions(hand, {')
    groups = {
        "thumb":  ["thumb_abd", "thumb_mcp", "thumb_pip", "thumb_dip"],
        "index":  ["index_abd", "index_mcp", "index_pip"],
        "middle": ["middle_abd", "middle_mcp", "middle_pip"],
        "ring":   ["ring_abd",   "ring_mcp",   "ring_pip"],
        "pinky":  ["pinky_abd",  "pinky_mcp",  "pinky_pip"],
        "wrist": ["wrist"]
    }
    for finger, joints in groups.items():
        print(f"    # {finger}")
        for joint in joints:
            if joint in fractions:
                print(f'    "{joint}": {fractions[joint]},')
    print('})')

# ── Setup ─────────────────────────────────────────────────
hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)
hand.enable_torque()
hand.set_control_mode('current_based_position')

saved_poses = {}
if os.path.exists(POSES_FILE):
    try:
        with open(POSES_FILE, 'r') as f:
            content = f.read().strip()
            saved_poses = json.loads(content) if content else {}
        print(f"\n✅ Loaded {len(saved_poses)} existing poses:")
        for name in saved_poses:
            print(f"   • {name}")
    except json.JSONDecodeError:
        print(f"\n⚠️  File '{POSES_FILE}' corrupted — starting from scratch.")
        saved_poses = {}

print(f"\n{'='*50}")
print("  POSE RECORDING")
print("  ENTER = record | 'q' = quit | 'd' = delete | 'l' = list")
print(f"{'='*50}")

try:
    while True:
        hand.disable_torque()
        print("\n\033[93m✋ Torque DISABLED — move the hand freely\033[0m")
        cmd = input("  > ").strip().lower()

        if cmd == 'q':
            break

        elif cmd == 'l':
            if saved_poses:
                print("  Saved poses:")
                for i, name in enumerate(saved_poses):
                    print(f"   {i+1}. {name}")
            else:
                print("  No poses saved yet.")
            continue

        elif cmd == 'd':
            if not saved_poses:
                print("  No poses to delete.")
                continue
            for i, name in enumerate(saved_poses):
                print(f"   {i+1}. {name}")
            to_delete = input("  Pose name to delete: ").strip()
            if to_delete in saved_poses:
                del saved_poses[to_delete]
                with open(POSES_FILE, 'w') as f:
                    json.dump(saved_poses, f, indent=2)
                print(f"  ✅ '{to_delete}' deleted.")
            else:
                print(f"  ⚠️  '{to_delete}' not found.")
            continue

        # ENTER → read current position
        hand.enable_torque()
        hand.set_control_mode('current_based_position')
        time.sleep(0.3)

        fractions = read_fractions(hand)

        name = input("  📝 Pose name (ENTER to skip): ").strip()
        if not name:
            print("  ⏭️  Skipped.")
            continue

        # print_pose_live(name, fractions)
        print_pose_code(name, fractions)

        confirm = input(f"\n  Save '{name}'? (ENTER = yes / 'n' = no): ").strip().lower()
        if confirm == 'n':
            print("  ⏭️  Not saved.")
            continue

        saved_poses[name] = fractions
        with open(POSES_FILE, 'w') as f:
            json.dump(saved_poses, f, indent=2)
        print(f"  ✅ '{name}' saved! ({len(saved_poses)} poses total)")

except KeyboardInterrupt:
    print("\n\nRecording interrupted.")
finally:
    print(f"\n✅ {len(saved_poses)} poses saved to '{POSES_FILE}'")
    shutdown_hand(hand)