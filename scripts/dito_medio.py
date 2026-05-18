from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions
from orca_core.constants import NUM_STEPS, STEP_SIZE

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)

hand.enable_torque()
hand.set_control_mode('current_based_position')

def pose_from_fractions(hand, fractions):
    pose = dict(hand.config.neutral_position)
    for joint, fraction in fractions.items():
        if joint not in hand.config.joint_roms_dict:
            continue
        joint_min, joint_max = hand.config.joint_roms_dict[joint]
        pose[joint] = joint_min + fraction * (joint_max - joint_min)
    return OrcaJointPositions.from_dict(pose)

middle_finger_pose = pose_from_fractions(hand, {
    # Medio su (esteso) → valore ALTO
    "middle_mcp": 0.90,
    "middle_pip": 0.95,
    # Altre dita chiuse → valore BASSO
    "index_mcp":  0.15,
    "index_pip":  0.10,
    "ring_mcp":   0.15,
    "ring_pip":   0.10,
    "pinky_mcp":  0.15,
    "pinky_pip":  0.10,
    # Pollice raccolto
    "thumb_mcp":  0.80,
    "thumb_dip":  0.15,
})

hand.set_joint_positions(middle_finger_pose, num_steps=NUM_STEPS, step_size=STEP_SIZE)

input("Premi ENTER per tornare in neutrale...")
hand.set_neutral_position()
shutdown_hand(hand)