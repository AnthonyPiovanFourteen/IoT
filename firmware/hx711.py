# Driver mínimo do HX711 (ganho 128, canal A) por bit-banging
from machine import Pin, disable_irq, enable_irq
import time


class HX711:
    def __init__(self, dout, sck, scale=1.0):
        self.dout = Pin(dout, Pin.IN)
        self.sck = Pin(sck, Pin.OUT, value=0)
        self.scale = scale
        self.offset = 0

    def is_ready(self):
        return self.dout.value() == 0

    def read_raw(self, timeout_ms=500):
        t0 = time.ticks_ms()
        while not self.is_ready():
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                return None
            time.sleep_ms(1)
        v = 0
        # Sem interrupções durante os 25 pulsos: SCK alto por >60 us faria o
        # HX711 entrar em power-down e a leitura sairia corrompida.
        estado = disable_irq()
        try:
            for _ in range(24):
                self.sck.value(1)
                time.sleep_us(2)  # dá tempo ao chip de atualizar o DOUT
                v = (v << 1) | self.dout.value()
                self.sck.value(0)
                time.sleep_us(2)
            # pulso extra: seleciona canal A, ganho 128 para a próxima leitura
            self.sck.value(1)
            self.sck.value(0)
        finally:
            enable_irq(estado)
        if v & 0x800000:
            v -= 1 << 24
        return v

    def get_units(self, n=5):
        """Mediana de n leituras convertidas pelo fator de calibração."""
        leituras = []
        for _ in range(n):
            r = self.read_raw()
            if r is not None:
                leituras.append(r)
        if not leituras:
            return None
        leituras.sort()
        mediana = leituras[len(leituras) // 2]
        return (mediana - self.offset) / self.scale
