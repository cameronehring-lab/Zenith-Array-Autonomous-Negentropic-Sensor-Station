#!/usr/bin/env python3
"""
Tesla "Extra Coil" — Quarter-Wave Helical Resonator for 146 MHz
=================================================================
Calculates the physical parameters for a self-resonant helical coil
on a 2-inch PVC form using 14 AWG copper wire.

Models:
  1. Wheeler inductance (single-layer solenoid)
  2. Medhurst self-capacitance (empirical)
  3. Helical transmission-line velocity factor
  4. Capacity-hat top-loading for practical Q improvement

Physics note:
  At 146 MHz, λ/4 = 51.3 cm of wire. On a 2" form that's only ~2.6 turns.
  A bare self-resonant coil at VHF has very low Q. Tesla's original extra
  coil operated at ~100 kHz where thousands of turns were practical.
  To make this work at VHF, we add a capacity hat (metal sphere/disc)
  which lowers f_res, allowing more turns and higher Q.

Usage:  python extra_coil.py
Deps:   numpy (required), matplotlib (optional)
"""

import numpy as np
import argparse

# ─── Physical Constants ──────────────────────────────────────────────────────
C = 299_792_458
MU_0 = 4 * np.pi * 1e-7
EPS_0 = 8.854187817e-12
INCH_TO_M = 0.0254
INCH_TO_CM = 2.54

# ─── Wire & Form Parameters ─────────────────────────────────────────────────
WIRE_AWG = 14
WIRE_DIA_IN = 0.0641          # 14 AWG bare diameter (inches)
WIRE_DIA_MM = WIRE_DIA_IN * 25.4  # 1.628 mm
WIRE_DIA_M = WIRE_DIA_IN * INCH_TO_M

# PVC form — 2" Schedule 40
PVC_OD_IN = 2.375             # outer diameter (inches)
PVC_OD_M = PVC_OD_IN * INCH_TO_M

# Coil mean diameter (wire center-to-center)
COIL_DIA_IN = PVC_OD_IN + WIRE_DIA_IN
COIL_DIA_M = COIL_DIA_IN * INCH_TO_M
COIL_DIA_CM = COIL_DIA_IN * INCH_TO_CM
COIL_RADIUS_IN = COIL_DIA_IN / 2
COIL_RADIUS_M = COIL_DIA_M / 2

# Target frequency
F_TARGET_MHZ = 146.0
F_TARGET_HZ = F_TARGET_MHZ * 1e6
WAVELENGTH = C / F_TARGET_HZ
QUARTER_WAVE = WAVELENGTH / 4


# ─── Medhurst Self-Capacitance ──────────────────────────────────────────────
# Empirical table: C_self(pF) = H × D(cm)
# l/D ratio → H coefficient (from Medhurst 1947)
MEDHURST_TABLE = [
    (0.10, 0.46), (0.15, 0.47), (0.20, 0.50), (0.25, 0.53),
    (0.30, 0.54), (0.35, 0.55), (0.40, 0.56), (0.50, 0.58),
    (0.60, 0.60), (0.70, 0.62), (0.80, 0.63), (0.90, 0.64),
    (1.00, 0.64), (1.50, 0.66), (2.00, 0.70), (2.50, 0.74),
    (3.00, 0.77), (3.50, 0.80), (4.00, 0.83), (4.50, 0.85),
    (5.00, 0.87), (7.00, 0.92), (10.0, 0.96),
]


def medhurst_H(l_over_d):
    """Interpolate Medhurst coefficient H for given l/D ratio."""
    xs = [p[0] for p in MEDHURST_TABLE]
    ys = [p[1] for p in MEDHURST_TABLE]
    if l_over_d <= xs[0]:
        return ys[0]
    if l_over_d >= xs[-1]:
        return ys[-1]
    return float(np.interp(l_over_d, xs, ys))


def medhurst_capacitance_pf(l_over_d, diameter_cm):
    """Medhurst self-capacitance in pF. C = H × D(cm)."""
    H = medhurst_H(l_over_d)
    return H * diameter_cm


def wheeler_inductance_uh(n_turns, radius_in, length_in):
    """
    Wheeler's formula for single-layer solenoid inductance.
    L(μH) = (r² × N²) / (9r + 10l)
    r = coil radius in inches, l = coil length in inches.
    Valid for l > 0.4 × diameter.
    """
    if length_in <= 0:
        return 0.0
    return (radius_in**2 * n_turns**2) / (9 * radius_in + 10 * length_in)


def wire_length_m(n_turns, pitch_m):
    """Total wire length for N turns of helix."""
    circumference = np.pi * COIL_DIA_M
    return n_turns * np.sqrt(circumference**2 + pitch_m**2)


def helix_velocity_factor(pitch_m):
    """
    Axial velocity factor for helical slow-wave structure.
    VF = p / √(p² + (πD)²)
    This is how fast the wave propagates along the coil axis
    relative to the speed of light.
    """
    circ = np.pi * COIL_DIA_M
    return pitch_m / np.sqrt(pitch_m**2 + circ**2)


def sphere_capacitance_pf(radius_m):
    """Capacitance of an isolated sphere: C = 4πε₀r."""
    return 4 * np.pi * EPS_0 * radius_m * 1e12  # convert to pF


def disc_capacitance_pf(radius_m):
    """Capacitance of an isolated disc: C = 8ε₀r."""
    return 8 * EPS_0 * radius_m * 1e12


def self_resonant_freq_hz(L_uh, C_pf):
    """f = 1 / (2π√(LC)), with L in μH and C in pF."""
    L = L_uh * 1e-6
    Cap = C_pf * 1e-12
    if L <= 0 or Cap <= 0:
        return float('inf')
    return 1.0 / (2 * np.pi * np.sqrt(L * Cap))


def find_self_resonant_turns(pitch_m=None, target_hz=None):
    """
    Sweep turn count to find where self-resonant frequency = target.
    Uses close-wound pitch if not specified.
    """
    if pitch_m is None:
        pitch_m = WIRE_DIA_M
    if target_hz is None:
        target_hz = F_TARGET_HZ

    results = []
    for n in np.arange(0.5, 50.0, 0.1):
        l_in = n * (pitch_m / INCH_TO_M)
        l_over_d = (n * pitch_m / COIL_DIA_M)

        L = wheeler_inductance_uh(n, COIL_RADIUS_IN, l_in)
        C = medhurst_capacitance_pf(l_over_d, COIL_DIA_CM)
        f = self_resonant_freq_hz(L, C)
        w_len = wire_length_m(n, pitch_m)

        results.append({
            'turns': n,
            'L_uh': L,
            'C_pf': C,
            'f_hz': f,
            'wire_m': w_len,
            'coil_len_in': l_in,
        })

    return results


def find_cap_hat_turns(cap_hat_pf, pitch_m=None, target_hz=None):
    """
    Find turn count for resonance WITH a capacity hat adding C_hat pF.
    """
    if pitch_m is None:
        pitch_m = WIRE_DIA_M
    if target_hz is None:
        target_hz = F_TARGET_HZ

    best = None
    best_err = float('inf')

    for n in np.arange(1.0, 100.0, 0.1):
        l_in = n * (pitch_m / INCH_TO_M)
        l_over_d = (n * pitch_m / COIL_DIA_M)

        L = wheeler_inductance_uh(n, COIL_RADIUS_IN, l_in)
        C_self = medhurst_capacitance_pf(l_over_d, COIL_DIA_CM)
        C_total = C_self + cap_hat_pf
        f = self_resonant_freq_hz(L, C_total)

        err = abs(f - target_hz)
        if err < best_err:
            best_err = err
            best = {
                'turns': n,
                'L_uh': L,
                'C_self_pf': C_self,
                'C_hat_pf': cap_hat_pf,
                'C_total_pf': C_total,
                'f_hz': f,
                'wire_m': wire_length_m(n, pitch_m),
                'coil_len_in': l_in,
                'coil_len_cm': l_in * INCH_TO_CM,
            }

    return best


def estimate_Q(L_uh, C_pf, wire_len_m, freq_hz):
    """
    Estimate unloaded Q factor.
    Q ≈ ωL / R_loss, where R_loss is AC resistance of the wire.
    """
    # Skin depth in copper at freq
    rho_cu = 1.68e-8  # Ω·m
    delta_cu = np.sqrt(rho_cu / (np.pi * freq_hz * MU_0))

    # AC resistance: R = ρ·l / (π·d·δ) for round wire where δ << d/2
    wire_circumference = np.pi * WIRE_DIA_M
    if delta_cu < WIRE_DIA_M / 2:
        # Skin effect regime
        R_ac = rho_cu * wire_len_m / (wire_circumference * delta_cu)
    else:
        # DC resistance (wire thinner than skin depth)
        area = np.pi * (WIRE_DIA_M / 2)**2
        R_ac = rho_cu * wire_len_m / area

    omega = 2 * np.pi * freq_hz
    L = L_uh * 1e-6
    Q = omega * L / R_ac if R_ac > 0 else 0

    return Q, R_ac, delta_cu


def print_report():
    """Full Extra Coil design report."""
    print(f"\n{'═'*72}")
    print(f"  TESLA EXTRA COIL — QUARTER-WAVE HELICAL RESONATOR")
    print(f"  Target: {F_TARGET_MHZ:.0f} MHz · 14 AWG · 2\" PVC Form")
    print(f"{'═'*72}")

    print(f"\n  ┌─ DESIGN PARAMETERS ───────────────────────────────────────────┐")
    print(f"  │  Wire:     14 AWG solid copper ({WIRE_DIA_MM:.3f} mm / "
          f"{WIRE_DIA_IN:.4f}\")          │")
    print(f"  │  Form:     2\" Sch40 PVC (OD = {PVC_OD_IN:.3f}\")     "
          f"                     │")
    print(f"  │  Coil D:   {COIL_DIA_IN:.3f}\" ({COIL_DIA_CM:.2f} cm)"
          f"                               │")
    print(f"  │  Target:   {F_TARGET_MHZ:.1f} MHz  "
          f"(λ = {WAVELENGTH:.4f} m, λ/4 = {QUARTER_WAVE*100:.1f} cm)      │")
    print(f"  └──────────────────────────────────────────────────────────────────┘")

    # ── Section 1: Raw wire-length quarter-wave ──
    print(f"\n{'─'*72}")
    print(f"  1. BASELINE: WIRE-LENGTH λ/4")
    print(f"{'─'*72}")
    wire_per_turn = np.pi * COIL_DIA_M
    n_bare = QUARTER_WAVE / wire_per_turn
    vf = helix_velocity_factor(WIRE_DIA_M)

    print(f"  Free-space λ/4:       {QUARTER_WAVE*100:.2f} cm ({QUARTER_WAVE*39.37:.2f}\")")
    print(f"  Wire per turn:        {wire_per_turn*100:.2f} cm ({wire_per_turn*39.37:.2f}\")")
    print(f"  Turns for λ/4 wire:   {n_bare:.1f} turns (close-wound)")
    print(f"  Helix velocity factor: {vf:.6f} (axial)")
    print(f"  Coil axial length:    {n_bare * WIRE_DIA_MM:.1f} mm "
          f"({n_bare * WIRE_DIA_IN:.3f}\")")
    print(f"\n  ⚠  {n_bare:.1f} turns is too few for a meaningful resonator.")
    print(f"     Distributed capacitance is negligible — this is just a")
    print(f"     short helical antenna, not a Tesla extra coil.")

    # ── Section 2: Self-resonant coil (Wheeler + Medhurst) ──
    print(f"\n{'─'*72}")
    print(f"  2. SELF-RESONANT COIL (Wheeler + Medhurst Model)")
    print(f"{'─'*72}")
    print(f"  Sweeping turn count to find f_self-res = {F_TARGET_MHZ:.0f} MHz...\n")

    results = find_self_resonant_turns()

    # Find closest to target
    best_idx = min(range(len(results)),
                   key=lambda i: abs(results[i]['f_hz'] - F_TARGET_HZ))
    best = results[best_idx]

    # Print sweep table (sampled)
    print(f"  {'Turns':>7} {'L (μH)':>9} {'C_self (pF)':>12} "
          f"{'f_res (MHz)':>12} {'Wire (cm)':>10}")
    print(f"  {'─'*7} {'─'*9} {'─'*12} {'─'*12} {'─'*10}")
    for r in results:
        if r['turns'] % 1.0 == 0 or abs(r['turns'] - best['turns']) < 0.15:
            marker = " ◄" if abs(r['turns'] - best['turns']) < 0.15 else ""
            print(f"  {r['turns']:>7.1f} {r['L_uh']:>9.4f} {r['C_pf']:>12.3f} "
                  f"{r['f_hz']/1e6:>12.1f} {r['wire_m']*100:>10.1f}{marker}")

    print(f"\n  ▶ Self-resonance at {F_TARGET_MHZ:.0f} MHz: "
          f"{best['turns']:.1f} turns, {best['wire_m']*100:.1f} cm wire")
    print(f"    L = {best['L_uh']:.4f} μH, C_self = {best['C_pf']:.3f} pF")

    Q, R_ac, delta_cu = estimate_Q(best['L_uh'], best['C_pf'],
                                     best['wire_m'], F_TARGET_HZ)
    print(f"    Q_unloaded ≈ {Q:.0f} (R_ac = {R_ac:.3f} Ω, "
          f"δ_Cu = {delta_cu*1e6:.1f} μm)")
    print(f"\n  ⚠  Q ≈ {Q:.0f} is {'marginal' if Q < 50 else 'acceptable' if Q < 200 else 'good'}.")

    # ── Section 3: Capacity Hat Design ──
    print(f"\n{'─'*72}")
    print(f"  3. CAPACITY HAT — TOP-LOADED EXTRA COIL (RECOMMENDED)")
    print(f"{'─'*72}")
    print(f"  Adding a metal sphere or disc at the top increases C_total,")
    print(f"  allowing more turns → higher Q → better resonator.\n")

    hat_configs = [
        ("2\" sphere (r=1\")",      sphere_capacitance_pf(1.0 * INCH_TO_M)),
        ("3\" sphere (r=1.5\")",    sphere_capacitance_pf(1.5 * INCH_TO_M)),
        ("4\" sphere (r=2\")",      sphere_capacitance_pf(2.0 * INCH_TO_M)),
        ("4\" disc (r=2\")",        disc_capacitance_pf(2.0 * INCH_TO_M)),
        ("6\" disc (r=3\")",        disc_capacitance_pf(3.0 * INCH_TO_M)),
        ("8\" disc (r=4\")",        disc_capacitance_pf(4.0 * INCH_TO_M)),
    ]

    print(f"  {'Cap Hat':^22} {'C_hat':>8} {'Turns':>7} {'Wire':>9} "
          f"{'Coil L':>9} {'Q_est':>7}")
    print(f"  {'─'*22} {'─'*8} {'─'*7} {'─'*9} {'─'*9} {'─'*7}")

    for label, c_hat in hat_configs:
        sol = find_cap_hat_turns(c_hat)
        if sol:
            Q_h, _, _ = estimate_Q(sol['L_uh'], sol['C_total_pf'],
                                     sol['wire_m'], F_TARGET_HZ)
            print(f"  {label:<22} {c_hat:>7.2f}p {sol['turns']:>6.1f} "
                  f"{sol['wire_m']*100:>8.1f}cm "
                  f"{sol['coil_len_cm']:>8.1f}cm {Q_h:>7.0f}")

    # ── Section 4: Recommended Build ──
    # Use 4" sphere as recommended config
    rec_hat_pf = sphere_capacitance_pf(2.0 * INCH_TO_M)
    rec = find_cap_hat_turns(rec_hat_pf)

    if rec:
        Q_rec, R_rec, _ = estimate_Q(rec['L_uh'], rec['C_total_pf'],
                                       rec['wire_m'], F_TARGET_HZ)
        turns_int = int(round(rec['turns']))

        print(f"\n{'═'*72}")
        print(f"  ▶ RECOMMENDED BUILD — 146 MHz EXTRA COIL")
        print(f"{'─'*72}")
        print(f"  Form:         2\" Sch40 PVC pipe")
        print(f"  Wire:         14 AWG solid copper, close-wound")
        print(f"  Turns:        {rec['turns']:.1f} (use {turns_int})")
        print(f"  Wire length:  {rec['wire_m']*100:.1f} cm "
              f"({rec['wire_m']*39.37:.1f}\")")
        print(f"  Coil length:  {rec['coil_len_cm']:.1f} cm "
              f"({rec['coil_len_in']:.2f}\")")
        print(f"  Cap hat:      4\" metal sphere (doorknob/ball)")
        print(f"  Inductance:   {rec['L_uh']:.4f} μH")
        print(f"  C_self:       {rec['C_self_pf']:.2f} pF")
        print(f"  C_hat:        {rec['C_hat_pf']:.2f} pF")
        print(f"  C_total:      {rec['C_total_pf']:.2f} pF")
        print(f"  f_resonance:  {rec['f_hz']/1e6:.1f} MHz")
        print(f"  Q_unloaded:   ≈{Q_rec:.0f}")
        print(f"  Bandwidth:    ≈{F_TARGET_MHZ/Q_rec*1000:.0f} kHz "
              f"(f/Q) at -3 dB")
        print(f"{'═'*72}")

    # ── Section 5: Space-wound variant ──
    print(f"\n{'─'*72}")
    print(f"  4. SPACE-WOUND VARIANT (1 wire-diameter gap)")
    print(f"{'─'*72}")
    pitch_spaced = 2 * WIRE_DIA_M  # 1 diameter gap between turns

    for label, c_hat in [("No cap hat", 0.0),
                          ("4\" sphere", sphere_capacitance_pf(2.0 * INCH_TO_M))]:
        sol = find_cap_hat_turns(c_hat, pitch_m=pitch_spaced)
        if sol:
            Q_s, _, _ = estimate_Q(sol['L_uh'], sol['C_total_pf'],
                                     sol['wire_m'], F_TARGET_HZ)
            print(f"  {label + ':':<18} {sol['turns']:.1f} turns, "
                  f"{sol['wire_m']*100:.1f} cm wire, "
                  f"coil = {sol['coil_len_cm']:.1f} cm, Q ≈ {Q_s:.0f}")

    # ── Section 6: Physics Reality Check ──
    print(f"\n{'═'*72}")
    print(f"  PHYSICS NOTES")
    print(f"{'═'*72}")
    print(f"""
  WHAT'S REAL:
  • The helical resonator is legitimate RF engineering (used in VHF
    filters, duplexers, and test equipment since the 1950s).
  • Tesla's extra coil was a real quarter-wave helical transmission
    line resonator. The Corum brothers proved this mathematically.
  • Voltage magnification at the open end is real: V_top ≈ Q × V_base.
    With Q ≈ {Q_rec:.0f}, a 5W signal produces {np.sqrt(50*5):.0f}V RMS at the
    base → up to {np.sqrt(50*5)*Q_rec:.0f}V at the capacity hat.
  • The coil IS a monopole antenna — it will radiate.

  WHAT MAXWELL CONSTRAINS:
  • Longitudinal EM waves do not propagate in free space. Maxwell's
    equations permit only transverse waves in vacuum/air. This is not
    a theory gap — it's a proven mathematical consequence of ∇·E = 0
    in charge-free space.
  • "Scalar waves" (∇×E = 0, ∇×B = 0 simultaneously) violate Faraday's
    law. No reproducible experiment has detected them.
  • Bifilar cancellation (B=0) doesn't create longitudinal radiation —
    it creates a transmission line that doesn't radiate at all.
  • Schumann resonance is ~7.83 Hz, not VHF. The Earth cavity cannot
    resonate at 146 MHz (λ >> cavity dimensions required).

  WHAT THIS COIL ACTUALLY DOES:
  • Acts as a high-Q, voltage-magnifying, electrically-short monopole
  • Couples strongly to the local E-field (electrostatic near-field)
  • Creates a very high voltage gradient at the top terminal
  • Ground-couples through displacement current (real and measurable)
  • Radiates transverse EM waves with a monopole pattern
  • The high Q means narrow bandwidth = concentrated spectral energy
""")
    print(f"{'═'*72}\n")


def main():
    p = argparse.ArgumentParser(description="Tesla Extra Coil Calculator")
    a = p.parse_args()
    print_report()


if __name__ == '__main__':
    main()
