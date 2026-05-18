import time
from common import connect_hand, create_hand, shutdown_hand

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)

hand.enable_torque()
hand.set_control_mode('current_based_position')

DELTA = 0.5      # spostamento totale
STEPS = 20       # quanti passi per arrivarci
STEP_PAUSE = 0.1 # secondi tra un passo e l'altro (~2 secondi totali)

def muovi_graduale(hand, motor_id, delta, steps, pause):
    current = hand.get_motor_pos(as_dict=True)
    start = current[motor_id]
    for i in range(1, steps + 1):
        target = start + (delta * i / steps)
        hand._set_motor_pos({motor_id: target})
        time.sleep(pause)

def torna_graduale(hand, motor_id, steps, pause):
    current_pos = hand.get_motor_pos(as_dict=True)
    original = hand.get_motor_pos(as_dict=True)[motor_id]
    # torna alla posizione iniziale salvata
    for i in range(1, steps + 1):
        target = current_pos[motor_id] + ((original - current_pos[motor_id]) * i / steps)
        hand._set_motor_pos({motor_id: target})
        time.sleep(pause)

for motor_id in [12]:
    input(f"\nMotor {motor_id} — ENTER per muovere lentamente (+{DELTA} rad totali)...")
    
    start_pos = hand.get_motor_pos(as_dict=True)[motor_id]
    
    muovi_graduale(hand, motor_id, DELTA, STEPS, STEP_PAUSE)
    
    direzione = input("  Il tendine si è TESO o ALLENTATO? (t/a): ")
    
    # Torna alla posizione iniziale
    current = hand.get_motor_pos(as_dict=True)[motor_id]
    for i in range(1, STEPS + 1):
        target = current + ((start_pos - current) * i / STEPS)
        hand._set_motor_pos({motor_id: target})
        time.sleep(STEP_PAUSE)
    
    if direzione.strip().lower() == 'a':
        print(f"  ⚠️  Motor {motor_id} gira al contrario! Devi invertire il segno.")
    else:
        print(f"  ✅ Motor {motor_id} gira nel verso corretto.")

shutdown_hand(hand)