#!/usr/bin/env python3
"""
Free Space Path Loss & RF Link Budget Calculator
==================================================
Calculates FSPL for a 5W VHF signal at vertical distances up to 100,000 ft.
Generates a complete link budget table and CSV data for plotting.

Usage:  python link_budget.py [--freq 146.0] [--power 5.0] [--gain 7.5]
Deps:   numpy (required), matplotlib (optional)
"""

import argparse
import numpy as np

# ─── Physical Constants ──────────────────────────────────────────────────────
C = 299_792_458  # speed of light (m/s)
MI_TO_KM = 1.60934
FT_TO_KM = 0.0003048

# ─── Default System Parameters ───────────────────────────────────────────────
DEFAULT_FREQ_MHZ = 146.0
DEFAULT_TX_POWER_W = 5.0
DEFAULT_TX_GAIN_DBI = 7.5   # estimated Yagi gain
DEFAULT_RX_GAIN_DBI = 0.0   # isotropic receiver assumed
DEFAULT_CABLE_LOSS_DB = 1.0  # coax + connector losses


def watts_to_dbm(watts):
    return 10 * np.log10(watts * 1000)


def fspl_db(d_km, f_mhz):
    """Free Space Path Loss: FSPL = 20*log10(d_km) + 20*log10(f_MHz) + 32.45"""
    return 20 * np.log10(d_km) + 20 * np.log10(f_mhz) + 32.45


def link_budget(tx_power_w, tx_gain_dbi, rx_gain_dbi,
                cable_loss_db, d_km, f_mhz):
    """Calculate received power in dBm using link budget equation."""
    ptx = watts_to_dbm(tx_power_w)
    loss = fspl_db(d_km, f_mhz)
    prx = ptx + tx_gain_dbi + rx_gain_dbi - cable_loss_db - loss
    return prx, loss, ptx


def print_report(f_mhz, tx_w, tx_gain, rx_gain, cable_loss):
    """Print formatted link budget report."""
    ptx_dbm = watts_to_dbm(tx_w)
    wl = C / (f_mhz * 1e6)
    eirp = ptx_dbm + tx_gain - cable_loss

    print(f"\n{'='*72}")
    print(f"  RF LINK BUDGET — CE5 BEACON VERTICAL PATH ANALYSIS")
    print(f"{'='*72}")
    print(f"  Frequency:       {f_mhz:.3f} MHz (λ = {wl:.4f} m)")
    print(f"  TX Power:        {tx_w:.1f} W ({ptx_dbm:.2f} dBm)")
    print(f"  TX Antenna:      3-Element Yagi ({tx_gain:.1f} dBi)")
    print(f"  RX Antenna:      Isotropic ({rx_gain:.1f} dBi)")
    print(f"  Cable Loss:      {cable_loss:.1f} dB")
    print(f"  EIRP:            {eirp:.2f} dBm ({10**(eirp/10)/1000:.2f} W)")
    print(f"{'─'*72}")

    # FSPL formula proof
    print(f"\n  ┌─ FSPL FORMULA ────────────────────────────────────────────┐")
    print(f"  │  FSPL(dB) = 20·log₁₀(d_km) + 20·log₁₀(f_MHz) + 32.45   │")
    print(f"  │  P_RX(dBm) = P_TX + G_TX + G_RX - L_cable - FSPL        │")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    # Key altitude targets
    targets = [
        ("1 mile (5,280 ft)",       1 * MI_TO_KM),
        ("5 miles (26,400 ft)",     5 * MI_TO_KM),
        ("10 miles (52,800 ft)",    10 * MI_TO_KM),
        ("20 miles (105,600 ft)",   20 * MI_TO_KM),
        ("11.36 mi (60,000 ft)",    60000 * FT_TO_KM),
        ("18.94 mi (100,000 ft)",   100000 * FT_TO_KM),
        ("47.35 mi (250,000 ft)",   250000 * FT_TO_KM),
    ]

    print(f"\n  {'Altitude':<30} {'d (km)':>8} {'FSPL':>10} "
          f"{'P_RX':>10} {'SNR*':>8} {'Status':>12}")
    print(f"  {'─'*30} {'─'*8} {'─'*10} {'─'*10} {'─'*8} {'─'*12}")

    for label, d_km in targets:
        prx, loss, _ = link_budget(tx_w, tx_gain, rx_gain, cable_loss,
                                    d_km, f_mhz)
        snr = prx - (-130)  # vs -130 dBm noise floor

        if prx > -110:
            status = "✓ STRONG"
        elif prx > -120:
            status = "~ READABLE"
        elif prx > -130:
            status = "⚠ MARGINAL"
        else:
            status = "✗ BELOW NF"

        print(f"  {label:<30} {d_km:>8.2f} {loss:>9.2f}  "
              f"{prx:>9.2f} {snr:>7.1f}  {status:>12}")

    print(f"\n  * SNR referenced to -130 dBm narrowband FM noise floor")

    # ── Primary target: 20 miles vertical ──
    d20 = 20 * MI_TO_KM
    prx20, loss20, _ = link_budget(tx_w, tx_gain, rx_gain, cable_loss,
                                     d20, f_mhz)
    snr20 = prx20 - (-130)

    print(f"\n{'═'*72}")
    print(f"  ▶ PRIMARY TARGET: 20 MILES VERTICAL")
    print(f"{'─'*72}")
    print(f"  Distance:        {d20:.2f} km ({20:.0f} mi)")
    print(f"  FSPL:            {loss20:.2f} dB")
    print(f"  Received Power:  {prx20:.2f} dBm")
    print(f"  SNR (vs -130):   {snr20:.2f} dB")
    print(f"  Assessment:      {'Signal detectable' if snr20 > 0 else 'Below noise floor'}")
    print(f"{'═'*72}")

    # ── Stratospheric analysis ──
    d60k = 60000 * FT_TO_KM
    d100k = 100000 * FT_TO_KM
    prx60, loss60, _ = link_budget(tx_w, tx_gain, rx_gain, cable_loss, d60k, f_mhz)
    prx100, loss100, _ = link_budget(tx_w, tx_gain, rx_gain, cable_loss, d100k, f_mhz)

    print(f"\n  ┌─ STRATOSPHERIC REACH ──────────────────────────────────┐")
    print(f"  │  60,000 ft:  FSPL = {loss60:.1f} dB  →  P_RX = {prx60:.1f} dBm")
    print(f"  │  100,000 ft: FSPL = {loss100:.1f} dB  →  P_RX = {prx100:.1f} dBm")
    print(f"  │")
    print(f"  │  At 146 MHz, the ionosphere is largely transparent.")
    print(f"  │  VHF signals propagate through the D, E, and F layers")
    print(f"  │  with minimal absorption in the vertical direction.")
    print(f"  │  Additional atmospheric loss: < 0.5 dB (negligible).")
    print(f"  └──────────────────────────────────────────────────────────┘\n")


def save_altitude_csv(f_mhz, tx_w, tx_gain, rx_gain, cable_loss,
                       output_path='link_budget_altitude.csv'):
    """Save altitude vs. received power data as CSV."""
    altitudes_ft = np.logspace(2, 5.5, 200)
    altitudes_km = altitudes_ft * FT_TO_KM

    with open(output_path, 'w') as f:
        f.write("altitude_ft,altitude_km,fspl_db,prx_dbm,snr_db\n")
        for alt_ft, alt_km in zip(altitudes_ft, altitudes_km):
            prx, loss, _ = link_budget(tx_w, tx_gain, rx_gain,
                                        cable_loss, alt_km, f_mhz)
            snr = prx - (-130)
            f.write(f"{alt_ft:.0f},{alt_km:.4f},{loss:.2f},{prx:.2f},{snr:.2f}\n")

    print(f"[✓] Altitude data saved: {output_path}")
    print(f"    200 data points from 100 ft to 316,228 ft")


def try_plot(f_mhz, tx_w, tx_gain, rx_gain, cable_loss, output_path=None):
    """Generate altitude plot if matplotlib is available."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("[!] matplotlib not available — skipping plot generation")
        print("    Install with: pip install matplotlib")
        return

    altitudes_ft = np.logspace(2, 5.5, 500)
    altitudes_km = altitudes_ft * FT_TO_KM
    prx = np.array([
        link_budget(tx_w, tx_gain, rx_gain, cable_loss, d, f_mhz)[0]
        for d in altitudes_km
    ])

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    ax.plot(altitudes_ft / 1000, prx, color='#00ccff', linewidth=2.5)
    ax.axhline(y=-110, color='#00ff88', linestyle='--', alpha=0.6,
               label='Strong (−110 dBm)')
    ax.axhline(y=-120, color='#ffaa00', linestyle='--', alpha=0.6,
               label='Readable (−120 dBm)')
    ax.axhline(y=-130, color='#ff4444', linestyle='--', alpha=0.6,
               label='Noise Floor (−130 dBm)')
    ax.axvspan(60, 100, color='#ff6644', alpha=0.05,
               label='Target (60k-100k ft)')

    for alt_ft, lbl in [(60000, '60k ft'), (100000, '100k ft')]:
        d = alt_ft * FT_TO_KM
        p = link_budget(tx_w, tx_gain, rx_gain, cable_loss, d, f_mhz)[0]
        ax.plot(alt_ft / 1000, p, 'o', color='#ff6644', markersize=8)
        ax.annotate(f'{lbl}\n{p:.1f} dBm', xy=(alt_ft / 1000, p),
                     xytext=(15, 15), textcoords='offset points',
                     color='#ccc', fontsize=10,
                     arrowprops=dict(arrowstyle='->', color='#666'))

    ax.set_xlabel('Altitude (thousands of feet)', color='#ccc', fontsize=12)
    ax.set_ylabel('Received Power (dBm)', color='#ccc', fontsize=12)
    ax.set_title(f'CE5 Beacon Link Budget — {f_mhz:.1f} MHz, {tx_w:.0f}W + '
                 f'{tx_gain:.1f} dBi Yagi', color='#fff', fontsize=14)
    ax.set_xscale('log')
    ax.tick_params(colors='#888')
    ax.legend(facecolor='#1a1a1a', edgecolor='#333', labelcolor='#ccc')
    ax.grid(True, color='#222', linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color('#333')

    plt.tight_layout()
    out = output_path or 'link_budget_altitude.png'
    plt.savefig(out, dpi=200, bbox_inches='tight', facecolor='#0a0a0a')
    print(f"[✓] Link budget plot saved: {out}")
    plt.close()


def main():
    p = argparse.ArgumentParser(description="RF Link Budget Calculator")
    p.add_argument('--freq', type=float, default=DEFAULT_FREQ_MHZ)
    p.add_argument('--power', type=float, default=DEFAULT_TX_POWER_W)
    p.add_argument('--gain', type=float, default=DEFAULT_TX_GAIN_DBI)
    p.add_argument('--rx-gain', type=float, default=DEFAULT_RX_GAIN_DBI)
    p.add_argument('--cable-loss', type=float, default=DEFAULT_CABLE_LOSS_DB)
    p.add_argument('--plot', action='store_true', default=True)
    p.add_argument('--csv', action='store_true', default=True)
    p.add_argument('--output', type=str, default=None)
    a = p.parse_args()

    print_report(a.freq, a.power, a.gain, a.rx_gain, a.cable_loss)

    if a.csv:
        save_altitude_csv(a.freq, a.power, a.gain, a.rx_gain, a.cable_loss)
    if a.plot:
        try_plot(a.freq, a.power, a.gain, a.rx_gain, a.cable_loss, a.output)


if __name__ == '__main__':
    main()
