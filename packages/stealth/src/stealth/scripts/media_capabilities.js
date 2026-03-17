/**
 * Media Capabilities 补丁
 * 
 * 模拟 navigator.mediaCapabilities API，提供与设备画像一致的媒体能力信息。
 */
(function() {
    'use strict';

    const profile = window.__kaitianDeviceProfile || {};
    const mobile = profile.mobile || false;
    const deviceMemory = profile.deviceMemory || 8;

    // 定义支持的媒体配置
    const supportedConfigs = {
        // 视频解码能力
        video: {
            'video/mp4; codecs="avc1.42001E"': { supported: true, smooth: true, powerEfficient: true },
            'video/mp4; codecs="avc1.4d0020"': { supported: true, smooth: true, powerEfficient: true },
            'video/mp4; codecs="avc1.640028"': { supported: true, smooth: !mobile, powerEfficient: !mobile },
            'video/webm; codecs="vp8"': { supported: true, smooth: true, powerEfficient: !mobile },
            'video/webm; codecs="vp9"': { supported: true, smooth: deviceMemory >= 4, powerEfficient: deviceMemory >= 8 },
            'video/webm; codecs="av1"': { supported: deviceMemory >= 8, smooth: deviceMemory >= 16, powerEfficient: false },
        },
        // 音频解码能力
        audio: {
            'audio/mp4; codecs="mp4a.40.2"': { supported: true, smooth: true, powerEfficient: true },
            'audio/mp4; codecs="mp4a.40.5"': { supported: true, smooth: true, powerEfficient: true },
            'audio/webm; codecs="opus"': { supported: true, smooth: true, powerEfficient: true },
            'audio/webm; codecs="vorbis"': { supported: true, smooth: true, powerEfficient: true },
            'audio/mpeg': { supported: true, smooth: true, powerEfficient: true },
            'audio/wav; codecs="1"': { supported: true, smooth: true, powerEfficient: true },
            'audio/flac': { supported: deviceMemory >= 4, smooth: true, powerEfficient: deviceMemory >= 4 },
        },
    };

    // 解析 MIME 类型
    function parseMimeType(mimeType) {
        if (!mimeType || typeof mimeType !== 'string') {
            return null;
        }
        
        const parts = mimeType.split(';');
        const type = parts[0].trim().toLowerCase();
        const params = {};
        
        for (let i = 1; i < parts.length; i++) {
            const param = parts[i].trim();
            const eqIndex = param.indexOf('=');
            if (eqIndex > -1) {
                const key = param.substring(0, eqIndex).trim();
                const value = param.substring(eqIndex + 1).trim().replace(/^["']|["']$/g, '');
                params[key] = value;
            }
        }
        
        return { type, params };
    }

    // 匹配媒体配置
    function matchMediaConfig(mediaType, config) {
        if (!config || !config.contentType) {
            return null;
        }
        
        const parsed = parseMimeType(config.contentType);
        if (!parsed) {
            return null;
        }
        
        const type = parsed.type;
        const codec = parsed.params.codecs;
        
        // 构建查找键
        let lookupKey = type;
        if (codec) {
            lookupKey += `; codecs="${codec}"`;
        }
        
        // 在支持列表中查找
        const typeMap = mediaType === 'audio' ? supportedConfigs.audio : supportedConfigs.video;
        
        // 精确匹配
        if (typeMap[lookupKey]) {
            return typeMap[lookupKey];
        }
        
        // 模糊匹配（只匹配 MIME 类型，不看 codec）
        for (const key in typeMap) {
            if (key.startsWith(type)) {
                return typeMap[key];
            }
        }
        
        // 默认保守返回
        return { supported: false, smooth: false, powerEfficient: false };
    }

    // 创建 MediaCapabilities 对象
    const mediaCapabilities = {
        decodingInfo: function(configuration) {
            return new Promise((resolve) => {
                if (!configuration) {
                    resolve({
                        supported: false,
                        smooth: false,
                        powerEfficient: false,
                    });
                    return;
                }

                // 检查音频配置
                if (configuration.audio) {
                    const result = matchMediaConfig('audio', configuration.audio);
                    resolve(result || { supported: false, smooth: false, powerEfficient: false });
                    return;
                }

                // 检查视频配置
                if (configuration.video) {
                    const result = matchMediaConfig('video', configuration.video);
                    resolve(result || { supported: false, smooth: false, powerEfficient: false });
                    return;
                }

                // 默认不支持
                resolve({
                    supported: false,
                    smooth: false,
                    powerEfficient: false,
                });
            });
        },

        encodingInfo: function(configuration) {
            return new Promise((resolve) => {
                // 编码能力通常有限
                const canEncode = deviceMemory >= 8;
                resolve({
                    supported: canEncode,
                    smooth: canEncode && !mobile,
                    powerEfficient: false, // 编码通常不节能
                });
            });
        },
    };

    // 注入 navigator.mediaCapabilities
    Object.defineProperty(navigator, 'mediaCapabilities', {
        get: () => mediaCapabilities,
        configurable: true,
        enumerable: true,
    });

    // 保持 toString 一致
    mediaCapabilities.decodingInfo.toString = function() {
        return 'function decodingInfo() { [native code] }';
    };
    mediaCapabilities.encodingInfo.toString = function() {
        return 'function encodingInfo() { [native code] }';
    };
})();
