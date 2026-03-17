/**
 * Visual Viewport 补丁
 * 
 * 模拟 window.visualViewport API，提供与设备画像一致的视口信息。
 */
(function() {
    'use strict';

    const profile = window.__kaitianDeviceProfile || {};
    
    // 从设备画像获取视口尺寸
    const viewportWidth = profile.viewport?.width || window.innerWidth || 1920;
    const viewportHeight = profile.viewport?.height || window.innerHeight || 1080;
    const devicePixelRatio = profile.devicePixelRatio || 1;
    const mobile = profile.mobile || false;

    // 创建 VisualViewport 对象
    const visualViewport = {
        width: viewportWidth,
        height: viewportHeight,
        scale: 1.0,
        offsetLeft: 0,
        offsetTop: 0,
        pageLeft: 0,
        pageTop: 0,
        onresize: null,
        onscroll: null,
    };

    // 如果原生 visualViewport 存在，尽量保持其部分行为
    if (window.visualViewport) {
        const original = window.visualViewport;
        
        // 复制原生的事件监听能力（如果有）
        if (original.addEventListener) {
            visualViewport.addEventListener = function(type, listener, options) {
                return original.addEventListener.call(original, type, listener, options);
            };
            visualViewport.removeEventListener = function(type, listener, options) {
                return original.removeEventListener.call(original, type, listener, options);
            };
            visualViewport.dispatchEvent = function(event) {
                return original.dispatchEvent.call(original, event);
            };
        }
    }

    // 计算 layout viewport 尺寸（通常与 visual viewport 相同或更大）
    const layoutViewportWidth = Math.max(viewportWidth, window.innerWidth || viewportWidth);
    const layoutViewportHeight = Math.max(viewportHeight, window.innerHeight || viewportHeight);

    // 注入 visualViewport
    Object.defineProperty(window, 'visualViewport', {
        get: () => visualViewport,
        configurable: true,
        enumerable: true,
    });

    // 同步更新函数（页面 resize/scroll 时调用）
    window.__kaitianUpdateVisualViewport = function() {
        // 保持 scale 为 1.0（桌面）或根据移动设备调整
        if (mobile) {
            // 移动设备可能有缩放，但默认保持 1.0
            visualViewport.scale = 1.0;
        }
        
        // 更新 offset（相对于 layout viewport）
        visualViewport.offsetLeft = 0;
        visualViewport.offsetTop = 0;
        
        // 更新 page 位置（相对于文档）
        visualViewport.pageLeft = window.scrollX || 0;
        visualViewport.pageTop = window.scrollY || 0;
    };

    // 监听窗口变化以更新 visualViewport
    if (window.addEventListener) {
        window.addEventListener('resize', window.__kaitianUpdateVisualViewport, { passive: true });
        window.addEventListener('scroll', window.__kaitianUpdateVisualViewport, { passive: true });
    }

    // 初始更新
    window.__kaitianUpdateVisualViewport();
})();
