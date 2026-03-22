({ token, responseField }) => {
  const selectors = [
    responseField ? `[name="${responseField}"]` : null,
    '[name="g-recaptcha-response"]',
    '[name="cf-turnstile-response"]',
  ].filter(Boolean);

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
}
