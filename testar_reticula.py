# -*- coding: utf-8 -*-
"""
Visualizador de Calibração da Retícula (Point Blank)
Mostra uma janela com zoom ampliado dos 3x3 pixels do centro em tempo real,
exibindo as cores exatas (R, G, B) e se o gatilho seria disparado.
"""
from __future__ import annotations

import ctypes
import cv2
import mss
import numpy as np

import config
from trigger import eh_vermelho, obter_centro_tela

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    cx, cy = obter_centro_tela()
    tam = max(1, config.TAMANHO_BOX)
    half = tam // 2

    roi = {
        "left": cx - half,
        "top": cy - half,
        "width": tam,
        "height": tam,
    }

    print("=" * 60)
    print("     TESTADOR VISUAL DA RETÍCULA (CENTRO DA TELA)")
    print("=" * 60)
    print(f"Centro: ({cx}, {cy}) | Área: {tam}x{tam} pixels")
    print("Pressione 'Q' ou 'ESC' na janelinha para fechar.")
    print("=" * 60)

    cv2.namedWindow("Reticula 3x3 (Zoom 50x)", cv2.WINDOW_AUTOSIZE)

    with mss.mss() as sct:
        while True:
            captura = sct.grab(roi)
            img = np.array(captura)[:, :, :3]  # BGR

            dispararia = eh_vermelho(img)

            # Pega o pixel central exato
            pixel_centro = img[half, half]
            b, g, r = int(pixel_centro[0]), int(pixel_centro[1]), int(pixel_centro[2])

            # Aumenta a imagem para 200x200 para visualização confortável
            zoom = cv2.resize(img, (200, 200), interpolation=cv2.INTER_NEAREST)

            # Cor da borda: Vermelha se detectou disparo, Verde se mira limpa
            cor_borda = (0, 0, 255) if dispararia else (0, 255, 0)
            cv2.rectangle(zoom, (0, 0), (199, 199), cor_borda, 4)

            # Informações na tela
            texto_status = "ALVO DETECTADO!" if dispararia else "MIRA VERDE / LIVRE"
            cv2.putText(zoom, texto_status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor_borda, 2)
            cv2.putText(zoom, f"R:{r} G:{g} B:{b}", (10, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.imshow("Reticula 3x3 (Zoom 50x)", zoom)

            tecla = cv2.waitKey(15) & 0xFF
            if tecla == ord("q") or tecla == 27:  # 27 = ESC
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
