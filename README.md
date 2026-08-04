# Hibiscus Phytocosméticos — Site Estático (Hugo)

Substitui o WordPress que rodava em `www.hibiscus.com.br`. Zero PHP, zero banco
de dados, zero painel admin para ser invadido. Conteúdo em Markdown, deploy
no Cloudflare Pages.

---

## Stack

- **Hugo extended 0.164.0** — gerador estático (versão fixada; ver Deploy)
- **Vanilla HTML/CSS** — sem framework JS; único script é o toggle do menu mobile
- **Newsreader + Manrope** — fontes variáveis, self-hosted em `static/fonts/`
- **Cloudflare Pages** — hospedagem estática

---

## Rodar localmente

```bash
brew install hugo
```

```bash
hugo server -D
```

Servidor de dev em `http://localhost:1313`. Build de produção vai para `./public/`.

O build de produção deve passar sem avisos:

```bash
hugo --panicOnWarning --minify
```

---

## Estrutura

```
hibiscus/
├── hugo.toml                  # config + dados da empresa (telefone, endereço…)
├── content/                   # CONTEÚDO EM MARKDOWN — edite aqui
│   ├── _index.md              # home
│   ├── quem-somos.md
│   ├── o-que-fazemos.md
│   ├── contato.md
│   ├── modelos-de-desenvolvimento.md
│   ├── regularizacao-anvisa-cosmeticos.md
│   ├── terceirizacao-para-industrias.md
│   ├── politica-de-privacidade.md
│   └── portfolio.md           # draft: true — não sai no build de produção
├── layouts/
│   ├── _default/              # baseof, single, contato, o-que-fazemos, quem-somos
│   ├── index.html             # home
│   ├── 404.html
│   └── partials/              # header, footer, FAB WhatsApp, whatsapp-url, service-icon
├── assets/css/main.css        # estilo único (minificado + fingerprinted no build)
├── scripts/download-fonts.sh  # rebaixa as fontes variáveis do fontsource
├── static/                    # arquivos servidos como-estão
│   ├── _headers               # headers de segurança e cache do Cloudflare Pages
│   ├── robots.txt             # estático (enableRobotsTXT = false no hugo.toml)
│   ├── llms.txt
│   ├── fonts/  img/  favicons
└── .gitignore
```

---

## Editar conteúdo

Tudo está em `content/*.md`. O front matter (YAML no topo) define os blocos
estruturados — serviços, valores, etapas do método. O texto em Markdown abaixo
do front matter é o corpo livre.

Para alterar telefone, e-mail, endereço, horário — **edite `hugo.toml`**
(seção `[params]`). Header, footer, página de contato, JSON-LD e o link do
WhatsApp puxam tudo de lá.

O endereço tem fonte única em `[params.postal]`. Dois partials derivam dele —
`address-line.html` (texto visível) e `schema-address.html` (PostalAddress do
JSON-LD) — e os links do Google Maps na página de contato são montados a partir
dos mesmos campos. Alterar o endereço em um lugar propaga para todos.

⚠️ `[params.postal]` é uma tabela TOML e precisa ficar **no fim** de `[params]`.
Qualquer chave escrita depois dela passa a pertencer a `params.postal` em vez de
`params`, e o site perde silenciosamente e-mails e verificações de busca.

Nota: o endereço também aparece hard-coded em `static/llms.txt` e em
`content/politica-de-privacidade.md` — nenhum dos dois passa pelo template.

O link do WhatsApp é montado pelo partial `whatsapp-url.html` a partir de
`whatsappPhone` + `whatsappTextDefault`. Para um CTA com mensagem própria,
passe o texto ao partial:

```go-html-template
{{ partial "whatsapp-url.html" "Olá! Vim da página X." }}
```

### Front matter opcional

- `draft: true` — exclui a página do build de produção
- `noindex: true` — emite `<meta name="robots" content="noindex, follow">`
- `ogImage: "/img/algo.jpg"` — imagem social específica da página (default: `params.ogImage`)
- `toc: true` — índice de âncoras no topo (h2 e h3). Só aparece se o sumário
  gerado tiver conteúdo real; use apenas em páginas longas.

### CTA no meio do texto

O `cta` do front matter gera a faixa do **fim** da página. Para um CTA no meio
do conteúdo, use o shortcode — a posição é escolhida por você, no markdown:

```
{{< cta-inline
     title="Já reconheceu o seu caso?"
     text="Opcional."
     label="Falar sobre o meu projeto"
     whatsapp="Mensagem pré-preenchida." >}}
```

Só `label` tem padrão (cai no genérico traduzido). Sem `title` sai apenas o botão.

### Rótulos de CTA por seção (O que Fazemos)

Cada item de `servicos` aceita `ctaLabel`, além do `whatsappText` que define a
mensagem pré-preenchida. Sem `ctaLabel`, cai no rótulo genérico. Rótulos
específicos ("Orçar linha facial") convertem melhor do que sete links iguais.

---

## Idiomas

O site publica em **português, espanhol e inglês**. O português fica na raiz
(`/contato/`); os outros idiomas em subpasta (`/es/contacto/`, `/en/contact/`).

Traduzidas hoje — home, Quem Somos, O que Fazemos e Contato:

| Português | Español | English |
|---|---|---|
| `/` | `/es/` | `/en/` |
| `/quem-somos/` | `/es/quienes-somos/` | `/en/about-us/` |
| `/o-que-fazemos/` | `/es/que-hacemos/` | `/en/what-we-do/` |
| `/contato/` | `/es/contacto/` | `/en/contact/` |

**Só em português:** Modelos de desenvolvimento, Terceirização, Regularização
na Anvisa e Política de Privacidade. Páginas sem tradução simplesmente não
existem no outro idioma — o seletor não as oferece e não há `hreflang` para
elas. Onde o texto em pt linkava para uma dessas páginas, a versão es/en traz
a frase sem o link (ver `trust_no_catalog` e `home_como_foot` em `i18n/`).

A interface inteira (header, rodapé, 404, mapa, FAB, home, O que Fazemos, Quem
Somos e Contato) sai de `i18n/pt-br.toml`, `i18n/es.toml` e `i18n/en.toml` —
as três com o mesmo conjunto de chaves. Os textos longos (serviços, método,
FAQ) ficam no front matter de cada `content/*.<lang>.md`.

### Ativar um idioma

⚠️ **Crie o `_index.<lang>.md` antes de tirar o idioma de `disableLanguages`.**
Home e 404 são sempre gerados para todo idioma ativo, mesmo sem conteúdo — e o
build **passa sem erro**. Ativar `es` sem `content/_index.es.md` publica um
`/es/` de 14 kB com o hero vazio. Páginas comuns não têm esse problema: sem
tradução, simplesmente não existem naquele idioma.

1. `content/_index.es.md` — copie o front matter de `content/_index.md`
   (`hero`, `servicos`, `valores`) e traduza. É obrigatório.
2. As páginas que quiser: `content/pagina.es.md`. Traduza o `slug` também, para
   a URL sair no idioma certo.
3. Menus em `hugo.toml`:

   ```toml
   [languages.es.menus]
     [[languages.es.menus.main]]
       name = "Inicio"
       url = "/es/"
       weight = 10
   ```

   Sem isso o idioma herda os menus em português, que apontam para URLs em
   português. Vale para `main`, `footer` e `services`.
4. Remova o idioma de `disableLanguages` no topo do `hugo.toml`.
5. `hugo --panicOnWarning --minify` e confira: `/es/` com hero preenchido,
   `hreflang` nas páginas com tradução, e o seletor de idioma no header.

O seletor só aparece quando a página atual tem tradução — nunca oferece um
idioma que levaria a um 404.

### hreflang

Usa código neutro (`es`, `en`), não `es-ES`/`en-US`. O público é Chile e
Caribe; `es-ES` diria ao Google que a página é para a Espanha.

---

## Deploy no Cloudflare Pages

1. Repositório no GitHub.
2. Em `pages.cloudflare.com` → Connect to Git → escolher o repo.
3. Build settings:
   - Framework preset: **Hugo**
   - Build command: `git fetch --unshallow || true && hugo --panicOnWarning --minify`
   - Build output directory: `public`
   - Environment variable: `HUGO_VERSION = 0.164.0`

**Fixe a versão.** O default do Cloudflare é antigo e diverge do ambiente local.
Ao atualizar o Hugo localmente, atualize `HUGO_VERSION` junto.

**O `git fetch --unshallow` não é opcional.** O Cloudflare Pages sempre clona
raso, e `enableGitInfo = true` no `hugo.toml` alimenta o `<lastmod>` do sitemap
com a data do último commit de *cada página*. Num clone raso só existe um
commit, então o Hugo carimba **todas** as páginas com a data desse commit.

O sintoma não é `lastmod` faltando — é `lastmod` presente e idêntico em todas as
URLs, mudando a cada deploy. Para o Google isso equivale a "o site inteiro mudou"
toda vez, que é o mesmo que não informar nada. O build passa sem erro nos dois
casos. O `|| true` evita quebrar o build caso o clone já venha completo (o
`--unshallow` falha se não há o que aprofundar).

Como conferir depois de um deploy — as datas têm que ser diferentes entre si:

```
curl -s https://hibiscus.com.br/pt-br/sitemap.xml | grep -o '<lastmod>[^<]*' | sort -u
```

### Formulário de contato

**Não existe formulário no site.** Os canais são WhatsApp, telefone e e-mail,
todos em `/contato/`. Se um formulário for adicionado no futuro, note que o
atributo `data-static-form-name` do Cloudflare **não** funciona sozinho: exige o
plugin Static Forms do Pages Functions e um handler. Não é uma caixa de entrada
que aparece no dashboard.
Docs: https://developers.cloudflare.com/pages/functions/plugins/static-forms/

---

## Pendências conhecidas

- **Redirects do WordPress antigo.** Não existe `static/_redirects`. URLs legadas
  (`/wp-content/...`, permalinks antigos) retornam 404 e perdem o link equity
  acumulado. Levantar as URLs com tráfego no Search Console e mapeá-las.
- **CSP.** `static/_headers` tem os headers de segurança básicos, mas nenhuma
  Content-Security-Policy. O script inline do menu em `partials/header.html`
  precisaria virar asset fingerprintado para uma CSP sem `unsafe-inline`.
  O Google Maps exige `frame-src`.
- **HSTS.** `max-age=86400` (1 dia), deliberadamente conservador. Subir para
  15552000 depois de confirmar estabilidade.
- **CSP e o segundo script inline.** Além do menu, `_default/contato.html` tem um
  script inline para o click-to-load do mapa. Ambos precisariam virar assets
  fingerprintados para uma CSP sem `unsafe-inline`.
- **Afirmações comerciais e jurídicas.** Há comentários `COMPLETAR` / `REVISAR`
  em `modelos-de-desenvolvimento.md` e `terceirizacao-para-industrias.md` sobre
  titularidade de fórmula, exclusividade, não solicitação, capacidade e
  calibração. Os comentários somem na minificação, mas as afirmações estão
  publicadas. Revisar contra o contrato-padrão antes de tratar as páginas como
  finais.

---

## Por que essa stack

- **Hugo**: builds em milissegundos, binário único, sem Node. Ideal para um site
  institucional editado raramente.
- **Cloudflare Pages**: free tier cobre tráfego e builds. CDN com POPs em SP e RJ.
- **Sem CMS**: conteúdo editado em Markdown direto no repo. Se em algum momento
  alguém não-técnico precisar editar, Decap ou Sveltia CMS (git-based) leva ~1h.
