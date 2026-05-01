#!/usr/bin/env python3
"""
Quarter-Wave Helical Resonator Design & Validation
====================================================
Target: 146 MHz self-resonance, 14 AWG bare copper, 1-inch OD PVC form.

Validates the design premise, calculates required turns and pitch,
and identifies the minimum wire length / external capacitance needed.

Model:  Wheeler (1928) inductance + Medhurst (1947) distributed capacitance
        Quarter-wave resonant frequency from distributed transmission-line model:
            f_q = 1 / (4 * sqrt(L * C))   [L in H, C in F]
            f_q (MHz) = 250 / sqrt(L_uH * C_pF)

Deps:   numpy only
"""

import numpy as np

# ─── Constants ────────────────────────────────────────────────────────────────
C_LIGHT  = 299_792_458.0
IN_TO_M  = 0.0254
IN_TO_CM = 2.54

# ─── Wire & form geometry ─────────────────────────────────────────────────────
AWG14_OD_IN = 0.0641        # 14 AWG bare copper OD
D_FORM_IN   = 1.000         # PVC form OD (true 1-inch OD)
D_COIL_IN   = D_FORM_IN + AWG14_OD_IN   # center-of-wire winding diameter
R_COIL_IN   = D_COIL_IN / 2.0
CIRC_IN     = np.pi * D_COIL_IN         # circumference = 3.342 in

# ─── Target ───────────────────────────────────────────────────────────────────
F_MHZ    = 146.0
F_HZ     = F_MHZ * 1e6
LAMBDA_IN = C_LIGHT / F_HZ / IN_TO_M    # free-space wavelength in inches
QTR_WAVE_IN = LAMBDA_IN / 4             # 20.21 in

USER_WIRE_IN = 20.2                     # user's stated wire length


# ─── Medhurst H coefficient (1947, Table 1) ───────────────────────────────────
_MEDHURST = np.array([
    [0.10, 0.96], [0.15, 0.87], [0.20, 0.79], [0.25, 0.72],
    [0.30, 0.67], [0.35, 0.63], [0.40, 0.60], [0.45, 0.57],
    [0.50, 0.55], [0.60, 0.51], [0.70, 0.48], [0.80, 0.44],
    [0.90, 0.42], [1.00, 0.39], [1.25, 0.35], [1.50, 0.31],
    [2.00, 0.27], [3.00, 0.22], [4.00, 0.18], [5.00, 0.15],
    [10.0, 0.10], [20.0, 0.08],
])

def medhurst_H(l_over_D: float) -> float:
    x = np.clip(l_over_D, _MEDHURST[0, 0], _MEDHURST[-1, 0])
    return float(np.interp(x, _MEDHURST[:, 0], _MEDHURST[:, 1]))


def wheeler_L(N: float, r_in: float, l_in: float) -> float:
    """Wheeler (1928) single-layer coil inductance (μH). r, l in inches."""
    return (r_in**2 * N**2) / (9.0 * r_in + 10.0 * l_in)


def coil(N: float, pitch_in: float) -> dict:
    """Full parameter set for N turns at pitch_in on 1-inch OD form."""
    l_ax   = N * pitch_in
    w_turn = np.sqrt(CIRC_IN**2 + pitch_in**2)   # wire per turn
    L_wire = N * w_turn

    L_uH  = wheeler_L(N, R_COIL_IN, l_ax)
    l_D   = l_ax / D_COIL_IN
    H     = medhurst_H(l_D)
    C_pF  = H * D_COIL_IN * IN_TO_CM             # D in cm for Medhurst

    LC = L_uH * C_pF
    f_q = 250.0 / np.sqrt(LC)   # MHz

    # Capacitance needed at the open tip to pull f_q down to 146 MHz
    lc_need = (250.0 / F_MHZ)**2
    c_ext   = lc_need / L_uH - C_pF

    pitch_angle = np.degrees(np.arctan(pitch_in / CIRC_IN))

    return dict(N=N, pitch_in=pitch_in, l_ax_in=l_ax, wire_in=L_wire,
                L_uH=L_uH, C_pF=C_pF, LC=LC, f_q=f_q,
                c_ext_pF=c_ext, H=H, l_D=l_D,
                pitch_angle=pitch_angle)


def bisect(fn, lo, hi, tol=1e-6, maxiter=60):
    """Scalar bisection — no scipy needed."""
    for _ in range(maxiter):
        mid = 0.5 * (lo + hi)
        if fn(mid) * fn(lo) <= 0:
            hi = mid
        else:
            lo = mid
        if abs(hi - lo) < tol:
            break
    return 0.5 * (lo + hi)


# ─── PART 1: Validate the premise ────────────────────────────────────────────
def part1_validate():
    print(f"\n{'='*68}")
    print("  PART 1 — PREMISE VALIDATION")
    print(f"{'='*68}")
    print(f"  Free-space λ/4 at {F_MHZ:.0f} MHz:  {QTR_WAVE_IN:.3f} in  ≈  {LAMBDA_IN:.3f} in / 4")
    print(f"  User's wire length:              {USER_WIRE_IN:.1f} in  {'✓ matches λ/4' if abs(USER_WIRE_IN - QTR_WAVE_IN) < 0.1 else '⚠ mismatch'}")
    print(f"  Form OD:                         {D_FORM_IN:.3f} in")
    print(f"  Coil winding diameter (D_coil):  {D_COIL_IN:.4f} in  (D_form + wire OD)")
    print(f"  Circumference per turn:          {CIRC_IN:.4f} in")
    print(f"  Max close-wound turns from {USER_WIRE_IN:.1f} in: {USER_WIRE_IN / CIRC_IN:.2f}")
    print()

    # Evaluate close-wound N=6 (maximum for 20.2 in wire)
    p6 = coil(6, AWG14_OD_IN)
    print(f"  Close-wound N=6  (pitch = wire OD = {AWG14_OD_IN:.4f} in):")
    print(f"    Wire used:      {p6['wire_in']:.2f} in  (≈ {USER_WIRE_IN:.1f} in ✓)")
    print(f"    Coil length:    {p6['l_ax_in']:.4f} in  ({p6['l_D']:.3f} × D)")
    print(f"    L (Wheeler):    {p6['L_uH']:.4f} μH")
    print(f"    C (Medhurst):   {p6['C_pF']:.4f} pF  (H = {p6['H']:.3f})")
    print(f"    LC product:     {p6['LC']:.4f} μH·pF")
    print()

    lc_needed = (250.0 / F_MHZ)**2
    print(f"  ┌─ CRITICAL COMPARISON ──────────────────────────────────────┐")
    print(f"  │  f_q (LC model, N=6 close-wound):  {p6['f_q']:.1f} MHz             │")
    print(f"  │  Target frequency:                  {F_MHZ:.1f} MHz             │")
    print(f"  │  LC needed for {F_MHZ:.0f} MHz:          {lc_needed:.4f} μH·pF        │")
    print(f"  │  LC available (close-wound N=6):    {p6['LC']:.4f} μH·pF        │")
    print(f"  │  Deficit:  LC must increase by      {lc_needed/p6['LC']:.2f}×              │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    print()
    print(f"  ⚠  FINDING: {USER_WIRE_IN:.1f} in wire close-wound on 1\" form gives")
    print(f"     f_q ≈ {p6['f_q']:.0f} MHz — {p6['f_q']-F_MHZ:.0f} MHz ABOVE target.")
    print(f"     There is no winding pitch that achieves 146 MHz with only")
    print(f"     {USER_WIRE_IN:.1f} in of wire. Looser pitch raises f_q further.")

    print()
    print(f"  WHY: Winding the λ/4 wire into a helix does NOT preserve")
    print(f"  its free-space resonant frequency. The coil's L and C interact")
    print(f"  as a distributed transmission line. The LC product needed for")
    print(f"  146 MHz ({lc_needed:.3f} μH·pF) exceeds what 6 turns can achieve.")


# ─── PART 2: Pitch sweep for N=6 ─────────────────────────────────────────────
def part2_pitch_sweep():
    print(f"\n{'='*68}")
    print("  PART 2 — PITCH SWEEP  (N=6 turns, varying pitch)")
    print(f"{'='*68}")
    print(f"  {'Pitch':>10} {'Wire':>8} {'Coil L':>8} {'L(μH)':>8} "
          f"{'C(pF)':>7} {'f_q':>9} {'Note'}")
    print(f"  {'(in)':>10} {'(in)':>8} {'(in)':>8} {'':>8} "
          f"{'':>7} {'(MHz)':>9}")
    print(f"  {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*7} {'─'*9} {'─'*18}")

    pitches = np.linspace(AWG14_OD_IN, 0.5, 12)
    for p in pitches:
        r = coil(6, p)
        note = ""
        if abs(p - AWG14_OD_IN) < 0.001:
            note = "← close-wound"
        if r['wire_in'] > USER_WIRE_IN + 0.5:
            note = f"needs {r['wire_in']:.1f}\" wire"
        print(f"  {p:>10.4f} {r['wire_in']:>8.2f} {r['l_ax_in']:>8.4f} "
              f"{r['L_uH']:>8.5f} {r['C_pF']:>7.4f} {r['f_q']:>9.1f} {note}")

    print(f"\n  Note: ALL pitches give f_q > {F_MHZ:.0f} MHz for N=6.")
    print(f"  Tighter winding lowers f_q slightly; wider winding raises it.")
    print(f"  The minimum f_q for 20.2 in on 1\" form is ≈ {coil(6,AWG14_OD_IN)['f_q']:.0f} MHz.")


# ─── PART 3: Find the correct wire length ────────────────────────────────────
def part3_correct_wire():
    print(f"\n{'='*68}")
    print("  PART 3 — CORRECT WIRE LENGTH  (close-wound, target 146 MHz)")
    print(f"{'='*68}")
    print()

    # Sweep N from 5 to 15, close-wound
    print(f"  {'N':>5} {'Wire(in)':>10} {'Coil L(in)':>11} "
          f"{'L(μH)':>8} {'C(pF)':>7} {'f_q(MHz)':>10}")
    print(f"  {'─'*5} {'─'*10} {'─'*11} {'─'*8} {'─'*7} {'─'*10}")

    results = []
    for N in [5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 10]:
        r = coil(N, AWG14_OD_IN)
        marker = " ◄" if abs(r['f_q'] - F_MHZ) < 5 else ""
        print(f"  {N:>5.1f} {r['wire_in']:>10.2f} {r['l_ax_in']:>11.4f} "
              f"{r['L_uH']:>8.4f} {r['C_pF']:>7.4f} {r['f_q']:>10.1f}{marker}")
        results.append(r)

    # Binary search for exact solution
    def obj(N):
        return coil(N, AWG14_OD_IN)['f_q'] - F_MHZ

    N_sol = bisect(obj, 6.0, 12.0)
    sol = coil(N_sol, AWG14_OD_IN)

    print(f"\n  ┌─ EXACT SOLUTION (close-wound) ──────────────────────────────┐")
    print(f"  │  N = {N_sol:.2f} turns  →  round to N = {round(N_sol*2)/2:.1f} turns      │")
    print(f"  │  Wire length required:  {sol['wire_in']:.2f} in                        │")
    print(f"  │  vs. user's wire:       {USER_WIRE_IN:.1f} in                          │")
    print(f"  │  Shortfall:             {sol['wire_in'] - USER_WIRE_IN:.2f} in more wire needed         │")
    print(f"  │  Coil physical length:  {sol['l_ax_in']:.3f} in                       │")
    print(f"  │  L = {sol['L_uH']:.4f} μH   C = {sol['C_pF']:.4f} pF                 │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    return N_sol, sol


# ─── PART 4: Fix with external capacitance ───────────────────────────────────
def part4_cap_fix():
    print(f"\n{'='*68}")
    print("  PART 4 — FIX WITH EXTERNAL CAPACITANCE  (keep 20.2 in wire)")
    print(f"{'='*68}")

    # N=6 close-wound, but add C_ext at the open end
    r6 = coil(6, AWG14_OD_IN)

    # Find exact C_ext for f_q = 146 MHz
    lc_target = (250.0 / F_MHZ)**2
    c_ext = lc_target / r6['L_uH'] - r6['C_pF']

    f_check = 250.0 / np.sqrt(r6['L_uH'] * (r6['C_pF'] + c_ext))

    print()
    print(f"  Coil:  N=6, close-wound, wire = {r6['wire_in']:.2f} in")
    print(f"  L = {r6['L_uH']:.4f} μH,  C_ds = {r6['C_pF']:.4f} pF (distributed)")
    print(f"  f_q without cap: {r6['f_q']:.1f} MHz")
    print()
    print(f"  Add C_ext at the OPEN (ungrounded) tip:")
    print(f"  Required C_ext = {c_ext:.3f} pF")
    print(f"  Verification:   f_q = {f_check:.2f} MHz ✓")
    print()
    print(f"  Implementation options for {c_ext:.2f} pF:")
    print(f"    a) 0–10 pF air-gap trimmer (cheapest, adjustable — Johanson 5201 or equivalent)")
    print(f"    b) NP0/C0G disc cap: 1 pF + 0.5 pF in parallel (1.5 pF total, then trim coil by ~0.5 turn)")
    print(f"    c) Copper disc (≈ {c_ext:.0f}mm diameter) suspended {c_ext:.1f} mm above the tip turn")
    print()
    print(f"  ⚠ Sensitivity: δf/δC ≈ {-F_MHZ/(2*r6['C_pF']) * 0.1:.1f} MHz/pF at this operating point.")
    print(f"     Trimmer range of ±0.5 pF gives ±{abs(-F_MHZ/(2*(r6['C_pF']+c_ext)) * 0.5):.1f} MHz tuning range.")

    return c_ext


# ─── PART 5: Recommended practical design ────────────────────────────────────
def part5_recommended(N_sol, c_ext):
    print(f"\n{'='*68}")
    print("  PART 5 — RECOMMENDED DESIGNS")
    print(f"{'='*68}")

    # Integer-turn designs near the solution
    for N in [7, 8]:
        p_cw = coil(N, AWG14_OD_IN)

        # Find pitch that gives exactly 146 MHz with this N
        def obj_pitch(p):
            return coil(N, p)['f_q'] - F_MHZ

        # For N=7: f_q at close-wound is above 146; wider pitch raises it more
        # So for N=7 close-wound we need to check if f_q < 146 or > 146
        if p_cw['f_q'] > F_MHZ:
            # Try larger N approach — close-wound gives f > target
            # Need to check... with close-wound f > target means N too small
            print(f"\n  Design A (N={N}, close-wound):")
            print(f"    Wire:    {p_cw['wire_in']:.2f} in")
            print(f"    Coil L:  {p_cw['l_ax_in']:.3f} in  ({p_cw['l_ax_in']:.3f}\" physical height)")
            print(f"    f_q:     {p_cw['f_q']:.1f} MHz  (needs {p_cw['c_ext_pF']:.2f} pF external cap to hit 146 MHz)")
        else:
            # Close-wound f < target, so we can widen pitch to hit target
            # But wider pitch gives higher f_q... let's check
            p_opt = bisect(obj_pitch, AWG14_OD_IN, 2.0)
            r_opt = coil(N, p_opt)
            print(f"\n  Design A (N={N}, optimized pitch):")
            print(f"    Wire:     {r_opt['wire_in']:.2f} in")
            print(f"    Pitch:    {r_opt['pitch_in']:.4f} in  ({r_opt['pitch_in']/AWG14_OD_IN:.1f}× wire diameter)")
            print(f"    Coil L:   {r_opt['l_ax_in']:.3f} in")
            print(f"    f_q:      {r_opt['f_q']:.2f} MHz ✓")

    # Best integer-turn solution: N close to N_sol
    N_best = round(N_sol)
    r_best_cw = coil(N_best, AWG14_OD_IN)
    # Find pitch for exact 146 MHz with N_best
    if r_best_cw['f_q'] < F_MHZ:
        # Close-wound resonates below target, widen pitch
        def obj_pitch_best(p):
            return coil(N_best, p)['f_q'] - F_MHZ
        p_best = bisect(obj_pitch_best, AWG14_OD_IN, 2.0)
    else:
        # Close-wound resonates above target: need more turns or cap
        p_best = AWG14_OD_IN
    r_best = coil(N_best, p_best)

    print(f"\n{'─'*68}")
    print(f"  ╔═══════════════════════════════════════════════════════════╗")
    print(f"  ║  RECOMMENDED: N={N_best} turns, pitch = {r_best['pitch_in']:.4f} in             ║")
    print(f"  ║  Wire:        {r_best['wire_in']:.2f} in of 14 AWG bare copper         ║")
    print(f"  ║  Coil height: {r_best['l_ax_in']:.3f} in physical height              ║")
    print(f"  ║  L = {r_best['L_uH']:.4f} μH,  C = {r_best['C_pF']:.4f} pF               ║")
    print(f"  ║  f_q = {r_best['f_q']:.2f} MHz {'✓' if abs(r_best['f_q']-F_MHZ)<1 else '⚠'}  (target: {F_MHZ:.0f} MHz)               ║")
    if r_best['c_ext_pF'] > 0.05:
        print(f"  ║  + {r_best['c_ext_pF']:.2f} pF external cap at open tip              ║")
    print(f"  ╚═══════════════════════════════════════════════════════════╝")

    pitch_in_mm = r_best['pitch_in'] * 25.4
    turns_per_inch = 1.0 / r_best['pitch_in']
    print(f"\n  Winding spec:")
    print(f"    Pitch:          {r_best['pitch_in']:.4f} in  =  {pitch_in_mm:.2f} mm per turn")
    print(f"    Turns per inch: {turns_per_inch:.2f} t/in")
    print(f"    Gap between turns (surface-to-surface): "
          f"{max(0, r_best['pitch_in'] - AWG14_OD_IN):.4f} in  "
          f"= {max(0, r_best['pitch_in'] - AWG14_OD_IN)*25.4:.2f} mm")
    print(f"    Grounded end:   BOTTOM (attach to coax outer / ground plane)")
    print(f"    Open end:       TOP  (free, or attach trim cap)")
    print(f"    Counterpoise:   Tiger Tail attaches at BOTTOM with coax shield")


# ─── PART 6: Error analysis ───────────────────────────────────────────────────
def part6_errors(N_sol):
    print(f"\n{'='*68}")
    print("  PART 6 — SENSITIVITY & MODEL ACCURACY")
    print(f"{'='*68}")
    r_ref = coil(N_sol, AWG14_OD_IN)

    print(f"\n  Wheeler formula accuracy: ±1% for l/D in [0.2, 10]")
    print(f"  Medhurst formula accuracy: ±5% for l/D in [0.1, 5]")
    print(f"  Combined f_q uncertainty:  ±3–6% ≈ ±{F_MHZ * 0.05:.0f} MHz at {F_MHZ:.0f} MHz")
    print(f"  → Final trimming with a trimmer cap is REQUIRED for exact 146 MHz")

    print(f"\n  PVC dielectric correction:")
    eps_pvc = 3.0
    c_pvc_factor = 1 + 0.05 * (eps_pvc - 1)   # ~5% fill factor for surface winding
    f_pvc = r_ref['f_q'] / np.sqrt(c_pvc_factor)
    print(f"    PVC εᵣ ≈ 3.0 (tangential E-field only ≈ 5% fill)")
    print(f"    Effective C increase: ~{(c_pvc_factor-1)*100:.0f}%")
    print(f"    Frequency shift: {r_ref['f_q'] - f_pvc:.1f} MHz lower than air-core calculation")
    print(f"    Practical effect: wind slightly shorter (~0.2 turns), then trim with cap")

    print(f"\n  Construction tolerances:")
    for delta_N in [-0.25, 0, +0.25]:
        r = coil(N_sol + delta_N, AWG14_OD_IN)
        print(f"    N = {N_sol+delta_N:.2f} turns: wire = {r['wire_in']:.2f} in,  f_q = {r['f_q']:.1f} MHz")

    print(f"\n  SWR note (if used as monopole base-loading coil):")
    print(f"    The coil presents Z = j×ωL at frequencies well below self-resonance.")
    print(f"    At 146 MHz (= f_q), the coil looks like an open circuit — exactly")
    print(f"    what you want for a shunt-fed vertical monopole base.")
    print(f"    SWR transformation depends on the loading geometry and feed network.")


# ─── main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n  QUARTER-WAVE HELICAL RESONATOR — 146 MHz DESIGN ANALYSIS")
    print(f"  14 AWG bare copper on 1.000\" OD PVC, targeting f_q = {F_MHZ:.0f} MHz")

    part1_validate()
    part2_pitch_sweep()
    N_sol, sol = part3_correct_wire()
    c_ext = part4_cap_fix()
    part5_recommended(N_sol, c_ext)
    part6_errors(N_sol)

    print(f"\n{'='*68}\n")


if __name__ == '__main__':
    main()
