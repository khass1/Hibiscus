# Contrato dos dados de conteúdo

O conteúdo fica em YAML front matter seguido de Markdown. O Hugo não valida um
schema: chave ausente normalmente vira texto vazio e o build continua verde.
Por isso, este documento define os campos aceitos e
`scripts/audit-build.py` valida as propriedades observáveis no HTML gerado.

## Campos comuns

Toda página em `content/` exige:

```yaml
---
lastmod: 2026-09-20T12:00:00-03:00
title: "Título da página"
description: "Descrição única para busca e compartilhamento."
---
```

- `lastmod`: data ISO 8601 com hora e fuso; não pode estar no futuro.
- `title`: texto não vazio. O HTML final deve ter também um único `h1`.
- `description`: texto não vazio; alimenta a meta description e o Open Graph.
- `layout`: obrigatório quando a página usa um layout especializado.
- `slug` ou `url`: opcionais; use um deles quando a rota não deve derivar do
  nome do arquivo.

Campos opcionais do layout genérico:

```yaml
lede: "Introdução curta."
toc: true
noindex: true
ogImage: "/img/imagem.jpg"
cta:
  title: "Título"
  text: "Texto opcional."
  label: "Rótulo do botão"
  whatsapp: "Mensagem pré-preenchida."
```

## Home

Arquivos: `_index.md`, `_index.es.md` e `_index.en.md`.

```yaml
type: home
hero:
  eyebrow: "Contexto curto"
  headline: "Título principal"
  subhead: "Explicação"
  primaryCta:
    label: "Fale com um especialista"
    href: "/rota-opcional/" # sem href, usa WhatsApp
  secondaryCta:
    label: "Conheça nosso método"
    href: "/o-que-fazemos/#metodo"
valores:
  - grupo: "Nome do grupo"
    itens: ["Item 1", "Item 2"]
servicos:
  - slug: "identificador-editorial"
    title: "Nome"
    summary: "Resumo curto"
    href: "/destino/"
```

`hero`, `valores` e `servicos` são obrigatórios e não podem estar vazios. As
três traduções devem manter a mesma quantidade de grupos e serviços. A grade de
serviços atual tem seis itens para preservar o desenho 3 × 2.

## O que Fazemos

```yaml
layout: "o-que-fazemos"
linhas_nota: "Nota opcional em Markdown."
servicos:
  - id: "linha-facial"
    title: "Linha facial"
    intro: "Descrição; HTML confiável é aceito neste campo."
    whatsappText: "Mensagem específica"
    ctaLabel: "Orçar linha facial"
    chips: ["Selo opcional"]
    items: ["Produto 1", "Produto 2"]
metodo:
  - titulo: "Etapa"
    resumo: "Resumo"
    pontos: ["Ação 1", "Ação 2"]
faqs:
  - q: "Pergunta?"
    lead: "Resposta curta"
    detail: "Complemento opcional"
```

- `servicos[].id` é obrigatório, único e estável.
- `title`, `intro` e `whatsappText` são obrigatórios por serviço.
- `items` pode ser vazio; `chips` e `ctaLabel` são opcionais.
- `metodo[].titulo` e `pontos` são obrigatórios; `resumo` é opcional.
- `faqs[].q` e `lead` são obrigatórios; `detail` é opcional.
- As versões pt-BR, es e en devem renderizar quantidades iguais de serviços,
  etapas e FAQs.

## Galeria e glossário

Uma imagem de `gallery` exige dimensões para evitar deslocamento de layout:

```yaml
gallery:
  - src: "/img/arquivo.webp"
    alt: "Descrição da imagem"
    width: 1600
    height: 900
    caption: "Legenda opcional"
```

O glossário usa:

```yaml
termos:
  - termo: "MOQ"
    expansao: "Minimum Order Quantity" # opcional
    definicao: "Definição em Markdown."
```

`termo` gera o id da âncora; mudar o nome pode quebrar links externos. A mesma
lista alimenta o conteúdo visível e o JSON-LD `DefinedTermSet`.

## Traduções e links

- Traduções usam o mesmo nome-base: `pagina.md`, `pagina.es.md` e
  `pagina.en.md`.
- A interface usa as mesmas chaves nos três arquivos `i18n/*.toml`.
- Uma página nova precisa das entradas correspondentes nos menus de cada idioma.
- Todo `<a>` precisa de `href`; links com `target="_blank"` precisam de
  `rel="noopener"`.
- URLs de WhatsApp devem ser produzidas por `whatsapp-url.html`, nunca montadas
  manualmente.

## Propriedades exigidas pela suíte

### Fatos comerciais compartilhados

`data/commercial.toml` concentra os valores da faixa de confiança: mínimo por
peso, mínimos por unidade, prazo típico de amostra, produção e marcas atendidas.
O partial recebe esses valores e os catálogos i18n mantêm apenas a redação.

Os parágrafos de conteúdo e `static/llms.txt` ainda são editoriais: não são
reescritos automaticamente. Ao mudar um valor comercial, revise as três
traduções de O que Fazemos, modelos de desenvolvimento, terceirização, páginas
de nicho, glossário e `llms.txt`. Preserve qualificadores de prazo e a distinção
entre kg por SKU e unidades por formato. Atualize `lastmod` das páginas alteradas.

### Validação

Execute `python3 scripts/check-hugo-version.py` antes do build. Mudanças na
interface exigem também [aceitação no navegador](browser-acceptance.md).

Os testes unitários em `scripts/test_audit_build.py` exercitam falhas do contrato;
após o build, `scripts/audit-build.py` exige:

- página não redirecionada com `lang`, título, descrição, canonical HTTPS, um
  único `h1` e metadados Open Graph não vazios;
- ids únicos, imagens com `alt`, links internos e fragmentos válidos;
- âncoras com destino e segurança em links que abrem nova aba;
- JSON-LD válido e CSP sem script executável inline;
- três homes, sem FAQ duplicada, com estruturas localizadas equivalentes;
- uma página O que Fazemos por idioma, com quantidades equivalentes e não
  vazias de serviços, etapas e FAQs;
- catálogos i18n com as mesmas chaves e `lastmod` válido em todo Markdown,
  inclusive futuros bundles em subdiretórios.

Quando uma mudança editorial alterar deliberadamente uma dessas propriedades,
atualize o conteúdo, este contrato e a auditoria no mesmo commit.
