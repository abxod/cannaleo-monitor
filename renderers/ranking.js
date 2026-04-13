import {openDetailPanel} from "./detail-panel.js";
import {STRAIN_TYPE_NORMALIZATION_MAP} from "../utils.js";
import {SUPABASE_URL} from "../config.js";

const RANK_COLORS = {
    1: {border: "border-yellow-400", rank: "text-yellow-400", badge: "bg-yellow-400 text-gray-900"},
    2: {border: "border-gray-400", rank: "text-gray-400", badge: "bg-gray-400 text-gray-900"},
    3: {border: "border-amber-600", rank: "text-amber-600", badge: "bg-amber-600 text-gray-900"},
};

const GENETIC_COLORS = {
    "Indica":          "border-purple-500",
    "Pure Indica":     "border-purple-600",
    "Indica_dominant": "border-purple-400",
    "Sativa":          "border-orange-400",
    "Sativa_dominant": "border-orange-300",
    "Hybrid":          "border-teal-400",
};

const STRAIN_ICONS = {
    "Indica":          "./assets/icons/indica.svg",
    "Pure Indica":     "./assets/icons/indica.svg",
    "Indica_dominant": "./assets/icons/indica.svg",
    "Sativa":          "./assets/icons/sativa.svg",
    "Sativa_dominant": "./assets/icons/sativa.svg",
    "Hybrid":          "./assets/icons/hybrid.svg",
};

const AVAILABILITY_LABELS = {
    available_immediately: "Available immediately",
    available: "Available",
    limited_stock: "Limited stock",
    unavailable: "Unavailable"
};

const BATCH_SIZE = 60;
const FLOWZZ_BASE_URL = "https://flowzz.com/product/";

let currentResults = [];
let currentIndex = 0;
let currentGrid = null;
let currentVendors = null;
let currentDistances = null;
let currentReviews = null;
let currentProducts = null;
let currentPidToVendors = null;
let currentHighlightedCard = null;

function getColumnCount() {
    if (!currentGrid) return 4;
    return Math.max(1, Math.floor(currentGrid.offsetWidth / 208));
}

function getNormalizedStrain(product) {
    if (!product) return null;
    const key = `${product.genetic}|${product.dominance}`;
    return STRAIN_TYPE_NORMALIZATION_MAP[key] ?? product.genetic ?? null;
}

function getRankStyle(rank, product) {
    if (RANK_COLORS[rank]) return RANK_COLORS[rank];
    const strain = getNormalizedStrain(product);
    return {
        border: GENETIC_COLORS[strain] ?? "border-border",
        rank: "text-accent",
        badge: "bg-surface border border-border text-muted"
    };
}

export function highlightCard(pid) {
    clearCardHighlight();
    const card = currentGrid?.querySelector(`[data-pid="${pid}"]`);
    if (card) {
        card.classList.add("ring-2", "ring-accent", "ring-offset-1", "ring-offset-surface");
        currentHighlightedCard = card;
        card.scrollIntoView({behavior: "smooth", block: "nearest"});
    }
}

export function clearCardHighlight() {
    if (currentHighlightedCard) {
        currentHighlightedCard.classList.remove("ring-2", "ring-accent", "ring-offset-1", "ring-offset-surface");
        currentHighlightedCard = null;
    }
}

export function buildStars(score) {
    if (score == null) return '<span class="text-xs text-muted">No rating</span>';
    const stars = [];
    for (let i = 1; i <= 5; i++) {
        const filled = i <= Math.round(score);
        stars.push(`
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="w-3 h-3 inline-block"
                fill="${filled ? "#f59e0b" : "none"}" stroke="#f59e0b" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
        `);
    }
    return stars.join("");
}

function getThumbnailUrl(pid) {
    return `${SUPABASE_URL}/storage/v1/object/public/strain-images/thumbnail/${pid}.png`;
}

function buildCard(result, rank) {
    const CANNABIS_FALLBACK_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Cannabis_leaf.svg/250px-Cannabis_leaf.svg.png";
    const product = currentProducts?.[result.pid];
    const strain = getNormalizedStrain(product);
    const style = getRankStyle(rank, product);

    const card = document.createElement("div");
    card.className = `relative flex flex-col bg-panel border ${style.border} rounded-lg overflow-hidden cursor-pointer hover:border-accent transition duration-150`;
    card.dataset.pid = result.pid;

    const vendorName = currentVendors[result.vendorId]?.cannabis_pharmacy_name ?? result.vendorId;
    const distance = currentDistances.get(result.vendorId) ?? currentDistances.get(String(result.vendorId));
    const distanceStr = distance != null ? `${distance.toFixed(1)} km` : "—";
    const productUrl = FLOWZZ_BASE_URL + result.url;
    const reviewData = currentReviews?.[result.pid];
    const score = reviewData?.avg_score ?? null;
    const availabilityLabel = AVAILABILITY_LABELS[result.availability] ?? result.availability;
    const iconUrl = STRAIN_ICONS[strain];
    const producerName = product?.producer_name ?? "—";

    card.innerHTML = `
        <!-- Rank badge -->
        <div class="absolute top-1.5 left-1.5 z-10 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${style.badge}">
            ${rank}
        </div>
        <!-- Strain icon -->
        ${iconUrl ? `
        <div class="absolute top-1.5 right-1.5 z-10 w-5 h-5">
            <img src="${iconUrl}" alt="${strain}"
                class="w-full h-full"
                onerror="this.src='${CANNABIS_FALLBACK_URL}'">
        </div>` : ""}
        <!-- Thumbnail -->
        <div class="w-full h-28 bg-surface flex items-center justify-center overflow-hidden">
            <img
                src="${getThumbnailUrl(result.pid)}"
                alt="${result.name}"
                class="w-full h-full object-cover"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
            >
            <div class="w-full h-full hidden items-center justify-center bg-surface">
                <span class="text-muted text-xs">No image</span>
            </div>
        </div>

        <!-- Content -->
        <div class="flex flex-col gap-1.5 p-2 flex-1">
            <p class="text-sm font-semibold text-gray-100 truncate">${result.name}</p>
            <p class="text-xs text-muted truncate">${producerName}</p>
            <div class="flex flex-col gap-0.5 text-xs text-muted">
                <span>THC: <span class="text-gray-300">${result.thc}%</span></span>
                <span>Price: <span class="text-gray-300">€${result.price.toFixed(2)}</span></span>
                <span>Vendor: <span class="text-gray-300 line-clamp-2 leading-tight">${vendorName}</span></span>
                <span>Distance: <span class="text-gray-300">${distanceStr}</span></span>
                <span>Status: <span class="text-gray-300">${availabilityLabel}</span></span>
            </div>
            <div class="flex items-center gap-1 mt-1">
                ${buildStars(score)}
                <span class="text-xs text-muted">${score != null ? score.toFixed(1) : "—"} (${reviewData?.reviews?.length ?? 0})</span>
            </div>
            <div class="mt-auto flex justify-between items-center pt-1">
                <div class="flex flex-col">
                    <span class="text-base font-bold ${style.rank}">${result.ratio.toFixed(3)}</span>
                    <span class="text-xs text-muted">THC/€</span>
                </div>
                <a href="${productUrl}" target="_blank" class="text-xs text-link hover:underline">flowzz</a>
            </div>
        </div>
    `;

    card.addEventListener("click", (e) => {
        if (e.target.tagName === "A") return;
        openDetailPanel(result, currentReviews, currentPidToVendors, currentVendors, currentProducts);
    });

    const delay = Math.min((rank - 1) * 40, 600);
    card.style.animationDelay = `${delay}ms`;
    card.classList.add("card-enter");

    return card;
}

function loadMore() {
    const cols = getColumnCount();
    const adjustedBatchSize = Math.ceil(BATCH_SIZE / cols) * cols;
    const start = currentIndex;
    const batch = currentResults.slice(start, start + adjustedBatchSize);

    batch.forEach((result, i) => {
        currentGrid.appendChild(buildCard(result, start + i + 1));
    });

    currentIndex += batch.length;

    const loadMoreBtn = document.getElementById("load-more-btn");
    if (loadMoreBtn && currentIndex >= currentResults.length) {
        loadMoreBtn.remove();
    }
}

export function renderRanking(results, vendors, distances, reviews, products, pidToVendors) {
    const output = document.getElementById("output");
    output.innerHTML = "";

    currentResults = results;
    currentVendors = vendors;
    currentDistances = distances;
    currentReviews = reviews;
    currentProducts = products;
    currentPidToVendors = pidToVendors;
    currentIndex = 0;
    currentHighlightedCard = null;

    if (results.length === 0) {
        output.innerHTML = `<p class="text-sm text-muted">No results found for the selected filters.</p>`;
        return;
    }

    currentGrid = document.createElement("div");
    currentGrid.className = "grid gap-3";
    currentGrid.style.gridTemplateColumns = "repeat(auto-fill, minmax(208px, 1fr))";
    output.appendChild(currentGrid);

    const loadMoreBtn = document.createElement("button");
    loadMoreBtn.id = "load-more-btn";
    loadMoreBtn.textContent = "Load more";
    loadMoreBtn.className = "mt-6 w-full py-2 text-sm border border-border text-muted rounded hover:border-accent hover:text-gray-300 active:scale-95 transition duration-100";
    loadMoreBtn.addEventListener("click", loadMore);
    output.appendChild(loadMoreBtn);

    loadMore();
}
