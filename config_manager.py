# -*- coding: utf-8 -*-
"""
Configurações e persistência em JSON para o Triggerbot Point Blank.
Suporta Modo Rifle e Modo Sniper com Trava de Scope (Vignette Redonda) e Corredor Vertical.
"""
from __future__ import annotations

import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "porta_pico": "COM3",
    "arma_modo": "SNIPER",          # "SNIPER", "RIFLE", "HIBRIDO"

    # Configurações de Tiro - Rifle
    "intervalo_tiros_ms": 70,
    "qtd_tiros": 3,
    "cooldown_rajada_ms": 250,
    "modo_disparo": "RAJADA",       # "RAJADA" ou "ENQUANTO_VERMELHO"

    # Configurações de Tiro - Sniper (Valores Calibrados Definitivos)
    "sniper_tiros": 1,
    "sniper_cooldown_ms": 271,      # 271 ms
    "sniper_corredor_w": 118,       # 118 px de largura
    "sniper_altura_max": 314,       # 314 px de altura máxima
    "sniper_dist_inicio": 40,       # 40 px acima do centro
    "sniper_min_pixels": 27,        # Mínimo de 27 pixels vermelhos para gatilho

    # Trava de Segurança do Scope (Vignette Redonda da Luneta)
    "sniper_exigir_scope": True,    # Exige que a luneta esteja aberta na tela
    "sniper_scope_min_pct": 77,     # Mínimo de 77% de escuridão nas bordas da luneta

    # Retícula Forçada na Tela (Sniper Crosshair Overlay)
    "reticula_ativa": True,
    "reticula_estilo": "PONTO",     # "PONTO", "CRUZ", "CIRCULO"
    "reticula_cor": "#00FFFF",       # Ciano Neon (contraste alto e seguro contra falsos positivos)
    "reticula_tamanho": 4,          # Tamanho do ponto / cruz (px)

    # Calibração Geral
    "offset_x": 0,
    "offset_y": 0,
    "sempre_no_topo": True,
}


def carregar_config() -> dict:
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(dados)
                return config
        except Exception as e:
            print(f"[CONFIG] Erro ao ler {CONFIG_FILE}: {e}")
    return DEFAULT_CONFIG.copy()


def salvar_config(cfg: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[CONFIG] Erro ao salvar {CONFIG_FILE}: {e}")
