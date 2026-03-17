/**
 * Device Profile - 设备画像共享基础
 * 
 * 这是所有反检测补丁的单一事实来源。
 * 其他补丁通过 __kaitianDeviceProfile 对象读取设备特征，
 * 确保所有浏览器特征的一致性。
 */
(function() {
    'use strict';

    // 设备画像配置（由 Python 端通过模板变量注入）
    const deviceProfile = {
        // 基础标识
        userAgent: '{{USER_AGENT}}',
        platform: '{{PLATFORM}}',
        vendor: '{{VENDOR}}',
        
        // 视口与显示
        viewport: {
            width: {{VIEWPORT_WIDTH}},
            height: {{VIEWPORT_HEIGHT}},
        },
        screen: {
            width: {{SCREEN_WIDTH}},
            height: {{SCREEN_HEIGHT}},
            colorDepth: {{COLOR_DEPTH}},
            pixelDepth: {{COLOR_DEPTH}},
        },
        devicePixelRatio: {{PIXEL_RATIO}},
        
        // 设备能力
        hardwareConcurrency: {{HARDWARE_CONCURRENCY}},
        deviceMemory: {{DEVICE_MEMORY}},
        maxTouchPoints: {{MAX_TOUCH_POINTS}},
        
        // 本地化
        locale: '{{LOCALE}}',
        timezone: '{{TIMEZONE}}',
        languages: ['{{LOCALE}}', '{{LOCALE_SHORT}}'],
        
        // 设备类型特征
        mobile: {{MOBILE_BOOL}},
        primaryPointer: '{{PRIMARY_POINTER}}',  // "fine" 或 "coarse"
        hoverCapable: {{HOVER_CAPABLE_BOOL}},
        prefersReducedMotion: {{PREFERS_REDUCED_MOTION_BOOL}},
        
        // 生成确定性种子（用于 canvas/webgl 稳定化）
        seed: '{{DEVICE_SEED}}',
    };

    // 将设备画像挂载到全局，供其他补丁使用
    Object.defineProperty(window, '__kaitianDeviceProfile', {
        get: () => deviceProfile,
        configurable: false,
        enumerable: false,
    });

    // 提供确定性随机数生成器（基于种子）
    window.__kaitianDeterministicRandom = function(seed) {
        let x = 0;
        for (let i = 0; i < seed.length; i++) {
            x = (x * 31 + seed.charCodeAt(i)) % 0x7FFFFFFF;
        }
        return function() {
            x = (x * 1103515245 + 12345) % 0x7FFFFFFF;
            return (x / 0x7FFFFFFF);
        };
    };

    // 提供字符串哈希函数（用于生成稳定指纹）
    window.__kaitianHashString = function(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash).toString(16);
    };
})();
