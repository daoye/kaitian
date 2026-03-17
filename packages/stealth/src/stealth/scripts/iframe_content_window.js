const originalCreateElement = Document.prototype.createElement;

Document.prototype.createElement = function () {
    const element = originalCreateElement.apply(this, arguments);
    if (arguments.length > 0 && String(arguments[0]).toLowerCase() === 'iframe') {
        Object.defineProperty(element, 'contentWindow', {
            get: () => window,
            configurable: true,
        });
    }
    return element;
};
