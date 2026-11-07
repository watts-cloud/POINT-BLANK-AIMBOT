# Auto Clique & Triggerbot para Point Blank em Python

Sistema inteligente de **Auto Clique por Visão Computacional** desenvolvido em Python para **Point Blank**, operando com latência sub-milissegundo e hardware USB HID externo (Raspberry Pi Pico) para máxima segurança e precisão.

---

## ⚡ Principais Recursos

- **Hardware USB HID Externo (Raspberry Pi Pico)**:
  - O clique do mouse é emitido fisicamente pelo microcontrolador como dispositivo HID padrão do Windows.
  - **Zero injeção em memória ou hooks de DLL** no processo do jogo.
- **Detecção Ultra-Rápida (Sub-Milissegundo / 500+ FPS)**:
  - Filtro SIMD vetorizado em C++ (`cv2.inRange` + subtração diferencial de canais).
  - Isolamento estrito de vermelho puro (rejeita tons de marrom, madeira, sombras e peles).
  - Captura de tela otimizada com leitura direta de buffers de memória (Zero-Copy).
- **Modo Sniper com Trava de Luneta (Scope Lock)**:
  - Corredor vertical adaptativo para identificar a exibição do nome/texto vermelho do inimigo.
  - **Trava Anti-Falso Positivo**: Analisa a vinheta preta da luneta na tela antes de autorizar o disparo, impedindo disparos indesejados ao andar ou mirar no cenário.
- **Modo Rifle**:
  - Detecção imediata na retícula central (3x3 pixels).
  - Controle configurável de rajadas (ex: 3 tiros com 70ms entre disparos e cooldown pós-rajada).
- **Overlay de Retícula Forçada na Tela (Crosshair)**:
  - Mira Always-on-Top com tecnologia transparente e **100% Click-Through** (`WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE`).
  - Permite jogar de Sniper no tiro livre (hip-fire) sabendo exatamente o centro da tela.
  - Estilos personalizáveis: Ponto, Cruz Tática e Círculo com Ponto.
  - Atalho global `F11` para ligar/desligar a mira a qualquer momento in-game.

---

## 📋 Requisitos

1. **Python 3.10 ou superior** instalado no Windows (com a opção *"Add Python to PATH"* marcada no instalador).
2. **Raspberry Pi Pico** plugado via USB e configurado com o firmware HID (`KMK` ou script serial).
3. **Point Blank configurado em Modo Janela (Windowed Mode)** para permitir a sobreposição da retícula.

---

## 🚀 Instalação Rápida

1. Clone o repositório ou baixe os arquivos:
   ```bash
   git clone https://github.com/watts-cloud/POINT-BLANK-AIMBOT.git
   cd POINT-BLANK-AIMBOT
   ```

2. Dê um duplo clique no arquivo **`INSTALADOR.bat`**.
   - O instalador verificará o ambiente Python, atualizará o `pip` e instalará todas as bibliotecas necessárias automaticamente.

---

## 🎮 Como Usar

1. Conecte o Raspberry Pi Pico na porta USB.
2. Dê um duplo clique em **`INICIAR.bat`** para abrir o Painel de Controle com interface gráfica.
3. No painel:
   - Selecione a porta serial do Pico (ex: `COM3`).
   - Escolha o modo de arma desejado: **Sniper**, **Rifle** ou **Híbrido**.
   - Ajuste os parâmetros conforme seu estilo de jogo.
   - Na aba **Retícula (Mira)**, ative e personalize o estilo e cor do crosshair.
4. Entre no Point Blank e aproveite!

### ⌨️ Atalhos de Teclado Globais (In-Game):
- **`[F10]`**: Pausar / Retomar o Auto Clique instantaneamente.
- **`[F11]`**: Ligar / Desligar a Retícula Forçada na tela.

---

## ⚙️ Configuração de Vídeo do Point Blank

Para que o overlay da retícula apareça perfeitamente sobre a tela do jogo:
1. Abra o arquivo **`PBConfig.exe`** na pasta do Point Blank (ou vá em *Configurações > Vídeo* dentro do jogo).
2. Marque a opção **☑ Modo Janela** (*Window Mode*).
3. Selecione a mesma resolução do seu monitor (ex: **1920x1080**).
4. Salve e inicie o jogo.

---

## 📦 Gerar Executável Standalone (.exe)

Caso deseje compilar a interface em um único executável sem precisar abrir o console do Python:
1. Dê um duplo clique em **`COMPILAR_EXE.bat`**.
2. O executável pronto será gerado dentro da pasta `dist/`.

---

## 📁 Estrutura do Projeto

```
├── config.json           # Armazenamento persistente das configurações
├── config_manager.py     # Gerenciador de leitura/escrita JSON
├── gui.py                # Interface gráfica completa com painel de controle
├── overlay_reticula.py   # Overlay Win32 click-through de alta performance
├── pico_serial.py        # Driver serial assíncrono para o Raspberry Pi Pico
├── trigger.py            # Loop de monitoramento e gatilho em tempo real
├── testar_mira.py        # Calibrador e visualizador de mira em tempo real
├── INSTALADOR.bat        # Instalador automático de dependências
├── INICIAR.bat           # Inicializador do painel principal
├── RETICULA.bat          # Inicializador independente do overlay de mira
├── COMPILAR_EXE.bat      # Script para compilar o executável com PyInstaller
├── requirements.txt      # Dependências do projeto
└── README.md             # Documentação do projeto
```

---

## ⚖️ Aviso Legal

Este projeto foi desenvolvido estritamente para fins de pesquisa educacional em visão computacional, automação de interface homem-máquina (HCI) e integração de microcontroladores USB HID. O uso em partidas online é de inteira responsabilidade do usuário.
