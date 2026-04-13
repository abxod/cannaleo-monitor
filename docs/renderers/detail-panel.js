import {buildStars, highlightCard, clearCardHighlight} from "./ranking.js";
import {SUPABASE_ANON_KEY, SUPABASE_URL} from "../config.js";

let currentPid = null;

const AVAILABILITY_LABELS = {
    available_immediately: "Immediately available",
    available: "Available",
    limited_stock: "Limited stock",
    unavailable: "Unavailable"
};

const COUNTRY_FLAGS = {
    "Deutschland": "🇩🇪",
    "Portugal": "🇵🇹",
    "portugal": "🇵🇹",
    "Portugal ": "🇵🇹",
    "Niederlande": "🇳🇱",
    "Spanien": "🇪🇸",
    "Spain": "🇪🇸",
    "Schweiz": "🇨🇭",
    "Dänemark": "🇩🇰",
    "DÃ¤nemark": "🇩🇰",
    "Tschechien": "🇨🇿",
    "Kanada": "🇨🇦",
    "Kanda": "🇨🇦",
    "Kolumbien": "🇨🇴",
    "Nordmazedonien": "🇲🇰",
    "Nord Mazedonien": "🇲🇰",
    "Mazedonien": "🇲🇰",
    "Israel": "🇮🇱",
    "Australien": "🇦🇺",
    "Neuseeland": "🇳🇿",
    "Chile": "🇨🇱",
    "Argentinien": "🇦🇷",
    "Uruguay": "🇺🇾",
    "Südafrika": "🇿🇦",
    "SÃ¼dafrika": "🇿🇦",
    "Süd Afrika": "🇿🇦",
    "SÃ¼d Afrika": "🇿🇦",
    "Zimbabwe": "🇿🇼",
    "Simbabwe": "🇿🇼",
    "Uganda": "🇺🇬",
    "Lesotho": "🇱🇸",
    "Griechenland": "🇬🇷",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Kanalinseln": "🇬🇧",
    "Jersey": "🇯🇪",
};

const STATE_TO_VENDOR_IDS = {
    "Baden-Württemberg": [8, 68, 74, 110, 129, 132, 135, 149, 151, 160, 184, 189, 202, 207, 212, 228, 229, 236, 243, 258, 277, 294, 299, 311, 312, 317, 318, 350, 363, 399, 417, 426, 438, 440, 441, 442, 452, 464, 466, 512],
    "Bavaria": [35, 37, 52, 53, 60, 79, 88, 91, 101, 102, 118, 131, 141, 145, 153, 156, 159, 179, 194, 209, 225, 230, 237, 247, 249, 254, 256, 270, 274, 302, 326, 330, 389, 393, 402, 432, 453, 478, 479, 481, 495],
    "Berlin": [133, 170, 178, 186, 242, 322, 323, 348, 375, 386, 419, 420, 445, 446],
    "Brandenburg": [281, 355, 427, 431],
    "Bremen": [412, 449],
    "Hamburg": [57, 85, 116, 211, 295, 306, 354, 407, 414, 450, 485, 486],
    "Hesse": [23, 54, 106, 144, 146, 155, 157, 162, 180, 192, 193, 235, 276, 291, 307, 320, 321, 329, 335, 361, 366, 376, 388, 391, 395, 396, 406, 433, 443, 465, 488, 502, 507],
    "Lower Saxony": [59, 120, 268, 297, 331, 383, 475],
    "Mecklenburg-Vorpommern": [214, 336, 492],
    "North Rhine-Westphalia": [33, 39, 56, 69, 70, 73, 76, 78, 80, 94, 100, 108, 115, 119, 122, 127, 134, 139, 166, 169, 175, 177, 181, 187, 191, 204, 215, 223, 224, 238, 244, 245, 248, 252, 255, 278, 282, 283, 285, 286, 290, 298, 303, 304, 333, 351, 356, 360, 362, 374, 385, 387, 400, 413, 415, 416, 418, 430, 454, 476, 477, 483, 484, 504, 510],
    "Rhineland-Palatinate": [182, 188, 195, 198, 233, 234, 251, 305, 358, 403, 405, 434, 435, 436, 467],
    "Saarland": [183, 411, 487],
    "Saxony": [344],
    "Saxony-Anhalt": [250, 332, 421, 473],
    "Schleswig-Holstein": [216, 222, 279, 373, 470, 471, 493],
    "Thuringia": [158, 280, 408, 480, 499],
};

const ALL_VENDOR_IDS = [...new Set(Object.values(STATE_TO_VENDOR_IDS).flat())];

const TIME_RANGE_DAYS = {
    "7D": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "Max": null,
};

const VALID_AVAILABILITY = new Set(["available_immediately", "available", "limited_stock"]);
const PRICE_UPPER_BOUND = 30;

let currentChart = null;
let currentGraphPid = null;
let currentGraphVendorIds = null;
let currentTimeRange = "1M";

// Vendor selector state
let allVendorsChecked = false;
let selectedStateIds = new Set();   // vendor IDs from selected states
let selectedIndividualIds = new Set(); // vendor IDs from individual search

function renderEmptyState() {
    document.getElementById("detail-title").textContent = "";
    document.getElementById("detail-close").style.display = "none";

    const imageEl = document.getElementById("detail-image");
    imageEl.querySelector("img").style.display = "none";
    imageEl.querySelector(".img-fallback").style.display = "flex";

    document.getElementById("detail-rating").innerHTML = "";

    document.getElementById("detail-scrollable").innerHTML = `
        <div class="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 text-border" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-sm text-muted">Select a product to view details</p>
        </div>
    `;
}

function getEffectiveVendorIds() {
    if (allVendorsChecked) return ALL_VENDOR_IDS;
    return [...new Set([...selectedStateIds, ...selectedIndividualIds])];
}

async function fetchPriceHistory(pid, vendorIds, timeRange) {
    const days = TIME_RANGE_DAYS[timeRange];
    const fromDate = days
        ? new Date(Date.now() - days * 86400000).toISOString().split("T")[0]
        : "2000-01-01";

    let vendorParam;
    if (vendorIds.length === 1) {
        vendorParam = `vendor_id=eq.${vendorIds[0]}`;
    } else {
        vendorParam = `or=(${vendorIds.map(id => `vendor_id.eq.${id}`).join(",")})`;
    }

    const url = `${SUPABASE_URL}/rest/v1/inventory_snapshots?pid=eq.${pid}&${vendorParam}&fetched_at=gte.${fromDate}&select=fetched_at,price,availability&order=fetched_at.asc`;

    const response = await fetch(url, {
        headers: {
            "Authorization": `Bearer ${SUPABASE_ANON_KEY}`,
            "apikey": SUPABASE_ANON_KEY
        }
    });

    if (!response.ok) throw new Error(`Failed to fetch price history: ${response.status}`);
    return response.json();
}

function aggregateByDate(rows) {
    const byDate = {};
    for (const row of rows) {
        if (!VALID_AVAILABILITY.has(row.availability)) continue;
        if (row.price > PRICE_UPPER_BOUND) continue;
        const date = row.fetched_at.slice(0, 10);
        if (!byDate[date]) byDate[date] = [];
        byDate[date].push(row.price);
    }
    return Object.entries(byDate)
        .map(([date, prices]) => ({
            date,
            avg: prices.reduce((a, b) => a + b, 0) / prices.length
        }))
        .sort((a, b) => a.date.localeCompare(b.date));
}

function renderChart(dataPoints) {
    const container = document.getElementById("price-chart-container");

    if (currentChart) {
        currentChart.destroy();
        currentChart = null;
    }

    if (dataPoints.length === 0) {
        container.innerHTML = `<p class="text-xs text-muted italic text-center py-8">No price data available.</p>`;
        return;
    }

    const avg = dataPoints.reduce((a, b) => a + b.avg, 0) / dataPoints.length;

    container.innerHTML = `
        <div class="flex justify-between items-center mb-2">
            <span class="text-xs text-muted">Period average</span>
            <span class="text-sm font-semibold text-accent">€${avg.toFixed(2)}</span>
        </div>
        <canvas id="price-chart"></canvas>
    `;

    const ctx = document.getElementById("price-chart").getContext("2d");

    currentChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: dataPoints.map(d => d.date),
            datasets: [{
                label: "Avg Price (€)",
                data: dataPoints.map(d => d.avg),
                borderColor: "#818cf8",
                backgroundColor: "rgba(129, 140, 248, 0.1)",
                pointBackgroundColor: "#818cf8",
                borderWidth: 2,
                pointRadius: 3,
                tension: 0.3,
                cubicInterpolationMode: "monotone",
                fill: true,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {display: false},
                tooltip: {
                    callbacks: {
                        label: ctx => `€${ctx.parsed.y.toFixed(2)}`
                    }
                }
            },
            scales: {
                x: {
                    ticks: {color: "#6b7280", maxTicksLimit: 6, font: {size: 10}},
                    grid: {color: "#374151"}
                },
                y: {
                    ticks: {
                        color: "#6b7280",
                        font: {size: 10},
                        callback: val => `€${val.toFixed(2)}`
                    },
                    grid: {color: "#374151"}
                }
            }
        }
    });
}

async function refreshGraph() {
    const container = document.getElementById("price-chart-container");
    container.innerHTML = `<p class="text-xs text-muted italic text-center py-8">Loading...</p>`;

    const vendorIds = getEffectiveVendorIds();
    if (vendorIds.length === 0) {
        container.innerHTML = `<p class="text-xs text-muted italic text-center py-8">No vendors selected.</p>`;
        return;
    }

    currentGraphVendorIds = vendorIds;

    try {
        const rows = await fetchPriceHistory(currentGraphPid, currentGraphVendorIds, currentTimeRange);
        const dataPoints = aggregateByDate(rows);
        renderChart(dataPoints);
    } catch (e) {
        console.error(e);
        container.innerHTML = `<p class="text-xs text-muted italic text-center py-8">Failed to load price history.</p>`;
    }
}

function buildGraphSection(pid, defaultVendorId, vendors) {
    currentGraphPid = pid;
    currentTimeRange = "1M";
    allVendorsChecked = false;
    selectedStateIds = new Set();
    selectedIndividualIds = new Set([parseInt(defaultVendorId)]);

    const defaultVendorName = vendors[String(defaultVendorId)]?.cannabis_pharmacy_name ?? String(defaultVendorId);

    const wrap = document.createElement("div");
    wrap.className = "p-4 border-b border-border";
    wrap.innerHTML = `
        <p class="text-xs text-muted uppercase tracking-wider mb-3">Price History</p>

        <!-- All vendors checkbox -->
        <label class="flex items-center gap-2 text-xs cursor-pointer mb-3">
            <input type="checkbox" id="graph-all-vendors-cb">
            <span class="text-gray-300">All vendors</span>
        </label>

        <!-- State multi-select -->
        <div id="graph-state-section" class="mb-2">
            <p class="text-xs text-muted mb-1">States</p>
            <div id="graph-state-pills" class="flex flex-wrap gap-1 mb-1"></div>
            <select id="graph-state-select" class="w-full bg-surface border border-border rounded text-xs px-2 py-1 text-gray-300 focus:outline-none focus:border-accent">
                <option value="">Add a state...</option>
                ${Object.keys(STATE_TO_VENDOR_IDS).map(state => `
                    <option value="${state}">${state}</option>
                `).join("")}
            </select>
        </div>

        <!-- Individual vendor search -->
        <div id="graph-vendor-section" class="mb-3">
            <p class="text-xs text-muted mb-1">Specific vendors</p>
            <div id="graph-vendor-pills" class="flex flex-wrap gap-1 mb-1"></div>
            <input type="text" id="graph-vendor-search" placeholder="Search by name..."
                class="w-full bg-surface border border-border rounded text-xs px-2 py-1.5 focus:outline-none focus:border-accent">
            <div id="graph-vendor-results" class="mt-1 flex flex-col gap-0.5 max-h-28 overflow-y-auto"></div>
        </div>

        <!-- Time range -->
        <div class="flex gap-1.5 flex-wrap mb-3">
            ${Object.keys(TIME_RANGE_DAYS).map(t => `
                <button data-range="${t}" class="graph-time-btn text-xs px-2 py-1 rounded border ${t === "1M" ? "border-accent text-accent" : "border-border text-muted"} hover:border-accent transition duration-100">
                    ${t}
                </button>
            `).join("")}
        </div>

        <!-- Chart -->
        <div id="price-chart-container" class="w-full">
            <p class="text-xs text-muted italic text-center py-8">Loading...</p>
        </div>
    `;

    // Helper: render state pills
    function renderStatePills() {
        const pillsContainer = wrap.querySelector("#graph-state-pills");
        pillsContainer.innerHTML = "";
        for (const state of selectedStates) {
            const pill = document.createElement("span");
            pill.className = "flex items-center gap-1 text-xs bg-surface border border-border rounded px-2 py-0.5 text-gray-300";
            pill.innerHTML = `${state} <button class="text-muted hover:text-gray-100 leading-none" data-state="${state}">✕</button>`;
            pill.querySelector("button").addEventListener("click", () => {
                selectedStates.delete(state);
                const ids = STATE_TO_VENDOR_IDS[state];
                ids.forEach(id => selectedStateIds.delete(id));
                renderStatePills();
                refreshGraph();
            });
            pillsContainer.appendChild(pill);
        }
    }

    // Helper: render vendor pills
    function renderVendorPills() {
        const pillsContainer = wrap.querySelector("#graph-vendor-pills");
        pillsContainer.innerHTML = "";
        for (const [id, name] of selectedVendors) {
            const pill = document.createElement("span");
            pill.className = "flex items-center gap-1 text-xs bg-surface border border-border rounded px-2 py-0.5 text-gray-300";
            pill.innerHTML = `${name} <button class="text-muted hover:text-gray-100 leading-none" data-id="${id}">✕</button>`;
            pill.querySelector("button").addEventListener("click", () => {
                selectedVendors.delete(id);
                selectedIndividualIds.delete(id);
                renderVendorPills();
                refreshGraph();
            });
            pillsContainer.appendChild(pill);
        }
    }

    // Local state for this panel instance
    const selectedStates = new Set();
    const selectedVendors = new Map(); // id → name

    // Pre-populate with default vendor
    selectedVendors.set(parseInt(defaultVendorId), defaultVendorName);
    renderVendorPills();

    // All vendors checkbox
    wrap.querySelector("#graph-all-vendors-cb").addEventListener("change", e => {
        allVendorsChecked = e.target.checked;
        const stateSection = wrap.querySelector("#graph-state-section");
        const vendorSection = wrap.querySelector("#graph-vendor-section");
        stateSection.style.opacity = allVendorsChecked ? "0.4" : "1";
        stateSection.style.pointerEvents = allVendorsChecked ? "none" : "auto";
        vendorSection.style.opacity = allVendorsChecked ? "0.4" : "1";
        vendorSection.style.pointerEvents = allVendorsChecked ? "none" : "auto";
        refreshGraph();
    });

    // State select
    wrap.querySelector("#graph-state-select").addEventListener("change", e => {
        const state = e.target.value;
        if (!state || selectedStates.has(state)) {
            e.target.value = "";
            return;
        }
        selectedStates.add(state);
        STATE_TO_VENDOR_IDS[state].forEach(id => selectedStateIds.add(id));
        renderStatePills();
        e.target.value = "";
        refreshGraph();
    });

    // Vendor search autocomplete
    const searchInput = wrap.querySelector("#graph-vendor-search");
    const searchResults = wrap.querySelector("#graph-vendor-results");

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.toLowerCase().trim();
        searchResults.innerHTML = "";
        if (!query) return;

        const matches = Object.entries(vendors)
            .filter(([, v]) => v.cannabis_pharmacy_name?.toLowerCase().includes(query))
            .slice(0, 8);

        for (const [id, v] of matches) {
            const btn = document.createElement("button");
            btn.textContent = v.cannabis_pharmacy_name;
            btn.className = "text-left text-xs px-2 py-1 rounded hover:bg-surface text-gray-300";
            btn.addEventListener("click", () => {
                const numId = parseInt(id);
                selectedIndividualIds.add(numId);
                selectedVendors.set(numId, v.cannabis_pharmacy_name);
                renderVendorPills();
                searchInput.value = "";
                searchResults.innerHTML = "";
                refreshGraph();
            });
            searchResults.appendChild(btn);
        }
    });

    // Time range buttons
    wrap.querySelectorAll(".graph-time-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            wrap.querySelectorAll(".graph-time-btn").forEach(b => {
                b.className = "graph-time-btn text-xs px-2 py-1 rounded border border-border text-muted hover:border-accent transition duration-100";
            });
            btn.className = "graph-time-btn text-xs px-2 py-1 rounded border border-accent text-accent hover:border-accent transition duration-100";
            currentTimeRange = btn.dataset.range;
            refreshGraph();
        });
    });

    return wrap;
}

function buildBar(value, max, color) {
    const pct = Math.min((value / max) * 100, 100).toFixed(1);
    return `
        <div class="w-full bg-surface rounded-full h-1.5">
            <div class="h-1.5 rounded-full transition-all duration-300" style="width: ${pct}%; background-color: ${color};"></div>
        </div>
    `;
}

function buildProductInfo(product) {
    const flag = COUNTRY_FLAGS[product.origin] ?? "🌍";
    return `
        <div class="p-4 border-b border-border">
            <p class="text-xs text-muted uppercase tracking-wider mb-3">Product Info</p>
            <div class="flex flex-col gap-2.5 text-xs">
                <div>
                    <div class="flex justify-between text-muted mb-1">
                        <span>THC</span>
                        <span class="text-gray-300">${product.thc}%</span>
                    </div>
                    ${buildBar(product.thc, 40, "#f59e0b")}
                </div>
                <div>
                    <div class="flex justify-between text-muted mb-1">
                        <span>CBD</span>
                        <span class="text-gray-300">${product.cbd}%</span>
                    </div>
                    ${buildBar(product.cbd, 20, "#3b82f6")}
                </div>
                <div class="flex justify-between">
                    <span class="text-muted">Genetic</span>
                    <span class="text-gray-300">${product.genetic ?? "—"}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-muted">Dominance</span>
                    <span class="text-gray-300">${product.dominance ?? "—"}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-muted">Origin</span>
                    <span class="text-gray-300">${flag} ${product.origin ?? "—"}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-muted">Irradiated</span>
                    <span class="text-gray-300">${product.irradiated ? "☢️" : "✗"}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-muted">Price range</span>
                    <span class="text-gray-300">€${product.min_price?.toFixed(2)} – €${product.max_price?.toFixed(2)}</span>
                </div>
            </div>
        </div>
    `;
}

function buildVendorList(pid, pidToVendors, vendors, productUrl) {
    const offers = pidToVendors[pid] ?? [];
    const sorted = [...offers].sort((a, b) => a.price - b.price);

    if (sorted.length === 0) {
        return `
            <div class="p-4 border-b border-border">
                <p class="text-xs text-muted uppercase tracking-wider mb-3">Available At</p>
                <p class="text-xs text-muted italic">No vendors found.</p>
            </div>
        `;
    }

    return `
        <div class="p-4 border-b border-border">
            <p class="text-xs text-muted uppercase tracking-wider mb-3">Available At</p>
            <div class="flex flex-col gap-2">
                ${sorted.map(offer => {
        const vendor = vendors[String(offer.vendor_id)];
        const vendorName = vendor?.cannabis_pharmacy_name ?? offer.vendor_id;
        const domain = vendor?.domain;
        const label = AVAILABILITY_LABELS[offer.availability] ?? offer.availability;
        const nameHtml = domain
            ? `<a href="https://${domain}/product/${productUrl ?? ""}" target="_blank" class="text-xs font-medium text-link hover:underline truncate">${vendorName}</a>`
            : `<span class="text-xs font-medium text-gray-300 truncate">${vendorName}</span>`;
        return `
                        <div class="flex flex-col gap-0.5 pb-2 border-b border-border last:border-0">
                            <div class="flex justify-between items-center">
                                ${nameHtml}
                                <span class="text-xs text-accent font-medium ml-2">€${offer.price.toFixed(2)}</span>
                            </div>
                            <span class="text-xs text-muted">${label}</span>
                        </div>
                    `;
    }).join("")}
            </div>
        </div>
    `;
}

export function initDetailPanel() {
    document.getElementById("detail-close").addEventListener("click", closePanel);
    document.addEventListener("keydown", e => {
        if (e.key === "Escape") closePanel();
    });
    renderEmptyState();
}

export async function openDetailPanel(result, reviews, pidToVendors, vendors, products) {
    if (currentPid === result.pid) {
        closePanel();
        return;
    }

    currentPid = result.pid;
    const product = products[result.pid];

    // Show close button
    document.getElementById("detail-close").style.display = "block";

    // Title
    document.getElementById("detail-title").textContent = result.name;

    // Image
    const imageEl = document.getElementById("detail-image");
    const imgTag = imageEl.querySelector("img");
    const imgFallback = imageEl.querySelector(".img-fallback");
    imgTag.src = `${SUPABASE_URL}/storage/v1/object/public/strain-images/expanded/${result.pid}.png`;
    imgTag.alt = result.name;
    imgTag.style.display = "block";
    imgFallback.style.display = "none";
    imgTag.onerror = () => {
        imgTag.style.display = "none";
        imgFallback.style.display = "flex";
    };

    // Rating
    const reviewData = reviews?.[result.pid];
    const score = reviewData?.avg_score ?? null;
    const reviewCount = reviewData?.reviews?.length ?? 0;
    document.getElementById("detail-rating").innerHTML = `
        <div class="flex items-center gap-2">
            ${buildStars(score)}
            <span class="text-xs text-muted">${score != null ? score.toFixed(1) : "—"} (${reviewCount} reviews)</span>
        </div>
    `;

    // Scrollable content
    const scrollable = document.getElementById("detail-scrollable");
    scrollable.innerHTML = "";
    scrollable.innerHTML = buildProductInfo(product) + buildVendorList(result.pid, pidToVendors, vendors, product.url);

    const graphSection = buildGraphSection(result.pid, result.vendorId, vendors);
    scrollable.appendChild(graphSection);
    scrollable.insertAdjacentHTML("beforeend", buildReviews(reviewData));

    highlightCard(result.pid);

    await refreshGraph();
}

export function closePanel() {
    currentPid = null;
    if (currentChart) {
        currentChart.destroy();
        currentChart = null;
    }
    clearCardHighlight();
    renderEmptyState();
}

function buildReviews(reviewData) {
    const count = reviewData?.reviews?.length ?? 0;

    if (!count) {
        return `
            <div class="p-4">
                <p class="text-xs text-muted uppercase tracking-wider mb-3">Reviews <span class="normal-case">(0)</span></p>
                <p class="text-xs text-muted italic">No reviews yet.</p>
            </div>
        `;
    }

    return `
        <div class="p-4">
            <p class="text-xs text-muted uppercase tracking-wider mb-3">Reviews <span class="normal-case">(${count})</span></p>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                ${reviewData.reviews.map(review => `
                    <div style="border-bottom: 1px solid #374151; padding-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span class="text-xs font-medium text-gray-300">${review.author?.username ?? "Anonymous"}</span>
                            <span class="text-xs text-muted">${review.createdAt ? new Date(review.createdAt).toLocaleDateString("de-DE") : "—"}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 4px;">
                            ${buildStars(review.score)}
                            <span class="text-xs text-muted">${review.score?.toFixed(1) ?? "—"}</span>
                        </div>
                        <p class="text-xs text-muted" style="line-height: 1.5;">${review.comment?.content ?? ""}</p>
                    </div>
                `).join("")}
            </div>
        </div>
    `;
}
