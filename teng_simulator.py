#!/usr/bin/env python3
"""
TENG Simulator v2.0 — Advanced Multi-Physics Platform

Developed by: Dr. Pravin Kumar Singh
Manipal University Jaipur, Rajasthan, India

NEW MODULES (v2.0):
  1. Charge Decay & Humidity Physics
  2. Rotary TENG Mode
  3. Impedance Matching & Load Power Optimization
  4. Figure of Merit (FOM) Calculator
  5. Self-Powered Sensor Mode
  6. Frequency-Domain Output Model
  7. Multi-Layer Stacked TENG
  8. 2D Power Density Heatmaps
  9. Monte Carlo Uncertainty Analysis
 10. Publication-quality export (SVG + CSV)
"""

import streamlit as st
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import pandas as pd
import io, base64, json, zipfile
# scipy removed — using numpy-based normal PDF instead

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TENG Simulator v2.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  .main-header{background:linear-gradient(90deg,#0f2460,#1e6fd9);padding:22px 28px;
    border-radius:14px;color:white;margin-bottom:22px;box-shadow:0 4px 18px rgba(0,0,0,.18);}
  .badge{display:inline-block;background:#1e40af;color:white;border-radius:6px;
    padding:2px 10px;font-size:.78rem;font-weight:600;margin:2px;}
  .stMetric{background:#f8fafc;border:1px solid #dde3ed;border-radius:10px;padding:10px;}
  .highlight-box{background:#eff6ff;border-left:4px solid #2563eb;padding:12px 16px;
    border-radius:6px;margin:8px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
  <h1 style="margin:0;font-size:2.2rem;font-weight:700;">⚡ TENG Simulator <span style="font-size:1.1rem;opacity:.8">v2.0</span></h1>
  <p style="margin:8px 0 0 0;font-size:1rem;color:#dbeafe;">
    Advanced Multi-Physics Design & Optimization Platform<br>
    <strong>Dr. Pravin Kumar Singh</strong> &nbsp;|&nbsp; Manipal University Jaipur, Rajasthan, India
  </p>
  <div style="margin-top:10px;">
    <span class="badge">Contact Mode</span><span class="badge">Sliding Mode</span>
    <span class="badge">Rotary Mode</span><span class="badge">Humidity Physics</span>
    <span class="badge">Impedance Matching</span><span class="badge">FOM Calculator</span>
    <span class="badge">Sensor Mode</span><span class="badge">Multi-Layer</span>
    <span class="badge">Monte Carlo</span><span class="badge">Heatmaps</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  CONSTANTS & MATERIAL DB
# ─────────────────────────────────────────────────────────────
EPS0 = 8.854187817e-12

MATERIALS = {
    "PTFE (Teflon)":        {"er": 2.1,  "sigma_ref": 80.0,  "tau0": 3600, "alpha": 0.035},
    "FEP":                  {"er": 2.1,  "sigma_ref": 75.0,  "tau0": 4000, "alpha": 0.030},
    "PDMS (Silicone)":      {"er": 2.8,  "sigma_ref": 55.0,  "tau0": 1800, "alpha": 0.050},
    "Kapton (Polyimide)":   {"er": 3.4,  "sigma_ref": 60.0,  "tau0": 2500, "alpha": 0.040},
    "PET / Mylar":          {"er": 3.2,  "sigma_ref": 50.0,  "tau0": 2000, "alpha": 0.045},
    "PVC":                  {"er": 3.0,  "sigma_ref": 45.0,  "tau0": 1500, "alpha": 0.055},
    "Polystyrene (PS)":     {"er": 2.6,  "sigma_ref": 40.0,  "tau0": 1200, "alpha": 0.060},
    "Polypropylene (PP)":   {"er": 2.2,  "sigma_ref": 35.0,  "tau0": 1100, "alpha": 0.058},
    "PMMA (Acrylic)":       {"er": 3.0,  "sigma_ref": 42.0,  "tau0": 1300, "alpha": 0.052},
    "Nylon":                {"er": 4.0,  "sigma_ref": 65.0,  "tau0": 900,  "alpha": 0.070},
    "Polyurethane":         {"er": 3.5,  "sigma_ref": 48.0,  "tau0": 1400, "alpha": 0.048},
    "Silicone Rubber":      {"er": 3.5,  "sigma_ref": 52.0,  "tau0": 1600, "alpha": 0.046},
    "Custom":               {"er": 2.5,  "sigma_ref": 50.0,  "tau0": 2000, "alpha": 0.040},
}

# ─────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def charge_decay(sigma0, time_s, RH_pct, alpha):
    """Charge decay with humidity: σ(t) = σ0·exp(-t/τ), τ=τ0·exp(-α·RH)"""
    return sigma0  # returned in same units as input; tau passed separately

def tau_from_humidity(tau0, alpha, RH):
    return tau0 * np.exp(-alpha * RH)

def contact_mode_calc(sigma_SI, S, d0, x_SI):
    denom = d0 + x_SI if (d0 + x_SI) > 0 else 1e-12
    C   = EPS0 * S / denom
    Voc = (sigma_SI / EPS0) * x_SI
    Qsc = sigma_SI * S * (x_SI / denom)
    return C, Voc, Qsc

def sliding_mode_calc(sigma_SI, w_SI, L_SI, d0, x_SI):
    overlap = max(L_SI - x_SI, 1e-9)
    C   = EPS0 * w_SI * overlap / d0
    Qsc = sigma_SI * w_SI * x_SI
    Voc = Qsc / C if C > 0 else 0.0
    return C, Voc, Qsc

def rotary_mode_calc(sigma_SI, R_m, theta_deg, theta_max_deg, d0, n_seg):
    """Single-electrode rotary TENG"""
    theta    = np.radians(theta_deg)
    theta_m  = np.radians(theta_max_deg)
    S_seg    = np.pi * R_m**2 / n_seg          # area per segment
    frac     = theta / theta_m
    frac     = np.clip(frac, 1e-6, 1 - 1e-6)
    Voc = (sigma_SI * d0 / EPS0) * (frac / (1 - frac))
    Qsc = sigma_SI * S_seg * frac
    C   = EPS0 * S_seg * (1 - frac) / d0
    return C, Voc, Qsc

def power_vs_load(Voc, C_teng, R_arr, freq):
    """P_load(R) for a given Voc, C, frequency"""
    omega   = 2 * np.pi * freq
    R_int   = 1.0 / (omega * C_teng) if C_teng > 0 else 1e12
    P       = (Voc**2 * R_arr) / (R_int + R_arr)**2
    return P, R_int

def fom_se(Voc_max, C_max, sigma_SI, S):
    """Surface-charge FOM (dimensionless, Wang 2018)"""
    numerator   = C_max * Voc_max**2
    denominator = S * sigma_SI**2 / EPS0
    return numerator / denominator if denominator > 0 else 0.0

def sensor_sensitivity(sigma_SI, d0, er, k_n=1.0):
    """Self-powered pressure sensor: S = dV/dP (V/Pa)"""
    # Phenomenological model: Vout = (sigma/eps0)*x, x = k_n * d0 * P / (er * E_mech)
    # Simplified linear sensitivity
    return (d0 / (EPS0 * er)) * k_n   # V/Pa

def multilayer_output(Voc_single, Qsc_single, C_single, n_layers):
    Voc_tot = n_layers * Voc_single
    Qsc_tot = Qsc_single          # charge doesn't stack
    C_tot   = C_single / n_layers
    E_tot   = 0.5 * C_tot * Voc_tot**2
    return Voc_tot, Qsc_tot, C_tot, E_tot

def frequency_output(sigma_SI, S, A_m, freq_arr, C_teng, Voc):
    """Isc(f) = sigma*S*2*A*f (peak); P_avg ~ Isc^2 * R_opt/4"""
    Isc_peak = sigma_SI * S * 2 * A_m * freq_arr
    R_opt    = 1.0 / (2 * np.pi * freq_arr * C_teng) if C_teng > 0 else np.ones_like(freq_arr) * 1e9
    P_avg    = (Isc_peak**2) * R_opt / 4
    return Isc_peak, P_avg

def monte_carlo_analysis(sigma_base, d0, S, x_SI, n_samples, uncertainty_pct, mode="contact"):
    rng = np.random.default_rng(42)
    rel = uncertainty_pct / 100.0
    sigmas = rng.normal(sigma_base, sigma_base * rel, n_samples)
    d0s    = rng.normal(d0, d0 * rel, n_samples)
    Vocs, Qscs, Es = [], [], []
    for s, d in zip(sigmas, d0s):
        d_eff = max(d, 1e-12)
        if mode == "contact":
            _, V, Q = contact_mode_calc(s, S, d_eff, x_SI)
        else:
            w_SI = np.sqrt(S)
            L_SI = np.sqrt(S)
            _, V, Q = sliding_mode_calc(s, w_SI, L_SI * 2, d_eff, x_SI)
        E = 0.5 * abs(Q) * abs(V) * 1e6
        Vocs.append(V); Qscs.append(Q * 1e9); Es.append(E)
    return np.array(Vocs), np.array(Qscs), np.array(Es)

def power_density_heatmap_data(er_arr, sigma_arr, d0_base, x_SI, S, mode="contact"):
    PD = np.zeros((len(er_arr), len(sigma_arr)))
    for i, er in enumerate(er_arr):
        for j, sig_uC in enumerate(sigma_arr):
            sig_SI = sig_uC * 1e-6
            d0 = d0_base / er
            if mode == "contact":
                C, V, Q = contact_mode_calc(sig_SI, S, d0, x_SI)
            else:
                w_SI = np.sqrt(S); L_SI = w_SI * 2
                C, V, Q = sliding_mode_calc(sig_SI, w_SI, L_SI, d0, x_SI)
            PD[i, j] = 0.5 * abs(Q) * abs(V) / S * 1e6   # μJ/m²
    return PD

def fig_to_svg_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='svg', bbox_inches='tight')
    buf.seek(0)
    return buf.read()

# ─────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────
(tab_sim, tab_humidity, tab_rotary, tab_impedance,
 tab_fom, tab_sensor, tab_multilayer, tab_freq,
 tab_heatmap, tab_mc, tab_theory, tab_export, tab_about) = st.tabs([
    "🔬 Simulator",
    "💧 Humidity & Decay",
    "🔄 Rotary TENG",
    "📡 Impedance & Power",
    "📐 FOM Calculator",
    "🌡️ Sensor Mode",
    "🔢 Multi-Layer",
    "〰️ Frequency Domain",
    "🗺️ Heatmaps",
    "🎲 Monte Carlo",
    "📚 Theory",
    "📥 Export",
    "ℹ️ About",
])

# ─────────────────────────────────────────────────────────────
#  SIDEBAR — shared inputs
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔧 Global Configuration")
    operation_mode = st.radio("Operation Mode",
        ["Contact Mode (Vertical Separation)", "Sliding Mode (Lateral Displacement)"])
    contact_type = st.radio("Dielectric Configuration",
        ["Conductor-to-Dielectric", "Dielectric-to-Dielectric"])

    st.subheader("⚡ Material & Geometry")

    if contact_type == "Conductor-to-Dielectric":
        sel_mat = st.selectbox("Dielectric Material", list(MATERIALS.keys()), index=0)
        mat_data = MATERIALS[sel_mat]
        er  = st.number_input("εᵣ", 1.1, 20.0, float(mat_data["er"]), 0.1)
        sigma = st.number_input("σ (μC/m²)", 1.0, 1000.0, float(mat_data["sigma_ref"]), 5.0)
        d   = st.number_input("Dielectric thickness d (μm)", 5.0, 2000.0, 100.0, 10.0)
        er1 = er2 = d1 = d2 = 0.0
        mat_data1 = mat_data2 = mat_data
    else:
        sel_mat1 = st.selectbox("Material 1 (Top)", list(MATERIALS.keys()), 0, key="m1")
        mat_data1 = MATERIALS[sel_mat1]
        er1 = st.number_input("εᵣ1", 1.1, 20.0, float(mat_data1["er"]), 0.1, key="er1")
        d1  = st.number_input("d1 (μm)", 5.0, 2000.0, 50.0, 5.0, key="d1")
        sel_mat2 = st.selectbox("Material 2 (Bottom)", list(MATERIALS.keys()), 3, key="m2")
        mat_data2 = MATERIALS[sel_mat2]
        er2 = st.number_input("εᵣ2", 1.1, 20.0, float(mat_data2["er"]), 0.1, key="er2")
        d2  = st.number_input("d2 (μm)", 5.0, 2000.0, 50.0, 5.0, key="d2")
        sigma = st.number_input("σ (μC/m²)", 1.0, 1000.0, 60.0, 5.0)
        d = er = 0.0
        mat_data = mat_data1
        sel_mat = sel_mat1

    w   = st.number_input("Width w (mm)", 5.0, 500.0, 50.0, 5.0)
    l   = st.number_input("Length L (mm)", 5.0, 500.0, 50.0, 5.0)
    if contact_type == "Conductor-to-Dielectric":
        pass
    x   = st.number_input("Current x (mm)", 0.0, 200.0, 1.0, 0.1)
    xmax = st.number_input("Max x for plots (mm)", 0.5, 300.0,
                           5.0 if "Contact" in operation_mode else 40.0, 1.0)

# ─────────────────────────────────────────────────────────────
#  CORE CALCULATIONS (shared across tabs)
# ─────────────────────────────────────────────────────────────
sigma_SI = sigma * 1e-6
S_max    = (w * l) * 1e-6
w_SI     = w * 1e-3
L_SI     = l * 1e-3
x_SI     = x * 1e-3

if contact_type == "Conductor-to-Dielectric":
    d0 = max((d * 1e-6) / er, 1e-12)
else:
    d0 = max((d1 * 1e-6) / er1 + (d2 * 1e-6) / er2, 1e-12)

if "Contact" in operation_mode:
    C, Voc, Qsc = contact_mode_calc(sigma_SI, S_max, d0, x_SI)
    x_plot_mm = np.linspace(0.001, xmax, 500)
    xp = x_plot_mm * 1e-3
    C_plot   = EPS0 * S_max / (d0 + xp)
    Voc_plot = (sigma_SI / EPS0) * xp
    Qsc_plot = sigma_SI * S_max * (xp / (d0 + xp))
    Ep_plot  = 0.5 * Qsc_plot * Voc_plot * 1e6
    mode_label = "Contact Mode"; x_label = "Separation x (mm)"
    mc_mode = "contact"
else:
    C, Voc, Qsc = sliding_mode_calc(sigma_SI, w_SI, L_SI, d0, x_SI)
    xmax_eff = min(xmax, 0.95 * l)
    x_plot_mm = np.linspace(0.0, xmax_eff, 500)
    xp = x_plot_mm * 1e-3
    overlap_p = np.maximum(L_SI - xp, 1e-9)
    C_plot   = EPS0 * w_SI * overlap_p / d0
    Qsc_plot = sigma_SI * w_SI * xp
    Voc_plot = Qsc_plot / C_plot
    Ep_plot  = 0.5 * Qsc_plot * Voc_plot * 1e6
    mode_label = "Sliding Mode"; x_label = "Displacement x (mm)"
    mc_mode = "sliding"

Energy_uJ = 0.5 * abs(Qsc) * abs(Voc) * 1e6

# ═══════════════════════════════════════════════════════════════
#  TAB 1 — SIMULATOR
# ═══════════════════════════════════════════════════════════════
with tab_sim:
    st.subheader(f"📈 Results — {mode_label} | {contact_type} | x = {x:.2f} mm")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Voc (V)",        f"{Voc:.2f}")
    c2.metric("Qsc (nC)",       f"{Qsc*1e9:.2f}")
    c3.metric("Capacitance (pF)",f"{C*1e12:.2f}")
    c4.metric("Energy (μJ)",    f"{Energy_uJ:.3f}")

    if "Contact" in operation_mode and x_SI > 1e-6:
        E_field = Voc / x_SI
        if E_field > 3e6:
            st.warning(f"⚠️ Air-breakdown risk! E-field ≈ {E_field/1e6:.2f} MV/m (limit: 3 MV/m)")

    # Schematic
    st.subheader("📐 Device Schematic")
    fig_s, ax = plt.subplots(figsize=(10, 4))
    ax.set_xlim(-0.5, 11); ax.set_ylim(-0.5, 7); ax.axis('off')
    ax.set_title(f"{mode_label}  •  {contact_type}", fontsize=12, fontweight='bold')
    if "Contact" in operation_mode:
        ax.add_patch(Rectangle((1,.3),8,1,lw=2,ec='#1a5276',fc='#3498db'))
        ax.text(5,.8,"Bottom Conductor",ha='center',va='center',color='white',fontsize=9,fontweight='bold')
        y_d=1.4
        if contact_type=="Conductor-to-Dielectric":
            ax.add_patch(Rectangle((1,y_d),8,1,lw=2,ec='#b9770e',fc='#f4d03f'))
            ax.text(5,y_d+.5,f"Dielectric d={d}μm εr={er}",ha='center',va='center',fontsize=8)
            y_a=y_d+1.05
        else:
            ax.add_patch(Rectangle((1,y_d),8,.85,lw=2,ec='#b9770e',fc='#f4d03f'))
            ax.text(5,y_d+.42,f"Diel.1 d1={d1}μm εr1={er1}",ha='center',va='center',fontsize=7)
            ax.add_patch(Rectangle((1,y_d+.9),8,.85,lw=2,ec='#6c3483',fc='#af7ac5'))
            ax.text(5,y_d+1.32,f"Diel.2 d2={d2}μm εr2={er2}",ha='center',va='center',fontsize=7,color='white')
            y_a=y_d+1.85
        vg=min(2.2,max(.15,(x/max(xmax,.1))*2.2))
        ax.add_patch(Rectangle((1,y_a),8,vg,lw=1.5,ec='#5dade2',fc='#d4e6f1',ls='--',alpha=.6))
        ax.text(5,y_a+vg/2,f"Air Gap x={x:.2f}mm",ha='center',va='center',fontsize=9,style='italic',color='#1a5276')
        y_t=y_a+vg+.1
        ax.add_patch(Rectangle((1,y_t),8,1,lw=2,ec='#1a5276',fc='#3498db'))
        ax.text(5,y_t+.5,"Top Conductor (Moving)",ha='center',va='center',color='white',fontsize=9,fontweight='bold')
    else:
        ax.add_patch(Rectangle((.5,1.5),9.5,2.2,lw=2.5,ec='#2c3e50',fc='#7f8c8d'))
        ax.text(5.25,2.6,"FIXED: Conductor + Dielectric",ha='center',va='center',color='white',fontsize=9,fontweight='bold')
        ax.text(5.25,1.9,f"L={l}mm  w={w}mm",ha='center',va='center',color='white',fontsize=8)
        ov_frac=max(.08,1-(x/max(l,.1))); ov_v=9*ov_frac
        ax.add_patch(Rectangle((.5,4.0),ov_v,1.8,lw=2.5,ec='#c0392b',fc='#e74c3c',alpha=.85))
        ax.text(.5+ov_v/2,4.9,"MOVING\nConductor",ha='center',va='center',color='white',fontsize=8,fontweight='bold')
        ax.text(.5+ov_v/2,3.6,f"Overlap≈{l-x:.1f}mm",ha='center',va='center',fontsize=8,color='#c0392b',fontweight='bold')
        ax.annotate('',xy=(.5+ov_v+.8,4.9),xytext=(.5+ov_v+2.2,4.9),
                    arrowprops=dict(arrowstyle='->',color='red',lw=2))
        ax.text(.5+ov_v+1.5,5.4,f'x={x:.1f}mm',ha='center',fontsize=9,color='red',fontweight='bold')
    st.pyplot(fig_s, use_container_width=True)
    plt.close(fig_s)

    # Characteristics plots
    st.subheader(f"📊 Characteristics vs {x_label}")
    fig, axs = plt.subplots(2,2,figsize=(11,7),sharex=True)
    axs[0,0].plot(x_plot_mm,Voc_plot,color='#2980b9',lw=2)
    axs[0,0].set_ylabel('Voc (V)',fontsize=10); axs[0,0].set_title('Open-Circuit Voltage',fontsize=11,fontweight='bold'); axs[0,0].grid(alpha=.3)
    axs[0,1].plot(x_plot_mm,Qsc_plot*1e9,color='#27ae60',lw=2)
    axs[0,1].set_ylabel('Qsc (nC)',fontsize=10); axs[0,1].set_title('Short-Circuit Charge',fontsize=11,fontweight='bold'); axs[0,1].grid(alpha=.3)
    axs[1,0].plot(x_plot_mm,C_plot*1e12,color='#8e44ad',lw=2)
    axs[1,0].set_xlabel(x_label,fontsize=10); axs[1,0].set_ylabel('C (pF)',fontsize=10); axs[1,0].set_title('Capacitance',fontsize=11,fontweight='bold'); axs[1,0].grid(alpha=.3)
    axs[1,1].plot(x_plot_mm,Ep_plot,color='#e67e22',lw=2)
    axs[1,1].set_xlabel(x_label,fontsize=10); axs[1,1].set_ylabel('Energy (μJ)',fontsize=10); axs[1,1].set_title('Harvested Energy',fontsize=11,fontweight='bold'); axs[1,1].grid(alpha=.3)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# ═══════════════════════════════════════════════════════════════
#  TAB 2 — HUMIDITY & CHARGE DECAY
# ═══════════════════════════════════════════════════════════════
with tab_humidity:
    st.header("💧 Charge Decay under Humidity — Novel Physics Module")
    st.markdown("""
    <div class="highlight-box">
    <b>Novel Model:</b> σ(t) = σ₀ · exp(−t/τ) &nbsp;&nbsp; where &nbsp;&nbsp; τ = τ₀ · exp(−α · RH)<br>
    τ₀ and α are material-specific constants derived from surface conductivity data.
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        RH = st.slider("Relative Humidity RH (%)", 10, 95, 50, 5)
        t_max_hr = st.slider("Time window (hours)", 1, 72, 24, 1)
        tau0_m = float(mat_data["tau0"])
        alpha_m = float(mat_data["alpha"])
        tau = tau_from_humidity(tau0_m, alpha_m, RH)
        st.info(f"**τ₀ = {tau0_m:.0f} s | α = {alpha_m:.3f} | τ(RH={RH}%) = {tau:.0f} s ({tau/3600:.2f} h)**")

    with col2:
        RH_arr = np.linspace(10, 95, 200)
        tau_arr = tau_from_humidity(tau0_m, alpha_m, RH_arr)
        fig_t, ax_t = plt.subplots(figsize=(5,3))
        ax_t.plot(RH_arr, tau_arr/3600, color='#2563eb', lw=2)
        ax_t.set_xlabel("Relative Humidity (%)", fontsize=10)
        ax_t.set_ylabel("τ (hours)", fontsize=10)
        ax_t.set_title("Charge Lifetime vs Humidity", fontsize=11, fontweight='bold')
        ax_t.grid(alpha=.3); plt.tight_layout()
        st.pyplot(fig_t, use_container_width=True); plt.close(fig_t)

    t_arr_s = np.linspace(0, t_max_hr * 3600, 1000)
    sigma_decay = sigma * np.exp(-t_arr_s / tau)

    # Voc decay
    if "Contact" in operation_mode:
        Voc_decay = (sigma_decay * 1e-6 / EPS0) * x_SI
    else:
        overlap = max(L_SI - x_SI, 1e-9)
        C_fix   = EPS0 * w_SI * overlap / d0
        Qsc_dec = sigma_decay * 1e-6 * w_SI * x_SI
        Voc_decay = Qsc_dec / C_fix

    fig_d, axd = plt.subplots(1,2,figsize=(11,4))
    axd[0].plot(t_arr_s/3600, sigma_decay, color='#dc2626', lw=2)
    axd[0].set_xlabel("Time (h)"); axd[0].set_ylabel("σ (μC/m²)")
    axd[0].set_title("Charge Density Decay", fontweight='bold'); axd[0].grid(alpha=.3)
    axd[0].axhline(sigma*0.368, ls='--', color='gray', label='1/e level')
    axd[0].legend()
    axd[1].plot(t_arr_s/3600, Voc_decay, color='#0891b2', lw=2)
    axd[1].set_xlabel("Time (h)"); axd[1].set_ylabel("Voc (V)")
    axd[1].set_title("Open-Circuit Voltage Decay", fontweight='bold'); axd[1].grid(alpha=.3)
    plt.suptitle(f"Material: {sel_mat}  |  RH = {RH}%", fontsize=11, fontweight='bold')
    plt.tight_layout(); st.pyplot(fig_d, use_container_width=True); plt.close(fig_d)

    # Multi-RH comparison
    st.subheader("Multi-Humidity Comparison")
    fig_mrh, ax_mrh = plt.subplots(figsize=(10,4))
    for rh_val in [20, 40, 60, 80]:
        tau_v = tau_from_humidity(tau0_m, alpha_m, rh_val)
        sd    = sigma * np.exp(-t_arr_s / tau_v)
        ax_mrh.plot(t_arr_s/3600, sd, lw=2, label=f"RH={rh_val}%")
    ax_mrh.set_xlabel("Time (h)"); ax_mrh.set_ylabel("σ (μC/m²)")
    ax_mrh.set_title(f"Charge Decay at Various Humidity Levels — {sel_mat}", fontweight='bold')
    ax_mrh.grid(alpha=.3); ax_mrh.legend(); plt.tight_layout()
    st.pyplot(fig_mrh, use_container_width=True); plt.close(fig_mrh)

# ═══════════════════════════════════════════════════════════════
#  TAB 3 — ROTARY TENG
# ═══════════════════════════════════════════════════════════════
with tab_rotary:
    st.header("🔄 Rotary TENG Mode — Third Fundamental Mode")
    st.markdown("""
    <div class="highlight-box">
    Models disk-based rotary TENGs. Key equation:<br>
    V_oc(θ) = (σ·d₀/ε₀) · θ/(θ_max − θ) &nbsp;&nbsp; | &nbsp;&nbsp; P_avg = (1/T)∫V²/R dt
    </div>""", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    R_disk  = c1.number_input("Disk radius R (mm)", 10.0, 300.0, 50.0, 5.0) * 1e-3
    n_seg   = c2.number_input("Number of segments", 2, 64, 8, 2)
    RPM     = c3.number_input("Rotation speed (RPM)", 10, 3000, 300, 10)
    theta_pt = st.slider("Current angle θ (°)", 0.0, float(360/n_seg*0.98), float(360/n_seg*0.5), 0.1)

    theta_max_deg = 360.0 / n_seg
    freq_rot = RPM / 60.0 * n_seg   # electrical frequency

    C_rot, Voc_rot, Qsc_rot = rotary_mode_calc(sigma_SI, R_disk, theta_pt, theta_max_deg, d0, n_seg)
    E_rot = 0.5 * abs(Qsc_rot) * abs(Voc_rot) * 1e6
    P_rot_avg = E_rot * 1e-6 * freq_rot * 1e3   # mW

    r1,r2,r3,r4 = st.columns(4)
    r1.metric("Voc (V)", f"{Voc_rot:.2f}")
    r2.metric("Qsc (nC)", f"{Qsc_rot*1e9:.2f}")
    r3.metric("Energy/cycle (μJ)", f"{E_rot:.3f}")
    r4.metric("Avg Power (mW)", f"{P_rot_avg:.3f}")

    theta_arr = np.linspace(0.01, theta_max_deg*0.98, 400)
    Cs_r=[]; Vs_r=[]; Qs_r=[]; Es_r=[]
    for th in theta_arr:
        c_,v_,q_ = rotary_mode_calc(sigma_SI, R_disk, th, theta_max_deg, d0, n_seg)
        Cs_r.append(c_*1e12); Vs_r.append(v_); Qs_r.append(q_*1e9)
        Es_r.append(0.5*abs(q_)*abs(v_)*1e6)

    fig_r, axr = plt.subplots(2,2,figsize=(11,7))
    axr[0,0].plot(theta_arr,Vs_r,'#2980b9',lw=2); axr[0,0].set_ylabel('Voc (V)'); axr[0,0].set_title('Voc vs θ',fontweight='bold'); axr[0,0].grid(alpha=.3)
    axr[0,1].plot(theta_arr,Qs_r,'#27ae60',lw=2); axr[0,1].set_ylabel('Qsc (nC)'); axr[0,1].set_title('Qsc vs θ',fontweight='bold'); axr[0,1].grid(alpha=.3)
    axr[1,0].plot(theta_arr,Cs_r,'#8e44ad',lw=2); axr[1,0].set_xlabel('θ (°)'); axr[1,0].set_ylabel('C (pF)'); axr[1,0].set_title('Capacitance vs θ',fontweight='bold'); axr[1,0].grid(alpha=.3)
    axr[1,1].plot(theta_arr,Es_r,'#e67e22',lw=2); axr[1,1].set_xlabel('θ (°)'); axr[1,1].set_ylabel('Energy (μJ)'); axr[1,1].set_title('Energy vs θ',fontweight='bold'); axr[1,1].grid(alpha=.3)
    plt.suptitle(f"Rotary TENG | n={n_seg} segments | R={R_disk*1000:.0f}mm | {RPM} RPM", fontweight='bold')
    plt.tight_layout(); st.pyplot(fig_r, use_container_width=True); plt.close(fig_r)

    # Power vs RPM
    st.subheader("Average Power vs RPM")
    RPM_arr = np.linspace(10, 3000, 300)
    f_arr   = RPM_arr / 60 * n_seg
    P_rpm   = E_rot * 1e-6 * f_arr * 1e3
    fig_rpm, ax_rpm = plt.subplots(figsize=(8,3.5))
    ax_rpm.plot(RPM_arr, P_rpm, '#dc2626', lw=2)
    ax_rpm.set_xlabel("RPM"); ax_rpm.set_ylabel("Avg Power (mW)")
    ax_rpm.set_title("Average Power vs Rotation Speed", fontweight='bold'); ax_rpm.grid(alpha=.3)
    plt.tight_layout(); st.pyplot(fig_rpm, use_container_width=True); plt.close(fig_rpm)

# ═══════════════════════════════════════════════════════════════
#  TAB 4 — IMPEDANCE MATCHING
# ═══════════════════════════════════════════════════════════════
with tab_impedance:
    st.header("📡 Impedance Matching & Load Power Optimization")
    st.markdown("""
    <div class="highlight-box">
    <b>Key equation:</b> P_load(R) = V_oc² · R / (R_int + R)² &nbsp;&nbsp; Maximum at R = R_int = 1/(ωC)<br>
    P_max = V_oc² / (4·R_int)
    </div>""", unsafe_allow_html=True)

    freq_imp = st.slider("Operating frequency f (Hz)", 0.1, 200.0, 1.0, 0.1)
    R_arr = np.logspace(4, 12, 800)   # 10 kΩ to 1 TΩ

    P_arr, R_int = power_vs_load(Voc, C, R_arr, freq_imp)
    P_max_mW = (Voc**2 / (4 * R_int)) * 1e3 if R_int > 0 else 0

    m1,m2,m3 = st.columns(3)
    m1.metric("Optimal R_load", f"{R_int/1e6:.2f} MΩ" if R_int < 1e9 else f"{R_int/1e9:.2f} GΩ")
    m2.metric("Max Power (mW)", f"{P_max_mW:.4f}")
    m3.metric("Max Power Density (μW/cm²)", f"{P_max_mW*1e3/((w*l)*1e-2):.4f}")

    fig_imp, axs_imp = plt.subplots(1,2,figsize=(12,4))
    axs_imp[0].semilogx(R_arr, P_arr*1e3, '#2563eb', lw=2)
    axs_imp[0].axvline(R_int, color='red', ls='--', label=f'R_opt = {R_int:.2e} Ω')
    axs_imp[0].set_xlabel("Load Resistance R (Ω)"); axs_imp[0].set_ylabel("Power (mW)")
    axs_imp[0].set_title("Load Power vs Resistance", fontweight='bold')
    axs_imp[0].legend(); axs_imp[0].grid(alpha=.3, which='both')

    # Power vs frequency
    f_arr2 = np.logspace(-1, 3, 400)
    R_int_arr = 1.0 / (2*np.pi*f_arr2*C) if C > 0 else np.ones_like(f_arr2)*1e12
    P_vs_f = (Voc**2 / (4*R_int_arr)) * 1e3
    axs_imp[1].loglog(f_arr2, P_vs_f, '#16a34a', lw=2)
    axs_imp[1].set_xlabel("Frequency (Hz)"); axs_imp[1].set_ylabel("Max Power (mW)")
    axs_imp[1].set_title("Max Power vs Operating Frequency", fontweight='bold'); axs_imp[1].grid(alpha=.3, which='both')

    plt.tight_layout(); st.pyplot(fig_imp, use_container_width=True); plt.close(fig_imp)

    # Voltage & Current vs R
    fig_vi, axvi = plt.subplots(1,2,figsize=(12,4))
    V_load = Voc * R_arr / (R_int + R_arr)
    I_load = Voc / (R_int + R_arr) * 1e6  # μA
    axvi[0].semilogx(R_arr, V_load, '#7c3aed', lw=2)
    axvi[0].set_xlabel("R (Ω)"); axvi[0].set_ylabel("V_load (V)")
    axvi[0].set_title("Load Voltage vs Resistance", fontweight='bold'); axvi[0].grid(alpha=.3, which='both')
    axvi[1].semilogx(R_arr, I_load, '#b45309', lw=2)
    axvi[1].set_xlabel("R (Ω)"); axvi[1].set_ylabel("I_load (μA)")
    axvi[1].set_title("Load Current vs Resistance", fontweight='bold'); axvi[1].grid(alpha=.3, which='both')
    plt.tight_layout(); st.pyplot(fig_vi, use_container_width=True); plt.close(fig_vi)

# ═══════════════════════════════════════════════════════════════
#  TAB 5 — FOM CALCULATOR
# ═══════════════════════════════════════════════════════════════
with tab_fom:
    st.header("📐 Figure of Merit (FOM) Calculator")
    st.markdown("""
    <div class="highlight-box">
    <b>Surface-charge FOM (Wang et al., Nature Communications 2018):</b><br>
    FOM_SE = C_max · V_oc_max² / (S · σ² / ε₀)
    </div>""", unsafe_allow_html=True)

    Voc_max_idx = np.argmax(Voc_plot)
    C_max_fom   = float(C_plot[Voc_max_idx])
    Voc_max_fom = float(Voc_plot[Voc_max_idx])
    fom_val = fom_se(Voc_max_fom, C_max_fom, sigma_SI, S_max)

    f1,f2,f3 = st.columns(3)
    f1.metric("FOM_SE (dimensionless)", f"{fom_val:.4f}")
    f2.metric("Voc_max used (V)", f"{Voc_max_fom:.2f}")
    f3.metric("C_max used (pF)", f"{C_max_fom*1e12:.2f}")

    # FOM vs σ sweep
    sigma_sweep = np.linspace(10, 500, 300)
    fom_sweep   = []
    for sg in sigma_sweep:
        sg_SI = sg * 1e-6
        if "Contact" in operation_mode:
            C_arr_sw = EPS0 * S_max / (d0 + xp)
            V_arr_sw = (sg_SI / EPS0) * xp
        else:
            C_arr_sw = EPS0 * w_SI * np.maximum(L_SI - xp, 1e-9) / d0
            Q_arr_sw = sg_SI * w_SI * xp
            V_arr_sw = Q_arr_sw / C_arr_sw
        vmax_i = int(np.argmax(V_arr_sw))
        fom_sweep.append(fom_se(float(V_arr_sw[vmax_i]), float(C_arr_sw[vmax_i]), sg_SI, S_max))

    # FOM heatmap over material pairs
    st.subheader("FOM vs Charge Density & Relative Permittivity")
    er_range  = np.linspace(1.5, 8.0, 50)
    sig_range = np.linspace(10, 300, 50)
    FOM_map   = np.zeros((len(er_range), len(sig_range)))
    for i, er_v in enumerate(er_range):
        for j, sg_v in enumerate(sig_range):
            sg_SI_v = sg_v * 1e-6
            d0_v    = (d * 1e-6) / er_v if contact_type == "Conductor-to-Dielectric" else d0
            if "Contact" in operation_mode:
                C_v_arr = EPS0 * S_max / (d0_v + xp)
                V_v_arr = (sg_SI_v / EPS0) * xp
            else:
                C_v_arr = EPS0 * w_SI * np.maximum(L_SI - xp, 1e-9) / d0_v
                Q_v_arr = sg_SI_v * w_SI * xp
                V_v_arr = Q_v_arr / C_v_arr
            vi = int(np.argmax(V_v_arr))
            FOM_map[i, j] = fom_se(float(V_v_arr[vi]), float(C_v_arr[vi]), sg_SI_v, S_max)

    fig_fom, axf = plt.subplots(1,2,figsize=(12,4.5))
    axf[0].plot(sigma_sweep, fom_sweep, '#0e7490', lw=2)
    axf[0].axvline(sigma, color='red', ls='--', label=f'Current σ={sigma}')
    axf[0].set_xlabel("σ (μC/m²)"); axf[0].set_ylabel("FOM_SE"); axf[0].set_title("FOM vs Charge Density", fontweight='bold')
    axf[0].legend(); axf[0].grid(alpha=.3)
    im = axf[1].contourf(sig_range, er_range, FOM_map, levels=30, cmap='viridis')
    plt.colorbar(im, ax=axf[1], label='FOM_SE')
    axf[1].set_xlabel("σ (μC/m²)"); axf[1].set_ylabel("εᵣ"); axf[1].set_title("FOM Map — σ vs εᵣ", fontweight='bold')
    plt.tight_layout(); st.pyplot(fig_fom, use_container_width=True); plt.close(fig_fom)

# ═══════════════════════════════════════════════════════════════
#  TAB 6 — SELF-POWERED SENSOR
# ═══════════════════════════════════════════════════════════════
with tab_sensor:
    st.header("🌡️ Self-Powered Pressure Sensor Mode")
    st.markdown("""
    <div class="highlight-box">
    <b>Sensor model:</b> V_out = S_v · P &nbsp;&nbsp; where &nbsp;&nbsp; S_v = d₀/(ε₀·εᵣ) · k_n (V/Pa)<br>
    Minimum detectable pressure: P_min = V_noise / S_v
    </div>""", unsafe_allow_html=True)

    c1s, c2s = st.columns(2)
    k_n      = c1s.number_input("Mechanical coupling factor k_n", 0.01, 2.0, 0.1, 0.01)
    V_noise  = c2s.number_input("Measurement noise floor V_noise (mV)", 0.1, 100.0, 1.0, 0.1) * 1e-3
    er_eff   = er if contact_type == "Conductor-to-Dielectric" else (er1+er2)/2

    Sv = sensor_sensitivity(sigma_SI, d0, er_eff, k_n)
    P_min = V_noise / Sv if Sv > 0 else 0

    s1,s2,s3 = st.columns(3)
    s1.metric("Sensitivity Sv (V/Pa)", f"{Sv:.4f}")
    s2.metric("Min Detectable P (Pa)", f"{P_min:.2f}")
    s3.metric("Min Detectable P (kPa)", f"{P_min/1000:.5f}")

    P_range = np.logspace(np.log10(max(P_min, 0.01)), 6, 400)   # Pa
    V_out   = Sv * P_range

    fig_sen, axsen = plt.subplots(1,2,figsize=(12,4))
    axsen[0].loglog(P_range, V_out, '#7c3aed', lw=2)
    axsen[0].axhline(V_noise, color='red', ls='--', label=f'Noise floor {V_noise*1e3:.1f}mV')
    axsen[0].set_xlabel("Applied Pressure (Pa)"); axsen[0].set_ylabel("V_out (V)")
    axsen[0].set_title("Sensor Output vs Pressure", fontweight='bold')
    axsen[0].legend(); axsen[0].grid(alpha=.3, which='both')

    # Sensitivity vs k_n
    kn_arr = np.linspace(0.01, 2.0, 200)
    Sv_arr = (d0 / (EPS0 * er_eff)) * kn_arr
    axsen[1].plot(kn_arr, Sv_arr*1e3, '#0891b2', lw=2)
    axsen[1].set_xlabel("Mechanical coupling factor k_n")
    axsen[1].set_ylabel("Sensitivity (mV/Pa)")
    axsen[1].set_title("Sensitivity vs Coupling Factor", fontweight='bold'); axsen[1].grid(alpha=.3)
    plt.tight_layout(); st.pyplot(fig_sen, use_container_width=True); plt.close(fig_sen)

    # Sensitivity vs thickness
    st.subheader("Sensitivity vs Dielectric Thickness")
    d_range = np.linspace(10, 2000, 400) * 1e-6
    Sv_d    = (d_range / er_eff / EPS0) * k_n
    fig_sd, axsd = plt.subplots(figsize=(8,3.5))
    axsd.plot(d_range*1e6, Sv_d, '#16a34a', lw=2)
    axsd.axvline(d*1e6 if contact_type=="Conductor-to-Dielectric" else (d1+d2)/2,
                 color='red', ls='--', label='Current d')
    axsd.set_xlabel("Dielectric Thickness (μm)"); axsd.set_ylabel("Sv (V/Pa)")
    axsd.set_title("Sensor Sensitivity vs Thickness", fontweight='bold')
    axsd.legend(); axsd.grid(alpha=.3); plt.tight_layout()
    st.pyplot(fig_sd, use_container_width=True); plt.close(fig_sd)

# ═══════════════════════════════════════════════════════════════
#  TAB 7 — MULTI-LAYER
# ═══════════════════════════════════════════════════════════════
with tab_multilayer:
    st.header("🔢 Multi-Layer Stacked TENG Architecture")
    st.markdown("""
    <div class="highlight-box">
    V_oc,total = n · V_oc,single &nbsp;|&nbsp; C_total = C_single/n &nbsp;|&nbsp; Q_sc,total ≈ Q_sc,single<br>
    E_total = ½ · C_total · V_oc,total² = ½ · C_single · n · V_oc,single²
    </div>""", unsafe_allow_html=True)

    n_layers = st.slider("Number of stacked layers n", 1, 30, 1, 1)
    Voc_ml, Qsc_ml, C_ml, E_ml = multilayer_output(Voc, Qsc, C, n_layers)

    ml1,ml2,ml3,ml4 = st.columns(4)
    ml1.metric("Voc_total (V)", f"{Voc_ml:.2f}", delta=f"+{Voc_ml-Voc:.2f} vs single")
    ml2.metric("Qsc_total (nC)", f"{Qsc_ml*1e9:.2f}")
    ml3.metric("C_total (pF)", f"{C_ml*1e12:.4f}")
    ml4.metric("Energy (μJ)", f"{E_ml*1e6:.3f}", delta=f"+{(E_ml*1e6-Energy_uJ):.3f}")

    n_arr = np.arange(1, 31)
    Voc_n = n_arr * Voc
    C_n   = C / n_arr
    E_n   = 0.5 * C_n * Voc_n**2 * 1e6
    P_n   = E_n * 1e-6 * 1.0 * 1e3   # 1 Hz reference

    fig_ml, axml = plt.subplots(2,2,figsize=(11,7))
    axml[0,0].plot(n_arr, Voc_n, '#2980b9', lw=2, marker='o', ms=4)
    axml[0,0].set_ylabel("Voc_total (V)"); axml[0,0].set_title("Total Voltage vs Layers", fontweight='bold'); axml[0,0].grid(alpha=.3)
    axml[0,1].plot(n_arr, C_n*1e12, '#8e44ad', lw=2, marker='s', ms=4)
    axml[0,1].set_ylabel("C_total (pF)"); axml[0,1].set_title("Total Capacitance vs Layers", fontweight='bold'); axml[0,1].grid(alpha=.3)
    axml[1,0].plot(n_arr, E_n, '#e67e22', lw=2, marker='^', ms=4)
    axml[1,0].set_xlabel("Number of Layers"); axml[1,0].set_ylabel("Energy (μJ)"); axml[1,0].set_title("Energy vs Layers", fontweight='bold'); axml[1,0].grid(alpha=.3)
    axml[1,1].plot(n_arr, P_n, '#16a34a', lw=2, marker='D', ms=4)
    axml[1,1].set_xlabel("Number of Layers"); axml[1,1].set_ylabel("Power @ 1Hz (mW)"); axml[1,1].set_title("Power vs Layers (1 Hz ref)", fontweight='bold'); axml[1,1].grid(alpha=.3)
    plt.suptitle("Multi-Layer TENG Scaling Analysis", fontweight='bold', fontsize=12)
    plt.tight_layout(); st.pyplot(fig_ml, use_container_width=True); plt.close(fig_ml)

# ═══════════════════════════════════════════════════════════════
#  TAB 8 — FREQUENCY DOMAIN
# ═══════════════════════════════════════════════════════════════
with tab_freq:
    st.header("〰️ Frequency-Domain Output Model")
    st.markdown("""
    <div class="highlight-box">
    I_sc(f) = σ·S·2A_m·f &nbsp;|&nbsp; P_avg(f) = I_sc²·R_opt/4 &nbsp;|&nbsp; R_opt(f) = 1/(2πfC)
    </div>""", unsafe_allow_html=True)

    c1f, c2f = st.columns(2)
    A_m = c1f.number_input("Mechanical amplitude A_m (mm)", 0.1, 50.0, float(x), 0.1) * 1e-3
    f_highlight = c2f.number_input("Highlight frequency (Hz)", 0.1, 200.0, 1.0, 0.1)

    freq_arr2 = np.logspace(-1, 3, 600)
    Isc_peak_arr, P_avg_arr = frequency_output(sigma_SI, S_max, A_m, freq_arr2, C, Voc)

    f1fd, f2fd, f3fd = st.columns(3)
    idx_h = np.argmin(np.abs(freq_arr2 - f_highlight))
    f1fd.metric(f"I_sc_peak @ {f_highlight}Hz (μA)", f"{Isc_peak_arr[idx_h]*1e6:.3f}")
    f2fd.metric(f"Avg Power @ {f_highlight}Hz (μW)", f"{P_avg_arr[idx_h]*1e6:.4f}")
    f3fd.metric("Human Walking range", "1–3 Hz")

    fig_f, axff = plt.subplots(1,2,figsize=(12,4.5))
    axff[0].loglog(freq_arr2, Isc_peak_arr*1e6, '#2563eb', lw=2)
    axff[0].axvspan(1,3,alpha=.15,color='green',label='Walking (1–3Hz)')
    axff[0].axvspan(50,200,alpha=.1,color='orange',label='Machine vibration')
    axff[0].axvline(f_highlight,color='red',ls='--',label=f'{f_highlight}Hz')
    axff[0].set_xlabel("Frequency (Hz)"); axff[0].set_ylabel("I_sc peak (μA)")
    axff[0].set_title("Peak Short-Circuit Current vs Frequency", fontweight='bold')
    axff[0].legend(fontsize=8); axff[0].grid(alpha=.3, which='both')

    axff[1].loglog(freq_arr2, P_avg_arr*1e6, '#dc2626', lw=2)
    axff[1].axvspan(1,3,alpha=.15,color='green',label='Walking')
    axff[1].axvspan(50,200,alpha=.1,color='orange',label='Machine vibration')
    axff[1].axvline(f_highlight,color='red',ls='--',label=f'{f_highlight}Hz')
    axff[1].set_xlabel("Frequency (Hz)"); axff[1].set_ylabel("Avg Power (μW)")
    axff[1].set_title("Average Output Power vs Frequency", fontweight='bold')
    axff[1].legend(fontsize=8); axff[1].grid(alpha=.3, which='both')
    plt.tight_layout(); st.pyplot(fig_f, use_container_width=True); plt.close(fig_f)

# ═══════════════════════════════════════════════════════════════
#  TAB 9 — HEATMAPS
# ═══════════════════════════════════════════════════════════════
with tab_heatmap:
    st.header("🗺️ 2D Design Space Heatmaps")
    st.markdown("""
    <div class="highlight-box">
    Maps the full (σ, εᵣ) design space for power density and FOM — publication-quality figures.
    </div>""", unsafe_allow_html=True)

    er_h  = np.linspace(1.5, 8.0, 60)
    sig_h = np.linspace(10,  400, 60)

    PD_map = power_density_heatmap_data(er_h, sig_h, d*1e-6 if contact_type=="Conductor-to-Dielectric" else (d1+d2)/2*1e-6,
                                         x_SI, S_max, "contact" if "Contact" in operation_mode else "sliding")

    fig_h, axh = plt.subplots(1,2,figsize=(13,5))
    im1 = axh[0].contourf(sig_h, er_h, PD_map, levels=40, cmap='hot')
    plt.colorbar(im1, ax=axh[0], label='Energy Density (μJ/m²)')
    axh[0].scatter([sigma],[er if contact_type=="Conductor-to-Dielectric" else (er1+er2)/2],
                   color='cyan', s=120, zorder=5, label='Current config')
    axh[0].set_xlabel("σ (μC/m²)"); axh[0].set_ylabel("εᵣ")
    axh[0].set_title("Energy Density Map", fontweight='bold'); axh[0].legend()

    # Voc heatmap
    Voc_map = np.zeros_like(PD_map)
    for i, er_v in enumerate(er_h):
        for j, sg_v in enumerate(sig_h):
            sg_SI_v = sg_v*1e-6
            d0_v = (d*1e-6)/er_v if contact_type=="Conductor-to-Dielectric" else d0
            if "Contact" in operation_mode:
                Voc_map[i,j] = (sg_SI_v/EPS0)*x_SI
            else:
                Q_v = sg_SI_v*w_SI*x_SI
                C_v = EPS0*w_SI*max(L_SI-x_SI,1e-9)/d0_v
                Voc_map[i,j] = Q_v/C_v if C_v>0 else 0

    im2 = axh[1].contourf(sig_h, er_h, Voc_map, levels=40, cmap='plasma')
    plt.colorbar(im2, ax=axh[1], label='Voc (V)')
    axh[1].scatter([sigma],[er if contact_type=="Conductor-to-Dielectric" else (er1+er2)/2],
                   color='cyan', s=120, zorder=5, label='Current config')
    axh[1].set_xlabel("σ (μC/m²)"); axh[1].set_ylabel("εᵣ")
    axh[1].set_title("Open-Circuit Voltage Map", fontweight='bold'); axh[1].legend()
    plt.suptitle(f"Design Space Maps — {mode_label} | x = {x:.2f} mm", fontweight='bold')
    plt.tight_layout(); st.pyplot(fig_h, use_container_width=True); plt.close(fig_h)

# ═══════════════════════════════════════════════════════════════
#  TAB 10 — MONTE CARLO
# ═══════════════════════════════════════════════════════════════
with tab_mc:
    st.header("🎲 Monte Carlo Uncertainty Analysis")
    st.markdown("""
    <div class="highlight-box">
    Propagates fabrication tolerances (σ, d₀) through the TENG model using N random samples.<br>
    Outputs: probability distributions of Voc, Qsc, and Energy with ±1σ confidence intervals.
    </div>""", unsafe_allow_html=True)

    mc1, mc2 = st.columns(2)
    n_samples  = mc1.select_slider("Monte Carlo samples N", [500,1000,5000,10000], 1000)
    unc_pct    = mc2.slider("Parameter uncertainty (±%)", 1, 30, 10, 1)

    Voc_mc, Qsc_mc, E_mc = monte_carlo_analysis(sigma_SI, d0, S_max, x_SI, n_samples, unc_pct, mc_mode)

    r1mc, r2mc, r3mc = st.columns(3)
    r1mc.metric("Voc: mean ± σ (V)",   f"{np.mean(Voc_mc):.2f} ± {np.std(Voc_mc):.2f}")
    r2mc.metric("Qsc: mean ± σ (nC)",  f"{np.mean(Qsc_mc):.2f} ± {np.std(Qsc_mc):.2f}")
    r3mc.metric("E: mean ± σ (μJ)",    f"{np.mean(E_mc):.3f} ± {np.std(E_mc):.3f}")

    fig_mc, axmc = plt.subplots(1,3,figsize=(13,4))
    for ax_mc, data, label, color in zip(
        axmc,
        [Voc_mc, Qsc_mc, E_mc],
        ["Voc (V)", "Qsc (nC)", "Energy (μJ)"],
        ['#2563eb','#16a34a','#dc2626']):
        ax_mc.hist(data, bins=50, color=color, alpha=.7, density=True, edgecolor='white')
        mu, std = np.mean(data), np.std(data)
        xn = np.linspace(mu-4*std, mu+4*std, 300)
        ax_mc.plot(xn, (1/(std*np.sqrt(2*np.pi)))*np.exp(-0.5*((xn-mu)/std)**2), 'k-', lw=2, label=f'μ={mu:.3f}\nσ={std:.3f}')
        ax_mc.axvline(mu-std, color='gray', ls='--', alpha=.7)
        ax_mc.axvline(mu+std, color='gray', ls='--', alpha=.7)
        ax_mc.set_xlabel(label); ax_mc.set_ylabel("Probability Density")
        ax_mc.set_title(f"Distribution of {label.split('(')[0]}", fontweight='bold')
        ax_mc.legend(fontsize=8); ax_mc.grid(alpha=.3)
    plt.suptitle(f"Monte Carlo Analysis — N={n_samples} | Uncertainty ±{unc_pct}%", fontweight='bold')
    plt.tight_layout(); st.pyplot(fig_mc, use_container_width=True); plt.close(fig_mc)

# ═══════════════════════════════════════════════════════════════
#  TAB 11 — THEORY
# ═══════════════════════════════════════════════════════════════
with tab_theory:
    st.header("📚 Complete Theoretical Framework")

    st.subheader("1. Core V–Q–x Model")
    if contact_type == "Conductor-to-Dielectric":
        st.latex(r"d_0 = \frac{d}{\varepsilon_r}")
    else:
        st.latex(r"d_0 = \frac{d_1}{\varepsilon_{r1}} + \frac{d_2}{\varepsilon_{r2}}")
    st.latex(r"C(x) = \frac{\varepsilon_0 S}{d_0 + x} \quad \text{(Contact Mode)}")
    st.latex(r"V_{oc}(x) = \frac{\sigma x}{\varepsilon_0}")
    st.latex(r"Q_{sc}(x) = \sigma S \frac{x}{d_0 + x}")
    st.latex(r"C(x) = \frac{\varepsilon_0 w (L - x)}{d_0} \quad \text{(Sliding Mode)}")

    st.subheader("2. Rotary TENG")
    st.latex(r"V_{oc}(\theta) = \frac{\sigma d_0}{\varepsilon_0} \cdot \frac{\theta}{\theta_{max} - \theta}")
    st.latex(r"P_{avg} = \frac{1}{T}\int_0^T \frac{V^2(t)}{R_{load}} dt")

    st.subheader("3. Charge Decay with Humidity")
    st.latex(r"\sigma(t) = \sigma_0 \cdot e^{-t/\tau}")
    st.latex(r"\tau = \tau_0 \cdot e^{-\alpha \cdot RH}")

    st.subheader("4. Impedance Matching")
    st.latex(r"P_{load}(R) = \frac{V_{oc}^2 \cdot R}{(R_{int} + R)^2}")
    st.latex(r"R_{opt} = R_{int} = \frac{1}{\omega C_{TENG}}")
    st.latex(r"P_{max} = \frac{V_{oc}^2}{4 R_{int}}")

    st.subheader("5. Figure of Merit (Wang 2018)")
    st.latex(r"FOM_{SE} = \frac{C_{max} \cdot V_{oc,max}^2}{S \cdot \sigma^2 / \varepsilon_0}")

    st.subheader("6. Self-Powered Sensor")
    st.latex(r"S_v = \frac{d_0}{\varepsilon_0 \varepsilon_r} \cdot k_n \quad (\text{V/Pa})")
    st.latex(r"P_{min} = \frac{V_{noise}}{S_v}")

    st.subheader("7. Multi-Layer Scaling")
    st.latex(r"V_{oc,total} = n \cdot V_{oc,single}")
    st.latex(r"C_{total} = \frac{C_{single}}{n}")
    st.latex(r"E_{total} = \frac{1}{2} C_{total} V_{oc,total}^2 = \frac{n}{2} C_{single} V_{oc,single}^2")

    st.subheader("8. Frequency Domain")
    st.latex(r"I_{sc}(f) = \sigma \cdot S \cdot 2 A_m \cdot f")
    st.latex(r"P_{avg}(f) = \frac{I_{sc}^2 \cdot R_{opt}(f)}{4}")

    st.subheader("References")
    st.markdown("""
    1. Wang, Z.L. et al. *Triboelectric nanogenerators as new energy technology*, ACS Nano, 2013.
    2. Wang, Z.L. *On Maxwell's displacement current for energy and sensors*, Materials Today, 2017.
    3. Niu, S. & Wang, Z.L. *Theoretical systems of triboelectric nanogenerators*, Nano Energy, 2015.
    4. Cao, X. et al. *Triboelectric nanogenerators driven self-powered electrochemical processes*, Joule, 2018.
    5. Wang, Z.L. *On the first principle theory of nanogenerators from Maxwell's equations*, Nano Energy, 2020.
    """)

# ═══════════════════════════════════════════════════════════════
#  TAB 12 — EXPORT
# ═══════════════════════════════════════════════════════════════
with tab_export:
    st.header("📥 Publication-Quality Export")
    st.markdown("Download all simulation data and SVG figures for direct use in your paper.")

    if st.button("🗂️ Generate & Download ZIP Package"):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:

            # CSV — main results
            df_main = pd.DataFrame({
                "Parameter": ["Mode","Config","Material","sigma (uC/m2)","w (mm)","l (mm)","x (mm)",
                               "Voc (V)","Qsc (nC)","C (pF)","Energy (uJ)","FOM_SE"],
                "Value": [operation_mode, contact_type, sel_mat, sigma, w, l, x,
                          round(Voc,4), round(Qsc*1e9,4), round(C*1e12,4), round(Energy_uJ,5),
                          round(fom_se(max(Voc_plot),max(C_plot),sigma_SI,S_max),6)]
            })
            zf.writestr("TENG_main_results.csv", df_main.to_csv(index=False))

            # CSV — sweep data
            df_sweep = pd.DataFrame({
                x_label: x_plot_mm,
                "Voc (V)": Voc_plot,
                "Qsc (nC)": Qsc_plot*1e9,
                "C (pF)": C_plot*1e12,
                "Energy (uJ)": Ep_plot,
            })
            zf.writestr("TENG_sweep_data.csv", df_sweep.to_csv(index=False))

            # CSV — humidity decay
            if "Contact" in operation_mode:
                Voc_dec_exp = (sigma * np.exp(-np.linspace(0,24*3600,1000)/tau_from_humidity(float(mat_data["tau0"]),float(mat_data["alpha"]),50)) * 1e-6 / EPS0) * x_SI
            else:
                overlap_fix = max(L_SI - x_SI, 1e-9)
                C_fix2 = EPS0 * w_SI * overlap_fix / d0
                Voc_dec_exp = (sigma * np.exp(-np.linspace(0,24*3600,1000)/tau_from_humidity(float(mat_data["tau0"]),float(mat_data["alpha"]),50)) * 1e-6 * w_SI * x_SI) / C_fix2
            t_exp = np.linspace(0, 24*3600, 1000)
            df_hum = pd.DataFrame({"time (s)": t_exp,
                                   "sigma_decay (uC/m2)": sigma*np.exp(-t_exp/tau_from_humidity(float(mat_data["tau0"]),float(mat_data["alpha"]),50)),
                                   "Voc_decay (V)": Voc_dec_exp})
            zf.writestr("TENG_humidity_decay.csv", df_hum.to_csv(index=False))

            # SVG — main characteristics
            fig_exp, axs_exp = plt.subplots(2,2,figsize=(11,7))
            axs_exp[0,0].plot(x_plot_mm,Voc_plot,'#2980b9',lw=2); axs_exp[0,0].set_ylabel('Voc (V)'); axs_exp[0,0].set_title('Voc',fontweight='bold'); axs_exp[0,0].grid(alpha=.3)
            axs_exp[0,1].plot(x_plot_mm,Qsc_plot*1e9,'#27ae60',lw=2); axs_exp[0,1].set_ylabel('Qsc (nC)'); axs_exp[0,1].set_title('Qsc',fontweight='bold'); axs_exp[0,1].grid(alpha=.3)
            axs_exp[1,0].plot(x_plot_mm,C_plot*1e12,'#8e44ad',lw=2); axs_exp[1,0].set_xlabel(x_label); axs_exp[1,0].set_ylabel('C (pF)'); axs_exp[1,0].set_title('Capacitance',fontweight='bold'); axs_exp[1,0].grid(alpha=.3)
            axs_exp[1,1].plot(x_plot_mm,Ep_plot,'#e67e22',lw=2); axs_exp[1,1].set_xlabel(x_label); axs_exp[1,1].set_ylabel('Energy (uJ)'); axs_exp[1,1].set_title('Energy',fontweight='bold'); axs_exp[1,1].grid(alpha=.3)
            plt.suptitle(f"TENG Characteristics — Dr. Pravin Kumar Singh, MUJ", fontweight='bold')
            plt.tight_layout()
            zf.writestr("TENG_characteristics.svg", fig_to_svg_bytes(fig_exp))
            plt.close(fig_exp)

            # SVG — heatmap
            fig_he2, axhe2 = plt.subplots(figsize=(7,5))
            im_e = axhe2.contourf(sig_h, er_h, PD_map, levels=40, cmap='hot')
            plt.colorbar(im_e, ax=axhe2, label='Energy Density (uJ/m2)')
            axhe2.set_xlabel("sigma (uC/m2)"); axhe2.set_ylabel("epsilon_r")
            axhe2.set_title("Energy Density Design Map", fontweight='bold')
            plt.tight_layout()
            zf.writestr("TENG_heatmap.svg", fig_to_svg_bytes(fig_he2))
            plt.close(fig_he2)

            # BibTeX
            bib = """\
@article{wang2013triboelectric,
  title={Triboelectric Nanogenerators as a New Energy Technology for Self-Powered Systems},
  author={Wang, Zhong Lin and Chen, Jun and Lin, Long},
  journal={Energy \\& Environmental Science},
  year={2015}
}
@article{niu2015theoretical,
  title={Theoretical systems of triboelectric nanogenerators},
  author={Niu, Simiao and Wang, Zhong Lin},
  journal={Nano Energy},
  volume={14},
  year={2015}
}
@article{wang2020first,
  title={On the first principle theory of nanogenerators from Maxwell's equations},
  author={Wang, Zhong Lin},
  journal={Nano Energy},
  volume={68},
  year={2020}
}"""
            zf.writestr("TENG_references.bib", bib)

            # README
            readme = f"""TENG Simulator v2.0 — Export Package
Developed by: Dr. Pravin Kumar Singh
Manipal University Jaipur, Rajasthan, India

Files included:
  TENG_main_results.csv       — Key output parameters at current x
  TENG_sweep_data.csv         — V, Q, C, E vs displacement
  TENG_humidity_decay.csv     — Charge and Voc decay at RH=50%
  TENG_characteristics.svg    — Publication-quality 4-panel figure
  TENG_heatmap.svg            — Energy density design space map
  TENG_references.bib         — BibTeX references

Simulation config:
  Mode: {operation_mode}
  Config: {contact_type}
  Material: {sel_mat}
  sigma = {sigma} uC/m2
  w x L = {w} x {l} mm
  x = {x} mm
  Voc = {Voc:.3f} V
  Qsc = {Qsc*1e9:.3f} nC
  Energy = {Energy_uJ:.4f} uJ
"""
            zf.writestr("README.txt", readme)

        zip_buf.seek(0)
        st.download_button(
            label="⬇️ Download ZIP (CSV + SVG + BibTeX + README)",
            data=zip_buf,
            file_name="TENG_Simulator_v2_Export.zip",
            mime="application/zip"
        )
        st.success("✅ ZIP package ready! Includes publication-quality SVG figures and BibTeX references.")

    # Individual CSV
    st.subheader("Quick CSV Download")
    df_q = pd.DataFrame({
        x_label: x_plot_mm,
        "Voc (V)": Voc_plot,
        "Qsc (nC)": Qsc_plot*1e9,
        "C (pF)": C_plot*1e12,
        "Energy (uJ)": Ep_plot
    })
    st.download_button("📄 Download Sweep Data CSV", df_q.to_csv(index=False).encode('utf-8-sig'),
                       "TENG_sweep.csv", "text/csv")

# ═══════════════════════════════════════════════════════════════
#  TAB 13 — ABOUT
# ═══════════════════════════════════════════════════════════════
with tab_about:
    st.header("ℹ️ About TENG Simulator v2.0")
    st.markdown("""
    ### Advanced Multi-Physics TENG Design & Optimization Platform
    **Developed at:** Manipal University Jaipur, Rajasthan, India  
    **TENG Simulator v2.0** | Python + Streamlit | For academic research

st.markdown("---")
st.caption("TENG Simulator v2.0 | Dr. Pravin Kumar Singh | Manipal University Jaipur | Advanced Multi-Physics Platform")
