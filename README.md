# Hibiscus Phytocosméticos — Site Estático (Hugo)

Substitui o WordPress que rodava em `www.hibiscus.com.br`. Zero PHP, zero banco
de dados, zero painel admin para ser invadido. Conteúdo em Markdown, deploy
no Cloudflare Pages.

---

## Stack

- **Hugo extended 0.165.0** — gerador estático (versão fixada; ver Deploy)
- **Vanilla HTML/CSS/JS** — sem framework; JS só para menu mobile e mapa sob consentimento
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
│   ├── protetor-solar-fotoprotecao.md      # nicho
│   ├── cosmeticos-naturais-veganos.md      # nicho
│   ├── maquiagem-bastao-po-compacto.md     # nicho
│   ├── glossario-cosmeticos.md             # termos no front matter
│   ├── politica-de-privacidade.md
│   └── portfolio.md           # draft: true — não sai no build de produção
├── layouts/
│   ├── _default/              # baseof, single, contato, o-que-fazemos, quem-somos
│   ├── index.html             # home
│   ├── 404.html
│   ├── partials/              # header, footer, FAB WhatsApp, whatsapp-url,
│   │                          # whatsapp-base, qualificador, service-icon
│   └── shortcodes/            # cta-inline, qualificador
├── assets/
│   ├── css/main.css           # estilo principal (minificado + fingerprinted)
│   ├── css/noscript.css       # fallback do menu quando JS está desativado
│   └── js/main.js             # menu mobile + carregamento consentido do mapa
├── scripts/
│   ├── audit-build.py         # invariantes de conteúdo, HTML gerado e CSP
│   └── download-fonts.sh      # rebaixa as fontes variáveis do fontsource
├── .github/workflows/build.yml # build e auditoria com Hugo fixado
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

### lastmod — obrigatório

Toda página em `content/` carrega um `lastmod:` no front matter, e é ele que
alimenta o `<lastmod>` do sitemap:

```yaml
---
lastmod: 2026-08-03T10:56:18-03:00
title: "O que Fazemos"
---
```

**Ao editar o conteúdo de uma página, atualize a data.** Não há automação — se
esquecer, o sitemap segue dizendo ao Google que a página não mudou. Só mude a
data quando o *conteúdo* mudar; ajuste de layout ou de CSS não conta.

Por que não vem do git: `enableGitInfo` daria a data do último commit de cada
página, mas o Cloudflare Pages sempre clona raso e o build aqui não pode rodar
`git fetch --unshallow`. Com histórico de um commit só, o Hugo carimba **todas**
as páginas com a mesma data, que muda a cada deploy — para o Google isso é o
mesmo que não informar nada, e o build passa sem erro. Daí `enableGitInfo =
false` e a ordem `["lastmod", ":fileModTime", ":default"]` em `[frontmatter]`.

⚠️ Página nova sem `lastmod:` cai em `:fileModTime`, que no Cloudflare é a hora
do checkout — idêntica para todos os arquivos, exatamente o problema que isto
resolve. O build **não** avisa.

Como conferir depois de um deploy — as datas têm que ser diferentes entre si:

```
curl -s https://hibiscus.com.br/pt-br/sitemap.xml | grep -o '<lastmod>[^<]*' | sort -u
```

### Perfis externos (sameAs)

`instagram`, `facebook`, `linkedin` e a lista `sameAs` em `[params]` alimentam o
`sameAs` do Organization e do LocalBusiness. Estão todos vazios hoje, e por isso
a propriedade **não é emitida** — string vazia no JSON-LD é pior que ausência.

É o que liga este site aos endereços da empresa fora dele: Google Business
Profile, diretórios B2B do setor, página de associação. Sem isso, cada menção da
Hibiscus por aí é uma entidade solta para o buscador, e o site não se apresenta
como o nó canônico.

Regra ao preencher: só URL canônica e ativa, e com nome, endereço e telefone
iguais aos de `[params.postal]`. `sameAs` apontando para um cadastro com dado
divergente atrapalha em vez de ajudar — é o mesmo problema que a consistência de
NAP resolve.

Os três primeiros também controlam o bloco social do rodapé (só o Instagram tem
ícone hoje); `sameAs` é lista livre e não aparece na interface.

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

**Exceção em inglês.** Em `o-que-fazemos.en.md` as quatro linhas de produto usam
o rótulo único "Request a quote" — decisão editorial: o equivalente específico
("Quote a facial line") não soa natural em inglês. A especificidade não se perde,
porque o `whatsappText` de cada seção continua identificando a linha na mensagem
que chega. Não "corrigir" de volta sem falar com quem escreve o conteúdo.

---

## Idiomas

O site publica em **português, espanhol e inglês**. O português fica na raiz
(`/contato/`); os outros idiomas em subpasta (`/es/contacto/`, `/en/contact/`).

Traduzidas hoje — home, Quem Somos, O que Fazemos, Modelos de desenvolvimento,
Regularização na Anvisa, Terceirização para indústrias, as três páginas de
nicho, o Glossário e Contato:

| Português | Español | English |
|---|---|---|
| `/` | `/es/` | `/en/` |
| `/quem-somos/` | `/es/quienes-somos/` | `/en/about-us/` |
| `/o-que-fazemos/` | `/es/que-hacemos/` | `/en/what-we-do/` |
| `/modelos-de-desenvolvimento/` | `/es/modelos-de-desarrollo/` | `/en/development-models/` |
| `/regularizacao-anvisa-cosmeticos/` | `/es/registro-anvisa-cosmeticos/` | `/en/anvisa-cosmetics-registration/` |
| `/terceirizacao-para-industrias/` | `/es/fabricacion-para-terceros/` | `/en/contract-manufacturing/` |
| `/protetor-solar-fotoprotecao/` | `/es/proteccion-solar-fotoproteccion/` | `/en/sunscreen-photoprotection/` |
| `/cosmeticos-naturais-veganos/` | `/es/cosmeticos-naturales-veganos/` | `/en/natural-vegan-cosmetics/` |
| `/maquiagem-bastao-po-compacto/` | `/es/maquillaje-barra-polvo-compacto/` | `/en/stick-pressed-powder-makeup/` |
| `/glossario/` | `/es/glosario/` | `/en/glossary/` |
| `/contato/` | `/es/contacto/` | `/en/contact/` |

**Só em português:** Política de Privacidade. Páginas sem tradução simplesmente
não existem no outro idioma — o seletor não as oferece e não há `hreflang` para
elas.

As páginas de nicho nasceram só em português, como teste de tração, e foram
traduzidas em seguida. Os slugs são traduzidos junto com o texto — repare que
nenhum deles é a tradução literal do português (`sunscreen-photoprotection`,
não `sunscreen-photoprotecao`): é o termo que a pessoa busca naquele idioma que
vale, não a simetria com a URL em pt.

⚠️ Cada idioma tem o seu próprio `[languages.<lang>.menus.services]`, e eles
**não herdam** de `[menus.services]`. Uma página nova precisa da entrada nos
três blocos, senão ela existe e fica fora do menu naquele idioma — sem erro de
build.

O guia da Anvisa é conteúdo regulatório **brasileiro**. As versões es/en existem
para marcas estrangeiras que fabricam no Brasil e trazem, no lugar da nota de
atualização, a ressalva de que o registro no país de destino é do importador.

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

`es` e `en` usam código neutro, não `es-ES`/`en-US`. O público é Chile e
Caribe; `es-ES` diria ao Google que a página é para a Espanha.

`pt` é a exceção deliberada: usa `pt-BR`, com território, porque precisa bater
com o `lang="pt-BR"` do `<html>` e com o hreflang do sitemap — os três vêm de
`Language.Locale` (ver `hugo.toml`), não do código curto `pt-br` da URL.

---

## Deploy no Cloudflare Pages

1. Repositório no GitHub.
2. Em `pages.cloudflare.com` → Connect to Git → escolher o repo.
3. Build settings:
   - Framework preset: **Hugo**
   - Build command: `hugo --panicOnWarning --minify`
   - Build output directory: `public`
   - Environment variable: `HUGO_VERSION = 0.165.0`

**Fixe a versão.** O default do Cloudflare é antigo e diverge do ambiente local.
Ao atualizar o Hugo localmente, atualize `HUGO_VERSION` junto.
A CI repete o build e roda `python3 scripts/audit-build.py`, que valida links,
metadados, FAQ multilíngue, JSON-LD e os hashes permitidos pela CSP.

O build não depende de histórico git — ver **lastmod** abaixo.

### Formulário de contato

**Não existe formulário no site** — e o qualificador de briefing não é um.
Os canais continuam sendo WhatsApp, telefone e e-mail, todos em `/contato/`.
Se um formulário de verdade for adicionado no futuro, note que o atributo
`data-static-form-name` do Cloudflare **não** funciona sozinho: exige o plugin
Static Forms do Pages Functions e um handler. Não é uma caixa de entrada que
aparece no dashboard.
Docs: https://developers.cloudflare.com/pages/functions/plugins/static-forms/

### Qualificador de briefing

Três `<select>` que reescrevem o `text=` do link do WhatsApp no navegador.
`partials/qualificador.html`, com o shortcode de mesmo nome para usar dentro de
markdown. Está em `/contato/` (os três idiomas) e nas três páginas de nicho.

**Não é formulário.** Não há `<form>`, não há POST e nenhum dado sai do site: as
respostas viram texto na mensagem que a própria pessoa envia, e ela ainda pode
editá-la no WhatsApp. É por isso que ele não muda nada na política de
privacidade nem exige base legal de tratamento — e é a razão de existir na forma
atual, em vez de um formulário com Pages Function e caixa de entrada.

Sem JS o bloco inteiro some (`.qualificador { display: none }` em
`noscript.css`): os selects não teriam efeito e o botão cairia na mensagem
genérica, que os outros CTAs da página já oferecem.

Rótulos e opções: chaves `qual_*` em `i18n/*.toml` — categorias em
`qual_cat_<valor>`, estágios em `qual_est_<valor>`, volumes em `qual_vol_<valor>`.
O valor no meio da chave é o mesmo que aparece nas listas `slice` do partial;
**acrescentar uma opção exige mexer nos dois lugares**, e a chave precisa existir
nos três catálogos.

⚠️ Rótulo comprido é cortado pelo `<select>` nativo, sem reticências. Mantenha as
opções curtas — foi por isso que o volume mínimo virou "20 kg por SKU" e perdeu o
parêntese do bastão.

Use no máximo **um por página**: os ids dos `<label for>` derivam do prefixo, que
tem valor fixo por padrão.

Nas páginas de nicho o shortcode pré-seleciona a primeira pergunta:

```
{{< qualificador categoria="solar" >}}
```

O clique também alimenta o Zaraz: `data-cta="qualificador"` mais um
`data-cta-detail` com as três respostas (`solar|referencia|minimo`). É o único
jeito de saber *que tipo de projeto* clicou — o WhatsApp abre em outra aba e
nunca volta para contar. Enquanto o Zaraz estiver desligado no painel, o evento
é um no-op silencioso.

### Glossário

`content/glossario-cosmeticos.md` (+ `.es.md` / `.en.md`). Os termos ficam em
`termos:` no front matter
(`termo`, `expansao` opcional, `definicao` em markdown) e alimentam **duas**
saídas em `single.html`: a lista visível e um `DefinedTermSet` de JSON-LD. Fonte
única, para as duas não divergirem.

Cada termo ganha `@id` próprio a partir do `anchorize` do nome, então dá para
linkar `/glossario/#moq` de qualquer lugar — inclusive de fora do site. Como a
âncora vem do nome do termo, **ela muda de idioma para idioma**: `#moq` existe
nos três, mas o de estabilidade é `#teste-de-estabilidade` em pt,
`#ensayo-de-estabilidad` em es e `#stability-testing` em en. Ao linkar uma
âncora de glossário, confira a do idioma certo. O título
da seção é um `h2` no markdown, logo acima da lista; não há string de interface,
e por isso o bloco não precisou de chaves i18n.

Qualquer página com `termos:` no front matter ganha o mesmo tratamento.

---

## Pendências conhecidas

- **Redirects do WordPress antigo.** Não existe `static/_redirects` — menos grave
  do que parece, e vale entender por quê antes de investir tempo nisso.

  O WordPress antigo usava `?page_id=NNN`, não permalinks bonitos. Query string
  num site estático é ignorada: `/?page_id=331` serve a home, com
  `rel=canonical` apontando para `https://hibiscus.com.br/`. O Google consolida
  os sinais e reporta "Crawled — currently not indexed", que é o resultado certo.
  Os artefatos do WP (`/feed/`, `/comments/feed/`, `/author/roberto/`) dão 404,
  e é isso mesmo que se quer.

  O que sobraria são permalinks legados de verdade, se existirem. Levantar no
  Search Console (Páginas → 404) antes de escrever qualquer `_redirects`.
- ~~**CSP.**~~ Resolvido — scripts executáveis viraram asset fingerprintado,
  sem `unsafe-inline`; `script-src 'self'` basta. `frame-src` limita o mapa a
  `maps.google.com` e `www.google.com`. Sem hashes de JSON-LD: data block não
  passa por `script-src` (o motivo está comentado em `static/_headers`), e
  `scripts/audit-build.py` falha se algum hash voltar.
- ~~**HSTS.**~~ Resolvido — `max-age=15552000` (180 dias) em `static/_headers`.
- **Afirmações comerciais e jurídicas.** Não há mais marcadores genéricos
  `COMPLETAR` / `REVISAR`. A revisão externa ainda precisa comparar com o
  contrato-padrão as afirmações publicadas sobre titularidade e transferência
  de fórmulas, exclusividade, capacidade sem lote máximo, calibração rastreável,
  acesso para auditoria e distribuição das responsabilidades regulatórias.
  Qualquer ajuste em Terceirização deve ser replicado nos três idiomas.

---

## Por que essa stack

- **Hugo**: builds em milissegundos, binário único, sem Node. Ideal para um site
  institucional editado raramente.
- **Cloudflare Pages**: free tier cobre tráfego e builds. CDN com POPs em SP e RJ.
- **Sem CMS**: conteúdo editado em Markdown direto no repo. Se em algum momento
  alguém não-técnico precisar editar, Decap ou Sveltia CMS (git-based) leva ~1h.
