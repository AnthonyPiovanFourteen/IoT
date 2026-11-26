// Configuração pública do painel (não contém segredos).
window.APP_CONFIG = {
  API_URL: "https://azjsleyewchvvzfkdpmw.supabase.co/functions/v1/api",
  DEVICE_ID: "esp32-alimentador-01",
  GRANDEZA: "peso",
  INTERVALO_COLETA_S: 5,    // deve bater com o firmware
  STALE_FATOR: 4,           // "desatualizado" após 4 intervalos sem leitura
  POLL_MS: 3000,            // consulta à API
  CAPACIDADE_G: 600,        // pote cheio (apenas para a visualização)
  LIMITE_ALERTA_G: 200,     // deve bater com o firmware
};
