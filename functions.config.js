export const FILTER_DEFAULTS = {
    maxDistance: Infinity,
    availability: new Set(["available_immediately", "available", "limited_stock"]),
    strainTypes: new Set(["Indica", "Sativa", "Hybrid", "Indica_dominant", "Sativa_dominant", "Pure Indica"]),
    thcRange: [1, 37],
    priceRange: [1, 30],
    producers: "all",
    timeRange: "1M",
    pid: null,
};

export const FUNCTIONS = {
    getMostInDemand: {
        label: "Most In Demand",
        filters: ["maxDistance", "strainTypes", "thcRange", "producer", "priceRange"],
    },
    getLeastInDemand: {
        label: "Least In Demand",
        filters: ["maxDistance", "strainTypes", "thcRange", "producer", "priceRange"],
    },
    getMostVolatilePricing: {
        label: "Most Volatile Pricing",
        filters: ["maxDistance", "strainTypes", "thcRange", "producer", "priceRange"],
    },
    getMostStablePricing: {
        label: "Most Stable Pricing",
        filters: ["maxDistance", "strainTypes", "thcRange", "producer", "priceRange"],
    },
    getAveragePriceHistory: {
        label: "Average Price History",
        filters: ["maxDistance", "strainTypes", "thcRange", "producer", "timeRange", "pid"],
    },
    getAverageAvailabilityHistory: {
        label: "Average Availability History",
        filters: ["maxDistance", "strainTypes", "thcRange", "producer", "timeRange", "pid"],
    },
};
export const BROWSER_FILTERS = ["maxDistance", "availability", "strainTypes", "thcRange", "producer"];
