# Hibiscus Phytocosméticos — Site Estático (Hugo)

Substitui o WordPress hospedado em `www.hibiscus.com.br`. Zero PHP, zero banco
de dados, zero painel admin para ser invadido. Conteúdo em Markdown, deploy
gratuito no Cloudflare Pages.

---

## Stack

- **Hugo** (extended) — gerador estático
- **Vanilla HTML/CSS** — sem framework JS
- **Fraunces + Manrope** (Google Fonts) — tipografia editorial
- **Cloudflare Pages** — hospedagem + formulários grátis até 1k submissões/mês

---

## Rodar localmente

```bash
# Instalar Hugo (Arch)
sudo pacman -S hugo

# Ou no Mac (M3)
brew install hugo

# Subir servidor de dev
hugo server -D

# Build de produção
hugo --minify
```

Servidor de dev em `http://localhost:1313`. Build vai para `./public/`.

---

## Estrutura

```
hibiscus/
├── hugo.toml                  # config + dados da empresa (telefone, endereço…)
├── content/                   # CONTEÚDO EM MARKDOWN — edite aqui
│   ├── _index.md              # home
│   ├── quem-somos.md
│   ├── o-que-fazemos.md
│   └── contato.md
├── layouts/                   # templates HTML
│   ├── _default/baseof.html   # wrapper geral (head, header, footer)
│   ├── index.html             # home
│   ├── quem-somos.html
│   ├── o-que-fazemos.html
│   ├── contato.html
│   └── partials/              # header, footer, FAB WhatsApp
├── assets/css/main.css        # estilo único (minificado no build)
├── static/                    # arquivos servidos como-estão
│   ├── favicon.svg
│   ├── robots.txt
│   ├── _redirects             # regras de redirect do Cloudflare Pages
│   └── img/                   # ⚠️ IMAGENS — PRECISAM SER MIGRADAS
└── .gitignore
```

---

## Migração de imagens do WP (passo obrigatório)

O WordPress atual hospeda imagens em `/wp-content/uploads/2024/03/...`.
Precisamos baixá-las e colocá-las em `static/img/`. Comandos:

```bash
cd static/img
mkdir -p quem-somos home

# Logotipo
curl -L -o logo.png "https://www.hibiscus.com.br/wp-content/uploads/2024/02/marca-hibiscus.png"

# Galeria do Quem Somos
for n in 04 05 06 07 08 09 10 11; do
  curl -L -o "quem-somos/imagem${n}.jpg" \
    "https://www.hibiscus.com.br/wp-content/uploads/2024/03/imagem${n}.jpg"
done

# Logo Anvisa
curl -L -o anvisa-logo.png "https://www.hibiscus.com.br/wp-content/uploads/2024/03/anvisa-logo-1024x235.png"
```

Depois disso o site funciona offline e sem dependência do WP.

**Opcional — converter para WebP** (Hugo faz processamento automático se você
mover imagens para `assets/img/` e usar o pipeline `image.Resize`, mas o
ganho aqui é marginal porque o site tem poucas imagens):

```bash
sudo pacman -S libwebp  # ou: brew install webp
for f in static/img/**/*.jpg; do cwebp -q 82 "$f" -o "${f%.jpg}.webp"; done
```

---

## Editar conteúdo

Tudo está em `content/*.md`. O front matter (YAML no topo) define os blocos
estruturados como serviços, valores, etapas do método. O texto em Markdown
abaixo do front matter é o corpo livre.

Para alterar telefone, e-mail, endereço, horário — **edite `hugo.toml`**
(seção `[params]`). Não precisa tocar em mais nada; tudo o resto puxa de lá.

---

## Deploy no Cloudflare Pages

1. Subir o repositório no GitHub (privado ou público).
2. Em `pages.cloudflare.com` → Connect to Git → escolher o repo.
3. Build settings:
   - Framework preset: **Hugo**
   - Build command: `hugo --minify`
   - Build output directory: `public`
   - Environment variable: `HUGO_VERSION = 0.135.0` (ou versão atual)
4. Deploy. Funciona na URL `*.pages.dev` imediatamente.
5. Custom domain: aponte `hibiscus.com.br` e `www.hibiscus.com.br` em CF DNS
   para o projeto Pages. SSL é automático.

### Formulário de contato

O `<form>` em `/contato/` tem o atributo `data-static-form-name="contato"`.
No Cloudflare Pages, isso ativa **Pages Forms** automaticamente após o
primeiro deploy. Submissões aparecem no dashboard CF; configure
encaminhamento por e-mail nas configurações do projeto.

Alternativas se preferir: Formspree, Web3Forms, ou simplesmente trocar o
form por um `mailto:` (o WhatsApp já é o canal principal).

---

## Política de Privacidade

O site original linka para uma política hospedada no domínio da agência
defunta (`rcbcorretora.mestresdosite.group`). Isso é um problema de LGPD.

Criar uma página `content/politica-de-privacidade.md` própria antes do
go-live. O footer já aponta para `/politica-de-privacidade/`.

---

## Checklist de go-live

- [ ] Migrar imagens do WP (script acima)
- [ ] Criar página de Política de Privacidade própria (LGPD)
- [ ] Atualizar `[params]` em `hugo.toml` com e-mails reais (contato@, rh@)
- [ ] Confirmar URL do Instagram (placeholder está com guess de username)
- [ ] Adicionar `og.jpg` em `static/img/` (1200x630) para preview social
- [ ] Adicionar `apple-touch-icon.png` 180x180 em `static/`
- [ ] Testar formulário após deploy
- [ ] Em CF DNS: apontar A/AAAA do apex e CNAME do `www` para o projeto Pages
- [ ] Manter o WP rodando em paralelo até o DNS propagar (24h), depois
      desligar o servidor PHP/MySQL antigo

---

## Por que essa stack

- **Hugo**: builds em milissegundos, binário único, sem Node, sem npm install
  de 800 MB. Ideal para um site de 4 páginas que será editado raramente.
- **Cloudflare Pages**: free tier cobre tráfego, builds e formulários para um
  site B2B. CDN com POPs em SP e RJ.
- **Sem CMS**: você é técnico, edita Markdown no Emacs. Se em algum momento
  alguém não-técnico precisar editar, adicionar Decap CMS ou Sveltia CMS
  (git-based, grátis) leva ~1h.

---

## Reverter

Esse projeto não toca no WP atual. Pode rodar os dois em paralelo até o
cutover do DNS, e voltar atrás é trivial — basta repontar o DNS.
