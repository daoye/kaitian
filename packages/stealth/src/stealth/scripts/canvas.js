/**
 * Canvas 指纹稳定化
 * 使用 profile 种子生成确定性噪声，确保同一 profile 输出稳定
 */
(function() {
    const profile = window.__kaitianDeviceProfile || {};
    const seed = '{{CANVAS_SEED}}' || profile.seed || 'default_seed';
    const rng = window.__kaitianDeterministicRandom ? window.__kaitianDeterministicRandom(seed) : () => Math.random();

    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;

    function addDeterministicNoise(imageData) {
        const data = imageData.data;
        const noiseStrength = 2;

        for (let i = 0; i < data.length; i += 4) {
            const noise = Math.floor((rng() - 0.5) * noiseStrength * 2);
            data[i] = Math.max(0, Math.min(255, data[i] + noise));
            data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + noise));
            data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + noise));
        }

        return imageData;
    }

    HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
        const context = this.getContext('2d');
        if (context && this.width > 0 && this.height > 0) {
            try {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                addDeterministicNoise(imageData);
                context.putImageData(imageData, 0, 0);
            } catch (e) {
                // Canvas 可能被污染，忽略
            }
        }
        return originalToDataURL.call(this, type, quality);
    };

    HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
        const self = this;
        const context = this.getContext('2d');

        if (context && this.width > 0 && this.height > 0) {
            try {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                addDeterministicNoise(imageData);
                context.putImageData(imageData, 0, 0);
            } catch (e) {
                // Canvas 可能被污染，忽略
            }
        }

        return originalToBlob.call(this, callback, type, quality);
    };

    if (HTMLCanvasElement.prototype.toBlob) {
        HTMLCanvasElement.prototype.toBlob.toString = function() {
            return 'function toBlob() { [native code] }';
        };
    }

    HTMLCanvasElement.prototype.toDataURL.toString = function() {
        return 'function toDataURL() { [native code] }';
    };
})();
