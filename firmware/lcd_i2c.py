# Driver mínimo para LCD HD44780 com adaptador I2C PCF8574 (modo 4 bits)
# Mapa do PCF8574: P0=RS P1=RW P2=E P3=luz de fundo P4..P7=D4..D7
import time

_LINHAS = (0x00, 0x40, 0x14, 0x54)  # endereços DDRAM das linhas do LCD 20x4


class LCD:
    def __init__(self, i2c, addr=0x27, cols=20, rows=4):
        self.i2c = i2c
        self.addr = addr
        self.cols = cols
        self.rows = rows
        self.luz = 0x08
        time.sleep_ms(50)
        for espera in (5, 1, 1):          # sequência de inicialização do HD44780
            self._nibble(0x3, 0)
            time.sleep_ms(espera)
        self._nibble(0x2, 0)              # passa para 4 bits
        self._cmd(0x28)                   # 2 linhas, fonte 5x8
        self._cmd(0x0C)                   # display ligado, sem cursor
        self._cmd(0x06)                   # cursor incrementa
        self.clear()

    def _escreve(self, byte):
        self.i2c.writeto(self.addr, bytes([byte | self.luz]))

    def _nibble(self, nib, rs):
        b = (nib << 4) | rs
        self._escreve(b | 0x04)           # E = 1
        time.sleep_us(2)
        self._escreve(b & ~0x04)          # E = 0
        time.sleep_us(60)

    def _cmd(self, c):
        self._nibble(c >> 4, 0)
        self._nibble(c & 0x0F, 0)
        if c < 4:
            time.sleep_ms(2)

    def _chr(self, c):
        self._nibble(c >> 4, 1)
        self._nibble(c & 0x0F, 1)

    def clear(self):
        self._cmd(0x01)
        time.sleep_ms(2)

    def put(self, linha, texto):
        """Escreve 'texto' (ASCII) na linha, completando com espaços."""
        self._cmd(0x80 | _LINHAS[linha])
        for ch in texto[: self.cols] + " " * (self.cols - len(texto)):
            o = ord(ch)
            self._chr(o if o < 128 else 63)
