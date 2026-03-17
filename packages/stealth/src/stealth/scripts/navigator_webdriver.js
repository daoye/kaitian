/**
 * 隐藏 navigator.webdriver 属性
 * 这是最常见的自动化检测点
 */
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
