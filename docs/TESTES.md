# Registro de testes

Data da execução: 25/11/2026 (horários em UTC; local = UTC-3).
Ambiente: ESP32 + HX711 + servo no Wokwi (MicroPython 1.28) → HTTPS → Supabase Edge Function `api` → Postgres → painel (Cloudflare).
Dispositivo: `esp32-alimentador-01` · grandeza: `peso` (g) · limite de alerta: 200 g · intervalo configurado: 5 s · média móvel de 5 leituras.

## Resumo

| # | Teste | Resultado |
|---|-------|-----------|
| 1 | Fluxo completo sensor → API → painel | ✅ passou |
| 2 | Situação de alerta (liga e desliga) | ✅ passou |
| 3 | Interrupção e retomada da transmissão | ✅ passou |
| 4 | Armazenamento com o painel fechado | ✅ passou |
| 5 | API: autenticação, rotas e CORS | ✅ passou |
| 6 | Efeito do intervalo de coleta | ✅ medido |
| 7 | Intervalo real de 5 s e reação do sistema ao peso (despejo simulado) | ✅ passou |

## 1. Fluxo completo
O ESP32 (Wokwi) lê o HX711, trata e envia por HTTPS. O serial mostra `HTTP 201` a cada envio; a API devolve a leitura em `GET /latest`; o painel exibe valor, unidade, horário da última atualização, histórico e alerta.
Evidências: `evidencias/t2-wokwi-alerta-100g.png`, `evidencias/t2-painel-alerta-100g.png`, `evidencias/api-historico-completo.json`.

## 2. Alerta
- 00:00 – peso em **0,1 kg**: leituras estabilizam em **100,0 g**, `alerta=true`, painel mostra banner vermelho e o servo abre (90°).
- 00:01 – peso em **0,5 kg**: a média móvel sobe em passos de 80 g (100 → 180 → **260** → 340 → 420 → 500). O alerta desliga ao passar de 200 g (leitura de 260 g, 00:01:26).
- 00:04 – com o painel fechado, peso de volta a 0,1 kg: 400 → 340 → 260 → **180 (alerta)** → 100.
Evidências: `t2-*`, `t2b-*`.

## 3. Interrupção e retomada
- Parada da simulação: 00:02:30. Última leitura gravada: 00:02:15.
- Às 00:03:00 o painel exibia **"Dados desatualizados — sem novas leituras"** mantendo o último valor (500 g). Evidência: `t3a-painel-dados-desatualizados.png`.
- Retomada: 00:03:06. Primeira leitura nova: 00:03:19 (lacuna de **65 s** no banco). O painel, **sem recarregar a página**, voltou a exibir leituras e removeu o aviso (00:03:32). Evidência: `t3b-painel-retomada.png`.

## 4. Armazenamento com o painel fechado
- Painel fechado às 00:03:56 (42 leituras no banco).
- Com o painel fechado, o peso foi alterado e o ESP32 continuou enviando: às 00:05:07 havia **5 novas leituras** (00:04:10 a 00:05:01), incluindo a passagem para alerta.
- Painel reaberto às 00:05:15 e exibiu o histórico completo, com a lacuna e o alerta. Evidências: `t4a-*`, `t4b-painel-reaberto-historico.png`.

## 5. API (contrato e segurança) — `evidencias/api-testes-negativos.txt`
| Requisição | Esperado | Obtido |
|---|---|---|
| `POST /ingest` sem chave | 401 | 401 |
| `POST /ingest` chave errada | 401 | 401 |
| Rota inexistente | 404 | 404 |
| `GET /latest` dispositivo inexistente | `null` | `null` (200) |
| `GET /history` dispositivo inexistente | `[]` | `[]` (200) |
| `OPTIONS` (CORS) | 200 + cabeçalhos | 200, `allow-origin: *` |

Não testado: resposta 400 para payload inválido (exige a chave da API; fica como pendência).

## 6. Intervalo de coleta — `evidencias/analise-intervalo.txt`
- Configurado: 5 s. Na primeira versão do firmware o intervalo **real** entre gravações foi de **~12,5 s** (mediana). Medindo no ESP32, a leitura+tratamento levava ~0,34 s e o **envio HTTPS ~6,5 s**: cada envio abria uma conexão nova com handshake TLS, e o ciclo era "5 s de pausa + ~7 s de trabalho" (o log acusava "ciclo atrasado"). Após reaproveitar a conexão (keep-alive) e esperar até o próximo instante múltiplo do intervalo, o envio caiu para ~0,4–0,8 s e o intervalo real passou a **5,02 s** (mediana; mín. 4,8 s). Dados em `evidencias/analise-intervalo.txt`.
- (Uma versão anterior deste registro atribuía os 12 s a uma simulação "a 41% da velocidade"; essa explicação estava errada — o indicador do Wokwi marcava ~100%.)
- Projeção por dispositivo: 5 s → 17.280 leituras/dia (~694 MB/ano); 30 s → 2.880/dia (~116 MB/ano); 5 min → 288/dia (~12 MB/ano).
- Trade-offs observados: intervalo menor melhora a rapidez do alerta e da resposta do painel, mas multiplica tráfego HTTPS, chamadas da Edge Function e armazenamento; intervalo maior economiza, mas atrasa o alerta e exige um limite de "desatualizado" maior (hoje 3–4× o intervalo).
- A média de 5 leituras atrasa a resposta a mudanças: ~25 s simulados para refletir 100% de uma variação de peso.

## 7. Intervalo de 5 s e reação do sistema ao peso
**Decisão final: despejo simulado ligado + LCD no Wokwi.** A célula de carga do Wokwi só muda pelo slider e o firmware não consegue movê-lo. Para o servo "acrescentar peso", o firmware soma uma dose (+120 g) a cada leitura em que a comporta está aberta (`SIMULAR_ENCHIMENTO = True`). Como o slider não mostra essa soma, foi adicionado um **LCD 20x4 (I2C)** ao circuito com o mesmo valor enviado ao painel (peso, limite/estado, comporta, gramas despejados). Houve uma fase intermediária com a soma desligada (painel = sensor puro), descartada porque com o sensor em zero o peso nunca subia, contrariando a simulação desejada.

Resultado medido (00:39 UTC), sensor zerado com o slider: **0,0 g (alerta) → 120 g (alerta, comporta aberta) → 240 g (alerta desliga)**, estável. LCD no instante do alerta: "Peso: 0.0 g / Limite: 200 g ALERTA / Comporta: ABERTA / Despejado: 120 g (sim)" (`evidencias/t8-wokwi-lcd-alerta-despejo.png`). Leitura+tratamento passou a ~0,85 s por causa do LCD; o ciclo de 5 s é mantido.

Descrição da lógica: o firmware soma uma dose (+120 g) a cada leitura em que a comporta está aberta (alerta). Qualquer mudança brusca do sensor (> 30 g) é tratada como mudança real de peso: zera a dose simulada e reinicia a média móvel, de modo que o valor acompanha o sensor sem atraso. A página **não** controla o sensor (só lê a API); o único controle é o slider.

Sequência medida no banco (00:25–00:27 UTC), intervalo entre gravações 4,8–5,2 s:

| Ação no slider | Valores gravados | Leitura |
|---|---|---|
| Partida com 50 g | 50 (alerta) → 170 (alerta, 1ª dose) → **290** (alerta desliga, estável) | servo repõe até passar de 200 g |
| Reposição para 0,4 kg | **400** já na leitura seguinte, sem alerta e sem dose indevida | sem atraso da média |
| Mexida manual para ~190 g | 188,1 (alerta) → 308,1 | 1 dose |
| Consumo para 0,05 kg | **50** (alerta) → 170 → **290** | 2 doses, estabiliza |

Achados que levaram a esta versão: (a) com a média móvel pura, subir o peso fazia a média "lembrar" o valor antigo, o sistema achava que faltava ração e despejava dose indevida; (b) o intervalo de 12 s era o handshake TLS a cada envio (item 6).
Evidências: `evidencias/t7-wokwi-ciclo-5s-despejo.png`, `evidencias/t7-painel-textos-neutros.png`, `evidencias/analise-intervalo.txt`, `evidencias/api-historico-completo.json`.

Observação: os testes 2 a 4 foram feitos com a versão 1 do firmware (média pura, transição em degraus de 80 g). A lógica de alerta e armazenamento é a mesma; a diferença é a resposta mais rápida a mudanças de peso.

## Painel v2 (visual do pote)
Os testes 2 a 4 foram executados com a primeira versão do painel (gráfico + banners). Depois foi publicado o painel v2 (pote de ração em corte que enche conforme o peso, funil com comporta, ração caindo, pet que reage, estatísticas, linha do tempo). A v2 foi validada com dados reais do sensor:
- `evidencias/v2-painel-publicado-500g.png` — 500 g (83% do pote), "Online · tudo certo", linha do tempo com "Nível normalizado" e "Ração reposta +400 g".
- `evidencias/v2-painel-alerta-real-100g.png` — alerta real a 100 g: comporta aberta, ração caindo, pet preocupado.
- `evidencias/v2-wokwi-500g.png` — Wokwi no mesmo instante.

O painel tem um **modo demonstração** (`?demo=alerta|ok|cheio|enchendo|stale`) que gera dados no navegador, com faixa de aviso visível, para ensaiar os estados visuais sem a simulação. Capturas desse modo (`evidencias/qa-demo-*.png`) **não são dados do sensor** e não contam como evidência de teste.

A linha do tempo mostra "Transmissão retomada após N s" nos trechos em que a simulação do Wokwi ficou pausada porque a aba estava em segundo plano durante os testes; são lacunas reais nos dados.

## Falhas encontradas durante os testes (e correções)
1. **`TypeError` em `sta.connect(..., channel=6)`** — o MicroPython 1.28 não aceita o argumento; removido.
2. **Leituras do HX711 corrompidas** (0,5 kg lido como 2.200 g, saltos para 6.500 g). O driver lia o DOUT imediatamente após subir o SCK e podia ser interrompido no meio dos 24 bits (SCK alto > 60 µs coloca o HX711 em power-down). Correções: pequeno atraso após cada pulso, interrupções desabilitadas durante a leitura e **mediana de 5 leituras**. Depois disso 0,5 kg passou a ser lido como 500,0 g de forma estável.
3. **Validação de faixa**: leituras fora de −50 g…5,5 kg são descartadas.
4. **`MBEDTLS_ERR_SSL_CONN_EOF` intermitente** observado quando a aba do Wokwi ficava em segundo plano (simulação desacelerada). O firmware registra o erro e tenta de novo no ciclo seguinte; não houve perda de dados com a aba em primeiro plano.
5. **Broker EMQX inacessível** (Opção A): o endereço público do deployment `iot-g01` não respondia em nenhuma porta de duas máquinas, mesmo "Running" no console e após reinício; a conta só permite um deployment Serverless. Decisão: Opção B (HTTPS direto), permitida pelo enunciado.

O histórico no banco/gráfico mantém os pontos espúrios anteriores à correção do item 2 (ex.: picos de ~6.500 g em 23:54–23:55 UTC), preservados como registro do antes/depois.
