# JGB37-520 encoder motors (mecanum)

Photos: `encoder_wiring.jpg`, `JGB37-520-178_spec.jpg`, `encoder_wiring.jpg`.

## Spec (this rover)

| Item | Value |
|------|--------|
| Model | JGB37-520 |
| Supply | **12 V** |
| Gearbox | **56:1** |
| Free speed | **178 rpm** @ 12 V |
| Encoder | dual Hall A/B, **11 pulses / motor revolution** |
| Counts / gearbox rev | ~`11 × 56 = 616` per channel (more if quadrature edges) |

## Motor cable colors (from `encoder_wiring.jpg`)

Physical ribbon order on the motor lead:

| Order | Color | Function |
|------:|-------|----------|
| 1 | **Red** | Motor power **+** |
| 2 | **White** | Motor power **−** (swap with red to reverse rotation) |
| 3 | **Yellow** | Encoder phase A (11 PPR on motor shaft) |
| 4 | **Green** | Encoder phase B |
| 5 | **Blue** | Encoder power **+** (3.3–5 V) — **do not reverse** |
| 6 | **Black** | Encoder power **−** (GND) — **do not reverse** |

## Yahboom ROS board 6-pin (Motor1..Motor4)

Silk on the board (left → right on each white connector):

| Pin | Board silk | Must connect to |
|----:|------------|-----------------|
| 1 | **M+** | Motor **Red** |
| 2 | **M−** | Motor **White** |
| 3 | **GND** | Encoder **Black** |
| 4 | **3V3** | Encoder **Blue** |
| 5 | **HA** | Encoder **Yellow** (or Green — swap only flips count direction) |
| 6 | **HB** | Encoder **Green** (or Yellow) |

**You cannot plug the motor ribbon 1:1 in color order.**  
Ribbon is `R W Y G Blu Blk`, board wants `R W Blk Blu Y G`.

```
Motor ribbon:  Red  White  Yellow  Green  Blue  Black
Board wants:   M+   M-     GND     3V3    HA    HB
So map to:     Red  White  Black   Blue   Yellow Green
```

Swapping only Yellow↔Green never fixes “encoders stuck at 0”.  
Wrong Blue/Black (encoder supply) = dead encoder. Wrong M+/M− = motor does not spin.

## Power (why IMU works but motors do not)

| Supply | What works |
|--------|------------|
| USB Micro « Connect USB » only | MCU, beep, **IMU**, serial — **not** motor drivers |
| **DC 6–13 V IN** + board **ON** switch | Motors + encoder 3.3 V + battery telemetry |

`set_car_type` / mecanum is **not** required for open-loop `set_motor` bench. Use it later for `set_car_motion`.

Check in the bench **ping**: battery should read roughly your pack voltage (e.g. ~12 V). If **0.0 V**, motors will not move.

## Channel map (our rover)

| Wheel | Connector |
|-------|-----------|
| Front right | Motor **1** |
| Front left | Motor **2** |
| Rear right | Motor **3** |
| Rear left | Motor **4** |

Only M1/M2 wired is fine for testing those two.

## Polarity calibration (do this once)

Rosmaster has **no per-motor invert** for closed-loop `set_car_motion`. Match hardware to the firmware convention:

**Rule:** positive PWM (`fwd` in the bench) must spin the wheel in the **robot-forward** direction, and the encoder count must **increase**.

For each motor M1..M4:

1. Mark an arrow on the chassis = robot forward for that corner (mecanum rollers matter).
2. Bench → that motor **fwd**.  
   - Wrong way → swap **Red ↔ White** (M+/M−).  
   - Right way → leave power wires.
3. Bench **fwd** again and watch the encoder.  
   - Count **decreases** → swap **Yellow ↔ Green** (HA/HB).  
   - Count **increases** → done.

Notes:

- Swapping Red/White reverses the wheel **and** the encoder together (command↔encoder link stays the same).
- Swapping Yellow/Green only flips the count sign (use this after motor direction is correct).
- Left/right motors often look “opposite” when you stare at the gearbox from outside — judge by the **robot**, not the motor can.
- Typical on a mirrored mecanum: you end up with Red/White swapped on one side (or Y/G on one side). That is normal.

After all four pass: `fwd` → robot-forward + encoder up → closed-loop PID will track. If encoder sign stays wrong, PID fights the motor.

## Bench

```powershell
.\tools\yahboom_bench.ps1 -Port COM15
```

1. Ping → confirm battery &gt; 6 V and beep.  
2. Fix wiring to the table above.  
3. Motor submenu → M1/M2 fwd (wheels off ground).  
4. Watch encoders while motor spins or while turning the shaft by hand.
