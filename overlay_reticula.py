# -*- coding: utf-8 -*-
"""
Overlay de Retícula Forçada na Tela (Crosshair Overlay para Point Blank).
Janela transparente, sem bordas, Always on Top e 100% Click-Through
(os cliques do mouse atravessam direto para o jogo sem delay ou roubo de foco).
"""
from __future__ import annotations

import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk

import config_manager

# Configurações de DPI Awareness para centralização perfeita em qualquer monitor
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32

# Assinaturas 64-bit seguras para Win32 API
try:
    SetWindowLongPtr = user32.SetWindowLongPtrW
    GetWindowLongPtr = user32.GetWindowLongPtrW
except AttributeError:
    SetWindowLongPtr = user32.SetWindowLongW
    GetWindowLongPtr = user32.GetWindowLongW

SetWindowLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_longlong]
SetWindowLongPtr.restype = ctypes.c_longlong
GetWindowLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int]
GetWindowLongPtr.restype = ctypes.c_longlong

user32.SetWindowPos.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_uint
]
user32.SetWindowPos.restype = ctypes.c_bool

HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008

# Cor transparente de fundo usada pelo Windows Layered Window
CHROMA_KEY = "#000001"


class CrosshairOverlay:
    def __init__(self, master=None, cfg: dict | None = None):
        self.cfg = cfg if cfg is not None else config_manager.carregar_config()
        self.master = master
        self.own_root = False

        if self.master is None:
            self.root = tk.Tk()
            self.root.withdraw()
            self.own_root = True
            self.win = tk.Toplevel(self.root)
        else:
            self.win = tk.Toplevel(self.master)

        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-transparentcolor", CHROMA_KEY)
        self.win.configure(bg=CHROMA_KEY)

        self.size = 60  # Tamanho do canvas central
        self.canvas = tk.Canvas(
            self.win,
            width=self.size,
            height=self.size,
            bg=CHROMA_KEY,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._tornar_click_through()
        self.atualizar_posicao()
        self.desenhar()

        if not self.cfg.get("reticula_ativa", True):
            self.ocultar()

        # Inicia loop persistente para garantir que a mira nunca fique atrás do jogo
        self._manter_no_topo()

    def _obter_hwnd(self) -> int:
        self.win.update_idletasks()
        hwnd = user32.GetParent(self.win.winfo_id())
        return hwnd if hwnd else self.win.winfo_id()

    def _tornar_click_through(self):
        """Torna a janela 100% transparente para cliques e força no topo absoluto."""
        try:
            hwnd = self._obter_hwnd()
            old_style = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
            new_style = old_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOPMOST
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, new_style)
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception as e:
            print(f"[RETICULA] Erro ao aplicar estilo click-through: {e}")

    def _manter_no_topo(self):
        """Loop a cada 150ms garantindo que a retícula fique sempre acima do Point Blank."""
        try:
            if self.win.winfo_exists() and self.cfg.get("reticula_ativa", True):
                hwnd = self._obter_hwnd()
                user32.SetWindowPos(
                    hwnd,
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
                )
        except Exception:
            pass
        try:
            self.win.after(150, self._manter_no_topo)
        except Exception:
            pass

    def atualizar_posicao(self):
        """Calcula o centro exato da tela levando em conta os offsets configurados."""
        w_scr = user32.GetSystemMetrics(0)
        h_scr = user32.GetSystemMetrics(1)

        cx = (w_scr // 2) + self.cfg.get("offset_x", 0)
        cy = (h_scr // 2) + self.cfg.get("offset_y", 0)

        x = cx - (self.size // 2)
        y = cy - (self.size // 2)

        self.win.geometry(f"{self.size}x{self.size}+{x}+{y}")

    def desenhar(self):
        """Desenha a retícula no centro do canvas conforme estilo e cor configurados."""
        self.atualizar_posicao()
        self.canvas.delete("all")

        estilo = self.cfg.get("reticula_estilo", "PONTO").upper()
        cor = self.cfg.get("reticula_cor", "#00FFFF")
        tam = int(self.cfg.get("reticula_tamanho", 4))

        mc = self.size // 2  # Ponto central exato do canvas (30, 30)

        if estilo == "PONTO":
            # Ponto central nítido com borda preta de alto contraste
            r = max(2, tam)
            self.canvas.create_oval(mc - r - 1, mc - r - 1, mc + r + 1, mc + r + 1, fill="#000000", outline="")
            self.canvas.create_oval(mc - r, mc - r, mc + r, mc + r, fill=cor, outline="")

        elif estilo == "CRUZ":
            # Mira estilo Cruz tática com abertura no centro
            gap = max(2, tam // 2)
            comp = max(6, tam * 2)
            larg = 2

            # Borda preta de fundo para destacar em qualquer mapa
            self.canvas.create_line(mc - comp - 1, mc, mc - gap + 1, mc, fill="#000000", width=larg + 2)
            self.canvas.create_line(mc + gap - 1, mc, mc + comp + 1, mc, fill="#000000", width=larg + 2)
            self.canvas.create_line(mc, mc - comp - 1, mc, mc - gap + 1, fill="#000000", width=larg + 2)
            self.canvas.create_line(mc, mc + gap - 1, mc, mc + comp + 1, fill="#000000", width=larg + 2)

            # Linhas coloridas internas
            self.canvas.create_line(mc - comp, mc, mc - gap, mc, fill=cor, width=larg)
            self.canvas.create_line(mc + gap, mc, mc + comp, mc, fill=cor, width=larg)
            self.canvas.create_line(mc, mc - comp, mc, mc - gap, fill=cor, width=larg)
            self.canvas.create_line(mc, mc + gap, mc, mc + comp, fill=cor, width=larg)

        elif estilo == "CIRCULO":
            # Círculo sutil com ponto central
            r_ext = max(7, tam * 2)
            r_pt = max(1, tam // 2)

            self.canvas.create_oval(mc - r_ext - 1, mc - r_ext - 1, mc + r_ext + 1, mc + r_ext + 1, outline="#000000", width=2)
            self.canvas.create_oval(mc - r_ext, mc - r_ext, mc + r_ext, mc + r_ext, outline=cor, width=1)

            self.canvas.create_oval(mc - r_pt - 1, mc - r_pt - 1, mc + r_pt + 1, mc + r_pt + 1, fill="#000000", outline="")
            self.canvas.create_oval(mc - r_pt, mc - r_pt, mc + r_pt, mc + r_pt, fill=cor, outline="")

    def mostrar(self):
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)
        hwnd = self._obter_hwnd()
        user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )

    def ocultar(self):
        self.win.withdraw()

    def alternar(self):
        if self.win.state() == "normal":
            self.ocultar()
            self.cfg["reticula_ativa"] = False
        else:
            self.mostrar()
            self.cfg["reticula_ativa"] = True
        config_manager.salvar_config(self.cfg)

    def destruir(self):
        try:
            self.win.destroy()
            if self.own_root:
                self.root.destroy()
        except Exception:
            pass


def main():
    """Modo Standalone para testes da retícula."""
    cfg = config_manager.carregar_config()
    cfg["reticula_ativa"] = True

    print("=" * 60)
    print("        RETÍCULA FORÇADA NA TELA (STANDALONE)")
    print("=" * 60)
    print("A retícula está ativa no centro exato da tela!")
    print("Clique-through ativo: você pode clicar normalmente no jogo.")
    print("Pressione Ctrl+C no console para fechar.")
    print("=" * 60)

    app = CrosshairOverlay(cfg=cfg)
    try:
        app.root.mainloop()
    except KeyboardInterrupt:
        app.destruir()


if __name__ == "__main__":
    main()
