"""Gera docs/Relatorio_Alimentador_Inteligente.pdf (2 a 4 páginas, Times 12, sem estilização).

Uso:  python gerar_relatorio.py        (requer: pip install reportlab pillow)
Edite MEMBROS, LINK_GITHUB e LINK_VIDEO abaixo e rode de novo.
"""
import os
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

# ----------------------------- DADOS A PREENCHER -----------------------------
MEMBROS = [  # (nome, RA, contribuição)
    ("Leonardo Nunes Navas", "2010317",
     "<b>Dupla 1 – Sensor e firmware (ESP32 no Wokwi), com Wendell.</b> Responsável individual: leitura do "
     "HX711 e tratamento dos dados (mediana, validação de faixa, média móvel, comparação com o limite e "
     "alerta) e envio HTTPS à API."),
    ("Wendell Pereira Ribeiro", "2004501",
     "<b>Dupla 1 – Sensor e firmware (ESP32 no Wokwi), com Leonardo.</b> Responsável individual: circuito no "
     "Wokwi (diagram.json), servo por PWM, LCD I2C e simulação do despejo de ração."),
    ("Luan Moreira Alves", "1996380",
     "<b>Dupla 2 – API, banco e painel, com Anthony.</b> Responsável individual: API REST (Edge Function), "
     "tabela leituras no Postgres (Supabase) e proteção das escritas por chave."),
    ("Anthony Piovan", "1987602",
     "<b>Dupla 2 – API, banco e painel, com Luan.</b> Responsável individual: painel web, publicação no "
     "Cloudflare e integração entre as partes."),
]
CONJUNTO = ("Todos", "Testes de integração, relatório, vídeo de demonstração e repositório no GitHub.")
LINK_GITHUB = "https://github.com/AnthonyPiovanFourteen/IoT"
LINK_VIDEO = "https://youtu.be/jiXkEV0LdVE"
# -----------------------------------------------------------------------------

AQUI = os.path.dirname(os.path.abspath(__file__))
EVID = os.path.normpath(os.path.join(AQUI, "..", "evidencias"))
SAIDA = os.path.normpath(os.path.join(AQUI, "..", "Relatorio_Alimentador_Inteligente.pdf"))
TMP = os.path.join(AQUI, ".tmp")
os.makedirs(TMP, exist_ok=True)

F, FB, FI = "Times-Roman", "Times-Bold", "Times-Italic"
base = ParagraphStyle("base", fontName=F, fontSize=12, leading=13.6, alignment=TA_JUSTIFY, spaceAfter=3)
esq = ParagraphStyle("esq", parent=base, alignment=0)
cab = ParagraphStyle("cab", parent=base, fontName=FB, alignment=0, spaceBefore=5, spaceAfter=2)
tit = ParagraphStyle("tit", parent=base, fontName=FB, alignment=TA_CENTER, spaceAfter=1)
sub = ParagraphStyle("sub", parent=base, alignment=TA_CENTER, spaceAfter=1)
leg = ParagraphStyle("leg", parent=base, alignment=TA_CENTER, leading=13, spaceAfter=0)
cel = ParagraphStyle("cel", parent=base, alignment=0, leading=13, spaceAfter=0)
celb = ParagraphStyle("celb", parent=cel, fontName=FB)


def P(t, s=base):
    return Paragraph(t, s)


def foto(arq, largura_cm, recorte=None, nome=None):
    caminho = os.path.join(EVID, arq)
    if recorte:
        im = PILImage.open(caminho).crop(recorte)
        caminho = os.path.join(TMP, nome)
        im.save(caminho)
    w, h = PILImage.open(caminho).size
    return Image(caminho, width=largura_cm * cm, height=largura_cm * cm * h / w)


def diagrama():
    W, H = 16.4 * cm, 4.6 * cm
    d = Drawing(W, H)

    def caixa(x, y, w, h, linhas):
        d.add(Rect(x, y, w, h, strokeColor=None, fillColor=None))
        d.add(Rect(x, y, w, h, strokeWidth=1, strokeColor="black", fillColor="white"))
        n = len(linhas)
        for i, t in enumerate(linhas):
            d.add(String(x + w / 2, y + h / 2 + (n / 2 - i - 0.75) * 12, t, fontName=F if i else FB,
                         fontSize=10.5, textAnchor="middle"))

    def seta(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeWidth=1))
        if x2 != x1:   # horizontal
            s = 1 if x2 > x1 else -1
            d.add(Polygon([x2, y2, x2 - s * 6, y2 + 3, x2 - s * 6, y2 - 3], fillColor="black", strokeWidth=0))
        else:          # vertical
            s = 1 if y2 > y1 else -1
            d.add(Polygon([x2, y2, x2 - 3, y2 - s * 6, x2 + 3, y2 - s * 6], fillColor="black", strokeWidth=0))

    # coluna 1: dispositivo | coluna 2: API | coluna 3: banco ; painel embaixo da API
    caixa(0, 2.7 * cm, 4.6 * cm, 1.9 * cm, ["ESP32 + HX711", "servo + LCD", "(Wokwi, MicroPython)"])
    caixa(5.9 * cm, 2.7 * cm, 4.6 * cm, 1.9 * cm, ["API REST", "Supabase Edge Function", "(HTTPS)"])
    caixa(11.8 * cm, 2.7 * cm, 4.6 * cm, 1.9 * cm, ["Armazenamento", "Postgres (Supabase)", "tabela leituras"])
    caixa(5.9 * cm, 0, 4.6 * cm, 1.6 * cm, ["Painel web", "(Cloudflare)"])
    seta(4.6 * cm, 3.65 * cm, 5.9 * cm, 3.65 * cm)
    seta(10.5 * cm, 3.65 * cm, 11.8 * cm, 3.65 * cm)
    seta(8.2 * cm, 1.6 * cm, 8.2 * cm, 2.7 * cm)      # painel consulta a API
    d.add(String(5.25 * cm, 3.85 * cm, "POST", fontName=F, fontSize=9, textAnchor="middle"))
    d.add(String(5.25 * cm, 3.1 * cm, "/ingest", fontName=F, fontSize=9, textAnchor="middle"))
    d.add(String(8.45 * cm, 2.05 * cm, "GET /latest, /history", fontName=F, fontSize=9, textAnchor="start"))
    d.add(String(11.15 * cm, 3.85 * cm, "grava", fontName=F, fontSize=9, textAnchor="middle"))
    return d


def tabela(linhas, larguras, cabecalho=True):
    dados = []
    for i, l in enumerate(linhas):
        dados.append([Paragraph(c, celb if (i == 0 and cabecalho) else cel) for c in l])
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1 if cabecalho else 0)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, "black"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def duas_figuras(a, b, largura=6.6):
    """a, b = (imagem, legenda). Lado a lado, legenda embaixo."""
    t = Table([[a[0], b[0]], [P(a[1], leg), P(b[1], leg)]], colWidths=[8.2 * cm, 8.2 * cm])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return t


story = []
story += [P("ALIMENTADOR INTELIGENTE: MONITORAMENTO IoT DO NÍVEL DE RAÇÃO", tit),
          P("Projeto Integrador – Arquitetura de Computadores", sub),
          P("Integrantes: " + "; ".join("%s (RA %s)" % (n, ra) for n, ra, _ in MEMBROS), sub), Spacer(1, 3)]

story += [P("Links do projeto", cab),
          P("Painel publicado: https://monitor-alimentador.anthonygpiovan14.workers.dev<br/>"
            "Projeto Wokwi: https://wokwi.com/projects/481705288139185153<br/>"
            "API: https://azjsleyewchvvzfkdpmw.supabase.co/functions/v1/api (rotas /latest e /history)<br/>"
            "Repositório GitHub: " + LINK_GITHUB + "<br/>"
            "Vídeo de demonstração: " + LINK_VIDEO, esq)]

story += [P("1. Problema escolhido", cab),
          P("Monitorar o peso de ração em um pote de alimentador de animais de estimação. A grandeza medida é o "
            "peso, em gramas, com uma leitura a cada 5 segundos. A condição de alerta é peso abaixo de 200 g: "
            "nesse caso o servo abre a comporta, o LCD indica o alerta e o painel exibe o aviso. Tudo é simulado "
            "no Wokwi, sem dispositivos físicos; o peso é alterado pelo controle de pressão da célula de carga.")]

story += [P("2. Arquitetura", cab), diagrama(),
          P("Figura 1 – Arquitetura adotada (Opção B: envio direto por HTTPS).", leg), Spacer(1, 3),
          P("Foi adotada a Opção B do enunciado: o ESP32 envia as leituras diretamente à API por HTTPS. O MQTT é "
            "opcional e não foi utilizado (ver Limitações); por isso a solução não tem broker. Em uma arquitetura "
            "com MQTT, o broker desacopla quem publica de quem consome as leituras.")]

story += [P("3. Funcionamento", cab),
          P("<b>Comunicação do ESP32 com o sensor.</b> O ESP32 (MicroPython) lê o HX711, conversor analógico-digital "
            "de 24 bits da célula de carga de 5 kg, por dois fios: DT (dados, GPIO 27) e SCK (relógio, GPIO 26). A "
            "cada leitura o ESP32 gera 25 pulsos em SCK e lê um bit de DT por pulso (comunicação serial síncrona "
            "feita por software), com interrupções desabilitadas durante os pulsos, pois o SCK em nível alto por "
            "mais de 60 µs coloca o HX711 em repouso e corrompe o valor. O resultado é um inteiro de 24 bits com "
            "sinal, convertido para gramas por um fator de calibração. O servo é acionado por PWM de 50 Hz (GPIO 13) "
            "e o LCD 20x4 pelo barramento I2C (GPIO 21 e 22)."),
          P("<b>Onde os dados são processados.</b> O tratamento ocorre no ESP32: mediana de 5 leituras brutas; "
            "validação de faixa (descarta valores fora de -50 g a 5,5 kg); média móvel de 5 amostras, reiniciada "
            "se o peso muda mais de 30 g; e comparação com o limite de 200 g. No Wokwi a célula de carga só muda "
            "pelo controle manual, então, para o servo \"acrescentar\" ração, o firmware soma 120 g por leitura com "
            "a comporta aberta; esse valor aparece no LCD e no painel."),
          P("<b>Onde são armazenados e como a API conecta o dispositivo ao painel.</b> A cada ciclo o ESP32 envia "
            "por HTTPS um JSON com device_id, grandeza, valor, unidade e alerta (POST /ingest, protegido por chave "
            "no cabeçalho x-api-key). A Edge Function valida o corpo, identifica o dispositivo e a grandeza e grava "
            "a linha na tabela leituras do Postgres, com o horário de recebimento, mesmo com o painel fechado. O "
            "painel consulta GET /latest (leitura mais recente) e GET /history (histórico) a cada 3 s."),
          P("<b>Painel.</b> Mostra o valor atual, a unidade, o horário da última atualização, o histórico em "
            "gráfico, a condição de alerta, um pote que se enche conforme o peso e uma linha do tempo de eventos. "
            "Se passam 20 s sem leitura nova, exibe \"Dados desatualizados\" e volta ao normal sozinho quando a "
            "transmissão é retomada."),
          P("<b>Efeito do intervalo de coleta.</b> O intervalo define o atraso máximo para detectar o alerta, o "
            "volume de dados (5 s: 17.280 leituras por dia por dispositivo, cerca de 694 MB por ano; 30 s: 2.880 por "
            "dia; 5 min: 288 por dia), o número de requisições à API e o limite de dados desatualizados (4 "
            "intervalos). O tempo de cada ciclo também importa: abrir uma conexão HTTPS nova a cada envio custa "
            "cerca de 6,5 s de handshake TLS no ESP32 e fazia o intervalo real chegar a 12,5 s; por isso a "
            "conexão é reaproveitada (keep-alive) e o intervalo real medido no banco é de 5,02 s (mediana).")]

story += [P("4. Testes", cab),
          P("Executados em 25/11/2026 (horários em UTC) e registrados com dados do banco e capturas de tela "
            "(pasta docs do repositório).", base),
          tabela([
              ["Teste", "Resultado"],
              ["1. Fluxo completo", "O peso alterado no Wokwi chegou à API (HTTP 201 no serial) e foi exibido no painel."],
              ["2. Alerta", "Em 100 g: alerta=true, banner vermelho e servo a 90 graus. Ao subir para 500 g o alerta "
                            "desligou ao passar de 200 g."],
              ["3. Interrupção e retomada", "Simulação parada às 00:02:30; o painel exibiu \"Dados desatualizados\". "
                                            "Retomada às 00:03:06: lacuna de 65 s no banco e painel recuperado sem recarregar."],
              ["4. Painel fechado", "Com o painel fechado por cerca de 70 s, o banco recebeu 5 leituras, inclusive a "
                                    "passagem para alerta; ao reabrir, o histórico as exibiu."],
              ["5. Despejo e intervalo", "Sensor zerado: 0 g (alerta) -> 120 g -> 240 g (alerta desliga), a cada 5 s. O LCD "
                                  "mostrou \"Peso: 0.0 g, ALERTA, Comporta: ABERTA, Despejado: 120 g\"."],
              ["6. API", "POST sem chave e com chave errada: 401; rota inexistente: 404; CORS liberado; consultas de "
                         "dispositivo inexistente: null e lista vazia."],
          ], [3.9, 12.5]), Spacer(1, 4)]

LF = 6.0  # largura das capturas (cm)
story += [KeepTogether([
    duas_figuras((foto("v2-painel-publicado-500g.png", LF), "Figura 2 – Painel com 500 g (nível normal)."),
                 (foto("v2-painel-alerta-real-100g.png", LF), "Figura 3 – Painel em alerta (100 g)."))]),
    Spacer(1, 3),
    KeepTogether([
    duas_figuras((foto("t8-wokwi-lcd-alerta-despejo.png", LF, recorte=(752, 40, 1500, 950), nome="wokwi.png"),
                  "Figura 4 – Wokwi: LCD em alerta."),
                 (foto("v2-painel-desatualizado-local.png", LF), "Figura 5 – Painel desatualizado."))]),
    Spacer(1, 3)]

story += [P("5. Limitações", cab),
          P("O projeto se limita a um escopo simulado: o ESP32 e o sensor rodam no Wokwi, sem dispositivos "
            "físicos, e a ração despejada pelo servo é simulada no firmware. A comunicação usa HTTPS direto, sem "
            "MQTT (opcional no enunciado). A segurança é básica: uma chave de escrita compartilhada, consultas "
            "públicas e TLS sem validação do certificado da CA. O painel exibe as últimas 60 leituras.")]

story += [KeepTogether([P("6. Contribuições dos integrantes", cab),
          tabela([["Integrante", "Contribuição"]] + [["%s (RA %s)" % (n, ra), c] for n, ra, c in MEMBROS]
                 + [[CONJUNTO[0], CONJUNTO[1]]], [4.6, 12.8])])]

doc = SimpleDocTemplate(SAIDA, pagesize=A4, leftMargin=2.0 * cm, rightMargin=2.0 * cm,
                        topMargin=1.7 * cm, bottomMargin=1.5 * cm,
                        title="Alimentador Inteligente - Relatório", author="Grupo do Projeto Integrador")
doc.build(story)
print("gerado:", SAIDA)
