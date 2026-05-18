import time
from common import connect_hand, create_hand, shutdown_hand

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)

hand.enable_torque()
hand.set_control_mode('current_based_position')

results = {}

for motor_id in range(1, 17):
    risposta = input(f"\nMotor {motor_id} — premi ENTER per muovere (+0.3 rad), 's' per skippare: ")
    if risposta.strip().lower() == 's':
        continue

    current = hand.get_motor_pos(as_dict=True)
    hand._set_motor_pos({motor_id: current[motor_id] + 0.3})
    time.sleep(1.5)

    joint = input(f"  Quale joint si è mosso? (es. thumb_mcp, index_pip...): ")
    direzione = input(f"  Si è FLESSO (chiuso) o ESTESO (aperto)? (f/e): ")

    segno = "-" if direzione.strip().lower() == 'e' else ""
    results[joint] = f"{segno}{motor_id}"

    hand._set_motor_pos({motor_id: current[motor_id]})
    time.sleep(0.5)

print("\n\njoint_to_motor_map:")
for joint, motor in results.items():
    print(f"  {joint}: {motor}")

shutdown_hand(hand)