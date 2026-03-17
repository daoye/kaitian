/**
 * Match Media 补丁
 * 
 * 模拟 CSS 媒体查询，使其与设备画像一致。
 * 包括 pointer、hover、prefers-reduced-motion 等。
 */
(function() {
    'use strict';

    const profile = window.__kaitianDeviceProfile || {};
    const primaryPointer = profile.primaryPointer || 'fine';
    const hoverCapable = profile.hoverCapable !== false;
    const prefersReducedMotion = profile.prefersReducedMotion || false;
    const mobile = profile.mobile || false;
    const devicePixelRatio = profile.devicePixelRatio || 1;

    // 原始 matchMedia（如果存在）
    const originalMatchMedia = window.matchMedia;

    // 创建 MediaQueryList 对象
    function createMediaQueryList(query, matches) {
        const mql = {
            matches: matches,
            media: query,
            onchange: null,
            addListener: function(callback) {
                if (typeof callback === 'function') {
                    // 存储回调但不实际触发（保持一致性）
                    if (!this._listeners) {
                        this._listeners = [];
                    }
                    this._listeners.push(callback);
                }
            },
            removeListener: function(callback) {
                if (this._listeners) {
                    const index = this._listeners.indexOf(callback);
                    if (index > -1) {
                        this._listeners.splice(index, 1);
                    }
                }
            },
            addEventListener: function(type, callback) {
                if (type === 'change' && typeof callback === 'function') {
                    this.addListener(callback);
                }
            },
            removeEventListener: function(type, callback) {
                if (type === 'change') {
                    this.removeListener(callback);
                }
            },
            dispatchEvent: function() {
                return true;
            },
        };

        return mql;
    }

    // 评估媒体查询
    function evaluateQuery(query) {
        const normalizedQuery = query.trim().toLowerCase();

        // pointer 查询
        if (normalizedQuery === '(pointer: coarse)') {
            return primaryPointer === 'coarse';
        }
        if (normalizedQuery === '(pointer: fine)') {
            return primaryPointer === 'fine';
        }
        if (normalizedQuery === '(pointer: none)') {
            return false; // 一般设备都有某种指针
        }

        // any-pointer 查询
        if (normalizedQuery === '(any-pointer: coarse)') {
            return mobile; // 移动设备有 coarse pointer
        }
        if (normalizedQuery === '(any-pointer: fine)') {
            return !mobile || primaryPointer === 'fine'; // 桌面或精细设备
        }

        // hover 查询
        if (normalizedQuery === '(hover: hover)') {
            return hoverCapable;
        }
        if (normalizedQuery === '(hover: none)') {
            return !hoverCapable;
        }

        // any-hover 查询
        if (normalizedQuery === '(any-hover: hover)') {
            return hoverCapable;
        }
        if (normalizedQuery === '(any-hover: none)') {
            return !hoverCapable;
        }

        // prefers-reduced-motion
        if (normalizedQuery === '(prefers-reduced-motion: reduce)') {
            return prefersReducedMotion;
        }
        if (normalizedQuery === '(prefers-reduced-motion: no-preference)' ||
            normalizedQuery === '(prefers-reduced-motion)') {
            return !prefersReducedMotion;
        }

        // color-gamut
        if (normalizedQuery.includes('color-gamut')) {
            return normalizedQuery.includes('srgb'); // 默认支持 srgb
        }

        // display-mode
        if (normalizedQuery.includes('display-mode')) {
            return normalizedQuery.includes('browser') || normalizedQuery.includes('fullscreen');
        }

        // 分辨率查询
        if (normalizedQuery.includes('resolution')) {
            // 根据 devicePixelRatio 判断
            if (normalizedQuery.includes('min-resolution')) {
                const match = normalizedQuery.match(/(\d+(?:\.\d+)?)/);
                if (match) {
                    const requiredDpi = parseFloat(match[1]);
                    return devicePixelRatio * 96 >= requiredDpi;
                }
            }
            return true;
        }

        // 默认回退到原始 matchMedia（如果有）
        if (originalMatchMedia && typeof originalMatchMedia === 'function') {
            try {
                const result = originalMatchMedia(query);
                return result.matches;
            } catch (e) {
                // 出错时返回保守值
                return false;
            }
        }

        // 完全不认识的查询返回 false
        return false;
    }

    // 替换 window.matchMedia
    window.matchMedia = function(query) {
        if (typeof query !== 'string') {
            throw new TypeError('matchMedia requires a string argument');
        }

        const matches = evaluateQuery(query);
        return createMediaQueryList(query, matches);
    };

    // 保持 toString 一致
    window.matchMedia.toString = function() {
        return 'function matchMedia() { [native code] }';
    };
})();
