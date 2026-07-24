// Proxy CORS mínimo para CELLAR / EUR-Lex — Cloudflare Workers (plan gratuito).
//
// Para qué: la demo de la landing verifica normas UE en vivo, pero CELLAR no
// envía cabeceras CORS y el navegador bloquea la respuesta. Este worker hace
// de tubo: recibe ?url=<destino>, la pide y la devuelve con Access-Control-*.
//
// Seguridad: SOLO acepta el host publications.europa.eu y cachea 24 h.
// Por la query solo viaja el número CELEX (dato público), nunca texto del usuario.
//
// Despliegue (sin instalar nada):
//   1. cloudflare.com → cuenta gratuita → Workers & Pages → Create Worker.
//   2. Pega este código → Deploy.
//   3. Copia la URL (https://<nombre>.<sub>.workers.dev) y ponla en
//      landing/index.html, constante UE_PROXY: "<tu-url>/?url=".

const HOST_PERMITIDO = "publications.europa.eu";

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Accept, Content-Type",
        },
      });
    }

    const destino = new URL(request.url).searchParams.get("url");
    if (!destino) return new Response("falta el parámetro ?url=", { status: 400 });

    let dest;
    try {
      dest = new URL(destino);
    } catch {
      return new Response("url inválida", { status: 400 });
    }
    if (dest.host !== HOST_PERMITIDO || dest.protocol !== "https:") {
      return new Response(`solo se permite https://${HOST_PERMITIDO}`, { status: 403 });
    }

    const resp = await fetch(dest.toString(), {
      headers: { Accept: request.headers.get("Accept") || "application/sparql-results+json" },
    });
    const salida = new Response(resp.body, resp);
    salida.headers.set("Access-Control-Allow-Origin", "*");
    salida.headers.set("Cache-Control", "public, max-age=86400");
    return salida;
  },
};
