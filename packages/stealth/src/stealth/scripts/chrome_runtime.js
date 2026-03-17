if (!window.chrome) {
    Object.defineProperty(window, 'chrome', {
        value: {
            runtime: {},
        },
        writable: false,
        configurable: false,
    });
} else if (!window.chrome.runtime) {
    Object.defineProperty(window.chrome, 'runtime', {
        value: {},
        writable: false,
        configurable: false,
    });
}
