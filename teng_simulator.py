#!/usr/bin/env python3
"""
TENG Simulator - Web App (Python + Streamlit)
Modes: Attached Electrode - Contact Mode & Sliding Mode
Types: Conductor-to-Dielectric and Dielectric-to-Dielectric

Run with: streamlit run teng_simulator.py
"""

import streamlit as st
import numpy as np
import matplotlib
matplotlib.use('Agg')          # Important for Streamlit Cloud
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Page setup
st.set_page_config(
    page_title="TENG CAD Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for nicer look (optional polish)
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ TENG Simulator")
st.markdown("**Interactive Web App** | Contact & Sliding Modes | Attached Electrode | Educational Tool")

st.markdown("---")

# ==================== SIDEBAR INPUTS ====================
with st.sidebar:
    st.header("🔧 Configuration")
    
    operation_mode = st.radio(
        "Operation Mode",
        ["Contact Mode (Vertical Separation)", "Sliding Mode (Lateral Displacement)"],
        index=0,
        help="Contact mode: layers move apart vertically. Sliding mode: one layer slides laterally over the other (assumes intimate contact)."
    )
    
    contact_type = st.radio(
        "Dielectric Configuration",
        ["Conductor-to-Dielectric", "Dielectric-to-Dielectric"],
        index=0,
        help="Conductor-to-Dielectric: one dielectric layer between two conductors. Dielectric-to-Dielectric: two dielectric layers between conductors."
    )
    
    st.subheader("⚡ Triboelectric & Geometry")
    
    sigma = st.number_input(
        "Triboelectric charge density σ (μC/m²)",
        min_value=1.0, max_value=1000.0, value=50.0, step=5.0,
        help="Surface charge density created by triboelectric effect. Typical range: 10–200 μC/m². Higher = stronger output. Depends on material pair, humidity, surface roughness."
    )
    
    w = st.number_input(
        "Width w (mm)",
        min_value=5.0, max_value=500.0, value=50.0, step=5.0,
        help="Width of the device (perpendicular to motion). Larger area → more total charge & energy."
    )
    
    l = st.number_input(
        "Length L (mm)  [direction of x motion]",
        min_value=5.0, max_value=500.0, value=50.0, step=5.0,
        help="Length along the direction of separation (contact) or sliding. In sliding mode: x cannot exceed ~0.9×L (as in original tool)."
    )
    
    # Dielectric parameters - conditional
    if contact_type == "Conductor-to-Dielectric":
        st.markdown("**Dielectric Layer**")
        d = st.number_input(
            "Dielectric thickness d (μm)",
            min_value=5.0, max_value=2000.0, value=100.0, step=10.0,
            help="Thickness of the single dielectric film (e.g. PTFE, Kapton, PDMS, Nylon)."
        )
        er = st.number_input(
            "Relative permittivity εᵣ",
            min_value=1.1, max_value=20.0, value=2.5, step=0.1,
            help="e.g. PTFE ≈ 2.1, Kapton ≈ 3.4, PDMS ≈ 2.7–3.0, Nylon ≈ 4.0, PET ≈ 3.2"
        )
        d1 = d2 = er1 = er2 = 0.0  # not used
    else:
        st.markdown("**Dielectric Layer 1 (top)**")
        d1 = st.number_input("Thickness d1 (μm)", min_value=5.0, max_value=2000.0, value=50.0, step=5.0)
        er1 = st.number_input("εᵣ1", min_value=1.1, max_value=20.0, value=2.0, step=0.1)
        
        st.markdown("**Dielectric Layer 2 (bottom)**")
        d2 = st.number_input("Thickness d2 (μm)", min_value=5.0, max_value=2000.0, value=50.0, step=5.0)
        er2 = st.number_input("εᵣ2", min_value=1.1, max_value=20.0, value=4.0, step=0.1)
        d = er = 0.0  # not used
    
    st.subheader("📍 Operating Point & Plot Range")
    
    x = st.number_input(
        "Current x (mm)  — separation or displacement",
        min_value=0.0, max_value=200.0, value=1.0, step=0.1,
        help="For Contact Mode: vertical air gap distance. For Sliding Mode: lateral sliding distance from full overlap."
    )
    
    xmax = st.number_input(
        "Maximum x for plots (mm)",
        min_value=0.5, max_value=300.0, 
        value= (5.0 if "Contact" in operation_mode else min(45.0, 0.9 * l) ),
        step=1.0,
        help="Range for the characteristic curves. In sliding mode, keep ≤ 0.9 × L"
    )
    
    st.markdown("---")
    st.info("💡 All calculations update **live** when you change any value. No need to press buttons!")

# ==================== UNIT CONVERSION & d0 ====================
epsilon0 = 8.854187817e-12  # F/m

sigma_SI = sigma * 1e-6          # C/m²
S_max = (w * l) * 1e-6           # m²  (maximum possible area)
w_SI = w * 1e-3                  # m
L_SI = l * 1e-3                  # m
x_SI = x * 1e-3                  # m

# Effective dielectric thickness d0
if contact_type == "Conductor-to-Dielectric":
    d0 = (d * 1e-6) / er
else:
    d0 = (d1 * 1e-6) / er1 + (d2 * 1e-6) / er2

# Safety
if d0 <= 0:
    d0 = 1e-9

# ==================== COMPUTE CURRENT VALUES ====================
if "Contact" in operation_mode:
    # ========== CONTACT MODE ==========
    denom = d0 + x_SI
    if denom <= 0:
        denom = 1e-12
    
    C = epsilon0 * S_max / denom
    Voc = (sigma_SI / epsilon0) * x_SI
    Qsc = sigma_SI * S_max * (x_SI / denom)
    Energy_uJ = 0.5 * abs(Qsc) * abs(Voc) * 1e6
    
    # Plot arrays
    x_plot_mm = np.linspace(0.001, xmax, 400)
    x_plot = x_plot_mm * 1e-3
    denom_plot = d0 + x_plot
    C_plot = epsilon0 * S_max / denom_plot
    Voc_plot = (sigma_SI / epsilon0) * x_plot
    Qsc_plot = sigma_SI * S_max * (x_plot / denom_plot)
    Energy_plot = 0.5 * Qsc_plot * Voc_plot * 1e6
    
    mode_label = "Contact Mode"
    x_label = "Separation x (mm)"
    
else:
    # ========== SLIDING MODE ==========
    overlap_current = max(L_SI - x_SI, 1e-9)
    
    C = epsilon0 * (w_SI * overlap_current) / d0
    Qsc = sigma_SI * w_SI * x_SI
    Voc = Qsc / C if C > 0 else 0.0
    Energy_uJ = 0.5 * abs(Qsc) * abs(Voc) * 1e6
    
    # Plot arrays (up to 0.95 L)
    xmax_eff = min(xmax, 0.95 * l)
    x_plot_mm = np.linspace(0.0, xmax_eff, 400)
    x_plot = x_plot_mm * 1e-3
    overlap_plot = np.maximum(L_SI - x_plot, 1e-9)
    
    C_plot = epsilon0 * (w_SI * overlap_plot) / d0
    Qsc_plot = sigma_SI * w_SI * x_plot
    Voc_plot = Qsc_plot / C_plot
    Energy_plot = 0.5 * Qsc_plot * Voc_plot * 1e6
    
    mode_label = "Sliding Mode"
    x_label = "Displacement x (mm)"

# ==================== MAIN PANEL ====================

# Metrics row
st.subheader(f"📈 Results at current x = {x:.2f} mm  |  {mode_label} — {contact_type}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Open-Circuit Voltage (Voc)", value=f"{Voc:.2f} V")

with col2:
    st.metric(label="Short-Circuit Charge (Qsc)", value=f"{Qsc*1e9:.2f} nC")

with col3:
    st.metric(label="Capacitance (C)", value=f"{C*1e12:.2f} pF")

with col4:
    st.metric(label="Energy (½ Qsc·Voc)", value=f"{Energy_uJ:.3f} μJ")

# Air breakdown warning (only meaningful in contact mode)
if "Contact" in operation_mode and x_SI > 1e-6:
    E_field = Voc / x_SI
    if E_field > 3.0e6:
        st.warning(
            f"⚠️ **Air-breakdown risk!** Electric field in gap ≈ **{E_field/1e6:.2f} MV/m** "
            f"(typical air strength ~3 MV/m). Reduce x, lower σ, or use encapsulation."
        )

# ==================== SCHEMATIC ====================
st.subheader("📐 Interactive Device Schematic (gap / overlap updates with x)")

fig_schem, ax = plt.subplots(figsize=(10, 4.5))
ax.set_xlim(-0.5, 11)
ax.set_ylim(-0.5, 7)
ax.axis('off')
ax.set_title(f"{mode_label}  •  {contact_type}", fontsize=13, fontweight='bold', pad=10)

if "Contact" in operation_mode:
    # Vertical stack schematic
    # Bottom conductor
    rect_bot = Rectangle((1, 0.3), 8, 1.0, linewidth=2.5, edgecolor='#1a5276', facecolor='#3498db')
    ax.add_patch(rect_bot)
    ax.text(5, 0.8, "Bottom Conductor (Electrode)", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
    
    # Dielectric layer(s)
    y_diel = 1.4
    if contact_type == "Conductor-to-Dielectric":
        h_diel = 1.0
        rect_d = Rectangle((1, y_diel), 8, h_diel, linewidth=2, edgecolor='#b9770e', facecolor='#f4d03f')
        ax.add_patch(rect_d)
        ax.text(5, y_diel + 0.5, f"Dielectric  •  d = {d} μm   εᵣ = {er}", ha='center', va='center', fontsize=8)
        y_air_start = y_diel + h_diel + 0.05
    else:
        h_d1 = 0.85
        rect_d1 = Rectangle((1, y_diel), 8, h_d1, linewidth=2, edgecolor='#b9770e', facecolor='#f4d03f')
        ax.add_patch(rect_d1)
        ax.text(5, y_diel + 0.42, f"Diel.1  d1={d1}μm  εr1={er1}", ha='center', va='center', fontsize=7)
        
        rect_d2 = Rectangle((1, y_diel + h_d1 + 0.05), 8, 0.85, linewidth=2, edgecolor='#6c3483', facecolor='#af7ac5')
        ax.add_patch(rect_d2)
        ax.text(5, y_diel + h_d1 + 0.47, f"Diel.2  d2={d2}μm  εr2={er2}", ha='center', va='center', fontsize=7, color='white')
        y_air_start = y_diel + 2*h_d1 + 0.15
    
    # Air gap (visual height scaled to x)
    visual_gap = min(2.2, max(0.15, (x / max(xmax, 0.1)) * 2.2))
    rect_air = Rectangle((1, y_air_start), 8, visual_gap, linewidth=1.5, 
                          edgecolor='#5dade2', facecolor='#d4e6f1', linestyle='--', alpha=0.6)
    ax.add_patch(rect_air)
    ax.text(5, y_air_start + visual_gap/2, f"Air Gap   x = {x:.2f} mm", ha='center', va='center', 
            fontsize=9, style='italic', color='#1a5276')
    
    # Top moving conductor
    y_top = y_air_start + visual_gap + 0.1
    rect_top = Rectangle((1, y_top), 8, 1.0, linewidth=2.5, edgecolor='#1a5276', facecolor='#3498db')
    ax.add_patch(rect_top)
    ax.text(5, y_top + 0.5, "Top Conductor (Moving)", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
    
    # Double arrow for x
    if x > 0.05:
        ax.annotate('', xy=(9.7, y_air_start + visual_gap/2), xytext=(9.7, y_air_start - 0.1),
                    arrowprops=dict(arrowstyle='<->', color='red', lw=2.5))
        ax.text(10.1, y_air_start + visual_gap/2, 'x', fontsize=11, color='red', fontweight='bold')

else:
    # Sliding mode - conceptual top/side view
    ax.set_title(f"Sliding Mode  •  {contact_type}   (Overlap = L − x)", fontsize=12, fontweight='bold')
    
    # Fixed bottom layer
    rect_fixed = Rectangle((0.5, 1.5), 9.5, 2.2, linewidth=2.5, edgecolor='#2c3e50', facecolor='#7f8c8d')
    ax.add_patch(rect_fixed)
    ax.text(5.25, 2.6, "FIXED: Conductor + Dielectric Layer(s)", ha='center', va='center', 
            color='white', fontsize=9, fontweight='bold')
    ax.text(5.25, 1.9, f"Full length L = {l} mm   |   Width w = {w} mm", ha='center', va='center', 
            color='white', fontsize=8)
    
    # Moving top layer (overlap shrinks with x)
    overlap_frac = max(0.08, 1 - (x / max(l, 0.1)))
    overlap_visual = 9.0 * overlap_frac
    rect_moving = Rectangle((0.5, 4.0), overlap_visual, 1.8, linewidth=2.5, 
                             edgecolor='#c0392b', facecolor='#e74c3c', alpha=0.85)
    ax.add_patch(rect_moving)
    ax.text(0.5 + overlap_visual/2, 4.9, "MOVING\nConductor", ha='center', va='center', 
            color='white', fontsize=8, fontweight='bold')
    
    # Overlap label
    ax.text(0.5 + overlap_visual/2, 3.6, f"Overlap ≈ {l - x:.1f} mm", ha='center', va='center', 
            fontsize=8, color='#c0392b', fontweight='bold')
    
    # Arrow showing sliding direction x
    ax.annotate('', xy=(0.5 + overlap_visual + 0.8, 4.9), xytext=(0.5 + overlap_visual + 2.2, 4.9),
                arrowprops=dict(arrowstyle='->', color='red', lw=2.5))
    ax.text(0.5 + overlap_visual + 1.5, 5.4, f'x = {x:.1f} mm', ha='center', fontsize=9, color='red', fontweight='bold')
    
    ax.text(5.25, 0.7, "Note: Conceptual top/side view. Tribo charges present on dielectric surface. Only overlapping region contributes to capacitance.", 
            ha='center', fontsize=7, style='italic', color='#555555')

st.pyplot(fig_schem, use_container_width=True)

# ==================== PLOTS ====================
st.subheader(f"📊 {mode_label} Characteristics vs {x_label}")

fig, axs = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)

# 1. Voc
axs[0, 0].plot(x_plot_mm, Voc_plot, color='#2980b9', linewidth=2.2)
axs[0, 0].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label=f'Current x = {x} mm')
axs[0, 0].set_ylabel('Voc  (V)', fontsize=10)
axs[0, 0].set_title('Open-Circuit Voltage', fontsize=11, fontweight='bold')
axs[0, 0].grid(True, alpha=0.3)
axs[0, 0].legend(loc='upper left', fontsize=8)

# 2. Qsc
axs[0, 1].plot(x_plot_mm, Qsc_plot * 1e9, color='#27ae60', linewidth=2.2)
axs[0, 1].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
axs[0, 1].set_ylabel('Qsc  (nC)', fontsize=10)
axs[0, 1].set_title('Short-Circuit Transferred Charge', fontsize=11, fontweight='bold')
axs[0, 1].grid(True, alpha=0.3)

# 3. Capacitance
axs[1, 0].plot(x_plot_mm, C_plot * 1e12, color='#8e44ad', linewidth=2.2)
axs[1, 0].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
axs[1, 0].set_xlabel(x_label, fontsize=10)
axs[1, 0].set_ylabel('C  (pF)', fontsize=10)
axs[1, 0].set_title('Capacitance', fontsize=11, fontweight='bold')
axs[1, 0].grid(True, alpha=0.3)

# 4. Energy
axs[1, 1].plot(x_plot_mm, Energy_plot, color='#e67e22', linewidth=2.2)
axs[1, 1].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
axs[1, 1].set_xlabel(x_label, fontsize=10)
axs[1, 1].set_ylabel('Energy  (μJ)', fontsize=10)
axs[1, 1].set_title('Potential Harvested Energy', fontsize=11, fontweight='bold')
axs[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig, use_container_width=True)

# ==================== THEORY ====================
with st.expander("📚 Theory, Formulas & Physical Explanation (click to expand)", expanded=False):
    st.markdown(f"""
    ### Core Model (Standard Analytical V–Q–x Relationship)
    
    This simulator uses the **widely accepted analytical model** for attached-electrode TENGs 
    developed by Simiao Niu, Zhong Lin Wang and co-workers (Georgia Tech / Wang Lab).
    
    **Effective dielectric thickness**  
    """)
    
    if contact_type == "Conductor-to-Dielectric":
        st.latex(r"d_0 = \frac{d}{\varepsilon_r}")
    else:
        st.latex(r"d_0 = \frac{d_1}{\varepsilon_{r1}} + \frac{d_2}{\varepsilon_{r2}}")
    
    st.markdown("**Contact Mode (Vertical Contact-Separation)**")
    
    st.latex(r"C(x) = \frac{\varepsilon_0 S}{d_0 + x}")
    st.latex(r"V_{oc}(x) = \frac{\sigma x}{\varepsilon_0}")
    st.latex(r"Q_{sc}(x) = \sigma S \left(1 - \frac{d_0}{d_0 + x}\right) = \sigma S \frac{x}{d_0 + x}")
    st.latex(r"E(x) = \frac12 |Q_{sc}(x) \cdot V_{oc}(x)| \quad \text{(energy released when discharging at fixed x)}")
    
    st.markdown("**Sliding Mode (Lateral Sliding, assuming contact)**")
    
    st.latex(r"C(x) = \frac{\varepsilon_0 w (L - x)}{d_0}")
    st.latex(r"Q_{sc}(x) = \sigma \cdot w \cdot x")
    st.latex(r"V_{oc}(x) = \frac{Q_{sc}(x)}{C(x)} = \frac{\sigma d_0}{\varepsilon_0} \cdot \frac{x}{L - x}")
    
    st.markdown("""
    **Physical meaning:**
    - When the layers separate (or slide), the triboelectric charges (σ) create an electric field and potential difference.
    - **Voc** = voltage you would measure with open circuit (no charge flow).
    - **Qsc** = charge that flows through an external short-circuit wire to keep voltage = 0.
    - **C** decreases with increasing x (or decreasing overlap).
    - The **energy** value shown is the electrostatic energy that can be harvested if you let the device charge to Voc and then discharge it through a load at that fixed x.
    
    **Design insights you can explore instantly:**
    - Thinner dielectric (smaller d) or higher εᵣ → smaller d₀ → higher Qsc and C, but Voc changes.
    - Larger area (w × L) scales Qsc and energy linearly.
    - In contact mode there is an optimal x ≈ d₀ where power transfer is often best.
    - In sliding mode, Voc rises sharply as overlap → 0 (but practically limited by breakdown and edge effects).
    - The original MATLAB TENG CAD Tool used very similar equations and design rules (e.g. x + g ≤ 10×d₀ and x ≤ 0.9w).
    """)

st.markdown("---")
st.caption("""
**TENG Simulator v1.0** | Built with Python + Streamlit (automatically generates HTML/JS/CSS)  
For education, rapid prototyping and teaching.
""")
