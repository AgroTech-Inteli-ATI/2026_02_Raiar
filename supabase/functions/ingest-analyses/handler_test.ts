import { assertEquals } from "jsr:@std/assert@1";
import { handle, MAX_BATCH, tokensEqual } from "./handler.ts";

const ok = { data: { accepted_analysis_ids: ["a"], rejected: [] }, error: null };

const post = (body: unknown, token = "segredo") =>
  new Request("https://x.test/ingest-analyses", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

Deno.test("aceita lote válido e repassa a resposta do banco", async () => {
  let received: unknown;
  const res = await handle(post({ schema_version: 1, analyses: [{ analise_id: "a" }] }), {
    token: "segredo",
    rpc: (b) => {
      received = b;
      return Promise.resolve(ok);
    },
  });
  assertEquals(res.status, 200);
  assertEquals(await res.json(), ok.data);
  assertEquals((received as { analyses: unknown[] }).analyses.length, 1);
});

Deno.test("rejeita token errado ou ausente sem tocar no banco", async () => {
  const rpc = () => Promise.reject(new Error("não deveria chamar"));
  for (const token of ["errado", "", "segredo-mais-longo"]) {
    const res = await handle(post({ schema_version: 1, analyses: [] }, token), {
      token: "segredo",
      rpc,
    });
    assertEquals(res.status, 401);
  }
  const semHeader = new Request("https://x.test", { method: "POST", body: "{}" });
  assertEquals((await handle(semHeader, { token: "segredo", rpc })).status, 401);
});

Deno.test("recusa quando o segredo não está configurado", async () => {
  const res = await handle(post({}), { token: undefined, rpc: () => Promise.resolve(ok) });
  assertEquals(res.status, 500);
});

Deno.test("valida método e formato do lote", async () => {
  const deps = { token: "segredo", rpc: () => Promise.resolve(ok) };
  assertEquals((await handle(new Request("https://x.test"), deps)).status, 405);
  assertEquals((await handle(post("{quebrado"), deps)).status, 400);
  assertEquals((await handle(post({ schema_version: 2, analyses: [] }), deps)).status, 400);
  assertEquals((await handle(post({ schema_version: 1 }), deps)).status, 400);
  const grande = { schema_version: 1, analyses: new Array(MAX_BATCH + 1).fill({}) };
  assertEquals((await handle(post(grande), deps)).status, 400);
});

Deno.test("erro do banco vira 502 sem vazar detalhes", async () => {
  const res = await handle(post({ schema_version: 1, analyses: [] }), {
    token: "segredo",
    rpc: () => Promise.resolve({ data: null, error: { message: "senha do banco: xyz" } }),
  });
  assertEquals(res.status, 502);
  assertEquals(await res.json(), { error: "database_error" });
});

Deno.test("tokensEqual compara conteúdo e tamanho", () => {
  assertEquals(tokensEqual("abc", "abc"), true);
  assertEquals(tokensEqual("abc", "abd"), false);
  assertEquals(tokensEqual("abc", "abcd"), false);
});
