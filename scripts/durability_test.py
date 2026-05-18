import time
from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)

hand.enable_torque()
hand.set_control_mode('current_based_position')

# Parametri movimento — modifica questi per cambiare velocità
NUM_STEPS_MOVE = 150   # più alto = più fluido
STEP_SIZE_MOVE = 0.02  # più alto = più lento
HOLD_TIME      = 3.0   # secondi di pausa tra una posa e l'altra
DURATION       = 10 * 60  # durata totale

def pose_from_fractions(hand, fractions):
    pose = dict(hand.config.neutral_position)
    for joint, fraction in fractions.items():
        if joint not in hand.config.joint_roms_dict:
            continue
        joint_min, joint_max = hand.config.joint_roms_dict[joint]
        pose[joint] = joint_min + fraction * (joint_max - joint_min)
    return OrcaJointPositions.from_dict(pose)

def remove_wrist(pose):
    d = pose.as_dict()
    d.pop("wrist", None)
    return OrcaJointPositions.from_dict(d)

def go_to(hand, pose, label):
    print(f"  → {label}")
    hand.set_joint_positions(pose, num_steps=NUM_STEPS_MOVE, step_size=STEP_SIZE_MOVE)

# ── open_pos ──
open_pos = remove_wrist(pose_from_fractions(hand, {
    # thumb
    "thumb_abd": 0.6610000133514404,
    "thumb_mcp": 0.44200000166893005,
    "thumb_pip": 0.40400001406669617,
    "thumb_dip": 0.16099999845027924,
    # index
    "index_abd": 0.5899999737739563,
    "index_mcp": 0.20499999821186066,
    "index_pip": 0.16200000047683716,
    # middle
    "middle_abd": 0.4790000021457672,
    "middle_mcp": 0.19099999964237213,
    "middle_pip": 0.164000004529953,
    # ring
    "ring_abd": 1.0,
    "ring_mcp": 0.17299999296665192,
    "ring_pip": 0.15399999916553497,
    # pinky
    "pinky_abd": 0.5600000023841858,
    "pinky_mcp": 0.1940000057220459,
    "pinky_pip": 0.16200000047683716,
    # wrist
    "wrist": 0.6209999918937683,
}))

# ── closed_pos ──
closed_pos = remove_wrist(pose_from_fractions(hand, {
    # thumb
    "thumb_abd": 0.8970000147819519,
    "thumb_mcp": 0.9739999771118164,
    "thumb_pip": 0.8429999947547913,
    "thumb_dip": 0.16300000250339508,
    # index
    "index_abd": 0.5040000081062317,
    "index_mcp": 0.8259999752044678,
    "index_pip": 0.7720000147819519,
    # middle
    "middle_abd": 0.5360000133514404,
    "middle_mcp": 0.9459999799728394,
    "middle_pip": 0.8410000205039978,
    # ring
    "ring_abd": 1.0,
    "ring_mcp": 0.9160000085830688,
    "ring_pip": 0.8299999833106995,
    # pinky
    "pinky_abd": 0.6859999895095825,
    "pinky_mcp": 0.6899999976158142,
    "pinky_pip": 0.7379999756813049,
    # wrist
    "wrist": 0.5839999914169312,
}))

# # ── Definisci qui le tue pose con i valori corretti ──────────────────
# open_pos = remove_wrist(pose_from_fractions(hand, {
#     # Dita aperte
#     "index_mcp":  0.15, "index_pip":  0.10,
#     "middle_mcp": 0.15, "middle_pip": 0.10,
#     "ring_mcp":   0.15, "ring_pip":   0.10,
#     "pinky_mcp":  0.15, "pinky_pip":  0.10,
#     # Pollice aperto — modifica questi in base al tuo test empirico
#     "thumb_abd":  0.20,
#     "thumb_mcp":  0.15,
#     "thumb_pip":  0.15,
#     "thumb_dip":  0.20,
# }))

# closed_pos = remove_wrist(pose_from_fractions(hand, {
#     # Dita chiuse
#     "index_mcp":  0.85, "index_pip":  0.90,
#     "middle_mcp": 0.85, "middle_pip": 0.90,
#     "ring_mcp":   0.85, "ring_pip":   0.90,
#     "pinky_mcp":  0.85, "pinky_pip":  0.90,
#     # Pollice chiuso — modifica questi in base al tuo test empirico
#     "thumb_abd":  0.80,
#     "thumb_mcp":  0.85,
#     "thumb_pip":  0.85,
#     "thumb_dip":  0.80,
# }))

# Puoi aggiungere altre pose intermedie qui
# meta_pos = remove_wrist(pose_from_fractions(hand, {...}))
# ─────────────────────────────────────────────────────────────────────

poses = [
    (open_pos,   "APERTA"),
    (closed_pos, "CHIUSA"),
    # Aggiungi altre pose qui se vuoi una sequenza più complessa
    # (meta_pos, "META"),
]


print(f"Avvio ciclo per {DURATION//60} minuti. Premi Ctrl+C per interrompere.")

try:
    start = time.time()
    cycle = 0
    while True:
        remaining = DURATION - (time.time() - start)
        if remaining <= 0:
            break

        pose, label = poses[cycle % len(poses)]
        print(f"  [{int(remaining):3d}s left]  {label}")
        go_to(hand, pose, label)
        cycle += 1

        hold_end = min(time.time() + HOLD_TIME, start + DURATION)
        while time.time() < hold_end:
            time.sleep(0.1)

    print("Test completato.")

except KeyboardInterrupt:
    print("\nTest interrotto dall'utente.")

finally:
    print("Torno in neutrale...")
    neutral = dict(hand.config.neutral_position)
    neutral.pop("wrist", None)
    hand.set_joint_positions(
        OrcaJointPositions.from_dict(neutral),
        num_steps=200,
        step_size=0.02
    )
    shutdown_hand(hand)