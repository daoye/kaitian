/**
 * 设置 navigator.languages
 * 与 locale 配置保持一致
 */
Object.defineProperty(navigator, 'languages', {
    get: () => ['{{LOCALE}}', '{{LOCALE_SHORT}}'],
});
