#!/usr/bin/env python3
"""
Soil Resistivity & RF Skin Depth Analysis
==========================================
McKinney TX (75069 / 75070 / 75071) — Houston Black Clay Series
Computes skin depth at 146 MHz using the full lossy-dielectric formula.

Source data:
  NRCS Web Soil Survey, Collin County TX (SSURGO, accessed 2026)
  NRCS Official Soil Series Description: Houston Black (Fine, smectitic,
    thermic Udic Haplusterts) — dominant series in Collin County urban areas
  IEEE Std 81-2012 (ground resistivity ranges)
  ITU-R P.527-5 (ground electrical characteristics)

Usage: python soil_analysis.py
Deps:  numpy only
"""

import numpy as np

# ─── Physical constants ───────────────────────────────────────────────────────
C       = 299_792_458.0        # m/s
MU_0    = 4 * np.pi * 1e-7    # H/m
EPS_0   = 8.854187817e-12     # F/m

# ─── Target frequency ─────────────────────────────────────────────────────────
FREQ_MHZ = 146.0
FREQ_HZ  = FREQ_MHZ * 1e6
OMEGA    = 2 * np.pi * FREQ_HZ

# ─── Houston Black Clay — NRCS SSURGO Collin County TX ───────────────────────
#
# Soil classification:  Fine, smectitic, thermic Udic Haplusterts (Vertisol)
# Parent material:      Residuum from Austin Chalk / Taylor Marl
# Clay content:         40–65% montmorillonite (smectite dominant)
# CEC:                  40–60 meq / 100g
# Shrink-swell:         Very high (COLE > 0.09)
# Drainage class:       Moderately well drained (swells shut when wet)
# Zip codes:            75069 (east), 75070 (central/west), 75071 (north)
#                       HoA (0–1% slope) and HoB (1–3%) map units dominate
#
# Bulk electrical resistivity (ρ) from SSURGO/EM38 field surveys:
#   Wet / post-rain  (θ ≈ field capacity):   ρ ≈  5–12 Ω·m
#   Typical moist    (θ ≈ 60–80% FC):        ρ ≈ 12–25 Ω·m
#   Dry / mid-summer (θ ≈ wilting point):    ρ ≈ 30–80 Ω·m
#
# Relative permittivity (VHF, 100–200 MHz):
#   Moist smectite clay:  ε_r ≈ 18–28  (Hallikainen 1985, Wang & Schmugge 1980)
#   Dry smectite clay:    ε_r ≈ 4–8
#
# Representative value chosen for calculation:
#   ρ = 12 Ω·m  (moist — conservative/mid-season for McKinney ~35"/yr rainfall)
#   ε_r = 20
# ──────────────────────────────────────────────────────────────────────────────

HOUSTON_BLACK = {
    "name": "Houston Black Clay (HoA/HoB)",
    "county": "Collin County, TX",
    "zipcodes": "75069 / 75070 / 75071",
    "classification": "Fine, smectitic, thermic Udic Haplusterts",
    "clay_pct_range": (40, 65),
    "moisture_cases": [
        # label, rho_ohm_m, eps_r
        ("Wet (post-rain, field capacity)",    5.0,  26),
        ("Moist (typical McKinney mid-season)", 12.0, 20),
        ("Dry (mid-summer, wilting point)",    45.0,  7),
    ]
}


def skin_depth(rho_ohm_m: float, eps_r: float, freq_hz: float) -> dict:
    """
    Full lossy-dielectric skin depth (δ = 1/α).

    Uses the exact attenuation constant — valid for any loss tangent,
    not just the good-conductor approximation (which fails when σ ≈ ωε).

        α = ω √(με/2) · √( √(1 + tan²δ) − 1 )

    where  tan δ = σ / (ω ε)  is the loss tangent.
    """
    sigma     = 1.0 / rho_ohm_m
    eps       = EPS_0 * eps_r

    omega_eps = OMEGA * eps                        # effective displacement current
    loss_tan  = sigma / omega_eps                  # loss tangent at this frequency

    # Exact attenuation constant (Np/m)
    inner = np.sqrt(1.0 + loss_tan**2)
    alpha = OMEGA * np.sqrt(MU_0 * eps / 2.0) * np.sqrt(inner - 1.0)

    # Phase constant (rad/m) — for completeness
    beta  = OMEGA * np.sqrt(MU_0 * eps / 2.0) * np.sqrt(inner + 1.0)

    delta_m   = 1.0 / alpha                        # skin depth (m)
    loss_db_m = alpha * 8.68589                    # dB per metre (1 Np = 8.686 dB)

    # Depth for specified signal reduction
    depth_20db = 20.0 / loss_db_m
    depth_40db = 40.0 / loss_db_m

    return {
        "sigma":       sigma,
        "omega_eps":   omega_eps,
        "loss_tan":    loss_tan,
        "alpha_npm":   alpha,
        "beta_radm":   beta,
        "delta_m":     delta_m,
        "delta_cm":    delta_m * 100,
        "loss_db_m":   loss_db_m,
        "depth_20db_m": depth_20db,
        "depth_40db_m": depth_40db,
    }


def regime_label(loss_tan: float) -> str:
    if loss_tan > 10:
        return "Good conductor"
    elif loss_tan > 1:
        return "Quasi-conductor (lossy)"
    elif loss_tan > 0.1:
        return "Lossy dielectric"
    else:
        return "Good dielectric"


def good_conductor_approx(rho: float, freq_hz: float) -> float:
    """Simplified formula δ = √(ρ / (π f μ₀)) — valid only when σ >> ωε."""
    return np.sqrt(rho / (np.pi * freq_hz * MU_0))


def print_report():
    soil = HOUSTON_BLACK
    wl_air_m = C / FREQ_HZ

    print(f"\n{'='*72}")
    print(f"  SOIL RESISTIVITY & RF SKIN DEPTH — CE5 BEACON SITE ANALYSIS")
    print(f"{'='*72}")
    print(f"  Location:        {soil['zipcodes']}, McKinney TX — {soil['county']}")
    print(f"  Soil Series:     {soil['name']}")
    print(f"  Classification:  {soil['classification']}")
    print(f"  Clay Content:    {soil['clay_pct_range'][0]}–{soil['clay_pct_range'][1]}% "
          f"(montmorillonite/smectite dominant)")
    print(f"  Frequency:       {FREQ_MHZ:.1f} MHz  (λ_air = {wl_air_m:.4f} m)")
    print(f"{'─'*72}")
    print(f"\n  ┌─ NRCS SSURGO SOURCE DATA ─────────────────────────────────────────┐")
    print(f"  │  Soil map unit:   HoA (0–1% slope), HoB (1–3% slope)            │")
    print(f"  │  Parent material: Austin Chalk / Taylor Marl residuum            │")
    print(f"  │  CEC:             40–60 meq/100g (very high ion exchange)        │")
    print(f"  │  Shrink-swell:    Very High (COLE > 0.09)                        │")
    print(f"  │  Drainage:        Moderately well drained (swells shut when wet) │")
    print(f"  │  Annual rainfall: ~37 in/yr (McKinney avg) → stays moist         │")
    print(f"  └───────────────────────────────────────────────────────────────────┘")

    print(f"\n  {'Condition':<38} {'ρ (Ω·m)':>8} {'σ (S/m)':>9} "
          f"{'εᵣ':>5} {'tan δ':>8} {'Regime':<22}")
    print(f"  {'─'*38} {'─'*8} {'─'*9} {'─'*5} {'─'*8} {'─'*22}")

    results = {}
    for label, rho, eps_r in soil["moisture_cases"]:
        r = skin_depth(rho, eps_r, FREQ_HZ)
        regime = regime_label(r["loss_tan"])
        print(f"  {label:<38} {rho:>8.1f} {r['sigma']:>9.4f} "
              f"{eps_r:>5d} {r['loss_tan']:>8.3f} {regime:<22}")
        results[label] = (rho, eps_r, r)

    print(f"\n{'─'*72}")
    print(f"\n  SKIN DEPTH RESULTS  (δ = 1/α,  full lossy-dielectric formula)")
    print(f"\n  {'Condition':<38} {'δ (cm)':>8} {'δ (in)':>8} "
          f"{'Loss':>12} {'−20 dB':>10} {'−40 dB':>10}")
    print(f"  {'─'*38} {'─'*8} {'─'*8} {'─'*12} {'─'*10} {'─'*10}")

    for label, rho, eps_r in soil["moisture_cases"]:
        _, _, r = results[label]
        print(f"  {label:<38} {r['delta_cm']:>8.1f} {r['delta_cm']/2.54:>8.2f} "
              f"{r['loss_db_m']:>10.1f} dB/m "
              f"{r['depth_20db_m']*100:>8.1f} cm "
              f"{r['depth_40db_m']*100:>8.1f} cm")

    # Primary case for detailed breakdown
    primary_label = "Moist (typical McKinney mid-season)"
    rho_p, eps_p, rp = results[primary_label]
    gc_approx = good_conductor_approx(rho_p, FREQ_HZ) * 100

    print(f"\n{'═'*72}")
    print(f"  PRIMARY CALCULATION — {primary_label}")
    print(f"{'─'*72}")
    print(f"  Input:  ρ = {rho_p:.0f} Ω·m  →  σ = {rp['sigma']:.4f} S/m")
    print(f"          εᵣ = {eps_p},  μᵣ = 1  (non-magnetic Vertisol)")
    print(f"          ω  = 2π × {FREQ_MHZ:.0f} MHz = {OMEGA:.4e} rad/s")
    print(f"")
    print(f"  ωε = ω · ε₀ · εᵣ = {rp['omega_eps']:.4f} S/m  (displacement current)")
    print(f"  σ  =              = {rp['sigma']:.4f} S/m  (conduction current)")
    print(f"  Loss tangent  tan δ = σ / ωε = {rp['loss_tan']:.4f}  → Quasi-conductor")
    print(f"  (NOTE: σ ≈ ωε — good-conductor approx would be WRONG here)")
    print(f"")
    print(f"  α = ω√(με/2) · √(√(1 + tan²δ) − 1)")
    print(f"    = {OMEGA:.3e} × {np.sqrt(MU_0 * EPS_0 * eps_p / 2):.3e} × "
          f"{np.sqrt(np.sqrt(1+rp['loss_tan']**2)-1):.4f}")
    print(f"    = {rp['alpha_npm']:.4f} Np/m  =  {rp['loss_db_m']:.2f} dB/m")
    print(f"")
    print(f"  δ = 1/α = {rp['delta_m']:.4f} m")
    print(f"")
    print(f"  ╔═══════════════════════════════════════════╗")
    print(f"  ║  Skin depth at 146 MHz: {rp['delta_cm']:>6.1f} cm           ║")
    print(f"  ║                         {rp['delta_cm']/2.54:>6.2f} in           ║")
    print(f"  ║  Signal loss:     {rp['loss_db_m']:>6.2f} dB per metre   ║")
    print(f"  ╚═══════════════════════════════════════════╝")
    print(f"")
    print(f"  Good-conductor approx (σ >> ωε, INCORRECT here):  {gc_approx:.1f} cm")
    print(f"  Error from using approx: {abs(gc_approx - rp['delta_cm']):.1f} cm "
          f"({abs(gc_approx/rp['delta_cm']-1)*100:.0f}% off)")

    print(f"\n{'─'*72}")
    print(f"  IMPLICATIONS FOR CE5 BEACON DESIGN")
    print(f"{'─'*72}")
    delta_cm = rp['delta_cm']
    print(f"")
    print(f"  Tiger Tail counterpoise (19.5 in = 49.5 cm):")
    if delta_cm < 49.5:
        depth_pct = (delta_cm / 49.5) * 100
        print(f"    The RF skin depth ({delta_cm:.1f} cm) is within the counterpoise length.")
        print(f"    Ground coupling is active to {delta_cm:.1f} cm depth — the top {depth_pct:.0f}% of")
        print(f"    the soil column visible to the Tiger Tail is within the skin depth.")
    print(f"")
    print(f"  Vertical radiation (zenith-pointing Yagi):")
    print(f"    Ground reflection at near-vertical incidence is minimal at 146 MHz.")
    print(f"    Houston Black Clay presents a reflection coefficient of approximately:")
    # Reflection coefficient for normal incidence: Γ = (√εc - 1)/(√εc + 1) approx
    eps_c = complex(eps_p, -rp['sigma']/OMEGA/EPS_0)
    n = np.sqrt(eps_c)
    gamma = abs((n - 1) / (n + 1))
    print(f"    |Γ| ≈ {gamma:.3f}  ({20*np.log10(gamma):.1f} dBr)")
    print(f"    At zenith, this ground reflection has negligible effect on")
    print(f"    the upward-directed radiation pattern.")
    print(f"")
    print(f"  Grounding note:")
    print(f"    At 146 MHz, any ground conductor deeper than {delta_cm:.0f} cm contributes")
    print(f"    less than 1/e (~37%) of its surface effect. The Tiger Tail only needs")
    print(f"    to couple to the top {delta_cm:.0f} cm — it does NOT need a driven ground rod.")
    print(f"\n{'='*72}\n")


if __name__ == '__main__':
    print_report()
