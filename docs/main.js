import {SUPABASE_URL, SUPABASE_ANON_KEY, BUCKETS, FILES} from "./config.js";
import {
    fetchFile,
    haversine,
    getUserLocation,
    STRAIN_TYPE_NORMALIZATION_MAP,
    getVendorsWithinDistance
} from "./utils.js";
import {getBestThcPriceRatios} from "./functions/get_best_thc_price_ratios.js";

let products = null;
let vendors = null;
let inventories = null;
let pidToVendors = null;
let userLocation = null;

document.getElementById("locate-btn").addEventListener("click", async () => {
    try {
        userLocation = await getUserLocation();
        document.getElementById("output").textContent = `Location saved: ${userLocation.lat}, ${userLocation.lon}`;
    } catch (error) {
        document.getElementById("output").textContent = `Location error: ${error.message}`;
    }
});


try {
    products = await fetchFile(BUCKETS.products, FILES.products)
    vendors = await fetchFile(BUCKETS.vendors, FILES.vendors)
    inventories = await fetchFile(BUCKETS.inventories, FILES.inventories)
    pidToVendors = await fetchFile(BUCKETS.inventories, FILES.pidToVendors)

    document.getElementById("output").textContent = JSON.stringify({
        productCount: Object.keys(products).length,
        vendorCount: Object.keys(vendors).length,
        inventoryCount: Object.keys(inventories).length,
    }, null, 2);
} catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
}

const DEFAULT_FILTERS = {
    maxDistance: Infinity,
    availability: new Set(["available_immediately", "available", "limited_stock"]),
    strainTypes: new Set(["Indica", "Sativa", "Hybrid", "Indica_dominant", "Sativa_dominant", "Pure Indica"]),
    productCount: 10
};

document.getElementById("get-best-thc-price-ratios-btn").addEventListener("click", async () => {
    // const filters = getFilters();
    // const maxDistance = userLocation === null ? Infinity : filters.maxDistnace
    const filteredVendorIds = getVendorsWithinDistance(DEFAULT_FILTERS.maxDistance, vendors, userLocation)
    const results = getBestThcPriceRatios(products, pidToVendors, filteredVendorIds, DEFAULT_FILTERS.availability, DEFAULT_FILTERS.strainTypes, DEFAULT_FILTERS.productCount)
    document.getElementById("output").textContent = JSON.stringify(results, null, 2)
})
