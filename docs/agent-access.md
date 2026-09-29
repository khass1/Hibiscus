# Acesso de agentes ao site

O site público permite busca (`search=yes`), uso do conteúdo em respostas
de IA (`ai-input=yes`) e treinamento de modelos (`ai-train=yes`): a decisão é
de visibilidade total em IA, e nenhum crawler é bloqueado. A política está
em `static/robots.txt` e no header global de `static/_headers`. São preferências
de uso, não autenticação nem bloqueio técnico de crawlers.

## Markdown for Agents: etapa de infraestrutura

A conversão prevista é do HTML renderizado na borda Cloudflare, não dos
arquivos Markdown do Hugo: assim inclui também templates e traduções.

Após publicar e verificar o header `Content-Signal`:

1. No painel Cloudflare, selecionar a zona `hibiscus.com.br`.
2. Em **AI Crawl Control**, habilitar **Markdown for Agents**, se disponível
   no plano atual. Não contratar upgrade automaticamente.
3. Validar respostas HTML e Markdown nas três línguas e em uma página interna.

A documentação consultada em 29/09/2026 lista Pro, Business e Enterprise.
Publicar o header antes da ativação mantém a política declarada explícita na
resposta convertida, em vez de depender do padrão do conversor.

```sh
curl -sS -D - https://hibiscus.com.br/robots.txt
curl -sS -D - -H 'Accept: text/html' https://hibiscus.com.br/
curl -sS -D - -H 'Accept: text/markdown' https://hibiscus.com.br/
curl -sS -D - -H 'Accept: text/markdown' https://hibiscus.com.br/en/
curl -sS -D - -H 'Accept: text/markdown' https://hibiscus.com.br/es/
curl -sS -D - -H 'Accept: text/markdown' https://hibiscus.com.br/o-que-fazemos/
```

Exigir HTTP 200, `Content-Type: text/markdown`, `Vary` contendo `Accept` e a
política `ai-train=yes, search=yes, ai-input=yes` na resposta convertida.
Confirmar conteúdo e idioma corretos; uma resposta HTML com status 200 não
comprova conversão. A requisição HTML deve continuar retornando HTML.
Conferir também o robots.txt publicado: regras gerenciadas na Cloudflare podem
modificar a resposta em relação ao arquivo do repositório.

Os testes locais verificam a política nos arquivos, não a configuração da
Cloudflare. Ativação e aceitação em produção são etapas separadas do build.

Não publicamos catálogos de API, metadados OAuth, cards MCP/A2A ou ferramentas
WebMCP: o site não oferece esses serviços. Headers de descoberta desses
serviços também não se aplicam.

Referências: [Content Signals](https://contentsignals.org/) e
[Markdown for Agents](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/).
