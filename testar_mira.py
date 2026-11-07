# -*- coding: utf-8 -*-
"""
Visualizador de Calibração da Retícula, Corredor Sniper e Leitor de Scope (Point Blank)
Com Filtro Estrito de Vermelho Puro (Anti-Marrom).
"""
from __future__ import annotations

import ctypes
import cv2
import mss
import numpy as np

from config_manager import carregar_config

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32


def eh_vermelho_reticula(crop_bgr: np.ndarray) -> bool:
    b = crop_bgr[:, :, 0]
    g = crop_bgr[:, :, 1]
    r = crop_bgr[:, :, 2]
    return bool(np.any((r >= 160) & (g <= 100) & (b <= 100)))


def eh_vermelho_sniper(crop_bgr: np.ndarray, min_pixels: int = 27) -> tuple[bool, int]:
    """Filtro de Vermelho Puro Estrito: Rejeita marrom, laranja, pele e madeira."""
    if crop_bgr is None or crop_bgr.size == 0:
        return False, 0
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    H = hsv[:, :, 0]
    S = hsv[:, :, 1]
    V = hsv[:, :, 2]

    r = crop_bgr[:, :, 2].astype(int)
    g = crop_bgr[:, :, 1].astype(int)
    b = crop_bgr[:, :, 0].astype(int)

    mascara = (
        ((H <= 3) | (H >= 174))
        & (S >= 75)
        & (V >= 85)
        & (r > g + 25)
        & (r > b + 25)
    )
    qtd = int(np.sum(mascara))
    return (qtd >= min_pixels), qtd


def verificar_scope(sct: mss.mss, w: int, h: int, min_pct: float = 77.0) -> tuple[bool, float, list[dict]]:
    cx, cy = w // 2, h // 2
    lado = 16
    half = lado // 2
    coords = [
        (cx - int(0.38 * w), cy),
        (cx + int(0.38 * w), cy),
        (cx - int(0.28 * w), cy - int(0.32 * h)),
        (cx + int(0.28 * w), cy - int(0.32 * h)),
    ]
    rois = [
        {"left": px - half, "top": py - half, "width": lado, "height": lado}
        for px, py in coords
    ]

    total_px = 0
    pretos_px = 0
    for r in rois:
        img = np.array(sct.grab(r))[:, :, :3]
        pretos_px += int(np.sum(img <= 18))
        total_px += img.size

    pct = (pretos_px / total_px) * 100.0 if total_px > 0 else 0.0
    return (pct >= min_pct), pct, rois


def main():
    cfg = carregar_config()

    w_scr = user32.GetSystemMetrics(0)
    h_scr = user32.GetSystemMetrics(1)

    cx = (w_scr // 2) + cfg.get("offset_x", 0)
    cy = (h_scr // 2) + cfg.get("offset_y", 0)

    corredor_w = int(cfg.get("sniper_corredor_w", 118))
    altura_max = int(cfg.get("sniper_altura_max", 314))
    dist_inicio = int(cfg.get("sniper_dist_inicio", 40))
    min_px = int(cfg.get("sniper_min_pixels", 27))
    min_scope = float(cfg.get("sniper_scope_min_pct", 77.0))

    print("=" * 70)
    print("  CALIBRADOR VISUAL: CORREDOR SNIPER + LEITOR DE SCOPE + RETÍCULA")
    print("  FILTRO ESTRITO ATIVO: Vermelho Puro (H: 0..3 / 174..180) Anti-Marrom")
    print("=" * 70)
    print(f"Resolução: {w_scr}x{h_scr} | Centro: ({cx}, {cy})")
    print(f"Corredor Sniper: {corredor_w}px larg | Altura {altura_max - dist_inicio}px")
    print(f"Trava de Scope: Exige >= {int(min_scope)}% de escuridão externa")
    print("Pressione 'Q' ou 'ESC' na janela para sair.")
    print("=" * 70)

    regiao_w = max(340, corredor_w + 120)
    regiao_h = max(500, altura_max + 100)

    regiao_left = cx - (regiao_w // 2)
    regiao_top = max(0, cy - altura_max - 40)

    roi_global = {
        "left": regiao_left,
        "top": regiao_top,
        "width": regiao_w,
        "height": regiao_h,
    }

    cv2.namedWindow("Calibrador Sniper - Point Blank", cv2.WINDOW_AUTOSIZE)

    with mss.mss() as sct:
        while True:
            # 1. Verifica Scope Aberto
            scope_ok, pct_scope, _ = verificar_scope(sct, w_scr, h_scr, min_pct=min_scope)

            # 2. Captura área central para visualização
            captura = sct.grab(roi_global)
            frame = np.array(captura)[:, :, :3]

            rcx = cx - regiao_left
            rcy = cy - regiao_top

            # 3. Retícula 3x3
            crop_reticula = frame[max(0, rcy - 1) : min(regiao_h, rcy + 2), max(0, rcx - 1) : min(regiao_w, rcx + 2)]
            reticula_ativa = eh_vermelho_reticula(crop_reticula) if crop_reticula.size > 0 else False

            # 4. Corredor Sniper
            sy_top = max(0, rcy - altura_max)
            sy_bottom = min(regiao_h, rcy - dist_inicio)
            sx_left = max(0, rcx - (corredor_w // 2))
            sx_right = min(regiao_w, rcx + (corredor_w // 2))

            crop_sniper = frame[sy_top:sy_bottom, sx_left:sx_right]
            texto_vermelho, count_px = eh_vermelho_sniper(crop_sniper, min_pixels=min_px) if crop_sniper.size > 0 else (False, 0)

            # Sniper só dispara se o scope estiver aberto E o texto estiver vermelho estrito!
            sniper_dispara = scope_ok and texto_vermelho

            # --- Overlays de Desenho ---
            canvas = frame.copy()

            # Linha da mira
            cv2.line(canvas, (rcx - 20, rcy), (rcx + 20, rcy), (120, 120, 120), 1)
            cv2.line(canvas, (rcx, rcy - 20), (rcx, rcy + 20), (120, 120, 120), 1)

            # Retícula Central
            cor_ret = (0, 0, 255) if reticula_ativa else (0, 255, 0)
            cv2.rectangle(canvas, (rcx - 4, rcy - 4), (rcx + 4, rcy + 4), cor_ret, 1)

            # Corredor do Sniper
            cor_snip = (0, 0, 255) if sniper_dispara else ((0, 165, 255) if texto_vermelho else (255, 180, 0))
            cv2.rectangle(canvas, (sx_left, sy_top), (sx_right, sy_bottom), cor_snip, 2)

            # Informações na tela
            cor_scope = (0, 255, 0) if scope_ok else (0, 0, 255)
            txt_scope = f"SCOPE LUNETA: {'[ABERTO]' if scope_ok else '[FECHADO/ANDANDO]'} ({pct_scope:.0f}% / {int(min_scope)}%)"
            cv2.putText(canvas, txt_scope, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cor_scope, 1)

            txt_snip = f"SNIPER STATUS: {'[DISPARANDO!]' if sniper_dispara else ('BLOQUEADO (SEM SCOPE)' if (texto_vermelho and not scope_ok) else 'LIVRE')}"
            cv2.putText(canvas, txt_snip, (sx_left, max(38, sy_top - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, cor_snip, 1)

            cv2.putText(canvas, f"Pixels texto (Vermelho Puro): {count_px}/{min_px} px", (sx_left, sy_top + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.40, cor_snip, 1)

            cv2.putText(canvas, f"RETICULA 3x3: {'[ALVO!]' if reticula_ativa else 'LIVRE'}", (10, regiao_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, cor_ret, 1)

            cv2.imshow("Calibrador Sniper - Point Blank", canvas)

            tecla = cv2.waitKey(20) & 0xFF
            if tecla == ord("q") or tecla == 27:
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
