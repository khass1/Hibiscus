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

    // O menu mobile cobre a tela inteira. Enquanto está aberto, o resto do
    // documento sai da árvore de acessibilidade e da ordem do teclado.
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
        if (open) {
          element.setAttribute('inert', '');
          // `inert` só é baseline desde 2022; em navegador anterior o
          // aria-hidden mantém o fundo fora da árvore de acessibilidade.
          element.setAttribute('aria-hidden', 'true');
        } else {
          element.removeAttribute('inert');
          element.removeAttribute('aria-hidden');
        }
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
      // telefone, o e-mail e outros destinos. Um
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
        page: location.pathname,
        lang: document.documentElement.lang
      });
    });
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
  initCtaTracking();
  initGlossary();
})();
