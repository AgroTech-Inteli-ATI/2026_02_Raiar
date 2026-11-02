// Contrato do `raiar-vision sync`: POST {schema_version: 1, analyses: [...]} com Bearer token;
// resposta 2xx com {accepted_analysis_ids: [...]}. A gravação é feita por public.ingest_analyses.

export const MAX_BATCH = 500;

export type RpcResult = { data: unknown; error: { message: string } | null };

export type Deps = {
  token: string | undefined;
  rpc: (batch: unknown) => Promise<RpcResult>;
};

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

// Comparação sem atalho por tamanho de prefixo, para não revelar o token por tempo de resposta.
export function tokensEqual(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a);
  const y = new TextEncoder().encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  }
  return diff === 0;
}

export async function handle(req: Request, deps: Deps): Promise<Response> {
  if (req.method !== "POST") return json(405, { error: "method_not_allowed" });
  if (!deps.token) return json(500, { error: "token_not_configured" });

  const header = req.headers.get("Authorization") ?? "";
  const given = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!tokensEqual(given, deps.token)) return json(401, { error: "unauthorized" });

  let batch: { schema_version?: unknown; analyses?: unknown };
  try {
    batch = await req.json();
  } catch {
    return json(400, { error: "invalid_json" });
  }
  if (
    batch?.schema_version !== 1 || !Array.isArray(batch.analyses) ||
    batch.analyses.length > MAX_BATCH
  ) {
    return json(400, { error: "invalid_batch" });
  }

  const { data, error } = await deps.rpc(batch);
  if (error) {
    console.error("ingest_analyses falhou:", error.message);
    return json(502, { error: "database_error" });
  }
  return json(200, data);
}
