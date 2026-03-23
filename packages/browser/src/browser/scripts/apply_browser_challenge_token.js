({ token, responseField }) => {
  const selectors = [
    responseField ? `[name="${responseField}"]` : null,
    '[name="g-recaptcha-response"]',
    '[name="cf-turnstile-response"]',
  ].filter(Boolean);

  const triggerRecaptchaClients = () => {
    const cfg = window.___grecaptcha_cfg;
    if (!cfg || !cfg.clients) {
      return;
    }

    const visit = (node) => {
      if (!node || typeof node !== 'object') {
        return false;
      }

      for (const value of Object.values(node)) {
        if (typeof value === 'function') {
          try {
            value(token);
            return true;
          } catch {}
        }

        if (value && typeof value === 'object' && visit(value)) {
          return true;
        }
      }

      return false;
    };

    for (const client of Object.values(cfg.clients)) {
      if (visit(client)) {
        return;
      }
    }
  };

  const triggerDomCallbacks = () => {
    const widgets = document.querySelectorAll('.g-recaptcha, [data-sitekey]');
    for (const widget of widgets) {
      const callbackName = widget.getAttribute('data-callback');
      if (!callbackName) {
        continue;
      }

      const callback = callbackName
        .split('.')
        .reduce((current, part) => current?.[part], window);

      if (typeof callback === 'function') {
        try {
          callback(token);
          return;
        } catch {}
      }
    }
  };

  for (const selector of selectors) {
    let field = document.querySelector(selector);
    if (!field) {
      field = document.createElement('textarea');
      field.name = selector.slice(7, -2);
      field.style.display = 'none';
      document.body.appendChild(field);
    }
    field.value = token;
    field.dispatchEvent(new Event('input', { bubbles: true }));
    field.dispatchEvent(new Event('change', { bubbles: true }));
  }

  triggerDomCallbacks();
  triggerRecaptchaClients();
}
