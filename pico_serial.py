# -*- coding: utf-8 -*-
"""
Driver de comunicação Serial com Raspberry Pi Pico via USB HID.
Compatível diretamente com o firmware code.py existente (Otimizado p/ Baixa Latência).
"""
from __future__ import annotations

import time
import serial
import config


class PicoSerial:
    def __init__(self, porta: str = config.PORTA_PICO, baudrate: int = config.BAUDRATE):
        self.porta = porta
        self.baudrate = baudrate
        self.conn: serial.Serial | None = None
        self._cmd_cache: dict[str, bytes] = {}
        self.conectar()

    def conectar(self) -> bool:
        try:
            # write_timeout=0.1 e timeout=0.1 para jamais travar o loop
            self.conn = serial.Serial(
                self.porta,
                self.baudrate,
                timeout=0.1,
                write_timeout=0.1,
            )
            time.sleep(0.3)
            print(f"[PICO] Conectado na porta {self.porta} (115200 baud).")
            return True
        except Exception as e:
            print(f"[PICO] FALHA ao conectar na porta {self.porta}: {e}")
            self.conn = None
            return False

    def enviar(self, comando: str | bytes) -> bool:
        if not self.conn or not self.conn.is_open:
            if not self.conectar():
                return False
        try:
            if isinstance(comando, str):
                if comando not in self._cmd_cache:
                    cmd_str = comando if comando.endswith("\n") else comando + "\n"
                    self._cmd_cache[comando] = cmd_str.encode("ascii")
                dados = self._cmd_cache[comando]
            else:
                dados = comando if comando.endswith(b"\n") else comando + b"\n"

            self.conn.write(dados)
            self.conn.flush()
            return True
        except Exception as e:
            print(f"[PICO] Erro ao enviar comando: {e}")
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
            return False

    def clique_unico(self, cmd: str = "CLICK_TAP") -> bool:
        return self.enviar(cmd)

    def rajada(self, tiros: int = 1, intervalo_s: float = 0.05, cmd: str = "CLICK_TAP") -> None:
        if tiros <= 1:
            self.enviar(cmd)
            return

        for i in range(tiros):
            self.enviar(cmd)
            if i + 1 < tiros and intervalo_s > 0:
                time.sleep(intervalo_s)

    def soltar(self) -> bool:
        return self.enviar(b"RELEASE\n")

    def fechar(self) -> None:
        try:
            if self.conn and self.conn.is_open:
                self.soltar()
                self.conn.close()
        except Exception:
            pass
        self.conn = None
