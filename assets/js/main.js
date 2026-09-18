// BASELINE DE NAVEGADOR: ES2017+ (Chrome 58+, Safari 11+, Firefox 54+).
//
// Não há transpilação — o pipeline é `resources.Minify` e nada mais (ver
// baseof.html), então o que está escrito aqui é o que chega ao navegador.
// `async`/`await`, `String.includes`, `String.normalize` e `NodeList.forEach`
// são permitidos.
//
// Por que não ES5: o main.css usa custom properties (`var(--x)`) em 327
// lugares, além de `100dvh` e `env(safe-area-inset-*)`. Qualquer navegador
// velho o bastante para precisar de ES5 — IE11 à frente — não renderiza este
// site de jeito nenhum, com ou sem JS. Escrever `Array.prototype.slice.call`
// por compatibilidade seria proteger um cenário que já não existe.
//
// As voltas em ES5 que sobraram no arquivo são históricas e funcionam; não
// precisam ser reescritas. Código NOVO segue a baseline acima.
(function () {
  'use strict';

  function initNavigation() {
    var btn = document.querySelector('[data-nav-toggle]');
    var nav = document.getElementById('primary-nav');
    if (!btn || !nav) return;

    // The mobile menu covers the viewport. Keep the rest of the document out
    // of the accessibility tree and keyboard order while it is open.
    var outside = null;
    function outsideElements() {
      if (!outside) {
        outside = [
          document.getElementById('conteudo'),
          document.querySelector('.site-footer'),
          document.querySelector('.wa-fab'),
          document.querySelector('.mobile-cta')
        ].filter(Boolean);
      }
      return outside;
    }

    function isOpen() {
      return btn.getAttribute('aria-expanded') === 'true';
    }

    var labelOpen = btn.getAttribute('data-label-open') || 'Abrir menu';
    var labelClose = btn.getAttribute('data-label-close') || 'Fechar menu';

    function setOpen(open) {
      btn.setAttribute('aria-expanded', String(open));
      btn.setAttribute('aria-label', open ? labelClose : labelOpen);
      nav.classList.toggle('is-open', open);
      document.body.classList.toggle('nav-open', open);
      outsideElements().forEach(function (element) {
        if (open) element.setAttribute('inert', '');
        else element.removeAttribute('inert');
      });
    }

    btn.addEventListener('click', function () {
      var next = !isOpen();
      setOpen(next);
      if (next) {
        var firstLink = nav.querySelector('a[href]');
        if (firstLink) firstLink.focus();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (!isOpen()) return;

      if (event.key === 'Escape') {
        setOpen(false);
        btn.focus();
        return;
      }

      if (event.key !== 'Tab') return;
      var items = [btn].concat(Array.prototype.slice.call(nav.querySelectorAll('a[href]')));
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });

    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) setOpen(false);
    });

    var wideViewport = window.matchMedia('(min-width: 881px)');
    var closeOnWideViewport = function (event) {
      if (event.matches && isOpen()) setOpen(false);
    };
    if (wideViewport.addEventListener) wideViewport.addEventListener('change', closeOnWideViewport);
    else if (wideViewport.addListener) wideViewport.addListener(closeOnWideViewport);
  }

  function initMap() {
    var box = document.querySelector('[data-map]');
    if (!box) return;
    var btn = box.querySelector('[data-map-load]');
    if (!btn) return;

    btn.addEventListener('click', function () {
      var frame = document.createElement('iframe');
      frame.title = box.getAttribute('data-map-title') || 'Google Maps';
      frame.src = box.getAttribute('data-map-src');
      frame.loading = 'lazy';
      frame.referrerPolicy = 'no-referrer-when-downgrade';
      box.replaceChildren(frame);
      box.classList.remove('mapa--consent');
      frame.focus();
    });
  }

  // Todo CTA de WhatsApp abre em nova aba (target="_blank"), então o pageview
  // sozinho nunca diz qual página — ou qual linha de produto — gerou o lead.
  // Cada link carrega data-cta (ver os templates); aqui só disparamos o evento.
  //
  // O Cloudflare Web Analytics NÃO tem API de evento customizado: quem tem é o
  // Zaraz (zaraz.track), que se liga no painel e é servido de /cdn-cgi/zaraz/,
  // mesma origem — a CSP atual já permite, sem mudança. Enquanto o Zaraz
  // estiver desligado isto é um no-op silencioso: nenhum erro, nenhum request.
  function track(evento, dados) {
    if (!window.zaraz || typeof window.zaraz.track !== 'function') return;
    window.zaraz.track(evento, dados);
  }

  function initCtaTracking() {
    document.addEventListener('click', function (event) {
      var link = event.target.closest && event.target.closest('a[data-cta]');
      if (!link) return;

      // O canal sai do href, não do nome do evento: `data-cta` também marca o
      // telefone (header e barra do mobile) e o e-mail do qualificador. Um
      // evento chamado `whatsapp_click` para tudo reportaria toque de telefone
      // como conversa iniciada, e o relatório mentiria na primeira campanha.
      var href = link.getAttribute('href') || '';
      var canal = 'outro';
      if (href.indexOf('https://wa.me/') === 0) canal = 'whatsapp';
      else if (href.indexOf('tel:') === 0) canal = 'telefone';
      else if (href.indexOf('mailto:') === 0) canal = 'email';

      track('cta_click', {
        cta: link.getAttribute('data-cta'),
        canal: canal,
        // O qualificador preenche isto com as três respostas; nos demais CTAs
        // fica vazio. É o único sinal de QUE projeto clicou — o WhatsApp abre
        // em outra aba e nunca volta para contar.
        detail: link.getAttribute('data-cta-detail') || '',
        page: location.pathname,
        lang: document.documentElement.lang
      });
    });
  }

  // Qualificador de briefing (partials/qualificador.html). Três selects que
  // reescrevem o `text=` do link do WhatsApp — nada é enviado por aqui, e a
  // pessoa ainda edita a mensagem no WhatsApp antes de mandar.
  //
  // Sem JS o bloco fica escondido por noscript.css: os selects não teriam
  // efeito e o botão cairia na mensagem genérica, que os outros CTAs da página
  // já oferecem.
  function initQualificador() {
    var box = document.querySelector('[data-qualificador]');
    if (!box) return;
    var link = box.querySelector('[data-qual-link]');
    var base = box.getAttribute('data-wa-base');
    if (!link || !base) return;

    var campos = Array.prototype.slice.call(box.querySelectorAll('[data-qual-campo]'));
    if (!campos.length) return;
    var previa = box.querySelector('[data-qual-previa]');
    var copy = box.querySelector('[data-qual-copy]');
    var copyStatus = box.querySelector('[data-qual-copy-status]');
    if (copy && previa && copyStatus) {
      copy.addEventListener('click', async function () {
        var summary = previa.textContent;
        try {
          await navigator.clipboard.writeText(summary);
          if (previa.textContent === summary && !previa.hidden) copyStatus.textContent = copy.getAttribute('data-success');
        } catch (_) {
          if (previa.textContent === summary && !previa.hidden) copyStatus.textContent = copy.getAttribute('data-failure');
        }
      });
    }
    var intro = box.getAttribute('data-msg-intro') || '';
    var outro = box.getAttribute('data-msg-outro') || '';

    // `?text=` e não `&text=`: a base (whatsapp-base.html) não tem mais query
    // nenhuma desde que virou wa.me — ver o comentário lá sobre o `&` que o
    // template escapa e que sumia com o destinatário.
    var hrefPadrao = link.getAttribute('href');
    var briefingCompleto = false;

    function update() {
      var partes = [];
      var chaves = [];
      campos.forEach(function (campo) {
        if (!campo.value) return;
        var rotulo = campo.options[campo.selectedIndex].text;
        partes.push(campo.getAttribute('data-qual-prefixo') + ' ' + rotulo + '.');
        chaves.push(campo.value);
      });
      if (copy) copy.disabled = !partes.length;
      if (copyStatus) copyStatus.textContent = '';

      // Nenhuma resposta: o botão volta ao link genérico que veio do build,
      // sem virar um "Olá!" pelado.
      if (!partes.length) {
        link.setAttribute('href', hrefPadrao);
        link.removeAttribute('data-cta-detail');
        if (previa) previa.hidden = true;
        return;
      }

      var mensagem = [intro].concat(partes).concat([outro]).join(' ').trim();
      link.href = base + '?text=' + encodeURIComponent(mensagem);
      link.setAttribute('data-cta-detail', chaves.join('|'));
      if (previa) {
        previa.textContent = mensagem;
        previa.hidden = false;
      }

      // Briefing completo: as três respostas dadas. Registra mesmo sem clique —
      // quem chegou aqui já disse o que quer, em que estágio e em que volume, e
      // o clique pode não vir. Uma vez por pageview.
      if (!briefingCompleto && chaves.length === campos.length) {
        briefingCompleto = true;
        track('briefing_complete', {
          briefing: chaves.join('|'),
          page: location.pathname,
          lang: document.documentElement.lang
        });
      }
    }

    campos.forEach(function (campo) {
      campo.addEventListener('change', update);
    });

    // As páginas de nicho já chegam com a categoria pré-selecionada, então a
    // mensagem precisa estar montada antes do primeiro change.
    update();
  }

  // Estimador de unidades (partials/estimador.html). O visitante informa o
  // lote em kg e o peso da própria unidade em gramas; a conta é aritmética
  // pura (kg × 1000 ÷ g) e o resultado vira texto no link do WhatsApp. Não há
  // constante de produto aqui de propósito: peso por unidade varia por
  // fórmula e envase, e chutar um valor daria um número errado com cara de
  // orçamento.
  function initEstimador() {
    var box = document.querySelector('[data-estimador]');
    if (!box) return;
    var link = box.querySelector('[data-est-link]');
    var base = box.getAttribute('data-wa-base');
    var kgCampo = box.querySelector('[data-est-campo="kg"]');
    var gCampo = box.querySelector('[data-est-campo="g"]');
    var saida = box.querySelector('[data-est-saida]');
    if (!link || !base || !kgCampo || !gCampo) return;

    var hrefPadrao = link.getAttribute('href');
    var tplSaida = box.getAttribute('data-resultado') || '{unidades}';
    var tplMensagem = box.getAttribute('data-msg') || '';
    var locale = document.documentElement.lang;

    // Vírgula decimal: o teclado numérico em pt-BR/es insere `,`, que
    // parseFloat não entende.
    function numero(campo) {
      var valor = parseFloat(campo.value.trim().replace(',', '.'));
      return isFinite(valor) && valor > 0 ? valor : 0;
    }

    function formatar(valor) {
      try {
        return new Intl.NumberFormat(locale || undefined).format(valor);
      } catch (erro) {
        return String(valor);
      }
    }

    function update() {
      var kg = numero(kgCampo);
      var gramas = numero(gCampo);

      if (!kg || !gramas) {
        saida.hidden = true;
        saida.textContent = '';
        link.setAttribute('href', hrefPadrao);
        link.removeAttribute('data-cta-detail');
        return;
      }

      var unidades = Math.round(kg * 1000 / gramas);
      var texto = formatar(unidades);
      saida.textContent = tplSaida.replace('{unidades}', texto);
      saida.hidden = false;

      var mensagem = tplMensagem
        .replace('{kg}', kgCampo.value.trim())
        .replace('{g}', gCampo.value.trim())
        .replace('{unidades}', texto);
      link.href = base + '?text=' + encodeURIComponent(mensagem);
      link.setAttribute('data-cta-detail', kg + 'kg|' + gramas + 'g|' + unidades);
    }

    [kgCampo, gCampo].forEach(function (campo) {
      campo.addEventListener('input', update);
    });
    update();
  }


  // Conteúdo de <details> fechado não entra no papel em nenhuma engine, e não
  // existe regra CSS aqui que cubra isso — este handler é o único mecanismo.
  // beforeprint abre tudo antes do spool; afterprint fecha de volta SÓ o que
  // este handler abriu, senão imprimir deixaria a página toda expandida na
  // tela depois, inclusive o que o leitor tinha fechado de propósito.
  var abertosPeloPrint = [];
  window.addEventListener('beforeprint', function () {
    abertosPeloPrint = Array.prototype.slice.call(
      document.querySelectorAll('details:not([open])')
    );
    abertosPeloPrint.forEach(function (detail) {
      detail.setAttribute('open', '');
    });
  });
  window.addEventListener('afterprint', function () {
    abertosPeloPrint.forEach(function (detail) {
      detail.removeAttribute('open');
    });
    abertosPeloPrint = [];
  });
  function initGlossary() {
    var filter = document.querySelector('[data-glossary-filter]');
    var list = document.getElementById('glossary-terms');
    if (!filter || !list) return;
    var input = filter.querySelector('input');
    var status = filter.querySelector('[data-glossary-status]');
    function normalize(text) {
      return text.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }
    var terms = Array.prototype.map.call(list.children, function (el) {
      return { el: el, text: normalize(el.textContent) };
    });
    function update() {
      var query = normalize(input.value.trim());
      var count = 0;
      terms.forEach(function (term) {
        term.el.hidden = !term.text.includes(query);
        if (!term.el.hidden) count++;
      });
      status.textContent = !query ? '' : count
        ? filter.getAttribute('data-results').replace('{count}', count)
        : filter.getAttribute('data-empty');
    }
    function revealAnchor() {
      var id;
      try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
      var target = document.getElementById(id);
      if (target && target.parentElement === list && target.hidden) {
        input.value = '';
        update();
        target.scrollIntoView();
      }
    }
    input.addEventListener('input', update);
    input.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        input.value = '';
        update();
      }
    });
    document.querySelector('.glossario-nav').addEventListener('click', function (event) {
      if (event.target.closest('a')) {
        input.value = '';
        update();
      }
    });
    window.addEventListener('hashchange', revealAnchor);
    filter.hidden = false;
    update();
    revealAnchor();
  }

  initNavigation();
  initMap();
  initQualificador();
  initEstimador();
  initCtaTracking();
  initGlossary();
})();
