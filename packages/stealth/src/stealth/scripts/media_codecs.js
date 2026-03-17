const originalCanPlayType = HTMLMediaElement.prototype.canPlayType;

HTMLMediaElement.prototype.canPlayType = function (type) {
    if (typeof type === 'string') {
        if (type.includes('video/mp4') || type.includes('audio/mpeg')) {
            return 'probably';
        }
        if (type.includes('audio/mp4')) {
            return 'maybe';
        }
    }
    return originalCanPlayType.call(this, type);
};
