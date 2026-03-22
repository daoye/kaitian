() => {
  const detectSiteKey = (selectors) => {
    for (const selector of selectors) {
      const node = document.querySelector(selector);
      if (node) {
        const value = node.getAttribute('data-sitekey') || node.getAttribute('sitekey');
        if (value) {
          return value;
        }
      }
    }
    return null;
  };

  const turnstileField = document.querySelector('[name="cf-turnstile-response"]');
  const turnstileValue = turnstileField ? turnstileField.value.trim() : '';
  if (
    (!turnstileValue && turnstileField) ||
    document.querySelector('.cf-turnstile') ||
    document.querySelector('iframe[src*="challenges.cloudflare.com"]')
  ) {
    return {
      provider: 'cloudflare',
      challenge_type: 'turnstile',
      message: 'Cloudflare Turnstile detected',
      site_key: detectSiteKey(['.cf-turnstile', '[data-sitekey]']),
      response_field: 'cf-turnstile-response',
      widget_selector: '.cf-turnstile',
      action: null,
    };
  }

  const recaptchaField = document.querySelector('[name="g-recaptcha-response"]');
  const recaptchaValue = recaptchaField ? recaptchaField.value.trim() : '';
  if (
    (!recaptchaValue && recaptchaField) ||
    document.querySelector('.g-recaptcha') ||
    document.querySelector('iframe[src*="recaptcha"]')
  ) {
    const widget = document.querySelector('.g-recaptcha, [data-sitekey]');
    return {
      provider: 'google',
      challenge_type: 'recaptcha',
      message: 'Google reCAPTCHA detected',
      site_key: widget ? (widget.getAttribute('data-sitekey') || widget.getAttribute('sitekey')) : null,
      response_field: 'g-recaptcha-response',
      widget_selector: '.g-recaptcha',
      action: widget ? widget.getAttribute('data-action') : null,
    };
  }

  return null;
}
