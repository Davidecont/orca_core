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
    # thumb
    "thumb_abd": 0.5860000252723694,
    "thumb_mcp": 0.9729999899864197,
    "thumb_pip": 0.3930000066757202,
    "thumb_dip": 0.35600000619888306,
    # index
    "index_abd": 0.574999988079071,
    "index_mcp": 0.4269999861717224,
    "index_pip": 0.4269999861717224,
    # middle
    "middle_abd": 0.6869999766349792,
    "middle_mcp": 0.22200000286102295,
    "middle_pip": 0.3199999928474426,
    # ring
    "ring_abd": 1.0,
    "ring_mcp": 0.9850000143051147,
    "ring_pip": 0.7889999747276306,
    # pinky
    "pinky_abd": 0.5180000066757202,
    "pinky_mcp": 0.8080000281333923,
    "pinky_pip": 0.843999981880188,
    # wrist
    "wrist": 0.6079999804496765,
})

hand.set_joint_positions(middle_finger_pose, num_steps=NUM_STEPS, step_size=STEP_SIZE)

input("Premi ENTER per tornare in neutrale...")
hand.set_neutral_position()
shutdown_hand(hand)