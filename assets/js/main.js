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
          document.querySelector('.wa-fab')
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

  // Todo CTA de WhatsApp leva o visitante para fora do site, então o pageview
  // sozinho nunca diz qual página — ou qual linha de produto — gerou o lead.
  // Cada link carrega data-cta (ver os templates); aqui só disparamos o evento.
  //
  // O Cloudflare Web Analytics NÃO tem API de evento customizado: quem tem é o
  // Zaraz (zaraz.track), que se liga no painel e é servido de /cdn-cgi/zaraz/,
  // mesma origem — a CSP atual já permite, sem mudança. Enquanto o Zaraz
  // estiver desligado isto é um no-op silencioso: nenhum erro, nenhum request.
  function initCtaTracking() {
    document.addEventListener('click', function (event) {
      var link = event.target.closest && event.target.closest('a[data-cta]');
      if (!link) return;
      if (!window.zaraz || typeof window.zaraz.track !== 'function') return;
      window.zaraz.track('whatsapp_click', {
        cta: link.getAttribute('data-cta'),
        page: location.pathname,
        lang: document.documentElement.lang
      });
    });
  }

  initNavigation();
  initMap();
  initCtaTracking();
})();
