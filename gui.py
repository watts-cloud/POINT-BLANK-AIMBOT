# -*- coding: utf-8 -*-
"""
Interface Gráfica (GUI) para Controle do Triggerbot Point Blank.
Versão Ultra-Otimizada (Sub-Milissegundo / 500+ FPS).
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
import time
import winsound
import tkinter as tk
from tkinter import ttk

import cv2
import mss
import numpy as np
import serial.tools.list_ports

from config_manager import carregar_config, salvar_config
from pico_serial import PicoSerial
from overlay_reticula import CrosshairOverlay

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Prioridade Alta e Timer de 1ms
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

user32 = ctypes.windll.user32
VK_PAUSA = 0x79     # F10 (Pausar/Retomar Triggerbot)
VK_RETICULA = 0x7A  # F11 (Ligar/Desligar Retícula Forçada)

# Limiares pré-compilados do Vermelho Puro (HSV)
HSV_LOWER1 = np.array([0, 75, 85], dtype=np.uint8)
HSV_UPPER1 = np.array([3, 255, 255], dtype=np.uint8)
HSV_LOWER2 = np.array([174, 75, 85], dtype=np.uint8)
HSV_UPPER2 = np.array([180, 255, 255], dtype=np.uint8)


class TriggerWorker(threading.Thread):
    def __init__(self, gui_app: TriggerGUI):
        super().__init__(daemon=True)
        self.app = gui_app
        self.rodando = True
        self.fps = 0.0

    def eh_vermelho_reticula(self, crop: np.ndarray) -> bool:
        b = crop[:, :, 0]
        g = crop[:, :, 1]
        r = crop[:, :, 2]
        return bool(np.any((r >= 160) & (g <= 100) & (b <= 100)))

    def eh_vermelho_sniper_simd(self, bgr: np.ndarray, min_pixels: int = 27) -> bool:
        """Filtro SIMD ultra-rápido em C++ (0.1ms): isola vermelho puro e rejeita marrom."""
        if bgr is None or bgr.size == 0:
            return False
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        m1 = cv2.inRange(hsv, HSV_LOWER1, HSV_UPPER1)
        m2 = cv2.inRange(hsv, HSV_LOWER2, HSV_UPPER2)
        m_hsv = cv2.bitwise_or(m1, m2)

        b, g, r = cv2.split(bgr)
        diff_rg = cv2.subtract(r, g)
        diff_rb = cv2.subtract(r, b)
        _, m_rg = cv2.threshold(diff_rg, 24, 255, cv2.THRESH_BINARY)
        _, m_rb = cv2.threshold(diff_rb, 24, 255, cv2.THRESH_BINARY)
        m_dom = cv2.bitwise_and(m_rg, m_rb)

        mascara_final = cv2.bitwise_and(m_hsv, m_dom)
        return cv2.countNonZero(mascara_final) >= min_pixels

    def obter_rois_scope(self, w: int, h: int) -> list[dict]:
        cx, cy = w // 2, h // 2
        lado = 16
        half = lado // 2
        coords = [
            (cx - int(0.38 * w), cy),
            (cx + int(0.38 * w), cy),
            (cx - int(0.28 * w), cy - int(0.32 * h)),
            (cx + int(0.28 * w), cy - int(0.32 * h)),
        ]
        return [
            {"left": px - half, "top": py - half, "width": lado, "height": lado}
            for px, py in coords
        ]

    def verificar_scope(self, sct: mss.mss, rois: list[dict], min_pct: float) -> bool:
        total = 0
        pretos = 0
        for r in rois:
            cap = sct.grab(r)
            img = np.frombuffer(cap.raw, dtype=np.uint8).reshape((cap.height, cap.width, 4))[:, :, :3]
            pretos += int(np.sum(img <= 18))
            total += img.size
        pct = (pretos / total) * 100.0 if total > 0 else 0.0
        return pct >= min_pct

    def run(self):
        ultimo_disparo = 0.0
        frames_count = 0
        t_fps = time.time()

        with mss.mss() as sct:
            while self.rodando:
                if not self.app.ativo or not self.app.pico or not self.app.pico.conn:
                    time.sleep(0.03)
                    continue

                w_scr = user32.GetSystemMetrics(0)
                h_scr = user32.GetSystemMetrics(1)
                cx = (w_scr // 2) + self.app.cfg.get("offset_x", 0)
                cy = (h_scr // 2) + self.app.cfg.get("offset_y", 0)

                modo_arma = self.app.cfg.get("arma_modo", "SNIPER").upper()

                disparar = False
                tipo_evento = ""

                # --- 1. Verificação Sniper (1 único Grab com Lazy Scope Gate) ---
                if modo_arma in ("SNIPER", "HIBRIDO"):
                    w = int(self.app.cfg.get("sniper_corredor_w", 118))
                    dist_inicio = int(self.app.cfg.get("sniper_dist_inicio", 40))
                    altura_max = int(self.app.cfg.get("sniper_altura_max", 314))
                    min_px = int(self.app.cfg.get("sniper_min_pixels", 27))

                    top = max(0, cy - altura_max)
                    height = max(10, altura_max - dist_inicio)
                    left = max(0, cx - (w // 2))

                    roi_snip = {
                        "left": left,
                        "top": top,
                        "width": w,
                        "height": height,
                    }

                    # Captura Zero-Copy do corredor
                    cap_snip = sct.grab(roi_snip)
                    img_snip = np.frombuffer(cap_snip.raw, dtype=np.uint8).reshape((cap_snip.height, cap_snip.width, 4))[:, :, :3]

                    # Filtro SIMD ultra-rápido (0.1ms)
                    if self.eh_vermelho_sniper_simd(img_snip, min_px):
                        exigir_scope = bool(self.app.cfg.get("sniper_exigir_scope", True))
                        min_scope_pct = float(self.app.cfg.get("sniper_scope_min_pct", 77.0))

                        # Só agora confirma se o scope está aberto (Lazy Check)
                        if not exigir_scope or self.verificar_scope(sct, self.obter_rois_scope(w_scr, h_scr), min_scope_pct):
                            disparar = True
                            tipo_evento = "SNIPER"

                # --- 2. Verificação Rifle (Retícula 3x3) ---
                if not disparar and modo_arma in ("RIFLE", "HIBRIDO"):
                    roi_ret = {
                        "left": cx - 1,
                        "top": cy - 1,
                        "width": 3,
                        "height": 3,
                    }
                    cap_ret = sct.grab(roi_ret)
                    img_ret = np.frombuffer(cap_ret.raw, dtype=np.uint8).reshape((cap_ret.height, cap_ret.width, 4))[:, :, :3]
                    if self.eh_vermelho_reticula(img_ret):
                        disparar = True
                        tipo_evento = "RIFLE"

                frames_count += 1
                agora = time.time()
                if agora - t_fps >= 1.0:
                    self.fps = frames_count / (agora - t_fps)
                    frames_count = 0
                    t_fps = agora

                if disparar:
                    if tipo_evento == "SNIPER":
                        cooldown = float(self.app.cfg.get("sniper_cooldown_ms", 271)) / 1000.0
                        tiros = int(self.app.cfg.get("sniper_tiros", 1))
                        intervalo_s = 0.05
                    else:
                        cooldown = float(self.app.cfg.get("cooldown_rajada_ms", 250)) / 1000.0
                        tiros = int(self.app.cfg.get("qtd_tiros", 3))
                        intervalo_s = float(self.app.cfg.get("intervalo_tiros_ms", 70)) / 1000.0

                    if agora - ultimo_disparo >= cooldown:
                        if tipo_evento == "SNIPER" or self.app.cfg.get("modo_disparo", "RAJADA") == "RAJADA":
                            self.app.pico.rajada(tiros=tiros, intervalo_s=intervalo_s, cmd="CLICK_TAP")
                        else:
                            self.app.pico.clique_unico("CLICK_TAP")
                            time.sleep(intervalo_s)
                        ultimo_disparo = time.time()

                time.sleep(0.0001)


class TriggerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Triggerbot Point Blank - Pico USB (Ultra-Fast)")
        self.root.geometry("450x690")
        self.root.resizable(False, False)

        self.cfg = carregar_config()
        self.ativo = True
        self.pico: PicoSerial | None = None

        self._aplicar_tema_escuro()
        self._construir_interface()

        self.overlay = CrosshairOverlay(master=self.root, cfg=self.cfg)
        if not self.cfg.get("reticula_ativa", True):
            self.overlay.ocultar()

        self.reconectar_pico()

        self.worker = TriggerWorker(self)
        self.worker.start()

        self.root.after(30, self._checar_hotkeys)
        self.root.after(500, self._atualizar_fps)

        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def _aplicar_tema_escuro(self):
        self.root.configure(bg="#18181b")
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background="#18181b", foreground="#f4f4f5", font=("Segoe UI", 9))
        style.configure("TLabel", background="#18181b", foreground="#e4e4e7")
        style.configure("TFrame", background="#18181b")
        style.configure("Card.TFrame", background="#27272a", relief="flat")
        style.configure("TCheckbutton", background="#18181b", foreground="#e4e4e7")
        style.configure("TRadiobutton", background="#27272a", foreground="#e4e4e7")
        style.configure("TCombobox", fieldbackground="#27272a", background="#3f3f46", foreground="#ffffff")
        style.configure("TNotebook", background="#18181b", tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", background="#27272a", foreground="#a1a1aa", padding=[9, 6], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#3b82f6")], foreground=[("selected", "#ffffff")])

    def _construir_interface(self):
        self.lbl_status = tk.Label(
            self.root,
            text="[ ATIVO - MONITORANDO ]",
            font=("Segoe UI", 12, "bold"),
            bg="#15803d",
            fg="#ffffff",
            pady=8,
        )
        self.lbl_status.pack(fill=tk.X, padx=12, pady=(10, 6))

        frame_arma = ttk.Frame(self.root, style="Card.TFrame", padding=8)
        frame_arma.pack(fill=tk.X, padx=12, pady=4)

        ttk.Label(frame_arma, text="MODO DE ARMA ATIVO:", font=("Segoe UI", 9, "bold"), foreground="#60a5fa").pack(anchor=tk.W, pady=(0, 4))
        self.var_arma = tk.StringVar(value=self.cfg.get("arma_modo", "SNIPER"))

        box_botoes_arma = ttk.Frame(frame_arma, style="Card.TFrame")
        box_botoes_arma.pack(fill=tk.X)

        for val, txt in [("SNIPER", "Sniper (Texto)"), ("RIFLE", "Rifle (Retícula)"), ("HIBRIDO", "Híbrido (Ambos)")]:
            ttk.Radiobutton(
                box_botoes_arma, text=txt, variable=self.var_arma, value=val, command=self._on_arma_change
            ).pack(side=tk.LEFT, expand=True)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        tab_sniper = ttk.Frame(self.notebook, style="Card.TFrame", padding=10)
        self.notebook.add(tab_sniper, text="Config Sniper")
        self._construir_aba_sniper(tab_sniper)

        tab_rifle = ttk.Frame(self.notebook, style="Card.TFrame", padding=10)
        self.notebook.add(tab_rifle, text="Config Rifle")
        self._construir_aba_rifle(tab_rifle)

        tab_reticula = ttk.Frame(self.notebook, style="Card.TFrame", padding=10)
        self.notebook.add(tab_reticula, text="Retícula (Mira)")
        self._construir_aba_reticula(tab_reticula)

        tab_serial = ttk.Frame(self.notebook, style="Card.TFrame", padding=10)
        self.notebook.add(tab_serial, text="Pico USB")
        self._construir_aba_serial(tab_serial)

        self.btn_toggle = tk.Button(
            self.root,
            text="PAUSAR [F10]",
            command=self.toggle_ativo,
            bg="#ef4444",
            fg="#ffffff",
            activebackground="#dc2626",
            activeforeground="#ffffff",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            pady=6,
        )
        self.btn_toggle.pack(fill=tk.X, padx=12, pady=(4, 4))

        btn_testar = tk.Button(
            self.root,
            text="Abrir Calibrador Visual de Mira (Tela)",
            command=self._abrir_calibrador_visual,
            bg="#27272a",
            fg="#60a5fa",
            activebackground="#3f3f46",
            activeforeground="#93c5fd",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            pady=4,
        )
        btn_testar.pack(fill=tk.X, padx=12, pady=(0, 6))

        frame_rodape = ttk.Frame(self.root)
        frame_rodape.pack(fill=tk.X, padx=14, pady=(2, 6))

        self.var_topo = tk.BooleanVar(value=self.cfg.get("sempre_no_topo", True))
        self.chk_topo = ttk.Checkbutton(
            frame_rodape, text="Fixar janela no topo", variable=self.var_topo, command=self._on_topo_change
        )
        self.chk_topo.pack(side=tk.LEFT)
        self._on_topo_change()

        self.lbl_fps = ttk.Label(frame_rodape, text="Scan: -- FPS", foreground="#71717a")
        self.lbl_fps.pack(side=tk.RIGHT)

    def _construir_aba_sniper(self, parent):
        self.var_scope_lock = tk.BooleanVar(value=self.cfg.get("sniper_exigir_scope", True))
        chk_scope = ttk.Checkbutton(
            parent,
            text="Exigir Luneta Aberta (Trava Anti-Falso Positivo Andando)",
            variable=self.var_scope_lock,
            command=self._on_scope_lock_change,
        )
        chk_scope.pack(anchor=tk.W, pady=(0, 6))

        cab_sc = ttk.Frame(parent, style="Card.TFrame")
        cab_sc.pack(fill=tk.X)
        ttk.Label(cab_sc, text="Sensibilidade da Luneta (Mínimo de Escuridão):").pack(side=tk.LEFT)
        self.lbl_val_scope_pct = ttk.Label(
            cab_sc, text=f"{int(self.cfg.get('sniper_scope_min_pct', 77))}%", font=("Segoe UI", 9, "bold"), foreground="#4ade80"
        )
        self.lbl_val_scope_pct.pack(side=tk.RIGHT)

        self.scale_scope_pct = ttk.Scale(
            parent, from_=50, to=95, value=self.cfg.get("sniper_scope_min_pct", 77), command=self._on_scope_pct_change
        )
        self.scale_scope_pct.pack(fill=tk.X, pady=(2, 8))

        cab_w = ttk.Frame(parent, style="Card.TFrame")
        cab_w.pack(fill=tk.X)
        ttk.Label(cab_w, text="Largura do Corredor (Variação lateral):").pack(side=tk.LEFT)
        self.lbl_val_snip_w = ttk.Label(
            cab_w, text=f"{self.cfg.get('sniper_corredor_w', 118)} px", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_snip_w.pack(side=tk.RIGHT)

        self.scale_snip_w = ttk.Scale(
            parent, from_=80, to=240, value=self.cfg.get("sniper_corredor_w", 118), command=self._on_snip_w_change
        )
        self.scale_snip_w.pack(fill=tk.X, pady=(2, 6))

        cab_h = ttk.Frame(parent, style="Card.TFrame")
        cab_h.pack(fill=tk.X)
        ttk.Label(cab_h, text="Altura do Corredor (Inimigos Perto):").pack(side=tk.LEFT)
        self.lbl_val_snip_h = ttk.Label(
            cab_h, text=f"{self.cfg.get('sniper_altura_max', 314)} px", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_snip_h.pack(side=tk.RIGHT)

        self.scale_snip_h = ttk.Scale(
            parent, from_=250, to=480, value=self.cfg.get("sniper_altura_max", 314), command=self._on_snip_h_change
        )
        self.scale_snip_h.pack(fill=tk.X, pady=(2, 6))

        cab_px = ttk.Frame(parent, style="Card.TFrame")
        cab_px.pack(fill=tk.X)
        ttk.Label(cab_px, text="Mínimo de Pixels Vermelhos (Gatilho):").pack(side=tk.LEFT)
        self.lbl_val_snip_px = ttk.Label(
            cab_px, text=f"{self.cfg.get('sniper_min_pixels', 27)} px", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_snip_px.pack(side=tk.RIGHT)

        self.scale_snip_px = ttk.Scale(
            parent, from_=5, to=45, value=self.cfg.get("sniper_min_pixels", 27), command=self._on_snip_px_change
        )
        self.scale_snip_px.pack(fill=tk.X, pady=(2, 6))

        cab_cd = ttk.Frame(parent, style="Card.TFrame")
        cab_cd.pack(fill=tk.X)
        ttk.Label(cab_cd, text="Cooldown (Recuo / Ferrolho):").pack(side=tk.LEFT)
        self.lbl_val_snip_cd = ttk.Label(
            cab_cd, text=f"{self.cfg.get('sniper_cooldown_ms', 271)} ms", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_snip_cd.pack(side=tk.RIGHT)

        self.scale_snip_cd = ttk.Scale(
            parent, from_=100, to=1000, value=self.cfg.get("sniper_cooldown_ms", 271), command=self._on_snip_cd_change
        )
        self.scale_snip_cd.pack(fill=tk.X, pady=(2, 6))

    def _construir_aba_rifle(self, parent):
        cab_int = ttk.Frame(parent, style="Card.TFrame")
        cab_int.pack(fill=tk.X)
        ttk.Label(cab_int, text="Intervalo entre tiros:").pack(side=tk.LEFT)
        self.lbl_val_intervalo = ttk.Label(
            cab_int, text=f"{self.cfg.get('intervalo_tiros_ms', 70)} ms", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_intervalo.pack(side=tk.RIGHT)

        self.scale_intervalo = ttk.Scale(
            parent, from_=10, to=200, value=self.cfg.get("intervalo_tiros_ms", 70), command=self._on_intervalo_change
        )
        self.scale_intervalo.pack(fill=tk.X, pady=(2, 8))

        cab_tiros = ttk.Frame(parent, style="Card.TFrame")
        cab_tiros.pack(fill=tk.X)
        ttk.Label(cab_tiros, text="Tiros por rajada:").pack(side=tk.LEFT)
        self.lbl_val_tiros = ttk.Label(
            cab_tiros, text=f"{self.cfg.get('qtd_tiros', 3)} tiros", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_tiros.pack(side=tk.RIGHT)

        self.scale_tiros = ttk.Scale(
            parent, from_=1, to=10, value=self.cfg.get("qtd_tiros", 3), command=self._on_tiros_change
        )
        self.scale_tiros.pack(fill=tk.X, pady=(2, 8))

        cab_cd = ttk.Frame(parent, style="Card.TFrame")
        cab_cd.pack(fill=tk.X)
        ttk.Label(cab_cd, text="Cooldown pós-rajada:").pack(side=tk.LEFT)
        self.lbl_val_cd = ttk.Label(
            cab_cd, text=f"{self.cfg.get('cooldown_rajada_ms', 250)} ms", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_cd.pack(side=tk.RIGHT)

        self.scale_cd = ttk.Scale(
            parent, from_=50, to=800, value=self.cfg.get("cooldown_rajada_ms", 250), command=self._on_cd_change
        )
        self.scale_cd.pack(fill=tk.X, pady=(2, 8))

        ttk.Label(parent, text="Modo de Disparo do Rifle:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(4, 2))
        self.var_modo = tk.StringVar(value=self.cfg.get("modo_disparo", "RAJADA"))
        box_modos = ttk.Frame(parent, style="Card.TFrame")
        box_modos.pack(fill=tk.X, pady=(2, 0))

        ttk.Radiobutton(
            box_modos, text="Rajada Fixa", variable=self.var_modo, value="RAJADA", command=self._on_modo_change
        ).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Radiobutton(
            box_modos, text="Enquanto Vermelho", variable=self.var_modo, value="ENQUANTO_VERMELHO", command=self._on_modo_change
        ).pack(side=tk.LEFT)

    def _construir_aba_reticula(self, parent):
        self.var_reticula_ativa = tk.BooleanVar(value=self.cfg.get("reticula_ativa", True))
        chk_ret = ttk.Checkbutton(
            parent,
            text="Exibir Retícula Forçada na Tela (Sniper Overlay)",
            variable=self.var_reticula_ativa,
            command=self._on_reticula_ativa_change,
        )
        chk_ret.pack(anchor=tk.W, pady=(0, 10))

        # Estilo da Mira
        ttk.Label(parent, text="Estilo da Retícula:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(2, 2))
        self.var_estilo_ret = tk.StringVar(value=self.cfg.get("reticula_estilo", "PONTO"))
        frame_estilos = ttk.Frame(parent, style="Card.TFrame")
        frame_estilos.pack(fill=tk.X, pady=(2, 10))

        for val, rotulo in [("PONTO", "Ponto"), ("CRUZ", "Cruz Tática"), ("CIRCULO", "Círculo")]:
            ttk.Radiobutton(
                frame_estilos,
                text=rotulo,
                variable=self.var_estilo_ret,
                value=val,
                command=self._on_reticula_estilo_change,
            ).pack(side=tk.LEFT, padx=(0, 14))

        # Cor da Mira
        ttk.Label(parent, text="Cor da Retícula (Com Contorno Preto):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(2, 2))
        self.cores_opcoes = {
            "Ciano Neon (Recomendado)": "#00FFFF",
            "Verde Neon": "#00FF00",
            "Amarelo": "#FFFF00",
            "Magenta": "#FF00FF",
            "Branco": "#FFFFFF",
            "Laranja": "#FFA500",
        }
        self.cb_cor_ret = ttk.Combobox(parent, state="readonly", values=list(self.cores_opcoes.keys()))
        cor_atual = self.cfg.get("reticula_cor", "#00FFFF").upper()
        rotulo_selecionado = "Ciano Neon (Recomendado)"
        for k, v in self.cores_opcoes.items():
            if v.upper() == cor_atual:
                rotulo_selecionado = k
                break
        self.cb_cor_ret.set(rotulo_selecionado)
        self.cb_cor_ret.bind("<<ComboboxSelected>>", self._on_reticula_cor_change)
        self.cb_cor_ret.pack(fill=tk.X, pady=(2, 10))

        # Slider de Tamanho
        cab_tam = ttk.Frame(parent, style="Card.TFrame")
        cab_tam.pack(fill=tk.X)
        ttk.Label(cab_tam, text="Tamanho / Raio da Retícula:").pack(side=tk.LEFT)
        self.lbl_val_tam_ret = ttk.Label(
            cab_tam, text=f"{self.cfg.get('reticula_tamanho', 4)} px", font=("Segoe UI", 9, "bold"), foreground="#38bdf8"
        )
        self.lbl_val_tam_ret.pack(side=tk.RIGHT)

        self.scale_tam_ret = ttk.Scale(
            parent,
            from_=2,
            to=10,
            value=self.cfg.get("reticula_tamanho", 4),
            command=self._on_reticula_tamanho_change,
        )
        self.scale_tam_ret.pack(fill=tk.X, pady=(2, 10))

        # Atalho F11
        lbl_info = ttk.Label(
            parent,
            text="★ Tecla de Atalho: [F11]\nLiga ou desliga a retícula instantaneamente enquanto joga.",
            foreground="#38bdf8",
            font=("Segoe UI", 8, "italic"),
            justify=tk.LEFT,
        )
        lbl_info.pack(anchor=tk.W, pady=(8, 0))

    def _construir_aba_serial(self, parent):
        ttk.Label(parent, text="Porta Serial do Raspberry Pi Pico:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(4, 6))

        sub_serial = ttk.Frame(parent, style="Card.TFrame")
        sub_serial.pack(fill=tk.X, pady=(2, 10))

        self.cb_portas = ttk.Combobox(sub_serial, state="readonly", width=14)
        self._listar_portas()
        self.cb_portas.pack(side=tk.LEFT, padx=(0, 8))

        btn_conectar = tk.Button(
            sub_serial,
            text="Reconectar",
            command=self.reconectar_pico,
            bg="#3b82f6",
            fg="#ffffff",
            relief="flat",
            padx=10,
            pady=2,
            font=("Segoe UI", 8, "bold"),
        )
        btn_conectar.pack(side=tk.LEFT)

        self.lbl_pico_info = ttk.Label(parent, text="Conectando...", foreground="#a1a1aa", font=("Segoe UI", 10))
        self.lbl_pico_info.pack(anchor=tk.W, pady=6)

    def _listar_portas(self):
        portas = [p.device for p in serial.tools.list_ports.comports()]
        if not portas:
            portas = ["COM3"]
        self.cb_portas["values"] = portas
        salva = self.cfg.get("porta_pico", "COM3")
        if salva in portas:
            self.cb_portas.set(salva)
        else:
            self.cb_portas.current(0)

    def reconectar_pico(self):
        porta = self.cb_portas.get().strip() or "COM3"
        self.cfg["porta_pico"] = porta
        salvar_config(self.cfg)

        if self.pico:
            self.pico.fechar()

        self.lbl_pico_info.config(text=f"Conectando na {porta}...", foreground="#fbbf24")
        self.pico = PicoSerial(porta=porta)
        if self.pico.conn:
            self.lbl_pico_info.config(text=f"Conectado com Sucesso na {porta}!", foreground="#4ade80")
            self._atualizar_banner()
        else:
            self.lbl_pico_info.config(text=f"Falha ao abrir {porta}. Verifique o cabo.", foreground="#f87171")
            self._atualizar_banner()

    def _on_arma_change(self):
        self.cfg["arma_modo"] = self.var_arma.get()
        salvar_config(self.cfg)

    def _on_scope_lock_change(self):
        self.cfg["sniper_exigir_scope"] = self.var_scope_lock.get()
        salvar_config(self.cfg)

    def _on_scope_pct_change(self, val):
        pct = int(float(val))
        self.lbl_val_scope_pct.config(text=f"{pct}%")
        self.cfg["sniper_scope_min_pct"] = pct
        salvar_config(self.cfg)

    def _on_snip_w_change(self, val):
        px = int(float(val))
        self.lbl_val_snip_w.config(text=f"{px} px")
        self.cfg["sniper_corredor_w"] = px
        salvar_config(self.cfg)

    def _on_snip_h_change(self, val):
        px = int(float(val))
        self.lbl_val_snip_h.config(text=f"{px} px")
        self.cfg["sniper_altura_max"] = px
        salvar_config(self.cfg)

    def _on_snip_px_change(self, val):
        px = int(float(val))
        self.lbl_val_snip_px.config(text=f"{px} px")
        self.cfg["sniper_min_pixels"] = px
        salvar_config(self.cfg)

    def _on_snip_cd_change(self, val):
        ms = int(float(val))
        self.lbl_val_snip_cd.config(text=f"{ms} ms")
        self.cfg["sniper_cooldown_ms"] = ms
        salvar_config(self.cfg)

    def _on_intervalo_change(self, val):
        ms = int(float(val))
        self.lbl_val_intervalo.config(text=f"{ms} ms")
        self.cfg["intervalo_tiros_ms"] = ms
        salvar_config(self.cfg)

    def _on_tiros_change(self, val):
        tiros = int(float(val))
        self.lbl_val_tiros.config(text=f"{tiros} tiros")
        self.cfg["qtd_tiros"] = tiros
        salvar_config(self.cfg)

    def _on_cd_change(self, val):
        ms = int(float(val))
        self.lbl_val_cd.config(text=f"{ms} ms")
        self.cfg["cooldown_rajada_ms"] = ms
        salvar_config(self.cfg)

    def _on_modo_change(self):
        self.cfg["modo_disparo"] = self.var_modo.get()
        salvar_config(self.cfg)

    def _on_topo_change(self):
        no_topo = self.var_topo.get()
        self.root.attributes("-topmost", no_topo)
        self.cfg["sempre_no_topo"] = no_topo
        salvar_config(self.cfg)

    def _on_reticula_ativa_change(self):
        ativa = self.var_reticula_ativa.get()
        self.cfg["reticula_ativa"] = ativa
        salvar_config(self.cfg)
        if hasattr(self, "overlay") and self.overlay:
            if ativa:
                self.overlay.mostrar()
                self.overlay.desenhar()
            else:
                self.overlay.ocultar()

    def _on_reticula_estilo_change(self):
        estilo = self.var_estilo_ret.get()
        self.cfg["reticula_estilo"] = estilo
        salvar_config(self.cfg)
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.desenhar()

    def _on_reticula_cor_change(self, event=None):
        sel = self.cb_cor_ret.get()
        cor_hex = self.cores_opcoes.get(sel, "#00FFFF")
        self.cfg["reticula_cor"] = cor_hex
        salvar_config(self.cfg)
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.desenhar()

    def _on_reticula_tamanho_change(self, val):
        tam = int(float(val))
        self.lbl_val_tam_ret.config(text=f"{tam} px")
        self.cfg["reticula_tamanho"] = tam
        salvar_config(self.cfg)
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.desenhar()

    def toggle_reticula(self):
        nova_ativa = not self.cfg.get("reticula_ativa", True)
        self.cfg["reticula_ativa"] = nova_ativa
        self.var_reticula_ativa.set(nova_ativa)
        salvar_config(self.cfg)
        if hasattr(self, "overlay") and self.overlay:
            if nova_ativa:
                self.overlay.mostrar()
                self.overlay.desenhar()
                try:
                    winsound.Beep(1200, 80)
                except Exception:
                    pass
            else:
                self.overlay.ocultar()
                try:
                    winsound.Beep(600, 80)
                except Exception:
                    pass

    def _abrir_calibrador_visual(self):
        pasta = os.path.dirname(os.path.abspath(__file__))
        script = os.path.join(pasta, "testar_mira.py")
        subprocess.Popen([sys.executable, script])

    def toggle_ativo(self):
        self.ativo = not self.ativo
        try:
            winsound.Beep(1000 if self.ativo else 500, 100)
        except Exception:
            pass
        self._atualizar_banner()

    def _atualizar_banner(self):
        if not self.pico or not self.pico.conn:
            self.lbl_status.config(text="[ PICO DESCONECTADO ]", bg="#b91c1c", fg="#ffffff")
            self.btn_toggle.config(text="PICO DESCONECTADO", bg="#7f1d1d", state=tk.DISABLED)
            return

        self.btn_toggle.config(state=tk.NORMAL)
        if self.ativo:
            self.lbl_status.config(text="[ ATIVO - MONITORANDO ]", bg="#15803d", fg="#ffffff")
            self.btn_toggle.config(text="PAUSAR [F10]", bg="#ef4444")
        else:
            self.lbl_status.config(text="[ PAUSADO ]", bg="#b45309", fg="#ffffff")
            self.btn_toggle.config(text="RETOMAR [F10]", bg="#22c55e")

    def _checar_hotkeys(self):
        if user32.GetAsyncKeyState(VK_PAUSA) & 0x0001:
            self.toggle_ativo()
        if user32.GetAsyncKeyState(VK_RETICULA) & 0x0001:
            self.toggle_reticula()
        self.root.after(40, self._checar_hotkeys)

    def _atualizar_fps(self):
        if self.worker:
            self.lbl_fps.config(text=f"Scan: {self.worker.fps:.0f} FPS")
        self.root.after(500, self._atualizar_fps)

    def ao_fechar(self):
        if self.worker:
            self.worker.rodando = False
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.destruir()
        if self.pico:
            self.pico.fechar()
        try:
            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TriggerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
