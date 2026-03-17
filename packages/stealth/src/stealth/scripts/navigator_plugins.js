/**
 * 模拟 navigator.plugins
 * 真实浏览器通常有 PDF 插件和 Native Client
 */
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            version: undefined,
            length: 1,
            item: () => ({ type: 'application/pdf' }),
            namedItem: () => ({ type: 'application/pdf' }),
        },
        {
            name: 'Native Client',
            filename: 'native-client.nmf',
            description: 'Native Client module',
            version: undefined,
            length: 0,
        },
    ],
});
