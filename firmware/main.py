# Alimentador pet monitorado - ESP32 (MicroPython) + HX711 + servo (Wokwi)
# Arquitetura (Opção B): ESP32 --HTTPS POST--> API (Supabase Edge Function) --> painel
import network
import socket
import ssl
import time
import ujson
from machine import Pin, PWM, I2C

import secrets
from hx711 import HX711
from lcd_i2c import LCD

# --- Identificação da leitura ---
DEVICE_ID = "esp32-alimentador-01"
GRANDEZA = "peso"
UNIDADE = "g"

# --- Parâmetros do problema ---
INTERVALO_COLETA_S = 5      # 1 leitura a cada 5 s
LIMITE_ALERTA_G = 200.0     # alerta: ração abaixo de 200 g
AMOSTRAS = 5                # média móvel de 5 leituras
FATOR_CALIBRACAO = 0.42
CAPACIDADE_G = 5000.0       # célula de carga de 5 kg

# --- Simulação do despejo de ração ---
# No Wokwi a célula de carga só muda pelo slider (manual) e o firmware não
# consegue mexer nele: o servo abrir não aumenta o peso do sensor. Para simular
# a ração caindo, cada ciclo com a comporta aberta soma DOSE_G ao peso. O valor
# somado é o que aparece no LCD e no painel (o slider é só a parte manual).
SIMULAR_ENCHIMENTO = True
DOSE_G = 120.0
# Variação brusca do sensor = alguém mexeu no peso (consumo/reposição manual):
# a ração "virtual" é zerada e o peso volta a ser o do sensor.
MUDANCA_MANUAL_G = 30.0

balanca = HX711(dout=27, sck=26, scale=FATOR_CALIBRACAO)
servo = PWM(Pin(13), freq=50)

try:
    lcd = LCD(I2C(0, scl=Pin(22), sda=Pin(21), freq=100000))
except Exception as e:
    lcd = None
    print("LCD indisponivel:", e)


def mostrar_lcd(peso, alerta, extra):
    """Mostra no LCD o mesmo peso que é enviado ao painel."""
    if lcd is None:
        return
    try:
        lcd.put(0, "Peso: %.1f g" % peso)
        lcd.put(1, "Limite: %d g %s" % (int(LIMITE_ALERTA_G), "ALERTA" if alerta else "OK"))
        lcd.put(2, "Comporta: " + ("ABERTA" if alerta else "fechada"))
        lcd.put(3, "Despejado: %d g%s" % (int(extra), " (sim)" if SIMULAR_ENCHIMENTO else ""))
    except Exception as e:
        print("LCD erro:", e)


def servo_angulo(graus):
    # pulso de 0,5 ms (0°) a 2,5 ms (180°) em período de 20 ms
    pulso_ms = 0.5 + (graus / 180) * 2.0
    servo.duty_u16(int(pulso_ms / 20 * 65535))


def conectar_wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if not sta.isconnected():
        print("WiFi...", end="")
        sta.connect("Wokwi-GUEST", "")
        while not sta.isconnected():
            time.sleep(0.2)
            print(".", end="")
    print(" ok")


_sock = None  # conexão HTTPS reaproveitada (o handshake TLS custa ~6 s na simulação)


def _conectar_https():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.verify_mode = ssl.CERT_NONE  # simulação: TLS sem validar a CA
    addr = socket.getaddrinfo(secrets.API_HOST, 443)[0][-1]
    s = socket.socket()
    s.settimeout(10)
    s.connect(addr)
    return ctx.wrap_socket(s, server_hostname=secrets.API_HOST)


def _ler_exato(s, n):
    while n > 0:
        parte = s.read(n)
        if not parte:
            raise OSError("conexão fechada")
        n -= len(parte)


def _ler_resposta(s):
    """Lê status + cabeçalhos + corpo (para a conexão poder ser reaproveitada)."""
    linha = s.readline()  # ex.: b"HTTP/1.1 201 Created\r\n"
    if not linha:
        raise OSError("conexão fechada")
    codigo = int(linha.split()[1])
    tamanho, chunked = 0, False
    while True:
        h = s.readline()
        if not h or h == b"\r\n":
            break
        minus = h.lower()
        if minus.startswith(b"content-length:"):
            tamanho = int(h.split(b":")[1])
        elif minus.startswith(b"transfer-encoding:") and b"chunked" in minus:
            chunked = True
    if chunked:
        while True:
            n = int(s.readline().split(b";")[0], 16)
            if n == 0:
                s.readline()
                break
            _ler_exato(s, n)
            s.readline()
    elif tamanho:
        _ler_exato(s, tamanho)
    return codigo


def enviar_leitura(corpo):
    """POST HTTPS (keep-alive) para a API. Devolve o código HTTP ou levanta exceção."""
    global _sock
    req = (
        "POST " + secrets.API_PATH + " HTTP/1.1\r\n"
        "Host: " + secrets.API_HOST + "\r\n"
        "x-api-key: " + secrets.API_KEY + "\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + str(len(corpo)) + "\r\n"
        "Connection: keep-alive\r\n\r\n" + corpo
    ).encode()
    for tentativa in (1, 2):
        try:
            if _sock is None:
                _sock = _conectar_https()
            _sock.write(req)
            return _ler_resposta(_sock)
        except Exception as e:
            try:
                _sock.close()
            except Exception:
                pass
            _sock = None  # na próxima tentativa/ciclo reconecta
            if tentativa == 2:
                raise e


janela = []
extra = 0.0          # ração "despejada" (simulação), em g
bruto_ant = None
servo_angulo(0)
conectar_wifi()
proximo = time.ticks_ms()

while True:
    t0 = time.ticks_ms()

    # 1) leitura + validação
    bruto = balanca.get_units(5)
    if bruto is None:
        print("HX711 sem resposta")
        time.sleep(1)
        continue
    if bruto < -50 or bruto > CAPACIDADE_G * 1.1:   # fora da faixa do sensor
        print("leitura inválida descartada:", bruto)
        time.sleep(1)
        continue
    if bruto < 0:
        bruto = 0.0

    # 2) tratamento: média móvel (+ ração despejada na simulação)
    if bruto_ant is not None and abs(bruto - bruto_ant) > MUDANCA_MANUAL_G:
        extra = 0.0      # a ração "virtual" some: o peso agora é o do sensor
        janela = []      # mudança real de peso: a média recomeça do novo valor
    bruto_ant = bruto
    janela.append(bruto)
    if len(janela) > AMOSTRAS:
        janela.pop(0)
    peso = sum(janela) / len(janela) + extra

    # 3) comparação com limite -> alerta; comporta aberta despeja ração
    alerta = peso < LIMITE_ALERTA_G
    servo_angulo(90 if alerta else 0)
    if alerta and SIMULAR_ENCHIMENTO:
        extra += DOSE_G          # vale a partir da próxima leitura
    mostrar_lcd(peso, alerta, extra)

    t1 = time.ticks_ms()

    # 4) envio à API
    corpo = ujson.dumps({
        "device_id": DEVICE_ID,
        "grandeza": GRANDEZA,
        "valor": round(peso, 1),
        "unidade": UNIDADE,
        "alerta": alerta,
    })
    try:
        codigo = enviar_leitura(corpo)
        print(corpo, "| HTTP", codigo)
    except Exception as e:
        print(corpo, "| ERRO no envio:", e)

    t2 = time.ticks_ms()
    print("tempos (ms): leitura+tratamento", time.ticks_diff(t1, t0),
          "| envio", time.ticks_diff(t2, t1),
          "| sensor", round(bruto, 1), "| extra", extra)

    # espera até o próximo instante múltiplo do intervalo (não "pausa + trabalho")
    proximo = time.ticks_add(proximo, INTERVALO_COLETA_S * 1000)
    espera = time.ticks_diff(proximo, time.ticks_ms())
    if espera > 0:
        time.sleep_ms(espera)
    else:
        print("ciclo atrasado em", -espera, "ms")
        proximo = time.ticks_ms()
