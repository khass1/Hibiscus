# Aceitação no navegador

Execute após mudanças em CSS, navegação ou JavaScript. O build e a auditoria
estática não comprovam estes comportamentos. Registre navegador, versão,
largura e resultado na revisão; uma etapa não executada fica pendente.

Use `hugo server` e confira `/`, `/es/` e `/en/` nas larguras 360, 880,
881 e 1280 px. Repita os fluxos móveis em Safari e Chromium.

- Abra e feche o menu pelo botão e por Escape. Tab e Shift+Tab devem permanecer
  no menu aberto; Escape devolve o foco ao botão. Ao ampliar para 881 px, o
  conteúdo deve voltar a aceitar foco e rolagem.
- Percorra a página por teclado. O FAB deve ter nome acessível e foco visível;
  não pode impedir o acesso aos links do rodapé, inclusive à privacidade.
  Confira também com zoom de 200% e em dispositivo com área segura inferior.
- Em `/glossario/`, `/es/glosario/` e `/en/glossary/`, filtre por um termo
  existente, uma palavra com acento e uma busca sem resultado. Confira a
  contagem anunciada, Escape para limpar e âncoras para termos filtrados.
- Desative JavaScript: navegação, termos e canais de contato continuam
  disponíveis; o controle de filtro fica oculto.
- Nas páginas de contato, o mapa não deve iniciar requisições ao Google antes
  do clique de carregamento. Depois do clique, confira título e foco do iframe.
- Com VoiceOver ou NVDA, confirme que o conteúdo de fundo não é anunciado
  enquanto o menu está aberto e volta a ser anunciado ao fechar.

Não confunda ausência de erro no console com aprovação visual ou de leitor de
tela. Corrija sobreposições e controles inacessíveis antes de publicar.
