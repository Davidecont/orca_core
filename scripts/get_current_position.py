import math
import yaml
import dataclasses
from common import connect_hand, create_hand, shutdown_hand


hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)


def leggi_frazioni(hand):
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
        fraction = max(0.0, min(1.0, fraction))
        result[joint] = round(fraction, 3)
    return result

def stampa_pose(label, frazioni):
    print(f"\n# ── {label} ──")
    print('pose = remove_wrist(pose_from_fractions(hand, {')
    gruppi = {
        "thumb":  ["thumb_abd", "thumb_mcp", "thumb_pip", "thumb_dip"],
        "index":  ["index_abd", "index_mcp", "index_pip"],
        "middle": ["middle_abd", "middle_mcp", "middle_pip"],
        "ring":   ["ring_abd",   "ring_mcp",   "ring_pip"],
        "pinky":  ["pinky_abd",  "pinky_mcp",  "pinky_pip"],
        "wrist":  ["wrist"],
    }
    for dito, joints in gruppi.items():
        print(f"    # {dito}")
        for joint in joints:
            if joint in frazioni:
                print(f'    "{joint}": {frazioni[joint]},')
    print('}))') 

# ── POSA APERTA ──────────────────────────────────────────
print("\n" + "="*50)
print("  POSA APERTA")
print("="*50)

# Disabilita torque PRIMA di chiedere di muovere
hand.disable_torque()
print("✅ Torque DISABILITATO — puoi muovere le dita liberamente.")
input("   Porta la mano nella posizione APERTA, poi premi ENTER...")

# Riabilita torque solo per leggere
hand.enable_torque()
hand.set_control_mode('current_based_position')
import time
time.sleep(0.3)  # piccola pausa per stabilizzarsi

frazioni_open = leggi_frazioni(hand)
stampa_pose("OPEN POSITION", frazioni_open)

# ── POSA CHIUSA ──────────────────────────────────────────
print("\n" + "="*50)
print("  POSA CHIUSA")
print("="*50)

hand.disable_torque()
print("✅ Torque DISABILITATO — puoi muovere le dita liberamente.")
input("   Porta la mano nella posizione CHIUSA, poi premi ENTER...")

hand.enable_torque()
hand.set_control_mode('current_based_position')
time.sleep(0.3)

frazioni_close = leggi_frazioni(hand)
stampa_pose("CLOSE POSITION", frazioni_close)

# ── OUTPUT FINALE ─────────────────────────────────────────
print("\n\n" + "="*60)
print("  COPIA QUESTO NEL TUO SCRIPT:")
print("="*60)
stampa_pose("open_pos", frazioni_open)
stampa_pose("closed_pos", frazioni_close)

shutdown_hand(hand)