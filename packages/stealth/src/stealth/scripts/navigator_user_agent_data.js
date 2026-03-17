const uaDataBrands = {{BRANDS_JSON}};
const uaDataMobile = {{MOBILE_BOOL}};
const uaDataPlatform = '{{PLATFORM}}';

const uaData = {
    brands: uaDataBrands,
    mobile: uaDataMobile,
    platform: uaDataPlatform,
    getHighEntropyValues: async (hints) => {
        const response = {
            architecture: '{{ARCHITECTURE}}',
            bitness: '{{BITNESS}}',
            model: '{{MODEL}}',
            platform: uaDataPlatform,
            platformVersion: '{{PLATFORM_VERSION}}',
            uaFullVersion: '{{UA_FULL_VERSION}}',
            fullVersionList: uaDataBrands,
            wow64: false,
        };

        if (!Array.isArray(hints)) {
            return response;
        }

        return hints.reduce((acc, hint) => {
            if (Object.prototype.hasOwnProperty.call(response, hint)) {
                acc[hint] = response[hint];
            }
            return acc;
        }, {});
    },
    toJSON: () => ({
        brands: uaDataBrands,
        mobile: uaDataMobile,
        platform: uaDataPlatform,
    }),
};

Object.defineProperty(navigator, 'userAgentData', {
    get: () => uaData,
});
