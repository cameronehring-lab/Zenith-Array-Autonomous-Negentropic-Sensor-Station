#!/usr/bin/env python3
"""
Ground Electromagnetic Analysis — Houston Black Clay (McKinney, TX)
=====================================================================
Calculates skin depth, ground conductivity, and RF propagation effects
for the Houston Black Clay soil series (Vertisol) at the 75069/75070/75071
deployment site.

Soil Data Sources:
  - USDA NRCS Official Series Description: Houston Black
  - Collin County Soil Survey (USDA-SCS)
  - Published resistivity: 5–50 Ω·m (moist–dry range for high-smectite clay)
  - Clay content: 40–60% montmorillonite (smectite)
  - Parent material: Taylor Marl / Austin Chalk residuum (Cretaceous)

Physics:
  Skin depth (δ) for a good conductor approximation:
    δ = √(2ρ / (ωμ))  =  √(ρ / (π·f·μ₀))

  For a lossy dielectric (more accurate at VHF):
    δ = 1 / (ω · √(μ·ε/2 · (√(1 + (σ/ωε)²) - 1)))

Usage:  python ground_analysis.py
Deps:   numpy (required), matplotlib (optional)
"""

import numpy as np
import argparse

# ─── Physical Constants ──────────────────────────────────────────────────────
C = 299_792_458              # speed of light (m/s)
MU_0 = 4 * np.pi * 1e-7     # permeability of free space (H/m)
EPS_0 = 8.854187817e-12      # permittivity of free space (F/m)

# ─── Beacon Frequencies ─────────────────────────────────────────────────────
VHF_FREQ_MHZ = 146.0
UHF_FREQ_MHZ = 440.0

# ─── Houston Black Clay Soil Parameters ─────────────────────────────────────
# Resistivity range from USDA survey data and geotechnical literature
# for high-smectite Vertisol in the Texas Blackland Prairie
SOIL_PARAMS = {
    "saturated": {
        "label": "Saturated (post-rain)",
        "resistivity_ohm_m": 5.0,
        "relative_permittivity": 30.0,   # εᵣ for wet clay
        "description": "After heavy rain, cracks sealed, soil fully swelled",
    },
    "moist": {
        "label": "Moist (field capacity)",
        "resistivity_ohm_m": 10.0,
        "relative_permittivity": 22.0,   # εᵣ at field capacity
        "description": "Typical spring/fall — soil at field capacity",
    },
    "average": {
        "label": "Average (seasonal mean)",
        "resistivity_ohm_m": 15.0,
        "relative_permittivity": 16.0,
        "description": "Annual mean for McKinney TX climate",
    },
    "dry": {
        "label": "Dry (summer drought)",
        "resistivity_ohm_m": 30.0,
        "relative_permittivity": 8.0,    # εᵣ for dry clay
        "description": "July-August drought, deep cracks open (>10 cm)",
    },
    "cracked": {
        "label": "Severely cracked",
        "resistivity_ohm_m": 50.0,
        "relative_permittivity": 5.0,    # air-filled cracks dominate
        "description": "Extended drought, gilgai cracks >15 cm, air gaps",
    },
}


def skin_depth_conductor(rho, freq_hz):
    """
    Skin depth using good-conductor approximation.
      δ = √(ρ / (π · f · μ₀))

    Valid when σ >> ωε  (conduction current dominates displacement current).

    Args:
        rho: resistivity in Ω·m
        freq_hz: frequency in Hz

    Returns:
        skin depth in meters
    """
    return np.sqrt(rho / (np.pi * freq_hz * MU_0))


def skin_depth_lossy(rho, eps_r, freq_hz):
    """
    Skin depth for a general lossy dielectric (exact formulation).
      δ = 1 / (ω · √(μ₀·ε/2 · (√(1 + (σ/(ωε))²) - 1)))

    This is the correct formulation at VHF where soil may be in the
    transition region between good conductor and lossy dielectric.

    Args:
        rho: resistivity in Ω·m
        eps_r: relative permittivity
        freq_hz: frequency in Hz

    Returns:
        skin depth in meters
    """
    omega = 2 * np.pi * freq_hz
    sigma = 1.0 / rho
    eps = eps_r * EPS_0

    # Loss tangent: tan(δ_loss) = σ / (ω·ε)
    loss_tangent = sigma / (omega * eps)

    # Attenuation constant α
    alpha = omega * np.sqrt(
        (MU_0 * eps / 2) * (np.sqrt(1 + loss_tangent**2) - 1)
    )

    return 1.0 / alpha


def loss_tangent(rho, eps_r, freq_hz):
    """Calculate the loss tangent σ/(ωε)."""
    sigma = 1.0 / rho
    omega = 2 * np.pi * freq_hz
    eps = eps_r * EPS_0
    return sigma / (omega * eps)


def wavelength_in_soil(eps_r, freq_hz):
    """Wavelength inside the soil medium."""
    return C / (freq_hz * np.sqrt(eps_r))


def attenuation_db_per_meter(rho, eps_r, freq_hz):
    """Signal attenuation in dB/m through soil."""
    delta = skin_depth_lossy(rho, eps_r, freq_hz)
    # At one skin depth, amplitude drops to 1/e = -8.686 dB
    return 8.686 / delta


def ground_reflection_loss(eps_r, rho, freq_hz):
    """
    Reflection coefficient at air-soil interface (normal incidence).
    Uses complex permittivity to compute intrinsic impedance ratio.
    """
    sigma = 1.0 / rho
    omega = 2 * np.pi * freq_hz
    eps_complex = eps_r * EPS_0 - 1j * sigma / omega

    eta_soil = np.sqrt(MU_0 / eps_complex)
    eta_air = np.sqrt(MU_0 / EPS_0)  # ≈ 377 Ω

    gamma = (eta_soil - eta_air) / (eta_soil + eta_air)
    return abs(gamma), 20 * np.log10(abs(gamma))


def print_analysis(freq_mhz):
    """Print complete ground analysis for a given frequency."""
    freq_hz = freq_mhz * 1e6
    wl_free = C / freq_hz

    print(f"\n{'═'*72}")
    print(f"  GROUND EM ANALYSIS — {freq_mhz:.0f} MHz")
    print(f"  Houston Black Clay Series · McKinney TX (75069/75070/75071)")
    print(f"{'═'*72}")
    print(f"  Free-space wavelength:  λ₀ = {wl_free:.4f} m ({wl_free*100:.1f} cm)")
    print(f"  Angular frequency:      ω  = {2*np.pi*freq_hz:.4e} rad/s")
    print(f"  Soil series:            Houston Black (Udic Haplustert)")
    print(f"  Clay mineral:           Smectite (montmorillonite), 40–60%")
    print(f"  Parent geology:         Taylor Marl / Austin Chalk (Cretaceous)")

    print(f"\n  ┌─ SOIL PARAMETERS ─────────────────────────────────────────────┐")
    print(f"  │  {'Condition':<22} {'ρ (Ω·m)':>9} {'εᵣ':>6} {'σ (S/m)':>10}    │")
    print(f"  │  {'─'*22} {'─'*9} {'─'*6} {'─'*10}    │")
    for key, p in SOIL_PARAMS.items():
        sigma = 1.0 / p['resistivity_ohm_m']
        print(f"  │  {p['label']:<22} {p['resistivity_ohm_m']:>9.1f} "
              f"{p['relative_permittivity']:>6.1f} {sigma:>10.4f}    │")
    print(f"  └──────────────────────────────────────────────────────────────────┘")

    # ── Skin Depth Table ──
    print(f"\n  ┌─ SKIN DEPTH ANALYSIS ──────────────────────────────────────────┐")
    print(f"  │  {'Condition':<22} {'δ_cond (m)':>11} {'δ_lossy (m)':>12} "
          f"{'δ (cm)':>8} {'δ (in)':>8} │")
    print(f"  │  {'─'*22} {'─'*11} {'─'*12} {'─'*8} {'─'*8} │")

    for key, p in SOIL_PARAMS.items():
        rho = p['resistivity_ohm_m']
        eps_r = p['relative_permittivity']

        d_cond = skin_depth_conductor(rho, freq_hz)
        d_lossy = skin_depth_lossy(rho, eps_r, freq_hz)

        # Use the lossy dielectric result (more accurate at VHF)
        d_cm = d_lossy * 100
        d_in = d_lossy * 39.3701

        marker = " ◄" if key == "average" else ""
        print(f"  │  {p['label']:<22} {d_cond:>11.4f} {d_lossy:>12.4f} "
              f"{d_cm:>8.1f} {d_in:>8.1f}{marker} │")
    print(f"  └──────────────────────────────────────────────────────────────────┘")
    print(f"  δ = depth at which field amplitude drops to 1/e (36.8%)")

    # ── Loss Tangent & Regime Classification ──
    print(f"\n  ┌─ LOSS TANGENT & PROPAGATION REGIME ──────────────────────────┐")
    print(f"  │  {'Condition':<22} {'tan(δ_L)':>10} {'Regime':<25}     │")
    print(f"  │  {'─'*22} {'─'*10} {'─'*25}     │")
    for key, p in SOIL_PARAMS.items():
        lt = loss_tangent(p['resistivity_ohm_m'], p['relative_permittivity'], freq_hz)
        if lt > 10:
            regime = "Good conductor"
        elif lt > 1:
            regime = "Quasi-conductor"
        elif lt > 0.1:
            regime = "Lossy dielectric"
        else:
            regime = "Low-loss dielectric"
        print(f"  │  {p['label']:<22} {lt:>10.2f} {regime:<25}     │")
    print(f"  │                                                                  │")
    print(f"  │  tan(δ_L) = σ/(ωε)                                              │")
    print(f"  │  >10: good conductor approx valid                                │")
    print(f"  │  1–10: transition — full lossy dielectric formula required        │")
    print(f"  │  <1: displacement current dominates                              │")
    print(f"  └──────────────────────────────────────────────────────────────────┘")

    # ── Attenuation ──
    print(f"\n  ┌─ SIGNAL ATTENUATION IN SOIL ────────────────────────────────┐")
    print(f"  │  {'Condition':<22} {'dB/m':>8} {'dB/ft':>8} {'λ_soil (m)':>11}   │")
    print(f"  │  {'─'*22} {'─'*8} {'─'*8} {'─'*11}   │")
    for key, p in SOIL_PARAMS.items():
        atten = attenuation_db_per_meter(
            p['resistivity_ohm_m'], p['relative_permittivity'], freq_hz)
        wl_soil = wavelength_in_soil(p['relative_permittivity'], freq_hz)
        print(f"  │  {p['label']:<22} {atten:>8.1f} {atten*0.3048:>8.1f} "
              f"{wl_soil:>11.4f}   │")
    print(f"  └──────────────────────────────────────────────────────────────────┘")

    # ── Ground Reflection ──
    print(f"\n  ┌─ AIR → SOIL REFLECTION (NORMAL INCIDENCE) ──────────────────┐")
    print(f"  │  {'Condition':<22} {'|Γ|':>8} {'Γ (dB)':>9} {'% Reflected':>12}  │")
    print(f"  │  {'─'*22} {'─'*8} {'─'*9} {'─'*12}  │")
    for key, p in SOIL_PARAMS.items():
        gamma_mag, gamma_db = ground_reflection_loss(
            p['relative_permittivity'], p['resistivity_ohm_m'], freq_hz)
        pct = gamma_mag**2 * 100
        print(f"  │  {p['label']:<22} {gamma_mag:>8.3f} {gamma_db:>9.2f} "
              f"{pct:>11.1f}%  │")
    print(f"  └──────────────────────────────────────────────────────────────────┘")

    # ── KEY RESULT ──
    avg = SOIL_PARAMS["average"]
    d_avg = skin_depth_lossy(avg['resistivity_ohm_m'],
                              avg['relative_permittivity'], freq_hz)
    atten_avg = attenuation_db_per_meter(
        avg['resistivity_ohm_m'], avg['relative_permittivity'], freq_hz)

    print(f"\n{'═'*72}")
    print(f"  ▶ KEY RESULT — {freq_mhz:.0f} MHz IN HOUSTON BLACK CLAY")
    print(f"{'─'*72}")
    print(f"  Seasonal-mean skin depth:    δ = {d_avg:.4f} m "
          f"({d_avg*100:.1f} cm / {d_avg*39.3701:.1f} in)")
    print(f"  Attenuation rate:            {atten_avg:.1f} dB/m")
    print(f"  At 1 meter depth:            {atten_avg:.1f} dB loss "
          f"(signal at {100*np.exp(-1/d_avg * 1):.2f}%)")
    print(f"  At 0.3 m (1 ft):             {atten_avg*0.3048:.1f} dB loss")
    print(f"")
    print(f"  Implication: At {freq_mhz:.0f} MHz, the VHF signal is")
    print(f"  effectively surface-coupled. Ground penetration is")
    print(f"  negligible beyond ~{3*d_avg*100:.0f} cm (3δ = 95% attenuation).")
    print(f"{'═'*72}\n")


def print_comparison():
    """Side-by-side comparison of VHF vs UHF skin depth."""
    print(f"\n{'═'*72}")
    print(f"  VHF vs UHF SKIN DEPTH — HOUSTON BLACK CLAY COMPARISON")
    print(f"{'═'*72}")
    print(f"  {'Condition':<22} {'146 MHz δ':>12} {'440 MHz δ':>12} {'Ratio':>8}")
    print(f"  {'─'*22} {'─'*12} {'─'*12} {'─'*8}")

    for key, p in SOIL_PARAMS.items():
        d_vhf = skin_depth_lossy(p['resistivity_ohm_m'],
                                  p['relative_permittivity'],
                                  VHF_FREQ_MHZ * 1e6)
        d_uhf = skin_depth_lossy(p['resistivity_ohm_m'],
                                  p['relative_permittivity'],
                                  UHF_FREQ_MHZ * 1e6)
        ratio = d_vhf / d_uhf
        print(f"  {p['label']:<22} {d_vhf*100:>10.1f} cm {d_uhf*100:>10.1f} cm "
              f"{ratio:>7.2f}x")

    print(f"\n  VHF penetrates ~{np.sqrt(UHF_FREQ_MHZ/VHF_FREQ_MHZ):.1f}x deeper "
          f"than UHF (scales as √(f₁/f₂) in conductor limit)")
    print(f"{'═'*72}\n")


def grounding_recommendations():
    """Print grounding system recommendations for the deployment site."""
    print(f"\n{'═'*72}")
    print(f"  ANTENNA GROUNDING RECOMMENDATIONS — MCKINNEY TX SITE")
    print(f"{'═'*72}")

    avg_rho = SOIL_PARAMS["average"]["resistivity_ohm_m"]
    dry_rho = SOIL_PARAMS["dry"]["resistivity_ohm_m"]

    print(f"""
  Houston Black Clay presents specific grounding challenges:

  1. SEASONAL RESISTIVITY SWING
     ρ_wet  =  5 Ω·m  →  ρ_dry = 50 Ω·m  (10:1 ratio)
     Ground rod resistance will fluctuate ≈ 3:1 seasonally.

  2. SHRINK-SWELL MECHANICAL FAILURE
     The soil physically separates from ground rods during drought.
     Active zone depth: 0 – 1.5 m (0 – 5 ft) in Collin County.
     Rods MUST extend below the active zone (minimum 8 ft / 2.4 m).

  3. RECOMMENDATIONS FOR RF GROUND SYSTEM
     • Use 8-ft copper-clad ground rod driven to full depth
     • Supplement with radial ground plane (≥4 radials, λ/4 each)
       - At 146 MHz: radials ≈ 50.1 cm (19.7 in) each
       - At 440 MHz: radials ≈ 17.0 cm (6.7 in) each
     • For portable deployment: ground rod + chemical ground
       enhancement compound in borehole
     • Worst-case ground resistance estimate (dry season):
       R_ground ≈ ρ/(2π·L) · ln(4L/d) ≈ {dry_rho/(2*np.pi*2.4) * np.log(4*2.4/0.016):.1f} Ω
       (L=2.4m rod, d=16mm diameter, ρ={dry_rho} Ω·m)
     • Best-case ground resistance (wet season):
       R_ground ≈ {avg_rho/(2*np.pi*2.4) * np.log(4*2.4/0.016):.1f} Ω
       (ρ={avg_rho} Ω·m)

  4. GILGAI MICRO-TOPOGRAPHY
     Houston Black Clay creates circular mounds/depressions.
     Select antenna location on a micro-high (better drainage,
     more consistent soil contact for ground rods).
""")
    print(f"{'═'*72}\n")


def try_plot(output_path=None):
    """Generate skin depth vs frequency plot if matplotlib is available."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("[!] matplotlib not available — skipping plot generation")
        return

    freqs_mhz = np.logspace(0, 3, 500)  # 1 MHz to 1 GHz
    freqs_hz = freqs_mhz * 1e6

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.patch.set_facecolor('#0a0a0a')
    for ax in (ax1, ax2):
        ax.set_facecolor('#0a0a0a')

    colors = {
        "saturated": "#0088ff",
        "moist":     "#00ccaa",
        "average":   "#ffcc00",
        "dry":       "#ff8844",
        "cracked":   "#ff4444",
    }

    # ── Left panel: Skin depth vs frequency ──
    for key, p in SOIL_PARAMS.items():
        depths = np.array([
            skin_depth_lossy(p['resistivity_ohm_m'], p['relative_permittivity'], f)
            for f in freqs_hz
        ])
        ax1.plot(freqs_mhz, depths * 100, color=colors[key],
                 linewidth=2, label=p['label'])

    # Mark beacon frequencies
    for f_mhz, lbl in [(146, '146 MHz'), (440, '440 MHz')]:
        ax1.axvline(x=f_mhz, color='#ffffff', linestyle=':', alpha=0.4)
        ax1.text(f_mhz * 1.05, ax1.get_ylim()[1] * 0.9 if ax1.get_ylim()[1] > 0 else 100,
                 lbl, color='#aaa', fontsize=9, rotation=90, va='top')

    ax1.set_xlabel('Frequency (MHz)', color='#ccc', fontsize=12)
    ax1.set_ylabel('Skin Depth (cm)', color='#ccc', fontsize=12)
    ax1.set_title('Skin Depth vs Frequency — Houston Black Clay',
                  color='#fff', fontsize=13)
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.tick_params(colors='#888')
    ax1.legend(facecolor='#1a1a1a', edgecolor='#333', labelcolor='#ccc',
               fontsize=9)
    ax1.grid(True, color='#222', linewidth=0.5, which='both')
    for spine in ax1.spines.values():
        spine.set_color('#333')

    # ── Right panel: Attenuation vs depth at 146 MHz ──
    depths_m = np.linspace(0, 2.0, 200)
    for key, p in SOIL_PARAMS.items():
        delta = skin_depth_lossy(p['resistivity_ohm_m'],
                                  p['relative_permittivity'],
                                  VHF_FREQ_MHZ * 1e6)
        atten = 8.686 / delta * depths_m  # dB
        ax2.plot(depths_m * 100, atten, color=colors[key],
                 linewidth=2, label=p['label'])

    ax2.axhline(y=8.686, color='#fff', linestyle='--', alpha=0.3)
    ax2.text(5, 8.686 + 1, '1/e (1 skin depth)', color='#888', fontsize=9)

    ax2.set_xlabel('Depth in Soil (cm)', color='#ccc', fontsize=12)
    ax2.set_ylabel('Cumulative Attenuation (dB)', color='#ccc', fontsize=12)
    ax2.set_title(f'146 MHz Attenuation vs Depth — Houston Black Clay',
                  color='#fff', fontsize=13)
    ax2.tick_params(colors='#888')
    ax2.legend(facecolor='#1a1a1a', edgecolor='#333', labelcolor='#ccc',
               fontsize=9)
    ax2.grid(True, color='#222', linewidth=0.5)
    ax2.invert_yaxis()
    for spine in ax2.spines.values():
        spine.set_color('#333')

    plt.tight_layout()
    out = output_path or 'ground_skin_depth.png'
    plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"[✓] Ground analysis plot saved: {out}")
    plt.close()


def main():
    p = argparse.ArgumentParser(
        description="Houston Black Clay Ground EM Analysis")
    p.add_argument('--plot', action='store_true', default=True,
                   help='Generate skin depth plot')
    p.add_argument('--output', type=str, default=None,
                   help='Plot output path')
    a = p.parse_args()

    # Full analysis at both beacon frequencies
    print_analysis(VHF_FREQ_MHZ)
    print_analysis(UHF_FREQ_MHZ)

    # Cross-frequency comparison
    print_comparison()

    # Site-specific grounding recommendations
    grounding_recommendations()

    # Generate plot
    if a.plot:
        try_plot(a.output)


if __name__ == '__main__':
    main()
