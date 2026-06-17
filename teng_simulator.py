#!/usr/bin/env python3
"""
TENG Simulator - Web App (Python + Streamlit)
Modes: Attached Electrode - Contact Mode & Sliding Mode
"""

import streamlit as st
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

# ==================== PAGE SETUP ====================
st.set_page_config(
    page_title="TENG CAD Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== TITLE ====================
st.title("⚡ TENG Simulator")

# ====================== ADD YOUR NAME & COLLEGE HERE ======================
st.markdown("**Developed by: Dr. Pravin Kumar Singh, Manipal University Jaipur, Rajasthan, India**")
st.markdown("**Interactive Web App replicating TENG CAD Tool** | Contact & Sliding Modes | Educational Tool")
# ==========================================================================

st.markdown("---")

# ==================== MATERIAL DATABASE ====================
MATERIALS = {
    "PTFE (Teflon)": 2.1,
    "FEP": 2.1,
    "PDMS (Silicone)": 2.8,
    "Kapton (Polyimide)": 3.4,
    "PET / Mylar": 3.2,
    "PVC": 3.0,
    "Polystyrene (PS)": 2.6,
    "Polypropylene (PP)": 2.2,
    "PMMA (Acrylic)": 3.0,
    "Nylon": 4.0,
    "Polyurethane": 3.5,
    "Silicone Rubber": 3.5,
    "Custom": None
}

with st.sidebar:
    st.header("🔧 Configuration")

    operation_mode = st.radio(
        "Operation Mode",
        ["Contact Mode (Vertical Separation)", "Sliding Mode (Lateral Displacement)"],
        index=0
    )

    contact_type = st.radio(
        "Dielectric Configuration",
        ["Conductor-to-Dielectric", "Dielectric-to-Dielectric"],
        index=0
    )

    st.subheader("⚡ Triboelectric & Geometry")

    # ==================== CONDUCTOR-TO-DIELECTRIC ====================
    if contact_type == "Conductor-to-Dielectric":

        selected_material = st.selectbox(
            "Dielectric Material",
            list(MATERIALS.keys()),
            index=0,
            key="material_select"
        )

        if "current_er" not in st.session_state:
            st.session_state.current_er = 2.1
            st.session_state.current_sigma = 80.0
            st.session_state.last_material = selected_material

        if selected_material != st.session_state.last_material:
            st.session_state.last_material = selected_material
            if selected_material != "Custom":
                st.session_state.current_er = MATERIALS[selected_material]
                st.session_state.current_sigma = 70.0

        er = st.number_input(
            "Relative permittivity εᵣ",
            min_value=1.1, max_value=20.0,
            value=st.session_state.current_er,
            step=0.1,
            key=f"er_{selected_material}"
        )

        sigma = st.number_input(
            "Triboelectric charge density σ (μC/m²)",
            min_value=1.0, max_value=1000.0,
            value=st.session_state.current_sigma,
            step=5.0,
            key=f"sigma_{selected_material}"
        )

        d1 = d2 = er1 = er2 = 0.0

    # ==================== DIELECTRIC-TO-DIELECTRIC ====================
    else:

        st.markdown("**Dielectric Layer 1 (Top)**")
        mat1 = st.selectbox("Material 1", list(MATERIALS.keys()), index=0, key="mat1")

        er1 = st.number_input(
            "εᵣ1",
            min_value=1.1, max_value=20.0,
            value=MATERIALS.get(mat1, 2.0) if mat1 != "Custom" else 2.0,
            step=0.1,
            key=f"er1_{mat1}"
        )

        st.markdown("**Dielectric Layer 2 (Bottom)**")
        mat2 = st.selectbox("Material 2", list(MATERIALS.keys()), index=3, key="mat2")

        er2 = st.number_input(
            "εᵣ2",
            min_value=1.1, max_value=20.0,
            value=MATERIALS.get(mat2, 4.0) if mat2 != "Custom" else 4.0,
            step=0.1,
            key=f"er2_{mat2}"
        )

        sigma = st.number_input(
            "Triboelectric charge density σ (μC/m²)",
            min_value=1.0, max_value=1000.0,
            value=60.0, step=5.0
        )
        d = er = 0.0

        # ==================== COMMON INPUTS ====================
    w = st.number_input("Width w (mm)", min_value=5.0, max_value=500.0, value=50.0, step=5.0, key="width")
    l = st.number_input("Length L (mm)", min_value=5.0, max_value=500.0, value=50.0, step=5.0, key="length")

    if contact_type == "Conductor-to-Dielectric":
        d = st.number_input("Dielectric thickness d (μm)", min_value=5.0, max_value=2000.0, value=100.0, step=10.0, key="d_thick")
    else:
        d1 = st.number_input("Dielectric 1 thickness d1 (μm)", min_value=5.0, max_value=2000.0, value=50.0, step=5.0, key="d1_thick")
        d2 = st.number_input("Dielectric 2 thickness d2 (μm)", min_value=5.0, max_value=2000.0, value=50.0, step=5.0, key="d2_thick")

    x = st.number_input("Current x (mm)", min_value=0.0, max_value=200.0, value=1.0, step=0.1, key="x_val")
    xmax = st.number_input("Maximum x for plots (mm)", min_value=0.5, max_value=300.0, 
                           value=5.0 if "Contact" in operation_mode else 40.0, step=1.0, key="xmax_val")
# ==================== CALCULATIONS ====================
epsilon0 = 8.854187817e-12
sigma_SI = sigma * 1e-6
S_max = (w * l) * 1e-6
w_SI = w * 1e-3
L_SI = l * 1e-3
x_SI = x * 1e-3

if contact_type == "Conductor-to-Dielectric":
    d0 = (d * 1e-6) / er
else:
    d0 = (d1 * 1e-6) / er1 + (d2 * 1e-6) / er2
if d0 <= 0: d0 = 1e-9

if "Contact" in operation_mode:
    denom = d0 + x_SI
    if denom <= 0: denom = 1e-12
    C = epsilon0 * S_max / denom
    Voc = (sigma_SI / epsilon0) * x_SI
    Qsc = sigma_SI * S_max * (x_SI / denom)
    Energy_uJ = 0.5 * abs(Qsc) * abs(Voc) * 1e6

    x_plot_mm = np.linspace(0.001, xmax, 400)
    x_plot = x_plot_mm * 1e-3
    C_plot = epsilon0 * S_max / (d0 + x_plot)
    Voc_plot = (sigma_SI / epsilon0) * x_plot
    Qsc_plot = sigma_SI * S_max * (x_plot / (d0 + x_plot))
    Energy_plot = 0.5 * Qsc_plot * Voc_plot * 1e6
    mode_label = "Contact Mode"
    x_label = "Separation x (mm)"
else:
    overlap_current = max(L_SI - x_SI, 1e-9)
    C = epsilon0 * (w_SI * overlap_current) / d0
    Qsc = sigma_SI * w_SI * x_SI
    Voc = Qsc / C if C > 0 else 0.0
    Energy_uJ = 0.5 * abs(Qsc) * abs(Voc) * 1e6

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

# ==================== RESULTS ====================
st.subheader(f"📈 Results at x = {x:.2f} mm | {mode_label} — {contact_type}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Open-Circuit Voltage (Voc)", f"{Voc:.2f} V")
with col2:
    st.metric("Short-Circuit Charge (Qsc)", f"{Qsc*1e9:.2f} nC")
with col3:
    st.metric("Capacitance (C)", f"{C*1e12:.2f} pF")
with col4:
    st.metric("Energy", f"{Energy_uJ:.3f} μJ")

# ==================== DOWNLOAD BUTTON ====================
if st.button("📥 Download Current Results as CSV"):
    data = {
        "Parameter": ["Material", "Mode", "Configuration", "σ (μC/m²)", "Width (mm)", "Length (mm)", 
                      "x (mm)", "Voc (V)", "Qsc (nC)", "Capacitance (pF)", "Energy (μJ)"],
        "Value": [selected_material, operation_mode, contact_type, sigma, w, l, x, 
                  round(Voc, 2), round(Qsc*1e9, 2), round(C*1e12, 2), round(Energy_uJ, 3)]
    }
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Click here to Download CSV",
        data=csv,
        file_name="TENG_Results.csv",
        mime="text/csv"
    )

# Air breakdown warning
if "Contact" in operation_mode and x_SI > 1e-6:
    E_field = Voc / x_SI
    if E_field > 3.0e6:
        st.warning(f"⚠️ Air-breakdown risk! Electric field ≈ {E_field/1e6:.2f} MV/m")

# ==================== SCHEMATIC ====================
st.subheader("📐 Interactive Device Schematic (gap / overlap updates with x)")

fig_schem, ax = plt.subplots(figsize=(10, 4.5))
ax.set_xlim(-0.5, 11)
ax.set_ylim(-0.5, 7)
ax.axis('off')
ax.set_title(f"{mode_label}  •  {contact_type}", fontsize=13, fontweight='bold', pad=10)

if "Contact" in operation_mode:
    rect_bot = Rectangle((1, 0.3), 8, 1.0, linewidth=2.5, edgecolor='#1a5276', facecolor='#3498db')
    ax.add_patch(rect_bot)
    ax.text(5, 0.8, "Bottom Conductor (Electrode)", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
    
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
    
    visual_gap = min(2.2, max(0.15, (x / max(xmax, 0.1)) * 2.2))
    rect_air = Rectangle((1, y_air_start), 8, visual_gap, linewidth=1.5, 
                          edgecolor='#5dade2', facecolor='#d4e6f1', linestyle='--', alpha=0.6)
    ax.add_patch(rect_air)
    ax.text(5, y_air_start + visual_gap/2, f"Air Gap   x = {x:.2f} mm", ha='center', va='center', fontsize=9, style='italic', color='#1a5276')
    
    y_top = y_air_start + visual_gap + 0.1
    rect_top = Rectangle((1, y_top), 8, 1.0, linewidth=2.5, edgecolor='#1a5276', facecolor='#3498db')
    ax.add_patch(rect_top)
    ax.text(5, y_top + 0.5, "Top Conductor (Moving)", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
    
    if x > 0.05:
        ax.annotate('', xy=(9.7, y_air_start + visual_gap/2), xytext=(9.7, y_air_start - 0.1),
                    arrowprops=dict(arrowstyle='<->', color='red', lw=2.5))
        ax.text(10.1, y_air_start + visual_gap/2, 'x', fontsize=11, color='red', fontweight='bold')
else:
    rect_fixed = Rectangle((0.5, 1.5), 9.5, 2.2, linewidth=2.5, edgecolor='#2c3e50', facecolor='#7f8c8d')
    ax.add_patch(rect_fixed)
    ax.text(5.25, 2.6, "FIXED: Conductor + Dielectric Layer(s)", ha='center', va='center', color='white', fontsize=9, fontweight='bold')
    ax.text(5.25, 1.9, f"Full length L = {l} mm   |   Width w = {w} mm", ha='center', va='center', color='white', fontsize=8)
    
    overlap_frac = max(0.08, 1 - (x / max(l, 0.1)))
    overlap_visual = 9.0 * overlap_frac
    rect_moving = Rectangle((0.5, 4.0), overlap_visual, 1.8, linewidth=2.5, 
                             edgecolor='#c0392b', facecolor='#e74c3c', alpha=0.85)
    ax.add_patch(rect_moving)
    ax.text(0.5 + overlap_visual/2, 4.9, "MOVING\nConductor", ha='center', va='center', color='white', fontsize=8, fontweight='bold')
    ax.text(0.5 + overlap_visual/2, 3.6, f"Overlap ≈ {l - x:.1f} mm", ha='center', va='center', fontsize=8, color='#c0392b', fontweight='bold')
    
    ax.annotate('', xy=(0.5 + overlap_visual + 0.8, 4.9), xytext=(0.5 + overlap_visual + 2.2, 4.9),
                arrowprops=dict(arrowstyle='->', color='red', lw=2.5))
    ax.text(0.5 + overlap_visual + 1.5, 5.4, f'x = {x:.1f} mm', ha='center', fontsize=9, color='red', fontweight='bold')

st.pyplot(fig_schem, use_container_width=True)

# ==================== PLOTS ====================
st.subheader(f"📊 {mode_label} Characteristics vs {x_label}")

fig, axs = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)

axs[0, 0].plot(x_plot_mm, Voc_plot, color='#2980b9', linewidth=2.2)
axs[0, 0].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label=f'Current x = {x} mm')
axs[0, 0].set_ylabel('Voc (V)', fontsize=10)
axs[0, 0].set_title('Open-Circuit Voltage', fontsize=11, fontweight='bold')
axs[0, 0].grid(True, alpha=0.3)
axs[0, 0].legend(loc='upper left', fontsize=8)

axs[0, 1].plot(x_plot_mm, Qsc_plot * 1e9, color='#27ae60', linewidth=2.2)
axs[0, 1].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
axs[0, 1].set_ylabel('Qsc (nC)', fontsize=10)
axs[0, 1].set_title('Short-Circuit Transferred Charge', fontsize=11, fontweight='bold')
axs[0, 1].grid(True, alpha=0.3)

axs[1, 0].plot(x_plot_mm, C_plot * 1e12, color='#8e44ad', linewidth=2.2)
axs[1, 0].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
axs[1, 0].set_xlabel(x_label, fontsize=10)
axs[1, 0].set_ylabel('C (pF)', fontsize=10)
axs[1, 0].set_title('Capacitance', fontsize=11, fontweight='bold')
axs[1, 0].grid(True, alpha=0.3)

axs[1, 1].plot(x_plot_mm, Energy_plot, color='#e67e22', linewidth=2.2)
axs[1, 1].axvline(x=x, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
axs[1, 1].set_xlabel(x_label, fontsize=10)
axs[1, 1].set_ylabel('Energy (μJ)', fontsize=10)
axs[1, 1].set_title('Potential Harvested Energy', fontsize=11, fontweight='bold')
axs[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig, use_container_width=True)

# ==================== THEORY ====================
with st.expander("📚 Theory, Formulas & Physical Explanation (click to expand)", expanded=False):
    st.markdown("""
    ### Core Model (Standard Analytical V–Q–x Relationship)
    This simulator uses the widely accepted analytical model for attached-electrode TENGs.
    """)
    
    if contact_type == "Conductor-to-Dielectric":
        st.latex(r"d_0 = \frac{d}{\varepsilon_r}")
    else:
        st.latex(r"d_0 = \frac{d_1}{\varepsilon_{r1}} + \frac{d_2}{\varepsilon_{r2}}")
    
    st.markdown("**Contact Mode**")
    st.latex(r"C(x) = \frac{\varepsilon_0 S}{d_0 + x}")
    st.latex(r"V_{oc}(x) = \frac{\sigma x}{\varepsilon_0}")
    st.latex(r"Q_{sc}(x) = \sigma S \frac{x}{d_0 + x}")
    
    st.markdown("**Sliding Mode**")
    st.latex(r"C(x) = \frac{\varepsilon_0 w (L - x)}{d_0}")
    st.latex(r"Q_{sc}(x) = \sigma \cdot w \cdot x")
    st.latex(r"V_{oc}(x) = \frac{\sigma d_0}{\varepsilon_0} \cdot \frac{x}{L - x}")

st.markdown("---")
st.caption("TENG Simulator v1.1 | Built with Python + Streamlit | For education & research")
