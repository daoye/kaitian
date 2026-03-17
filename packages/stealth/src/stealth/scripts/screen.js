/**
 * 修改 screen 对象
 * 与 viewport 和指纹配置保持一致
 */
Object.defineProperty(screen, 'width', { get: () => {{SCREEN_WIDTH}} });
Object.defineProperty(screen, 'height', { get: () => {{SCREEN_HEIGHT}} });
Object.defineProperty(screen, 'availWidth', { get: () => {{SCREEN_WIDTH}} });
Object.defineProperty(screen, 'availHeight', { get: () => {{SCREEN_HEIGHT}} });
Object.defineProperty(screen, 'colorDepth', { get: () => {{COLOR_DEPTH}} });
Object.defineProperty(screen, 'pixelDepth', { get: () => {{COLOR_DEPTH}} });
Object.defineProperty(window, 'devicePixelRatio', { get: () => {{PIXEL_RATIO}} });
