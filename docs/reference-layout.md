# Layout de referência

Este documento registra a composição das páginas. Ele é o contrato de
arquitetura visual; medidas, cores e breakpoints continuam em
`assets/css/main.css`.

## Moldura global

Todas as páginas passam por `layouts/_default/baseof.html` e seguem esta ordem:

1. cabeçalho fixo, link de salto, navegação principal e seletor de idioma;
2. `main#conteudo`, preenchido pelo layout da página;
3. rodapé institucional;
4. FAB do WhatsApp no desktop ou barra de telefone/WhatsApp no mobile.

O cabeçalho muda para menu de tela inteira até `880px`. Abaixo desse limite, a
barra de CTA ocupa o rodapé; acima dele, aparece o FAB. Conteúdo essencial não
pode depender de JavaScript: sem JS, a navegação vira uma lista estática e o
mapa preserva o link externo. Ao abrir o menu, `inert` e `aria-hidden` retiram o
restante da página da ordem de foco e da árvore de acessibilidade.

## Home

Fontes: `layouts/index.html` e `content/_index[.<idioma>].md`.

Ordem de referência:

1. hero com um `h1` e dois CTAs;
2. faixa de confiança;
3. três perfis de comprador;
4. três modelos de desenvolvimento;
5. catálogo com seis serviços em grade 3 × 2 no desktop;
6. quatro grupos de valores;
7. CTA final.

A home resume e encaminha. FAQ, matriz de capacidades e explicações técnicas
completas ficam nas páginas próprias. Isso evita duplicação editorial e mantém a
entrada curta.

## O que Fazemos

Fontes: `layouts/_default/o-que-fazemos.html` e
`content/o-que-fazemos[.<idioma>].md`.

Ordem de referência:

1. título e introdução;
2. faixa de confiança;
3. linhas de serviço vindas de `servicos`;
4. matriz de capacidades;
5. método vindo de `metodo`;
6. FAQ completa vinda de `faqs`, junto do JSON-LD `FAQPage`;
7. JSON-LD `Service`/`OfferCatalog` e CTA final.

Esta é a única página institucional que deve renderizar a FAQ completa. Cada
serviço precisa de id estável porque menus, links internos e dados estruturados
apontam para a mesma âncora.

## Páginas especializadas

- `single.html`: páginas editoriais, glossário, índice opt-in e CTA de rodapé.
- `quem-somos.html`: texto, licenças, fotos reais da fábrica e CTA.
- `contato.html`: três canais, endereço e mapa carregado só após consentimento.
- `404.html`: mensagem localizada e rotas de recuperação.

Páginas de nicho e guias usam `single.html`. Detalhes técnicos devem morar
nelas, não ser copiados para a home.

## Regras de mudança

- Preserve um único `h1` não vazio por página.
- Mantenha a mesma quantidade de blocos estruturais nas traduções equivalentes.
- Atualize este documento quando a ordem ou a responsabilidade de uma seção
  mudar; alterações puramente visuais pertencem ao CSS.
- Depois de mudar layout ou conteúdo, execute o build e a auditoria descritos
  no README.
