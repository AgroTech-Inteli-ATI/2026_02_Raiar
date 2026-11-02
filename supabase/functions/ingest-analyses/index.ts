import { createClient } from "npm:@supabase/supabase-js@2";
import { handle } from "./handler.ts";

// SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são injetadas pela plataforma; a chave de serviço
// fica só aqui, nunca no Raspberry Pi. RAIAR_SYNC_TOKEN é o segredo que o nó envia como Bearer.
const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  { auth: { persistSession: false } },
);

Deno.serve((req) =>
  handle(req, {
    token: Deno.env.get("RAIAR_SYNC_TOKEN"),
    rpc: async (batch) => {
      const { data, error } = await supabase.rpc("ingest_analyses", { batch });
      return { data, error };
    },
  })
);
