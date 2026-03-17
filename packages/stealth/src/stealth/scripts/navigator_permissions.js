const originalQuery = navigator.permissions && navigator.permissions.query
    ? navigator.permissions.query.bind(navigator.permissions)
    : null;

if (originalQuery) {
    navigator.permissions.query = async (parameters) => {
        if (parameters && parameters.name === 'notifications') {
            return { state: Notification.permission };
        }
        return originalQuery(parameters);
    };
}
