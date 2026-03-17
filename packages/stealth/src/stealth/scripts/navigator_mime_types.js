/**
 * Navigator.mimeTypes 与 plugins 联动补丁
 * 
 * 创建真实的 MimeTypeArray 和 PluginArray，并确保它们双向关联。
 * 这是应对浏览器特征检测的关键补丁。
 */
(function() {
    'use strict';

    const profile = window.__kaitianDeviceProfile || {};
    
    // MIME 类型定义
    const mimeTypeData = [
        { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', pluginName: 'Chrome PDF Plugin' },
        { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', pluginName: 'Chrome PDF Plugin' },
        { type: 'application/x-nacl', suffixes: '', description: 'Native Client module', pluginName: 'Native Client' },
        { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client module', pluginName: 'Native Client' },
        { type: 'application/octet-stream', suffixes: '', description: 'Binary data', pluginName: 'Native Client' },
    ];

    // 插件定义
    const pluginData = [
        {
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
            description: 'Portable Document Format',
            version: undefined,
            itemTypes: ['application/pdf', 'application/x-google-chrome-pdf'],
        },
        {
            name: 'Native Client',
            filename: 'native-client.nmf',
            description: 'Native Client module',
            version: undefined,
            itemTypes: ['application/x-nacl', 'application/x-pnacl', 'application/octet-stream'],
        },
    ];

    // 创建 MimeType 对象
    function createMimeType(mimeData, plugin) {
        const mimeType = {
            type: mimeData.type,
            suffixes: mimeData.suffixes,
            description: mimeData.description,
            enabledPlugin: plugin,
        };
        return mimeType;
    }

    // 创建 Plugin 对象
    function createPlugin(pluginInfo, mimeTypes) {
        const plugin = {
            name: pluginInfo.name,
            filename: pluginInfo.filename,
            description: pluginInfo.description,
            version: pluginInfo.version,
            length: mimeTypes.length,
            item: function(index) {
                return mimeTypes[index] || null;
            },
            namedItem: function(name) {
                for (let i = 0; i < mimeTypes.length; i++) {
                    if (mimeTypes[i].type === name) {
                        return mimeTypes[i];
                    }
                }
                return null;
            },
        };
        
        // 将 mimeTypes 添加到 plugin 对象
        for (let i = 0; i < mimeTypes.length; i++) {
            plugin[i] = mimeTypes[i];
        }
        
        return plugin;
    }

    // 创建 MimeTypeArray
    const mimeTypeObjects = [];
    const pluginObjects = [];
    
    // 先创建插件（用于关联）
    pluginData.forEach(pluginInfo => {
        const pluginMimeTypes = [];
        pluginInfo.itemTypes.forEach(type => {
            const mimeData = mimeTypeData.find(m => m.type === type);
            if (mimeData) {
                const mimeType = createMimeType(mimeData, null);
                mimeTypeObjects.push({ mimeType, pluginInfo });
                pluginMimeTypes.push(mimeType);
            }
        });
        const plugin = createPlugin(pluginInfo, pluginMimeTypes);
        pluginObjects.push(plugin);
    });
    
    // 更新 MimeType 的 enabledPlugin 引用
    mimeTypeObjects.forEach(({ mimeType }, index) => {
        const plugin = pluginObjects.find(p => 
            pluginData.find(pi => pi.name === p.name)?.itemTypes.includes(mimeType.type)
        );
        if (plugin) {
            mimeTypeObjects[index].mimeType.enabledPlugin = plugin;
        }
    });

    // 构建最终的 MimeTypeArray
    const finalMimeTypes = mimeTypeObjects.map(({ mimeType }) => mimeType);
    
    const mimeTypeArray = {
        length: finalMimeTypes.length,
        item: function(index) {
            return finalMimeTypes[index] || null;
        },
        namedItem: function(name) {
            for (let i = 0; i < finalMimeTypes.length; i++) {
                if (finalMimeTypes[i].type === name) {
                    return finalMimeTypes[i];
                }
            }
            return null;
        },
    };
    
    // 将 mimeTypes 添加到数组
    for (let i = 0; i < finalMimeTypes.length; i++) {
        mimeTypeArray[i] = finalMimeTypes[i];
    }

    // 构建 PluginArray
    const pluginArray = {
        length: pluginObjects.length,
        item: function(index) {
            return pluginObjects[index] || null;
        },
        namedItem: function(name) {
            for (let i = 0; i < pluginObjects.length; i++) {
                if (pluginObjects[i].name === name) {
                    return pluginObjects[i];
                }
            }
            return null;
        },
        refresh: function() {
            // 空实现，兼容旧版浏览器
        },
    };
    
    // 将 plugins 添加到数组
    for (let i = 0; i < pluginObjects.length; i++) {
        pluginArray[i] = pluginObjects[i];
    }

    // 设置原型，使 instanceof 检查更真实
    Object.setPrototypeOf(mimeTypeArray, MimeTypeArray.prototype);
    Object.setPrototypeOf(pluginArray, PluginArray.prototype);

    // 注入 navigator.mimeTypes
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => mimeTypeArray,
        configurable: true,
        enumerable: true,
    });

    // 注入 navigator.plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => pluginArray,
        configurable: true,
        enumerable: true,
    });
})();
