"""Codice per definire neutral position manualmente."""

import math
from common import connect_hand, create_hand, shutdown_hand
import time

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)

hand.disable_torque()
print("✅ Torque DISABILITATO — porta la mano nella posizione neutrale desiderata.")
input("Premi ENTER quando sei soddisfatto...")

hand.enable_torque()
hand.set_control_mode('current_based_position')
time.sleep(0.3)

motor_pos = hand.get_motor_pos(as_dict=True)
motor_to_joint = hand.config.motor_to_joint_dict

print("\nneutral_position da copiare nel config.yaml:")
for joint in hand.config.joint_ids:
    motor_id = abs(hand.config.joint_to_motor_map[joint])
    limits = hand.calibration.motor_limits_dict.get(motor_id, [None, None])
    rom = hand.config.joint_roms_dict.get(joint, [None, None])
    pos = motor_pos.get(motor_id)

    if None in limits or None in rom or pos is None:
        print(f"  {joint}: ???  ← non calibrato")
        continue

    inverted = hand.config.joint_inversion_dict.get(joint, False)
    ratio = hand.calibration.joint_to_motor_ratios_dict.get(motor_id, 0)

    if ratio == 0:
        print(f"  {joint}: ???  ← ratio zero")
        continue

    if inverted:
        joint_val = rom[1] - (pos - limits[0]) / ratio
    else:
        joint_val = rom[0] + (pos - limits[0]) / ratio

    print(f"  {joint}: {round(joint_val, 1)}")

shutdown_hand(hand)