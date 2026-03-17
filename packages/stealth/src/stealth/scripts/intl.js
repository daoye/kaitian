/**
 * Intl 补丁
 * 
 * 模拟 Intl API（Internationalization API），提供与设备画像一致的本地化设置。
 */
(function() {
    'use strict';

    const profile = window.__kaitianDeviceProfile || {};
    const locale = profile.locale || 'zh-CN';
    const timezone = profile.timezone || 'Asia/Shanghai';
    const languages = profile.languages || [locale, locale.split('-')[0]];

    // 保存原始 Intl（如果存在）
    const OriginalIntl = window.Intl;

    // 创建统一的 resolvedOptions 返回值
    function createResolvedOptions(baseOptions) {
        return Object.assign({}, baseOptions, {
            locale: baseOptions.locale || locale,
            numberingSystem: baseOptions.numberingSystem || 'latn',
        });
    }

    // 修补 DateTimeFormat
    if (OriginalIntl.DateTimeFormat) {
        const OriginalDateTimeFormat = OriginalIntl.DateTimeFormat;
        
        OriginalIntl.DateTimeFormat = function(locales, options) {
            const fmt = new OriginalDateTimeFormat(locales || languages, options);
            
            // 覆盖 resolvedOptions
            const originalResolvedOptions = fmt.resolvedOptions.bind(fmt);
            fmt.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.timeZone = timezone;
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return fmt;
        };
        
        OriginalIntl.DateTimeFormat.supportedLocalesOf = OriginalDateTimeFormat.supportedLocalesOf;
        OriginalIntl.DateTimeFormat.prototype = OriginalDateTimeFormat.prototype;
    }

    // 修补 NumberFormat
    if (OriginalIntl.NumberFormat) {
        const OriginalNumberFormat = OriginalIntl.NumberFormat;
        
        OriginalIntl.NumberFormat = function(locales, options) {
            const fmt = new OriginalNumberFormat(locales || languages, options);
            
            const originalResolvedOptions = fmt.resolvedOptions.bind(fmt);
            fmt.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return fmt;
        };
        
        OriginalIntl.NumberFormat.supportedLocalesOf = OriginalNumberFormat.supportedLocalesOf;
        OriginalIntl.NumberFormat.prototype = OriginalNumberFormat.prototype;
    }

    // 修补 Collator
    if (OriginalIntl.Collator) {
        const OriginalCollator = OriginalIntl.Collator;
        
        OriginalIntl.Collator = function(locales, options) {
            const collator = new OriginalCollator(locales || languages, options);
            
            const originalResolvedOptions = collator.resolvedOptions.bind(collator);
            collator.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return collator;
        };
        
        OriginalIntl.Collator.supportedLocalesOf = OriginalCollator.supportedLocalesOf;
        OriginalIntl.Collator.prototype = OriginalCollator.prototype;
    }

    // 修补 ListFormat（如果支持）
    if (OriginalIntl.ListFormat) {
        const OriginalListFormat = OriginalIntl.ListFormat;
        
        OriginalIntl.ListFormat = function(locales, options) {
            const fmt = new OriginalListFormat(locales || languages, options);
            
            const originalResolvedOptions = fmt.resolvedOptions.bind(fmt);
            fmt.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return fmt;
        };
        
        OriginalIntl.ListFormat.supportedLocalesOf = OriginalListFormat.supportedLocalesOf;
        OriginalIntl.ListFormat.prototype = OriginalListFormat.prototype;
    }

    // 修补 RelativeTimeFormat（如果支持）
    if (OriginalIntl.RelativeTimeFormat) {
        const OriginalRelativeTimeFormat = OriginalIntl.RelativeTimeFormat;
        
        OriginalIntl.RelativeTimeFormat = function(locales, options) {
            const fmt = new OriginalRelativeTimeFormat(locales || languages, options);
            
            const originalResolvedOptions = fmt.resolvedOptions.bind(fmt);
            fmt.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return fmt;
        };
        
        OriginalIntl.RelativeTimeFormat.supportedLocalesOf = OriginalRelativeTimeFormat.supportedLocalesOf;
        OriginalIntl.RelativeTimeFormat.prototype = OriginalRelativeTimeFormat.prototype;
    }

    // 修补 DisplayNames（如果支持）
    if (OriginalIntl.DisplayNames) {
        const OriginalDisplayNames = OriginalIntl.DisplayNames;
        
        OriginalIntl.DisplayNames = function(locales, options) {
            const dn = new OriginalDisplayNames(locales || languages, options);
            
            const originalResolvedOptions = dn.resolvedOptions.bind(dn);
            dn.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return dn;
        };
        
        OriginalIntl.DisplayNames.supportedLocalesOf = OriginalDisplayNames.supportedLocalesOf;
        OriginalIntl.DisplayNames.prototype = OriginalDisplayNames.prototype;
    }

    // 修补 PluralRules
    if (OriginalIntl.PluralRules) {
        const OriginalPluralRules = OriginalIntl.PluralRules;
        
        OriginalIntl.PluralRules = function(locales, options) {
            const pr = new OriginalPluralRules(locales || languages, options);
            
            const originalResolvedOptions = pr.resolvedOptions.bind(pr);
            pr.resolvedOptions = function() {
                const resolved = originalResolvedOptions();
                resolved.locale = resolved.locale || locale;
                return resolved;
            };
            
            return pr;
        };
        
        OriginalIntl.PluralRules.supportedLocalesOf = OriginalPluralRules.supportedLocalesOf;
        OriginalIntl.PluralRules.prototype = OriginalPluralRules.prototype;
    }
})();
