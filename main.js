import {SUPABASE_URL, SUPABASE_ANON_KEY, BUCKETS, FILES, DASHBOARD_PASSWORD} from "./config.js";
import {
    fetchFile,
    getUserLocation,
    getVendorsWithinDistance,
    haversine,
    STRAIN_TYPE_NORMALIZATION_MAP
} from "./utils.js";
import {getBestThcPriceRatios} from "./functions/get_best_thc_price_ratios.js";
import {initUI, readFilters} from "./ui.js";
import {renderRanking} from "./renderers/ranking.js";
import {initDetailPanel, openDetailPanel} from "./renderers/detail-panel.js";

// const CORRECT_PASSWORD = DASHBOARD_PASSWORD;
//
// function initLockScreen() {
//     return new Promise(resolve => {
//         const lockScreen = document.getElementById("lock-screen");
//         const input = document.getElementById("lock-password");
//         const error = document.getElementById("lock-error");
//
//         // Check session
//         if (sessionStorage.getItem("unlocked") === "true") {
//             lockScreen.style.display = "none";
//             resolve();
//             return;
//         }
//
//         input.addEventListener("keydown", e => {
//             if (e.key !== "Enter") return;
//             if (input.value === CORRECT_PASSWORD) {
//                 sessionStorage.setItem("unlocked", "true");
//                 lockScreen.classList.add("lock-fade-out");
//                 lockScreen.addEventListener("animationend", () => {
//                     lockScreen.style.display = "none";
//                     resolve();
//                 }, { once: true });
//             } else {
//                 error.classList.remove("hidden");
//                 input.value = "";
//                 input.classList.add("border-red-400");
//                 setTimeout(() => {
//                     error.classList.add("hidden");
//                     input.classList.remove("border-red-400");
//                 }, 2000);
//             }
//         });
//     });
// }
//
// await initLockScreen();

let products = null;
let vendors = null;
let pidToVendorOffers = null;
let userLocation = null;
let reviews = null;
let precomputedBase = null;

const savedLocation = localStorage.getItem("userLocation");
if (savedLocation) {
    userLocation = JSON.parse(savedLocation);
    document.getElementById("locate-label").textContent = `${userLocation.lat.toFixed(2)}, ${userLocation.lon.toFixed(2)}`;
}

document.getElementById("locate-btn").addEventListener("click", async () => {
    try {
        userLocation = await getUserLocation();
        localStorage.setItem("userLocation", JSON.stringify(userLocation));
        document.getElementById("locate-label").textContent = `${userLocation.lat.toFixed(2)}, ${userLocation.lon.toFixed(2)}`;
    } catch (error) {
        document.getElementById("output").textContent = `Location error: ${error.message}`;
    }
});

function precompute() {
    const allVendorIds = new Set(Object.keys(vendors));
    const allStrains = new Set([
        "Indica", "Pure Indica", "Indica_dominant",
        "Sativa", "Sativa_dominant", "Hybrid"
    ]);
    const allAvailability = new Set([
        "available_immediately", "available", "limited_stock", "unavailable"
    ]);
    const allProducers = new Set(
        Object.values(products).map(p => p.producer_name).filter(Boolean)
    );
    precomputedBase = getBestThcPriceRatios(
        products, pidToVendorOffers, allVendorIds,
        allAvailability, allStrains, [1, 37], allProducers
    );
}

function applyFiltersToPrecomputed(results, filters, vendorIds) {
    return results.filter(r => {
        if (!vendorIds.has(r.vendorId) && !vendorIds.has(String(r.vendorId))) return false;
        if (!filters.availability.has(r.availability)) return false;
        const product = products[r.pid];
        if (!product) return false;
        const key = `${product.genetic}|${product.dominance}`;
        const strain = STRAIN_TYPE_NORMALIZATION_MAP[key];
        if (!filters.strainTypes.has(strain)) return false;
        if (product.thc < filters.thcRange[0] || product.thc > filters.thcRange[1]) return false;
        if (filters.producers.size > 0 && !filters.producers.has(product.producer_name)) return false;
        return true;
    });
}

function getActiveProductScope() {
    const productInput = document.getElementById("product-search");
    const query = productInput?.value.trim().toLowerCase();
    if (!query) return null;

    const matches = Object.entries(products)
        .filter(([, p]) => p.name.toLowerCase().includes(query));

    return matches.length > 0 ? new Set(matches.map(([pid]) => pid)) : new Set();
}

function getActiveVendorScope(filters) {
    const vendorInput = document.getElementById("vendor-search");
    const query = vendorInput?.value.trim().toLowerCase();

    if (query) {
        const match = Object.entries(vendors).find(
            ([, v]) => v.cannabis_pharmacy_name?.toLowerCase() === query
        );
        if (match) {
            const [id, v] = match;
            const distances = new Map();
            if (userLocation && v.latitude && v.longitude && !(v.latitude === 0 && v.longitude === 0)) {
                distances.set(id, haversine(userLocation.lon, userLocation.lat, v.longitude, v.latitude));
            }
            return { ids: new Set([id]), distances };
        }
    }

    const maxDistance = userLocation === null ? Infinity : filters.maxDistance;
    return getVendorsWithinDistance(maxDistance, vendors, userLocation);
}

function runProductBrowser(filters, pidSubset = null) {
    const {ids: filteredVendorIds, distances} = getActiveVendorScope(filters);

    let results;

    // If vendor scope changed or pidSubset active, rerun full function
    // Otherwise use pre-computed base and filter client-side
    const vendorScopeIsAll = filteredVendorIds.size === Object.keys(vendors).length;

    if (vendorScopeIsAll && !pidSubset && precomputedBase) {
        results = applyFiltersToPrecomputed(precomputedBase, filters, filteredVendorIds);
    } else {
        let filteredPidToVendorOffers = pidToVendorOffers;
        if (pidSubset) {
            filteredPidToVendorOffers = Object.fromEntries(
                Object.entries(pidToVendorOffers).filter(([pid]) => pidSubset.has(pid))
            );
        }
        results = getBestThcPriceRatios(
            products, filteredPidToVendorOffers, filteredVendorIds,
            filters.availability, filters.strainTypes,
            filters.thcRange, filters.producers,
        );
    }

    renderRanking(results, vendors, distances, reviews, products, pidToVendorOffers);
}

// --- Tabs ---
function switchTab(tab) {
    const isProducts = tab === "products";
    document.getElementById("products-sidebar-panel").classList.toggle("hidden", !isProducts);
    document.getElementById("vendors-sidebar-panel").classList.toggle("hidden", isProducts);
    document.getElementById("tab-products").className = `flex-1 text-xs py-2.5 font-medium border-b-2 transition duration-150 ${isProducts ? "border-accent text-accent" : "border-transparent text-muted hover:text-gray-300"}`;
    document.getElementById("tab-vendors").className = `flex-1 text-xs py-2.5 font-medium border-b-2 transition duration-150 ${!isProducts ? "border-accent text-accent" : "border-transparent text-muted hover:text-gray-300"}`;

    if (isProducts) {
        runProductBrowser(readFilters());
    } else {
        document.getElementById("output").innerHTML = `<p class="text-sm text-muted italic">Vendor browser coming soon.</p>`;
    }
}

// --- Search bars ---
function makeAutocomplete({ inputEl, resultsEl, onQuery, onClear, onSelect }) {
    let activeIndex = -1;

    function setActive(items, index) {
        items.forEach((item, i) => {
            item.classList.toggle("bg-surface", i === index);
        });
        activeIndex = index;
    }

    inputEl.addEventListener("input", () => {
        activeIndex = -1;
        const query = inputEl.value.trim();
        if (!query) {
            resultsEl.classList.add("hidden");
            resultsEl.innerHTML = "";
            onClear();
            return;
        }
        onQuery(query);
    });

    inputEl.addEventListener("keydown", e => {
        const items = [...resultsEl.querySelectorAll("button")];
        if (!items.length) return;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive(items, Math.min(activeIndex + 1, items.length - 1));
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive(items, Math.max(activeIndex - 1, 0));
        } else if (e.key === "Enter") {
            e.preventDefault();
            if (activeIndex >= 0) items[activeIndex].click();
        } else if (e.key === "Escape") {
            resultsEl.classList.add("hidden");
        }
    });

    // Close on outside click
    document.addEventListener("click", e => {
        if (!inputEl.contains(e.target) && !resultsEl.contains(e.target)) {
            resultsEl.classList.add("hidden");
        }
    });
}

function initSearchBars() {
    const bar = document.getElementById("search-bar");
    bar.innerHTML = `
        <div class="relative flex-1">
            <input type="text" id="product-search" placeholder="🔍 Search products..."
                class="w-full bg-surface border border-border rounded text-xs px-3 py-1.5 focus:outline-none focus:border-accent text-gray-300">
            <div id="product-search-results"
                class="absolute z-30 top-full mt-1 w-full bg-panel border border-border rounded shadow-lg flex flex-col max-h-48 overflow-y-auto hidden">
            </div>
        </div>
        <div class="relative flex-1">
            <input type="text" id="vendor-search" placeholder="🔍 Search vendors..."
                class="w-full bg-surface border border-border rounded text-xs px-3 py-1.5 focus:outline-none focus:border-accent text-gray-300">
            <div id="vendor-search-results"
                class="absolute z-30 top-full mt-1 w-full bg-panel border border-border rounded shadow-lg flex flex-col max-h-48 overflow-y-auto hidden">
            </div>
        </div>
    `;

    const productInput = document.getElementById("product-search");
    const productResults = document.getElementById("product-search-results");
    const vendorInput = document.getElementById("vendor-search");
    const vendorResults = document.getElementById("vendor-search-results");

    // --- Product search ---
    makeAutocomplete({
        inputEl: productInput,
        resultsEl: productResults,
        onClear: () => runProductBrowser(readFilters()),
        onQuery: (query) => {
            const matches = Object.entries(products)
                .filter(([, p]) => p.name.toLowerCase().includes(query.toLowerCase()))
                .slice(0, 8);

            productResults.innerHTML = "";
            if (matches.length === 0) {
                productResults.innerHTML = `<p class="text-xs text-muted px-3 py-2 italic">No products found.</p>`;
                productResults.classList.remove("hidden");
                // Still filter the grid with no matches
                runProductBrowser(readFilters(), new Set());
                return;
            }

            // Filter grid immediately as user types
            const pidSubset = new Set(matches.map(([pid]) => pid));
            runProductBrowser(readFilters(), pidSubset);

            for (const [pid, p] of matches) {
                const btn = document.createElement("button");
                btn.textContent = p.name;
                btn.className = "text-left text-xs px-3 py-2 hover:bg-surface text-gray-300 border-b border-border last:border-0 transition duration-100";
                btn.addEventListener("click", () => {
                    productInput.value = p.name;
                    productResults.classList.add("hidden");
                    // Open detail panel for this product
                    const offers = pidToVendorOffers[pid] ?? [];
                    const bestOffer = offers[0];
                    if (bestOffer) {
                        const result = {
                            pid,
                            name: p.name,
                            thc: p.thc,
                            price: bestOffer.price,
                            ratio: p.thc / bestOffer.price,
                            url: p.url,
                            vendorId: String(bestOffer.vendor_id),
                            availability: bestOffer.availability,
                        };
                        openDetailPanel(result, reviews, pidToVendorOffers, vendors, products);
                    }
                });
                productResults.appendChild(btn);
            }
            productResults.classList.remove("hidden");
        },
        onSelect: () => {},
    });

    // --- Vendor search ---
    makeAutocomplete({
        inputEl: vendorInput,
        resultsEl: vendorResults,
        onClear: () => runProductBrowser(readFilters()),
        onQuery: (query) => {
            const matches = Object.entries(vendors)
                .filter(([, v]) => v.cannabis_pharmacy_name?.toLowerCase().includes(query.toLowerCase()))
                .slice(0, 8);

            vendorResults.innerHTML = "";
            if (matches.length === 0) {
                vendorResults.innerHTML = `<p class="text-xs text-muted px-3 py-2 italic">No vendors found.</p>`;
                vendorResults.classList.remove("hidden");
                return;
            }

            for (const [id, v] of matches) {
                const btn = document.createElement("button");
                btn.textContent = v.cannabis_pharmacy_name;
                btn.className = "text-left text-xs px-3 py-2 hover:bg-surface text-gray-300 border-b border-border last:border-0 transition duration-100";
                btn.addEventListener("click", () => {
                    vendorInput.value = v.cannabis_pharmacy_name;
                    vendorResults.classList.add("hidden");

                    const vendorIdSet = new Set([id]);
                    const distances = new Map();
                    if (userLocation && v.latitude && v.longitude && !(v.latitude === 0 && v.longitude === 0)) {
                        const dist = haversine(userLocation.lon, userLocation.lat, v.longitude, v.latitude);
                        distances.set(id, dist);
                    }

                    const filters = readFilters();
                    const results = getBestThcPriceRatios(
                        products, pidToVendorOffers, vendorIdSet,
                        filters.availability, filters.strainTypes,
                        filters.thcRange, filters.producers,
                    );
                    renderRanking(results, vendors, distances, reviews, products, pidToVendorOffers);
                });
                vendorResults.appendChild(btn);
            }
            vendorResults.classList.remove("hidden");
        },
        onSelect: () => {},
    });
}

try {
    products = await fetchFile(BUCKETS.products, FILES.products);
    vendors = await fetchFile(BUCKETS.vendors, FILES.vendors);
    pidToVendorOffers = await fetchFile(BUCKETS.inventories, FILES.pidToVendors);
    reviews = await fetchFile(BUCKETS.pidToReviews, FILES.pidToReviews);

    precompute();

    initUI(products, (filters) => {
        runProductBrowser(filters);
    }, (fnKey, filters) => {
        switch (fnKey) {
            default:
                document.getElementById("output").textContent = `${fnKey} is not yet implemented.`;
        }
    });

    document.getElementById("reset-filters-btn").addEventListener("click", () => {
        document.getElementById("product-search").value = "";
        document.getElementById("vendor-search").value = "";
    });

    initDetailPanel();
    initSearchBars();

    document.getElementById("tab-products").addEventListener("click", () => switchTab("products"));
    document.getElementById("tab-vendors").addEventListener("click", () => switchTab("vendors"));

    runProductBrowser(readFilters());
} catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
}
