Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => {{HARDWARE_CONCURRENCY}},
});

Object.defineProperty(navigator, 'deviceMemory', {
    get: () => {{DEVICE_MEMORY}},
});
