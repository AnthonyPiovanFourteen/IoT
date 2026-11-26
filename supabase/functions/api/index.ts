// API REST (Supabase Edge Function)
//   POST /ingest   <- webhook do EMQX (protegido por x-api-key)
//   GET  /latest   -> leitura mais recente   (?device_id=&grandeza=)
//   GET  /history  -> histórico              (?device_id=&grandeza=&limit=)
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.4";

const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const INGEST_KEY = Deno.env.get("API_INGEST_KEY")!;

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, x-api-key",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  const url = new URL(req.url);
  const route = url.pathname.split("/").pop();

  if (req.method === "POST" && route === "ingest") {
    if (req.headers.get("x-api-key") !== INGEST_KEY) return json({ error: "não autorizado" }, 401);
    let b: any;
    try { b = await req.json(); } catch { return json({ error: "JSON inválido" }, 400); }
    // O EMQX pode enviar o payload como objeto ou como string JSON.
    if (typeof b.payload === "string") { try { b = JSON.parse(b.payload); } catch { /* mantém */ } }
    const valor = Number(b.valor);
    if (!b.device_id || !b.grandeza || !b.unidade || !Number.isFinite(valor)) {
      return json({ error: "campos obrigatórios: device_id, grandeza, valor, unidade" }, 400);
    }
    const { error } = await db.from("leituras").insert({
      device_id: String(b.device_id),
      grandeza: String(b.grandeza),
      valor,
      unidade: String(b.unidade),
      alerta: Boolean(b.alerta),
    });
    if (error) return json({ error: error.message }, 500);
    return json({ ok: true }, 201);
  }

  if (req.method === "GET" && (route === "latest" || route === "history")) {
    const device = url.searchParams.get("device_id");
    const grandeza = url.searchParams.get("grandeza");
    let q = db.from("leituras").select("*").order("recebido_em", { ascending: false });
    if (device) q = q.eq("device_id", device);
    if (grandeza) q = q.eq("grandeza", grandeza);
    const limit = route === "latest" ? 1 : Math.min(Number(url.searchParams.get("limit")) || 100, 500);
    const { data, error } = await q.limit(limit);
    if (error) return json({ error: error.message }, 500);
    return json(route === "latest" ? (data[0] ?? null) : data.reverse());
  }

  return json({ error: "rota não encontrada" }, 404);
});
