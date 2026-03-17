/**
 * 修改 WebGL 指纹
 * 覆盖 vendor 和 renderer 信息
 */
const WEBGL_VENDOR = 37445;
const WEBGL_RENDERER = 37446;

const patchGetParameter = (proto) => {
    if (!proto || typeof proto.getParameter !== 'function') {
        return;
    }
    const originalGetParameter = proto.getParameter;
    proto.getParameter = function (parameter) {
        if (parameter === WEBGL_VENDOR) {
            return '{{VENDOR}}';
        }
        if (parameter === WEBGL_RENDERER) {
            return '{{RENDERER}}';
        }
        return originalGetParameter.call(this, parameter);
    };
};

patchGetParameter(WebGLRenderingContext && WebGLRenderingContext.prototype);
patchGetParameter(WebGL2RenderingContext && WebGL2RenderingContext.prototype);
