import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 设置 Matplotlib 中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif'] # 指定默认字体
plt.rcParams['axes.unicode_minus'] = False # 解决保存图像时负号'-'显示为方块的问题

# 设置网页标题与布局
st.set_page_config(page_title="Axially Loaded Bars Analysis Module", layout="wide")

st.title("Axially Loaded Bars Analysis Module (拉压分析模块)")
# st.markdown("将原本的 Tkinter 桌面版转换为 Streamlit 网页版，直接在表格中修改数据后点击计算。")

# --- 初始化 Session State 变量 ---
if 'n_elem' not in st.session_state:
    st.session_state['n_elem'] = 3
if 'unit_system' not in st.session_state:
    st.session_state['unit_system'] = 'SI (mm/kN)'

# --- 侧边栏：全局设置与单位 ---
with st.sidebar:
    st.header("⚙️ Settings (设置)")
    
    # 预设单位系统切换
    st.subheader("Presets (预设系统)")
    col1, col2 = st.columns(2)
    if col1.button("US (in/lb)"):
        st.session_state['unit_system'] = 'US (in/lb)'
    if col2.button("SI (mm/kN)"):
        st.session_state['unit_system'] = 'SI (mm/kN)'

    # 元素数量
    n_elem = st.number_input("Element Count (单元数量):", min_value=1, max_value=20, value=st.session_state['n_elem'], step=1)
    st.session_state['n_elem'] = n_elem

    # 单位下拉菜单
    st.subheader("Units (单位)")
    is_si = st.session_state['unit_system'] == 'SI (mm/kN)'
    
    u_len = st.selectbox("Length (长度)", ["mm", "m", "in", "ft"], index=0 if is_si else 2)
    u_area = st.selectbox("Area (面积)", ["mm2", "m2", "in2", "ft2"], index=0 if is_si else 2)
    u_mod = st.selectbox("Modulus (模数)", ["GPa", "MPa", "Pa", "ksi", "psi"], index=0 if is_si else 4)
    u_force = st.selectbox("Force (力)", ["kN", "N", "kips", "lb"], index=0 if is_si else 3)
    u_disp = st.selectbox("Deflection (位移)", ["mm", "m", "in", "ft"], index=0 if is_si else 2)

# --- 生成预设数据表格 ---
# 根据单位系统给予不同的预设值
def_L = 100.0 if is_si else 10.0
def_A = 100.0 if is_si else 1.0
def_E = 200.0 if is_si else 29000.0

n_node = n_elem + 1

# 建立单元 DataFrame
elem_data = {
    f"L ({u_len})": [def_L] * n_elem,
    f"A ({u_area})": [def_A] * n_elem,
    f"E ({u_mod})": [def_E] * n_elem
}
df_elem_default = pd.DataFrame(elem_data)
df_elem_default.index = [f"Elem {i+1}" for i in range(n_elem)]

# 建立节点 DataFrame
node_data = {
    f"Force ({u_force})": [0.0] * n_node,
    "Constraint (1=Fix, 0=Free)": [1 if i == 0 else 0 for i in range(n_node)]
}
df_node_default = pd.DataFrame(node_data)
df_node_default.index = [f"Node {i+1}" for i in range(n_node)]

# --- 主画面：数据输入区 ---
st.subheader("📝 Input Data (输入数据)")
# st.caption("您可以直接点击下方表格内的数字进行修改 (You can directly edit the values in the tables below)")

col_table1, col_table2 = st.columns(2)

with col_table1:
    st.markdown("**Element Properties (单元属性)**")
    df_elem = st.data_editor(df_elem_default, use_container_width=True)

with col_table2:
    st.markdown("**Node Loads & BCs (节点负载与边界条件)**")
    df_node = st.data_editor(df_node_default, use_container_width=True)

# --- 计算与绘图 ---
st.markdown("---")
if st.button("🚀 Compute & Plot (计算与绘图)", type="primary"):
    try:
        # 提取数据
        L = df_elem.iloc[:, 0].values.astype(float)
        A = df_elem.iloc[:, 1].values.astype(float)
        E = df_elem.iloc[:, 2].values.astype(float)
        
        Forces = df_node.iloc[:, 0].values.astype(float)
        Constraints = df_node.iloc[:, 1].values.astype(int)

        # --- 刚度矩阵计算 ---
        K = np.zeros((n_node, n_node))
        F = np.array(Forces)
        for i in range(n_elem):
            k = (E[i] * A[i]) / L[i]
            K[i, i] += k
            K[i, i+1] -= k
            K[i+1, i] -= k
            K[i+1, i+1] += k

        # --- 边界条件 (Penalty Method) ---
        penalty = 1e20
        for i in range(n_node):
            if Constraints[i] == 1:
                K[i, i] *= penalty
                F[i] = 0

        # --- 求解位移 ---
        U = np.linalg.solve(K, F)
        
        # --- 计算内力 ---
        Internal_Forces = []
        for i in range(n_elem):
            f = ((E[i] * A[i]) / L[i]) * (U[i+1] - U[i])
            Internal_Forces.append(f)

        # --- 寻找极值 ---
        abs_forces = [abs(f) for f in Internal_Forces]
        max_f_idx = np.argmax(abs_forces)
        max_f_val = Internal_Forces[max_f_idx]
        
        abs_disp = [abs(d) for d in U]
        max_d_idx = np.argmax(abs_disp)
        max_d_val = U[max_d_idx]

        # --- 显示关键结果 ---
        st.subheader("📊 Critical Results Summary (关键结果总结)")
        res_col1, res_col2 = st.columns(2)
        res_col1.metric(label=f"Max Force (最大内力) @ Elem {max_f_idx+1}", value=f"{max_f_val:.2f} {u_force}")
        res_col2.metric(label=f"Max Disp. (最大位移) @ Node {max_d_idx+1}", value=f"{max_d_val:.4f} {u_disp}")

        # --- 绘图 ---
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        fig.patch.set_facecolor('#ffffff')
        plt.subplots_adjust(hspace=0.3)

        x_coords = [0]
        cur_x = 0
        for l in L: 
            cur_x += l
            x_coords.append(cur_x)

        # 1. 轴力图 (Axial Force Diagram)
        x_plot, y_plot = [], []
        for i in range(n_elem):
            x_plot.extend([x_coords[i], x_coords[i+1]])
            y_plot.extend([Internal_Forces[i], Internal_Forces[i]])

        ax1.plot(x_plot, y_plot, color='#3f51b5', linewidth=2)
        ax1.fill_between(x_plot, y_plot, 0, alpha=0.2, color='#3f51b5')
        ax1.set_title("Axial Force Diagram (轴力图)", fontsize=12, fontweight='bold')
        ax1.set_ylabel(f"Force ({u_force})", fontsize=10)
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        y_min, y_max = min(y_plot), max(y_plot)
        margin = (y_max - y_min) * 0.3 if y_max != y_min else abs(y_max)*0.5 + 1.0
        ax1.set_ylim(y_min - margin*0.5, y_max + margin)

        # 标注轴力
        for i in range(n_elem):
            mid_x = (x_coords[i] + x_coords[i+1]) / 2
            val = Internal_Forces[i]
            is_max = (i == max_f_idx)
            
            if is_max:
                offset_y = margin * 0.8 
                ax1.annotate(f"MAX: {val:.2f}", 
                             xy=(mid_x, val), 
                             xytext=(mid_x, val + offset_y),
                             arrowprops=dict(facecolor='red', arrowstyle='->', connectionstyle="arc3"),
                             fontsize=10, color='red', fontweight='bold', ha='center',
                             bbox=dict(facecolor='white', alpha=0.9, edgecolor='red', boxstyle='round,pad=0.2'))
            else:
                force_range = max(Internal_Forces) - min(Internal_Forces)
                offset = force_range * 0.05 if force_range != 0 else 1.0
                ax1.text(mid_x, val + offset, f"{val:.2f}", 
                        ha='center', va='bottom', 
                        fontsize=9, color='#1a237e',
                        bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))

        # 2. 位移图 (Displacement Diagram)
        ax2.plot(x_coords, U, 'r-o', linewidth=2, markersize=6)
        ax2.set_title("Displacement Diagram (位移图)", fontsize=12, fontweight='bold')
        ax2.set_ylabel(f"Displacement ({u_disp})", fontsize=10)
        ax2.set_xlabel(f"Position ({u_len})", fontsize=10)
        ax2.grid(True, linestyle='--', alpha=0.6)
        
        y_d_min, y_d_max = min(U), max(U)
        margin_d = (y_d_max - y_d_min) * 0.3 if y_d_max != y_d_min else abs(y_d_max)*0.5 + 0.1
        ax2.set_ylim(y_d_min - margin_d, y_d_max + margin_d)

        # 标注位移
        for i, (x, y) in enumerate(zip(x_coords, U)):
            is_max = (i == max_d_idx)
            
            if is_max:
                arrow_offset = 40 if y >= 0 else -40 
                ax2.annotate(f"MAX: {y:.4f}", 
                             xy=(x, y), 
                             xytext=(0, arrow_offset), 
                             textcoords='offset points',
                             arrowprops=dict(facecolor='red', arrowstyle='->'),
                             fontsize=10, color='red', fontweight='bold', ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.9, edgecolor='red', boxstyle='round,pad=0.2'))
            else:
                y_offset = 15 if i % 2 == 0 else -20
                ax2.annotate(f"{y:.4f}", 
                             xy=(x, y), 
                             xytext=(0, y_offset), 
                             textcoords='offset points',
                             ha='center', va='center',
                             fontsize=9, color='#b71c1c',
                             bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=0.5))

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Error during calculation (计算时发生错误): {e}")
