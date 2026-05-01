#!/usr/bin/env python3
"""
UHF 440 MHz Yagi-Uda Optimization
====================================
Rescales the 146 MHz 3-element Yagi to 440 MHz and uses the analytical
Yagi model (or NEC-2 if available) to sweep director length for optimal gain.

Usage:  python uhf_optimization.py
Deps:   numpy (required), necpp (optional)
"""

import sys
import argparse
import numpy as np

# ─── Import the analytical engine from the main simulation ───────────────────
sys.path.insert(0, '.')

# ─── VHF Reference Geometry (146 MHz, inches) ───────────────────────────────
VHF_FREQ = 146.0
UHF_FREQ = 440.0
SCALE = VHF_FREQ / UHF_FREQ  # 0.3318

INCH_TO_M = 0.0254
C = 299_792_458
Z_REF = 50.0

# VHF dimensions
VHF_REFLECTOR = 40.125
VHF_DRIVEN = 38.250
VHF_DIRECTOR = 36.312
VHF_DRIVEN_X = 16.125
VHF_DIRECTOR_X = 28.250
VHF_WIRE_R = 0.25

# UHF scaled (linear)
UHF_REFLECTOR = VHF_REFLECTOR * SCALE
UHF_DRIVEN = VHF_DRIVEN * SCALE
UHF_DIRECTOR = VHF_DIRECTOR * SCALE
UHF_DRIVEN_X = VHF_DRIVEN_X * SCALE
UHF_DIRECTOR_X = VHF_DIRECTOR_X * SCALE
UHF_WIRE_R = VHF_WIRE_R * SCALE

def in2m(v):
    return v * INCH_TO_M


def analytical_yagi_gain(freq_mhz, refl_len, driven_len, dir_len,
                          driven_x, dir_x, wire_r):
    """
    Analytical Yagi model using Kraus empirical gain + induced EMF impedance.
    Returns (gain_dbi, z_feed, swr).
    """
    freq_hz = freq_mhz * 1e6
    wavelength = C / freq_hz
    k = 2 * np.pi / wavelength

    positions = np.array([0.0, in2m(driven_x), in2m(dir_x)])
    half_lengths = np.array([in2m(refl_len/2), in2m(driven_len/2), in2m(dir_len/2)])

    def dipole_z_self(half_len):
        el = k * half_len
        r_rad = 73.13 * (np.sin(el))**2
        delta_l = 2 * half_len - wavelength / 2
        if abs(delta_l) < wavelength / 4:
            x = 42.5 * np.tan(k * delta_l / 2)
        else:
            x = 500.0 * np.sign(delta_l)
        return complex(r_rad + 0.5, x)

    def mutual_z(d, h1, h2):
        kd = k * d
        d_lambda = d / wavelength
        coupling = np.sin(k * h1) * np.sin(k * h2)
        if d_lambda < 0.05:
            decay = 1.0
        elif d_lambda < 0.5:
            decay = 0.7 * np.exp(-0.5 * (d_lambda - 0.1))
        else:
            decay = 0.3 * np.exp(-0.8 * (d_lambda - 0.5))
        r_m = 30.0 * coupling * np.cos(kd) * decay
        x_m = -30.0 * coupling * np.sin(kd) * decay
        return complex(r_m, x_m)

    z_self = [dipole_z_self(hl) for hl in half_lengths]
    z12 = mutual_z(in2m(driven_x), half_lengths[0], half_lengths[1])
    z13 = mutual_z(in2m(dir_x), half_lengths[0], half_lengths[2])
    z23 = mutual_z(in2m(dir_x - driven_x), half_lengths[1], half_lengths[2])

    Z = np.array([
        [z_self[0], z12, z13],
        [z12, z_self[1], z23],
        [z13, z23, z_self[2]]
    ], dtype=complex)

    V = np.array([0, 1, 0], dtype=complex)
    I = np.linalg.solve(Z, V)
    z_feed = 1.0 / I[1]

    # Kraus empirical gain for 3-element Yagi
    boom_lambda = in2m(dir_x) / wavelength
    if boom_lambda < 0.15:
        gain_dbi = 5.0
    elif boom_lambda < 0.5:
        gain_dbi = 6.0 + 5.0 * (boom_lambda - 0.15)
    else:
        gain_dbi = 7.75 + 2.0 * (boom_lambda - 0.5)

    # Element ratio corrections
    refl_ratio = in2m(refl_len) / wavelength
    driven_ratio = in2m(driven_len) / wavelength
    dir_ratio = in2m(dir_len) / wavelength
    gain_dbi -= abs(refl_ratio - 0.495) * 5
    gain_dbi -= abs(driven_ratio - 0.473) * 5
    gain_dbi -= abs(dir_ratio - 0.447) * 5

    # Efficiency
    r_rad = max(z_feed.real, 1.0)
    efficiency = r_rad / (r_rad + 0.5)
    gain_dbi += 10 * np.log10(efficiency)

    gamma = abs((z_feed - Z_REF) / (z_feed + Z_REF))
    swr = (1 + gamma) / (1 - gamma) if gamma < 1 else float('inf')

    return gain_dbi, z_feed, swr


def try_necpp_simulate(freq, refl_len, driven_len, dir_len,
                        driven_x, dir_x, wire_r):
    """Try NEC-2 if available."""
    try:
        import necpp
    except ImportError:
        return None

    nec = necpp.nec_create()
    rh, dh, dirh = in2m(refl_len/2), in2m(driven_len/2), in2m(dir_len/2)
    dx, dirx, wr = in2m(driven_x), in2m(dir_x), in2m(wire_r)
    ns = 21

    necpp.nec_wire(nec, 1, ns, 0, -rh, 0, 0, rh, 0, wr, 1, 1)
    necpp.nec_wire(nec, 2, ns, dx, -dh, 0, dx, dh, 0, wr, 1, 1)
    necpp.nec_wire(nec, 3, ns, dirx, -dirh, 0, dirx, dirh, 0, wr, 1, 1)
    necpp.nec_geometry_complete(nec, 0)
    necpp.nec_gn_card(nec, -1, 0, 0, 0, 0, 0, 0, 0)
    necpp.nec_ex_card(nec, 0, 2, 11, 0, 1, 0, 0, 0, 0, 0)
    necpp.nec_fr_card(nec, 0, 1, freq, 0)
    necpp.nec_rp_card(nec, 0, 91, 360, 0, 5, 0, 0, 0, 0, 2, 1, 0, 0)

    gains = [necpp.nec_gain(nec, 0, i) for i in range(91 * 360)]
    zr = necpp.nec_impedance_real(nec, 0)
    zi = necpp.nec_impedance_imag(nec, 0)
    z = complex(zr, zi)
    gamma = abs((z - Z_REF) / (z + Z_REF))
    swr = (1 + gamma) / (1 - gamma) if gamma < 1 else float('inf')
    necpp.nec_delete(nec)
    return max(gains), z, swr


def director_sweep(steps=21, sweep_pct=5):
    """Sweep director length ±sweep_pct% around scaled value."""
    base = UHF_DIRECTOR
    low = base * (1 - sweep_pct / 100)
    high = base * (1 + sweep_pct / 100)
    dir_lengths = np.linspace(low, high, steps)

    # Detect engine
    nec_test = try_necpp_simulate(UHF_FREQ, UHF_REFLECTOR, UHF_DRIVEN,
                                   UHF_DIRECTOR, UHF_DRIVEN_X, UHF_DIRECTOR_X,
                                   UHF_WIRE_R)
    use_nec = nec_test is not None
    engine = "NEC-2 (necpp)" if use_nec else "Analytical (Induced EMF)"

    print(f"\n[*] Engine: {engine}")
    print(f"[*] Sweeping director: {low:.3f}\" to {high:.3f}\" ({steps} steps)")

    results = []
    print(f"\n  {'Director (in)':>14} {'Director (mm)':>14} {'Gain (dBi)':>11} "
          f"{'SWR':>7} {'Z (Ω)':>22}")
    print(f"  {'─'*14} {'─'*14} {'─'*11} {'─'*7} {'─'*22}")

    for dl in dir_lengths:
        if use_nec:
            gain, z, swr = try_necpp_simulate(
                UHF_FREQ, UHF_REFLECTOR, UHF_DRIVEN, dl,
                UHF_DRIVEN_X, UHF_DIRECTOR_X, UHF_WIRE_R)
        else:
            gain, z, swr = analytical_yagi_gain(
                UHF_FREQ, UHF_REFLECTOR, UHF_DRIVEN, dl,
                UHF_DRIVEN_X, UHF_DIRECTOR_X, UHF_WIRE_R)

        results.append((dl, gain, z.real, z.imag, swr))
        z_str = f"{z.real:.1f} + j{z.imag:.1f}"
        marker = " ◄" if abs(dl - base) < 0.001 else ""
        print(f"  {dl:>14.3f} {dl*25.4:>14.1f} {gain:>11.2f} "
              f"{swr:>7.2f} {z_str:>22}{marker}")

    return results, engine


def save_sweep_csv(results, output='uhf_director_sweep.csv'):
    """Save sweep results as CSV."""
    with open(output, 'w') as f:
        f.write("director_in,director_mm,gain_dbi,swr,z_real,z_imag\n")
        for dl, gain, zr, zi, swr in results:
            f.write(f"{dl:.4f},{dl*25.4:.1f},{gain:.3f},{swr:.3f},{zr:.2f},{zi:.2f}\n")
    print(f"[✓] Sweep data saved: {output}")


def print_report(results, engine):
    """Print final optimization report."""
    gains = [r[1] for r in results]
    best_idx = np.argmax(gains)
    opt = results[best_idx]

    wl_vhf = C / (VHF_FREQ * 1e6) * 100  # cm
    wl_uhf = C / (UHF_FREQ * 1e6) * 100  # cm

    print(f"\n{'═'*68}")
    print(f"  UHF OPTIMIZATION REPORT — {UHF_FREQ:.0f} MHz")
    print(f"  Engine: {engine}")
    print(f"{'═'*68}")
    print(f"  Scale Factor: {SCALE:.4f} ({VHF_FREQ:.0f} / {UHF_FREQ:.0f})")
    print(f"  λ_VHF: {wl_vhf:.1f} cm  →  λ_UHF: {wl_uhf:.1f} cm")

    print(f"\n  ┌─ DIMENSION TABLE ──────────────────────────────────────────┐")
    print(f"  │  {'Element':<14} {'VHF (in)':<10} {'UHF (in)':<10} "
          f"{'UHF (mm)':<10} {'UHF (cm)':<10} │")
    print(f"  │  {'─'*14} {'─'*10} {'─'*10} {'─'*10} {'─'*10} │")

    rows = [
        ("Reflector", VHF_REFLECTOR, UHF_REFLECTOR),
        ("Driven", VHF_DRIVEN, UHF_DRIVEN),
        ("Director", VHF_DIRECTOR, UHF_DIRECTOR),
        ("Drv Spacing", VHF_DRIVEN_X, UHF_DRIVEN_X),
        ("Dir Spacing", VHF_DIRECTOR_X, UHF_DIRECTOR_X),
    ]
    for label, vhf, uhf in rows:
        print(f"  │  {label:<14} {vhf:<10.3f} {uhf:<10.3f} "
              f"{uhf*25.4:<10.1f} {uhf*2.54:<10.2f} │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    print(f"\n  ┌─ OPTIMIZED DIRECTOR ──────────────────────────────────────┐")
    print(f"  │  Linear Scaled:   {UHF_DIRECTOR:.3f} in ({UHF_DIRECTOR * 25.4:.1f} mm)")
    print(f"  │  NEC-Optimized:   {opt[0]:.3f} in ({opt[0] * 25.4:.1f} mm)")
    delta = opt[0] - UHF_DIRECTOR
    print(f"  │  Delta:           {delta:+.3f} in ({delta * 25.4:+.1f} mm)")
    print(f"  │  Optimal Gain:    {opt[1]:.2f} dBi")
    print(f"  │  SWR (50Ω):       {opt[4]:.2f}:1")
    print(f"  │  Feedpoint Z:     {opt[2]:.1f} + j{opt[3]:.1f} Ω")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    print(f"\n  ┌─ UHF BAND ADVANTAGES ────────────────────────────────────┐")
    print(f"  │  • Higher atmospheric penetration                        │")
    print(f"  │    (reduced ionospheric refraction at 440 MHz)           │")
    print(f"  │  • Shorter elements → more rigid construction            │")
    print(f"  │    (13\" vs 40\" — fits on a small PVC cross)             │")
    print(f"  │  • Better near-space propagation characteristics         │")
    print(f"  │  • λ reduction: {wl_vhf:.0f} cm → {wl_uhf:.0f} cm "
          f"({(1-wl_uhf/wl_vhf)*100:.0f}% smaller)             │")
    print(f"  │  • Compatible with UV-5R 70cm band (430-450 MHz)        │")
    print(f"  └──────────────────────────────────────────────────────────┘")

    # Hairpin match recommendation
    if opt[4] > 1.5:
        print(f"\n  ⚠ SWR > 1.5:1 — Hairpin match recommended")
        z_feed = complex(opt[2], opt[3])
        # Hairpin length estimate: L = (Z0 / (2π * f * Z_feed.imag)) * λ
        if abs(z_feed.imag) > 1:
            print(f"    Feedpoint reactance: j{z_feed.imag:.1f} Ω")
            print(f"    Scale hairpin from VHF: 5\" × {SCALE:.4f} ≈ "
                  f"{5 * SCALE:.2f}\" ({5 * SCALE * 25.4:.0f} mm)")

    print(f"\n{'═'*68}\n")


def main():
    p = argparse.ArgumentParser(description="UHF Yagi Optimization")
    p.add_argument('--steps', type=int, default=21)
    p.add_argument('--csv', action='store_true', default=True)
    a = p.parse_args()

    print(f"[*] Scaling VHF {VHF_FREQ:.0f} MHz → UHF {UHF_FREQ:.0f} MHz")
    print(f"[*] Scale factor: {SCALE:.4f}")

    results, engine = director_sweep(steps=a.steps)
    print_report(results, engine)

    if a.csv:
        save_sweep_csv(results)

    return results


if __name__ == '__main__':
    main()
