import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AxialAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Axially Loaded Bars Analysis Module (拉压分析模块)")
        self.root.geometry("1100x900") 

        # --- 数据存储 ---
        self.num_elements = 3
        self.entries_elements = []
        self.entries_nodes = []

        # --- 单位变量 ---
        self.u_len = tk.StringVar(value="mm")
        self.u_area = tk.StringVar(value="mm2")
        self.u_mod = tk.StringVar(value="GPa")
        self.u_force = tk.StringVar(value="kN")
        self.u_disp = tk.StringVar(value="mm")

        # --- 界面布局 ---
        self.setup_ui()

    def setup_ui(self):
        # 1. 顶部控制栏
        control_frame = tk.Frame(self.root, pady=5, padx=5, relief="raised", bd=1)
        control_frame.pack(fill="x")
        
        tk.Label(control_frame, text="Element Count:").pack(side="left", padx=5)
        self.elem_count_var = tk.StringVar(value="3")
        tk.Entry(control_frame, textvariable=self.elem_count_var, width=5).pack(side="left")
        
        tk.Button(control_frame, text="Reset Table", command=self.reset_tables).pack(side="left", padx=10)
        
        # 预设按钮
        tk.Label(control_frame, text="|  Presets: ").pack(side="left", padx=10)
        tk.Button(control_frame, text="US (in/lb)", command=self.set_imperial, bg="#e1f5fe").pack(side="left", padx=2)
        tk.Button(control_frame, text="SI (mm/kN)", command=self.set_metric, bg="#e1f5fe").pack(side="left", padx=2)

        tk.Button(control_frame, text="Compute & Plot", command=self.calculate, bg="#c8e6c9", font=('Arial', 10, 'bold')).pack(side="right", padx=10)

        # 2. 表格区域
        self.main_pane = tk.PanedWindow(self.root, orient="vertical")
        self.main_pane.pack(fill="both", expand=True, padx=5, pady=5)

        self.top_frame = tk.Frame(self.main_pane)
        self.main_pane.add(self.top_frame)

        # 2.1 单元表
        self.elem_frame_container = tk.LabelFrame(self.top_frame, text="Element Properties", padx=5, pady=5)
        self.elem_frame_container.pack(fill="x", padx=5, pady=5)
        self.elem_table = tk.Frame(self.elem_frame_container)
        self.elem_table.pack(fill="x")

        # 2.2 单位栏
        unit_bar = tk.LabelFrame(self.top_frame, text="Units & Settings", padx=5, pady=5, bg="#f0f0f0")
        unit_bar.pack(fill="x", padx=5, pady=5)

        def create_unit_combo(parent, label_text, var, options, col):
            frame = tk.Frame(parent, bg="#f0f0f0")
            frame.grid(row=0, column=col, padx=10)
            tk.Label(frame, text=label_text, font=('Arial', 8), bg="#f0f0f0").pack(anchor="w")
            cb = ttk.Combobox(frame, textvariable=var, values=options, width=7, state="readonly")
            cb.pack()
            cb.bind("<<ComboboxSelected>>", self.update_headers)

        create_unit_combo(unit_bar, "Length", self.u_len, ["in", "ft", "mm", "m"], 0)
        create_unit_combo(unit_bar, "Area", self.u_area, ["in2", "ft2", "mm2", "m2"], 1)
        create_unit_combo(unit_bar, "Modulus", self.u_mod, ["psi", "ksi", "Pa", "MPa", "GPa"], 2)
        ttk.Separator(unit_bar, orient="vertical").grid(row=0, column=3, sticky="ns", padx=10)
        create_unit_combo(unit_bar, "Force", self.u_force, ["lb", "kips", "N", "kN"], 4)
        create_unit_combo(unit_bar, "Deflection", self.u_disp, ["in", "ft", "mm", "m"], 5)

        # 2.3 节点表
        self.node_frame_container = tk.LabelFrame(self.top_frame, text="Node Loads & BCs", padx=5, pady=5)
        self.node_frame_container.pack(fill="x", padx=5, pady=5)
        self.node_table = tk.Frame(self.node_frame_container)
        self.node_table.pack(fill="x")

        # 3. 结果汇总区
        self.result_frame = tk.LabelFrame(self.top_frame, text="Critical Results Summary", padx=5, pady=5, bg="#fff3e0")
        self.result_frame.pack(fill="x", padx=5, pady=5)
        self.lbl_max_force = tk.Label(self.result_frame, text="Max Force: N/A", font=('Arial', 10, 'bold'), bg="#fff3e0", fg="#d32f2f")
        self.lbl_max_force.pack(side="left", padx=20)
        self.lbl_max_disp = tk.Label(self.result_frame, text="Max Disp: N/A", font=('Arial', 10, 'bold'), bg="#fff3e0", fg="#1976d2")
        self.lbl_max_disp.pack(side="left", padx=20)

        # 4. 绘图区
        self.plot_frame = tk.Frame(self.main_pane, bg="white", bd=2, relief="sunken")
        self.main_pane.add(self.plot_frame)

        self.reset_tables()

    def set_imperial(self):
        self.u_len.set("in"); self.u_area.set("in2"); self.u_mod.set("psi")
        self.u_force.set("lb"); self.u_disp.set("in")
        self.reset_tables()

    def set_metric(self):
        self.u_len.set("mm"); self.u_area.set("mm2"); self.u_mod.set("GPa")
        self.u_force.set("kN"); self.u_disp.set("mm")
        self.reset_tables()

    def update_headers(self, event=None):
        self.reset_tables()

    def reset_tables(self):
        for widget in self.elem_table.winfo_children(): widget.destroy()
        for widget in self.node_table.winfo_children(): widget.destroy()
        self.entries_elements.clear()
        self.entries_nodes.clear()

        try:
            n_elem = int(self.elem_count_var.get())
            n_node = n_elem + 1
        except ValueError: return

        # 样式
        header_font = ('Arial', 9, 'bold'); header_color = "#3f51b5"
        
        # 单元表头
        headers = ["#", f"L ({self.u_len.get()})", f"A ({self.u_area.get()})", f"E ({self.u_mod.get()})"]
        for col, t in enumerate(headers): tk.Label(self.elem_table, text=t, font=header_font, fg=header_color).grid(row=0, column=col, padx=10)

        # 默认值
        is_metric = self.u_len.get() in ["mm", "m"]
        def_L, def_A, def_E = ("100", "100", "200") if is_metric else ("10.0", "1.0", "29000")

        for i in range(n_elem):
            tk.Label(self.elem_table, text=str(i+1)).grid(row=i+1, column=0)
            e_L = tk.Entry(self.elem_table, width=10, bg="#fffde7"); e_L.insert(0, def_L); e_L.grid(row=i+1, column=1)
            e_A = tk.Entry(self.elem_table, width=10, bg="#fffde7"); e_A.insert(0, def_A); e_A.grid(row=i+1, column=2)
            e_E = tk.Entry(self.elem_table, width=10, bg="#fffde7"); e_E.insert(0, def_E); e_E.grid(row=i+1, column=3)
            self.entries_elements.append((e_L, e_A, e_E))

        # 节点表头
        headers_n = ["#", f"Force ({self.u_force.get()})", "Constraint (1=Fix)"]
        for col, t in enumerate(headers_n): tk.Label(self.node_table, text=t, font=header_font, fg=header_color).grid(row=0, column=col, padx=10)

        for i in range(n_node):
            tk.Label(self.node_table, text=str(i+1)).grid(row=i+1, column=0)
            e_P = tk.Entry(self.node_table, width=10, bg="#fffde7"); e_P.insert(0, "0.0"); e_P.grid(row=i+1, column=1)
            e_BC = tk.Entry(self.node_table, width=10, bg="#fffde7"); e_BC.insert(0, "1" if i==0 else "0"); e_BC.grid(row=i+1, column=2)
            self.entries_nodes.append((e_P, e_BC))

    def calculate(self):
        try:
            n_elem = len(self.entries_elements); n_node = n_elem + 1
            L, A, E, Forces, Constraints = [], [], [], [], []

            for ent in self.entries_elements:
                L.append(float(ent[0].get())); A.append(float(ent[1].get())); E.append(float(ent[2].get()))
            for ent in self.entries_nodes:
                Forces.append(float(ent[0].get())); Constraints.append(int(ent[1].get()))

            # 刚度矩阵计算
            K = np.zeros((n_node, n_node)); F = np.array(Forces)
            for i in range(n_elem):
                k = (E[i]*A[i])/L[i]
                K[i,i]+=k; K[i,i+1]-=k; K[i+1,i]-=k; K[i+1,i+1]+=k

            # 边界条件
            penalty = 1e20
            for i in range(n_node):
                if Constraints[i] == 1: K[i,i] *= penalty; F[i] = 0

            U = np.linalg.solve(K, F)
            Internal_F = []
            for i in range(n_elem):
                f = ((E[i]*A[i])/L[i]) * (U[i+1] - U[i])
                Internal_F.append(f)

            self.draw_plots(n_elem, L, Internal_F, U)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def draw_plots(self, n_elem, L, Internal_Forces, Displacements):
        # --- 1. 寻找极值 ---
        abs_forces = [abs(f) for f in Internal_Forces]
        max_f_idx = np.argmax(abs_forces)
        max_f_val = Internal_Forces[max_f_idx]
        
        abs_disp = [abs(d) for d in Displacements]
        max_d_idx = np.argmax(abs_disp)
        max_d_val = Displacements[max_d_idx]

        # 更新汇总栏
        self.lbl_max_force.config(text=f"Max Force: {max_f_val:.2f} {self.u_force.get()} @ Elem {max_f_idx+1}")
        self.lbl_max_disp.config(text=f"Max Disp: {max_d_val:.4f} {self.u_disp.get()} @ Node {max_d_idx+1}")

        # --- 2. 准备绘图 ---
        for widget in self.plot_frame.winfo_children(): widget.destroy()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        fig.patch.set_facecolor('#f0f0f0') 
        plt.subplots_adjust(hspace=0.35, bottom=0.1, top=0.92, left=0.1, right=0.95)

        x_coords = [0]
        cur_x = 0
        for l in L: cur_x += l; x_coords.append(cur_x)

        # ==========================================
        # Plot 1: 轴力图 (Axial Force)
        # ==========================================
        x_plot, y_plot = [], []
        for i in range(n_elem):
            x_plot.extend([x_coords[i], x_coords[i+1]])
            y_plot.extend([Internal_Forces[i], Internal_Forces[i]])

        ax1.plot(x_plot, y_plot, color='#3f51b5', linewidth=2)
        ax1.fill_between(x_plot, y_plot, 0, alpha=0.2, color='#3f51b5')
        ax1.set_title("Axial Force Diagram", fontsize=10, fontweight='bold')
        ax1.set_ylabel(f"Force ({self.u_force.get()})", fontsize=9)
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        # 动态调整Y轴范围，为标签留出空间
        y_min, y_max = min(y_plot), max(y_plot)
        margin = (y_max - y_min) * 0.3 if y_max != y_min else abs(y_max)*0.5 + 1.0
        ax1.set_ylim(y_min - margin*0.5, y_max + margin)

        # ★★★ 遍历标注每一个单元的轴力 (修复遮挡) ★★★
        for i in range(n_elem):
            mid_x = (x_coords[i] + x_coords[i+1]) / 2
            val = Internal_Forces[i]
            is_max = (i == max_f_idx)
            
            if is_max:
                # 【最大值】：使用带箭头的标注，文字移到箭头尾部，防止遮挡数值
                # 箭头指向 (mid_x, val)，文字位于上方
                offset_y = margin * 1.3 # 文字向上偏移量
                # 如果数值为负，且空间足够，也可以考虑向下偏移，这里默认向上
                
                ax1.annotate(f"MAX: {val:.2f}", 
                             xy=(mid_x, val), 
                             xytext=(mid_x, val + offset_y),
                             arrowprops=dict(facecolor='red', arrowstyle='->', connectionstyle="arc3"),
                             fontsize=9, color='red', fontweight='bold', ha='center',
                             bbox=dict(facecolor='white', alpha=0.9, edgecolor='red', boxstyle='round,pad=0.2'))
            else:
                # 【普通值】：仅显示数值
                
                # 计算力值范围的自适应偏移（避免固定值在不同量级下偏移过大/过小）
                force_range = max(Internal_Forces) - min(Internal_Forces)
                offset = force_range * 0.03 if force_range != 0 else 1.0  # 3%的力值范围作为偏移

# 标注文字（向上偏移offset）
                ax1.text(mid_x, val + offset, f"{val:.2f}", 
                        ha='center', va='bottom', 
                        fontsize=8, color='#1a237e',
                        bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1))

        # ==========================================
        # Plot 2: 位移图 (Displacement)
        # ==========================================
        ax2.plot(x_coords, Displacements, 'r-o', linewidth=2, markersize=5)
        ax2.set_title("Displacement Diagram", fontsize=10, fontweight='bold')
        ax2.set_ylabel(f"Displacement ({self.u_disp.get()})", fontsize=9)
        ax2.set_xlabel(f"Position ({self.u_len.get()})", fontsize=9)
        ax2.grid(True, linestyle='--', alpha=0.6)
        
        # 动态调整Y轴范围
        y_d_min, y_d_max = min(Displacements), max(Displacements)
        margin_d = (y_d_max - y_d_min) * 0.3 if y_d_max != y_d_min else abs(y_d_max)*0.5 + 0.1
        ax2.set_ylim(y_d_min - margin_d, y_d_max + margin_d)

        # ★★★ 遍历标注每一个节点的位移 (修复遮挡) ★★★
        for i, (x, y) in enumerate(zip(x_coords, Displacements)):
            is_max = (i == max_d_idx)
            
            if is_max:
                # 【最大值】：带箭头标注
                # 为了显眼，给一个固定的偏移距离
                arrow_offset = 30 if y >= 0 else -30 
                
                ax2.annotate(f"MAX: {y:.4f}", 
                             xy=(x, y), 
                             xytext=(0, arrow_offset), 
                             textcoords='offset points',
                             arrowprops=dict(facecolor='red', arrowstyle='->'),
                             fontsize=9, color='red', fontweight='bold', ha='center', va='center',
                             bbox=dict(facecolor='white', alpha=0.9, edgecolor='red', boxstyle='round,pad=0.2'))
            else:
                # 【普通值】：错位排布
                y_offset = 12 if i % 2 == 0 else -18
                ax2.annotate(f"{y:.4f}", 
                             xy=(x, y), 
                             xytext=(0, y_offset), 
                             textcoords='offset points',
                             ha='center', va='center',
                             fontsize=8, color='#b71c1c',
                             bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=0.5))

        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
if __name__ == "__main__":
    root = tk.Tk()
    app = AxialAnalysisApp(root)
    root.mainloop()
