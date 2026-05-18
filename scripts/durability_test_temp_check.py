import time
from datetime import datetime
from common import connect_hand, create_hand, shutdown_hand
from orca_core import OrcaJointPositions

# ── Parametri ─────────────────────────────────────────────
NUM_STEPS_MOVE = 50
STEP_SIZE_MOVE = 0.01
HOLD_TIME      = 3.0
DURATION       = 20 * 60 #10x60
MAX_TEMP       = 70
TEMP_CHECK_INTERVAL = 5.0

# ── Colori terminale ──────────────────────────────────────
RST    = "\033[0m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

def temp_color(pct):
    if pct >= 90:
        return RED 
    elif pct >= 70:
        return YELLOW
    return GREEN

def print_temp_table(hand, temps, cicli, remaining):
    motor_to_joint = hand.config.motor_to_joint_dict
    fingers = ['thumb', 'index', 'middle', 'ring', 'pinky', 'wrist']
    grouped = {f: [] for f in fingers}
    for mid, t in temps.items():
        joint = motor_to_joint.get(mid, f"motor_{mid}")
        finger = joint.split('_')[0]
        if finger in grouped:
            grouped[finger].append((joint, mid, t))

    print("\033[2J\033[H", end="")
    print(f"{BOLD}  ORCA Hand — Durability Test{RST}")
    print(f"  Cicli: {cicli}  |  Tempo rimasto: {int(remaining)}s\n")
    print(f"  {BOLD}{'Joint':<14} {'Motor':>5} {'Temp':>6} {'%Max':>6}  {'':>10}{RST}")
    print(f"  {'─' * 48}")

    for finger in fingers:
        joints = grouped[finger]
        if not joints:
            continue
        for joint, mid, t in joints:
            pct = t / MAX_TEMP * 100
            c = temp_color(pct)
            bar_len = int(pct / 100 * 10)
            bar = f"{c}{'█' * bar_len}{DIM}{'░' * (10 - bar_len)}{RST}"
            print(f"  {joint:<14} {mid:>5} {c}{t:>4.0f}°C {pct:>5.0f}%{RST}  {bar}")

    print(f"  {'─' * 48}")
    max_t = max(temps.values())
    max_pct = max_t / MAX_TEMP * 100
    c = temp_color(max_pct)
    print(f"  {'Peak':<14} {'':>5} {c}{max_t:>4.0f}°C {max_pct:>5.0f}%{RST}\n")

def salva_report(hand, cicli_totali, temp_history, duration_effettiva):
    motor_to_joint = hand.config.motor_to_joint_dict
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_durability_{timestamp}.txt"

    with open(filename, 'w') as f:
        f.write("="*60 + "\n")
        f.write("  ORCA HAND — DURABILITY TEST REPORT\n")
        f.write(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")

        f.write(f"Durata effettiva:  {duration_effettiva:.1f}s ({duration_effettiva/60:.1f} min)\n")
        f.write(f"Cicli completati:  {cicli_totali}\n")
        if duration_effettiva > 0:
            f.write(f"Frequenza cicli:   {cicli_totali/duration_effettiva*60:.1f} cicli/min\n\n")

        f.write("TEMPERATURE MOTORI (°C)\n")
        f.write(f"{'Joint':<16} {'Motor':>5} {'Min':>6} {'Max':>6} {'Media':>7} {'%Max':>6}\n")
        f.write("-"*50 + "\n")
        for motor_id in sorted(temp_history.keys()):
            temps = temp_history[motor_id]
            if not temps:
                continue
            joint = motor_to_joint.get(motor_id, f"motor_{motor_id}")
            t_min = min(temps)
            t_max = max(temps)
            t_avg = sum(temps) / len(temps)
            pct = t_max / MAX_TEMP * 100
            warning = " ⚠️" if pct >= 70 else ""
            f.write(f"{joint:<16} {motor_id:>5} {t_min:>6.1f} {t_max:>6.1f} {t_avg:>7.1f} {pct:>5.1f}%{warning}\n")

        f.write("\nLIMITI CALIBRAZIONE\n")
        f.write(f"{'Joint':<16} {'Motor':>5} {'Min':>8} {'Max':>8} {'Range':>8}\n")
        f.write("-"*50 + "\n")
        for motor_id, limits in sorted(hand.calibration.motor_limits_dict.items()):
            joint = motor_to_joint.get(motor_id, f"motor_{motor_id}")
            if limits[0] is not None and limits[1] is not None:
                rng = limits[1] - limits[0]
                f.write(f"{joint:<16} {motor_id:>5} {limits[0]:>8.3f} {limits[1]:>8.3f} {rng:>8.3f}\n")

        f.write("\nPOSIZIONI FINALI MOTORI\n")
        f.write(f"{'Joint':<16} {'Motor':>5} {'Pos (rad)':>10}\n")
        f.write("-"*35 + "\n")
        motor_pos = hand.get_motor_pos(as_dict=True)
        for motor_id, pos in sorted(motor_pos.items()):
            joint = motor_to_joint.get(motor_id, f"motor_{motor_id}")
            f.write(f"{joint:<16} {motor_id:>5} {pos:>10.4f}\n")

    print(f"\n✅ Report salvato: {filename}")

# ── Setup ─────────────────────────────────────────────────
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
    hand.set_joint_positions(pose, num_steps=NUM_STEPS_MOVE, step_size=STEP_SIZE_MOVE)

hand = create_hand("orca_core/models/v1/orcahand_right/config.yaml", use_mock=False)
connect_hand(hand)
hand.enable_torque()
hand.set_control_mode('current_based_position')

# ── open_pos ──
open_pos = pose_from_fractions(hand, {
    # thumb
    "thumb_abd": 0.5170000195503235,
    "thumb_mcp": 0.27300000190734863,
    "thumb_pip": 0.3540000021457672,
    "thumb_dip": 0.09600000083446503,
    # index
    "index_abd": 0.6330000162124634,
    "index_mcp": 0.20900000631809235,
    "index_pip": 0.15600000321865082,
    # middle
    "middle_abd": 0.46700000762939453,
    "middle_mcp": 0.18799999356269836,
    "middle_pip": 0.16200000047683716,
    # ring
    "ring_abd": 0.4749999940395355,
    "ring_mcp": 0.2290000021457672,
    "ring_pip": 0.16599999368190765,
    # pinky
    "pinky_abd": 0.5410000085830688,
    "pinky_mcp": 0.19699999690055847,
    "pinky_pip": 0.16300000250339508,
    # wrist
    "wrist": 0.47099998593330383,
})

# ── closed_pos ──
closed_pos = pose_from_fractions(hand, {
    # thumb
    "thumb_abd": 0.6380000114440918,
    "thumb_mcp": 0.9539999961853027,
    "thumb_pip": 0.7919999957084656,
    "thumb_dip": 0.07599999755620956,
    # index
    "index_abd": 0.4620000123977661,
    "index_mcp": 0.6159999966621399,
    "index_pip": 0.824999988079071,
    # middle
    "middle_abd": 0.5360000133514404,
    "middle_mcp": 0.8360000252723694,
    "middle_pip": 0.8930000066757202,
    # ring
    "ring_abd": 0.5460000038146973,
    "ring_mcp": 0.8209999799728394,
    "ring_pip": 0.9509999752044678,
    # pinky
    "pinky_abd": 0.6209999918937683,
    "pinky_mcp": 0.6859999895095825,
    "pinky_pip": 0.8240000009536743,
    # wrist
    "wrist": 0.5230000019073486,
})

poses = [
    (open_pos,   "APERTA"),
    (closed_pos, "CHIUSA"),
]

# ── Loop principale ───────────────────────────────────────
temp_history = {mid: [] for mid in hand.config.motor_ids}
cicli_totali = 0
last_temp_check = 0.0
start_time = time.time()

print(f"Avvio durability test — {DURATION//60} minuti. Ctrl+C per interrompere.")

try:
    cycle = 0
    while True:
        remaining = DURATION - (time.time() - start_time)
        if remaining <= 0:
            break

        now = time.monotonic()
        if now - last_temp_check >= TEMP_CHECK_INTERVAL:
            last_temp_check = now
            temps = hand.get_motor_temp(as_dict=True)
            for mid, t in temps.items():
                if mid in temp_history:
                    temp_history[mid].append(t)
            print_temp_table(hand, temps, cicli_totali, remaining)

        pose, label = poses[cycle % len(poses)]
        print(f"  [{int(remaining):3d}s left]  {label}")
        go_to(hand, pose, label)
        cycle += 1

        if cycle % 2 == 0:
            cicli_totali += 1

        hold_end = min(time.time() + HOLD_TIME, start_time + DURATION)
        while time.time() < hold_end:
            time.sleep(0.1)

    print("\nTest completato.")

except KeyboardInterrupt:
    print("\nTest interrotto dall'utente.")

finally:
    duration_effettiva = time.time() - start_time
    salva_report(hand, cicli_totali, temp_history, duration_effettiva)
    print("Torno in neutrale...")
    neutral = dict(hand.config.neutral_position)
    neutral.pop("wrist", None)
    hand.set_joint_positions(
        OrcaJointPositions.from_dict(neutral),
        num_steps=200,
        step_size=0.02
    )
    shutdown_hand(hand)