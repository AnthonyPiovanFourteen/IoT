# Alimentador Inteligente — monitoramento IoT do pote de ração

Sistema IoT com três blocos: **sensor simulado** (ESP32 + célula de carga HX711 no Wokwi), **API REST** (Supabase Edge Function + Postgres) e **painel web** (Cloudflare). Mede o peso de ração no pote, guarda as leituras e avisa quando o nível fica abaixo de 200 g (e o servo abre a comporta).

## Links
- Painel publicado: https://monitor-alimentador.anthonygpiovan14.workers.dev
- Projeto Wokwi: https://wokwi.com/projects/481705288139185153
- API: `https://azjsleyewchvvzfkdpmw.supabase.co/functions/v1/api` (`/latest`, `/history`)
- Vídeo de demonstração: https://youtu.be/jiXkEV0LdVE
- Repositório: https://github.com/AnthonyPiovanFourteen/IoT

## Arquitetura (Opção B — HTTPS direto)

```
ESP32 + HX711 (Wokwi) --HTTPS POST /ingest (x-api-key)--> Supabase Edge Function "api" --> Postgres (tabela leituras)
                                                                       ^                         |
              Painel (Cloudflare) --GET /latest, GET /history----------+-------------------------+
```

Escolhemos a Opção B porque o broker EMQX Serverless ficou inacessível (ver [docs/TESTES.md](docs/TESTES.md), item 5 das falhas). O MQTT é opcional no enunciado.

| Item | Valor |
|---|---|
| Problema | Peso de ração no pote de um alimentador de pet |
| Grandeza / unidade | `peso` / `g` |
| Dispositivo | `esp32-alimentador-01` |
| Coleta | a cada 5 s (tempo simulado) |
| Tratamento | mediana de 5 leituras do HX711 → validação de faixa (−50 g … 5,5 kg) → média móvel de 5 (reinicia se o peso muda > 30 g) → comparação com limite |
| Envio | HTTPS com conexão reaproveitada (keep-alive): intervalo real medido de 5,0 s |
| Alerta | `peso < 200 g` (servo abre a 90°) |
| "Desatualizado" no painel | sem leitura nova há 4 intervalos (20 s) |

## Estrutura

```
firmware/   main.py, hx711.py, lcd_i2c.py, diagram.json, secrets.example.py   (Wokwi / MicroPython)
supabase/   migrations/001_leituras.sql, functions/api/index.ts
web/        index.html, style.css, app.js, config.js               (painel)
docs/       TESTES.md, evidencias/, Relatorio_Alimentador_Inteligente.pdf, relatorio/gerar_relatorio.py
```

## Banco de dados
`supabase/migrations/001_leituras.sql` cria a tabela `leituras` (`device_id`, `grandeza`, `valor`, `unidade`, `alerta`, `recebido_em`) com índice por dispositivo/grandeza/tempo e RLS ligado. Só a Edge Function (service role) acessa a tabela.

## API
| Método e rota | Descrição |
|---|---|
| `POST /ingest` | Recebe uma leitura. Exige o header `x-api-key`. Corpo: `{device_id, grandeza, valor, unidade, alerta}`. 201 ok, 400 payload inválido, 401 sem/errada a chave. |
| `GET /latest?device_id=&grandeza=` | Leitura mais recente (ou `null`). |
| `GET /history?device_id=&grandeza=&limit=` | Histórico em ordem cronológica (limite 500). |

## Como reproduzir

### 1. Supabase (banco + API)
```bash
npx supabase login
npx supabase link --project-ref SEU_REF
npx supabase db push
# gere uma chave e guarde-a (não a versione):
printf 'API_INGEST_KEY=%s\n' "$(openssl rand -hex 24)" > .env.api
npx supabase secrets set --env-file .env.api
npx supabase functions deploy api --no-verify-jwt
```

### 2. Wokwi (ESP32 em MicroPython)
1. Crie um projeto **MicroPython on ESP32** em wokwi.com.
2. Copie `firmware/main.py`, `firmware/hx711.py` e `firmware/diagram.json`.
3. Crie `secrets.py` a partir de `firmware/secrets.example.py` com o host da sua função e o valor de `API_INGEST_KEY`.
4. ▶ Rode. O monitor serial mostra o JSON enviado e `HTTP 201`. Clique na célula de carga para mudar o peso.

### 3. Painel (Cloudflare)
Edite `web/config.js` (URL da API, limite, capacidade) e publique a pasta `web/`:
```bash
npx wrangler login
# em um diretório SEM espaços no caminho, com um wrangler.jsonc apontando assets.directory para a pasta web
npx wrangler deploy
```
Para ensaiar os estados visuais sem o sensor: `…/?demo=alerta|ok|cheio|enchendo|stale` (exibe uma faixa de aviso: dados simulados).

## Segurança
- Nenhuma credencial no repositório: `firmware/secrets.py`, `.env*` e `supabase/.temp/` estão no `.gitignore`.
- A chave `x-api-key` protege só a escrita; a leitura (`GET`) é pública porque o painel é estático.
- O firmware usa TLS **sem validar a CA** (simulação). Em produção, validar o certificado e usar uma chave por dispositivo.
- A chave aparece no `secrets.py` do projeto Wokwi: **rotacione-a** depois da avaliação (`supabase secrets set API_INGEST_KEY=<nova>`).

## Equipe e divisão de responsabilidades

| Integrante | RA | Dupla e responsabilidade individual |
|---|---|---|
| Leonardo Nunes Navas | 2010317 | Dupla 1 (sensor e firmware): leitura do HX711, tratamento dos dados, alerta e envio HTTPS |
| Wendell Pereira Ribeiro | 2004501 | Dupla 1 (sensor e firmware): circuito no Wokwi, servo (PWM), LCD I2C e simulação do despejo |
| Luan Moreira Alves | 1996380 | Dupla 2 (API, banco e painel): API REST (Edge Function), tabela `leituras` e chave de escrita |
| Anthony Piovan | 1987602 | Dupla 2 (API, banco e painel): painel web, publicação no Cloudflare e integração |

Todos: testes de integração, relatório, vídeo e repositório.

## Testes e análise
Veja [docs/TESTES.md](docs/TESTES.md): fluxo completo, alerta, interrupção/retomada, armazenamento com o painel fechado, testes da API e efeito do intervalo de coleta, além das falhas encontradas e corrigidas.

## Limitações
- A simulação do Wokwi pausa/desacelera com a aba em segundo plano (gera lacunas nos dados e erros TLS pontuais).
- No Wokwi a célula de carga só muda pelo slider e o firmware não consegue movê-lo. Por isso a ração despejada pelo servo é **simulada no firmware**: +120 g por leitura com a comporta aberta (`SIMULAR_ENCHIMENTO = True`). O peso enviado ao painel é "sensor + ração simulada" e aparece também no LCD do circuito; o slider mostra só a parte manual. Com `False` o valor enviado é só o do sensor.
- Sem validação de certificado TLS; uma única chave compartilhada.
- `GET` público; sem autenticação de usuário no painel.
- O servo só sinaliza a abertura da comporta; não há realimentação do peso real após o despejo (o peso é alterado manualmente no simulador).
- A parte MQTT (EMQX) não foi concluída por indisponibilidade do broker.
