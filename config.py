# -*- coding: utf-8 -*-
"""
Configurações do Triggerbot Point Blank com Raspberry Pi Pico.
"""

# Porta Serial do Raspberry Pi Pico
PORTA_PICO = "COM3"
BAUDRATE = 115200

# =====================================================================
# AJUSTES DA MIRA E DETECÇÃO (3x3 PIXELS NO CENTRO)
# =====================================================================
# Tamanho da área monitorada no centro (3 = 3x3 pixels: -1, 0, +1)
TAMANHO_BOX = 3

# Offset fino do centro da tela caso a retícula não esteja no pixel exato
OFFSET_X = 0
OFFSET_Y = 0

# Limiares de cor vermelha (BGR)
# A retícula verde normal tem R~0, G~255, B~0.
# A retícula sobre o inimigo tem R~252, G~25, B~6.
VERMELHO_R_MIN = 160
VERMELHO_G_MAX = 100
VERMELHO_B_MAX = 100

# =====================================================================
# AJUSTES DA RAJADA (PICO HARDWARE)
# =====================================================================
# Comando enviado ao firmware da Pico:
# "CLICK_TAP" = clique físico rápido (35ms segurado, nativo do firmware)
# "CLICK"     = clique longo padrão (220ms segurado)
CMD_CLIQUE = "CLICK_TAP"

# Modo de disparo:
# "RAJADA"            -> Dispara uma quantidade fixa (QTD_TIROS_RAJADA) a cada detecção
# "ENQUANTO_VERMELHO" -> Continua atirando enquanto a mira estiver vermelha
MODO_DISPARO = "RAJADA"

# Quantidade de tiros na rajada (modo "RAJADA")
QTD_TIROS_RAJADA = 3

# Intervalo entre os cliques da rajada (em segundos)
# 70ms = 0.070
INTERVALO_TIROS_S = 0.070

# Cooldown após encerrar a rajada antes de autorizar o próximo disparo (em segundos)
# Evita atirar sozinho durante a animação de recuo / coice da arma
COOLDOWN_POS_RAJADA = 0.25

# =====================================================================
# HOTKEYS DE CONTROLE (TECLADO)
# =====================================================================
VK_PAUSA = 0x79      # F10: Pausa / Retoma o bot
VK_PANICO = 0x7B     # F12: Encerra o bot imediatamente
