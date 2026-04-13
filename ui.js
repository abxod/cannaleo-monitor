import {FUNCTIONS, BROWSER_FILTERS} from "./functions.config.js";

let selectedFunction = null;
let onRunCallback = null;
let onApplyCallback = null;

export function initUI(products, onApply, onRun) {
    window.__products = products;
    onApplyCallback = onApply;
    onRunCallback = onRun;
    renderBrowserFilters(products);
    renderFunctionList();
    setupButtons();
}

function renderBrowserFilters(products) {
    const panel = document.getElementById("filter-panel");
    panel.innerHTML = "";
    for (const filter of BROWSER_FILTERS) {
        const el = buildFilter(filter, products);
        if (el) panel.appendChild(el);
    }
    restoreFilters();
}

function renderFunctionList() {
    const nav = document.getElementById("function-list");
    nav.innerHTML = `
        <div class="relative" id="function-dropdown">
            <button id="function-dropdown-btn" class="w-full flex justify-between items-center bg-surface border border-border rounded text-sm px-3 py-1.5 text-gray-300 hover:border-accent transition duration-150">
                <span id="function-dropdown-label">Products</span>
                <span class="text-muted text-xs">▾</span>
            </button>
            <div id="function-dropdown-menu" class="absolute z-10 w-full mt-1 bg-panel border border-border rounded shadow-lg
                opacity-0 -translate-y-1 pointer-events-none transition-all duration-150 ease-out">
                ${[["products", "Products"], ...Object.entries(FUNCTIONS)].map(([key, fn]) => `
                    <button data-key="${key}" class="function-option w-full text-left text-sm px-3 py-2 text-muted hover:text-gray-100 hover:bg-surface transition duration-100 first:rounded-t last:rounded-b">
                        ${typeof fn === "string" ? fn : fn.label}
                    </button>
                `).join("")}
            </div>
        </div>
    `;

    const btn = nav.querySelector("#function-dropdown-btn");
    const menu = nav.querySelector("#function-dropdown-menu");

    btn.addEventListener("click", () => {
        const isOpen = !menu.classList.contains("pointer-events-none");
        isOpen ? closeDropdown(menu) : openDropdown(menu);
    });

    nav.querySelectorAll(".function-option").forEach(option => {
        option.addEventListener("click", () => {
            const key = option.dataset.key;
            const label = key === "products" ? "Products" : FUNCTIONS[key].label;
            document.getElementById("function-dropdown-label").textContent = label;
            closeDropdown(menu);
            selectedFunction = key === "products" ? null : key;
        });
    });

    document.addEventListener("click", e => {
        if (!nav.contains(e.target)) closeDropdown(menu);
    });
}

function openDropdown(menu) {
    menu.classList.remove("opacity-0", "-translate-y-1", "pointer-events-none");
    menu.classList.add("opacity-100", "translate-y-0");
}

function closeDropdown(menu) {
    menu.classList.remove("opacity-100", "translate-y-0");
    menu.classList.add("opacity-0", "-translate-y-1", "pointer-events-none");
}

function selectFunction(key) {
    selectedFunction = key;
}

function setupButtons() {
    document.getElementById("apply-filters-btn").addEventListener("click", () => {
        saveFilters();
        const filters = readFilters();
        if (selectedFunction && selectedFunction !== "products" && onRunCallback) {
            onRunCallback(selectedFunction, filters);
        } else if (onApplyCallback) {
            onApplyCallback(filters);
        }
    });

    document.getElementById("reset-filters-btn").addEventListener("click", () => {
        resetFilters();
        if (onApplyCallback) onApplyCallback(readFilters());
    });
}

export function resetFilters() {
    localStorage.removeItem("filters");

    // maxDistance
    const slider = document.getElementById("max-distance");
    const noLimit = document.getElementById("no-distance-limit");
    const display = document.getElementById("max-distance-display");
    if (slider) { slider.value = 100; slider.disabled = false; }
    if (noLimit) noLimit.checked = false;
    if (display) display.textContent = "100 km";

    // availability
    document.querySelectorAll(".availability-checkbox").forEach(cb => {
        cb.checked = ["available_immediately", "available", "limited_stock"].includes(cb.value);
    });

    // strainTypes
    document.querySelectorAll(".strainTypes-checkbox").forEach(cb => { cb.checked = true; });

    // producers
    document.querySelectorAll(".producer-checkbox").forEach(cb => { cb.checked = false; });

    // thcRange
    const thcMin = document.getElementById("thcRange-min");
    const thcMax = document.getElementById("thcRange-max");
    const thcDisplay = document.getElementById("thcRange-display");
    if (thcMin) thcMin.value = 1;
    if (thcMax) thcMax.value = 37;
    if (thcDisplay) thcDisplay.textContent = "1 – 37";

    // priceRange
    const priceMin = document.getElementById("priceRange-min");
    const priceMax = document.getElementById("priceRange-max");
    const priceDisplay = document.getElementById("priceRange-display");
    if (priceMin) priceMin.value = 1;
    if (priceMax) priceMax.value = 30;
    if (priceDisplay) priceDisplay.textContent = "1 – 30";

    // timeRange
    document.querySelectorAll(".time-range-btn").forEach(btn => {
        const isDefault = btn.dataset.value === "1M";
        btn.className = `time-range-btn text-xs px-2 py-1 rounded border ${isDefault ? "border-accent text-accent" : "border-border text-muted"} hover:border-accent transition`;
    });
}

function buildFilter(filter, products) {
    switch (filter) {
        case "maxDistance":
            return buildMaxDistance();
        case "availability":
            return buildCheckboxGroup("availability", "Availability", [{
                value: "available_immediately",
                label: "Available immediately",
                checked: true
            }, {value: "available", label: "Available", checked: true}, {
                value: "limited_stock",
                label: "Limited stock",
                checked: true
            }, {value: "unavailable", label: "Unavailable", checked: false},]);
        case "strainTypes":
            return buildCheckboxGroup("strainTypes", "Strain types", [{
                value: "Indica",
                label: "Indica",
                checked: true
            }, {value: "Sativa", label: "Sativa", checked: true}, {
                value: "Hybrid",
                label: "Hybrid",
                checked: true
            }, {value: "Indica_dominant", label: "Indica dominant", checked: true}, {
                value: "Sativa_dominant",
                label: "Sativa dominant",
                checked: true
            }, {value: "Pure Indica", label: "Pure Indica", checked: true},]);
        case "thcRange":
            return buildDualSlider("thcRange", "THC range", 1, 37, 1, 37);
        case "priceRange":
            return buildDualSlider("priceRange", "Price range (€)", 1, 30, 1, 30);
        case "producer":
            return buildProducerSelect(products);
        case "timeRange":
            return buildTimeRange();
        case "pid":
            return buildPidSearch(products);
        default:
            return null;
    }
}

function buildMaxDistance() {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
        <div class="flex justify-between text-xs text-muted mb-1">
            <span>Max distance</span>
            <span id="max-distance-display">100 km</span>
        </div>
        <input type="range" id="max-distance" min="1" max="1000" value="100" class="w-full">
        <label class="flex items-center gap-2 text-xs text-muted mt-2 cursor-pointer">
            <input type="checkbox" id="no-distance-limit">
            No limit
        </label>
    `;
    wrap.querySelector("#max-distance").addEventListener("input", e => {
        wrap.querySelector("#max-distance-display").textContent = `${e.target.value} km`;
    });
    wrap.querySelector("#no-distance-limit").addEventListener("change", e => {
        const slider = wrap.querySelector("#max-distance");
        slider.disabled = e.target.checked;
        wrap.querySelector("#max-distance-display").textContent = e.target.checked ? "∞" : `${slider.value} km`;
    });
    return wrap;
}

function buildDualSlider(id, label, min, max, defaultMin, defaultMax) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
        <div class="flex justify-between text-xs text-muted mb-1">
            <span>${label}</span>
            <span id="${id}-display">${defaultMin} – ${defaultMax}</span>
        </div>
        <div class="flex gap-2 items-center">
            <input type="range" id="${id}-min" min="${min}" max="${max}" value="${defaultMin}" class="w-full">
            <input type="range" id="${id}-max" min="${min}" max="${max}" value="${defaultMax}" class="w-full">
        </div>
    `;
    const update = () => {
        const lo = parseInt(wrap.querySelector(`#${id}-min`).value);
        const hi = parseInt(wrap.querySelector(`#${id}-max`).value);
        wrap.querySelector(`#${id}-display`).textContent = `${Math.min(lo, hi)} – ${Math.max(lo, hi)}`;
    };
    wrap.querySelector(`#${id}-min`).addEventListener("input", update);
    wrap.querySelector(`#${id}-max`).addEventListener("input", update);
    return wrap;
}

function buildCheckboxGroup(id, label, options) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
        <div class="flex justify-between text-xs text-muted mb-2">
            <span>${label}</span>
            <button id="${id}-select-all" class="text-accent hover:underline">All</button>
        </div>
        <div id="${id}-options" class="flex flex-col gap-1">
            ${options.map(o => `
                <label class="flex items-center gap-2 text-xs cursor-pointer">
                    <input type="checkbox" value="${o.value}" ${o.checked ? "checked" : ""} class="${id}-checkbox">
                    ${o.label}
                </label>
            `).join("")}
        </div>
    `;
    wrap.querySelector(`#${id}-select-all`).addEventListener("click", () => {
        wrap.querySelectorAll(`.${id}-checkbox`).forEach(cb => cb.checked = true);
    });
    return wrap;
}

function buildProducerSelect(products) {
    const producers = [...new Set(Object.values(products).map(p => p.producer_name).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    const wrap = document.createElement("div");
    wrap.innerHTML = `
        <div class="flex justify-between text-xs text-muted mb-2">
            <span>Producer</span>
            <button id="producer-select-all" class="text-accent hover:underline">All</button>
        </div>
        <div id="producer-options" class="flex flex-col gap-1 max-h-32 overflow-y-auto">
            ${producers.map(p => `
                <label class="flex items-center gap-2 text-xs cursor-pointer">
                    <input type="checkbox" value="${p}" class="producer-checkbox">
                    ${p}
                </label>
            `).join("")}
        </div>
    `;
    wrap.querySelector("#producer-select-all").addEventListener("click", () => {
        wrap.querySelectorAll(".producer-checkbox").forEach(cb => cb.checked = true);
    });
    return wrap;
}

function buildTimeRange() {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
        <p class="text-xs text-muted mb-2">Time range</p>
        <div class="flex gap-2 flex-wrap">
            ${["1W", "1M", "3M", "6M", "1Y", "Max"].map((t, i) => `
                <button data-value="${t}" class="time-range-btn text-xs px-2 py-1 rounded border ${i === 1 ? "border-accent text-accent" : "border-border text-muted"} hover:border-accent transition">
                    ${t}
                </button>
            `).join("")}
        </div>
    `;
    wrap.querySelectorAll(".time-range-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            wrap.querySelectorAll(".time-range-btn").forEach(b => {
                b.className = "time-range-btn text-xs px-2 py-1 rounded border border-border text-muted hover:border-accent transition";
            });
            btn.className = "time-range-btn text-xs px-2 py-1 rounded border border-accent text-accent hover:border-accent transition";
        });
    });
    return wrap;
}

function buildPidSearch(products) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
        <p class="text-xs text-muted mb-2">Product <span class="text-muted italic">(optional)</span></p>
        <input type="text" id="pid-search" placeholder="Search by name..." class="w-full bg-surface border border-border rounded text-xs px-2 py-1.5 focus:outline-none focus:border-accent">
        <div id="pid-results" class="mt-1 flex flex-col gap-0.5 max-h-32 overflow-y-auto"></div>
        <input type="hidden" id="pid-value">
    `;
    const input = wrap.querySelector("#pid-search");
    const results = wrap.querySelector("#pid-results");
    const hidden = wrap.querySelector("#pid-value");

    input.addEventListener("input", () => {
        const query = input.value.toLowerCase();
        results.innerHTML = "";
        hidden.value = "";
        if (!query) return;

        const matches = Object.entries(products)
            .filter(([, p]) => p.name.toLowerCase().includes(query))
            .slice(0, 8);

        for (const [pid, p] of matches) {
            const btn = document.createElement("button");
            btn.textContent = p.name;
            btn.className = "text-left text-xs px-2 py-1 rounded hover:bg-surface text-gray-300";
            btn.addEventListener("click", () => {
                input.value = p.name;
                hidden.value = pid;
                results.innerHTML = "";
            });
            results.appendChild(btn);
        }
    });
    return wrap;
}

export function readFilters() {
    const get = id => document.getElementById(id);
    const noLimit = get("no-distance-limit");

    return {
        maxDistance: noLimit?.checked ? Infinity : parseInt(get("max-distance")?.value ?? 500),
        availability: new Set([...document.querySelectorAll(".availability-checkbox:checked")].map(c => c.value)),
        strainTypes: new Set([...document.querySelectorAll(".strainTypes-checkbox:checked")].map(c => c.value)),
        thcRange: [parseInt(get("thcRange-min")?.value ?? 1), parseInt(get("thcRange-max")?.value ?? 37)],
        priceRange: [parseInt(get("priceRange-min")?.value ?? 1), parseInt(get("priceRange-max")?.value ?? 30)],
        producers: new Set([...document.querySelectorAll(".producer-checkbox:checked")].map(c => c.value)),
        timeRange: document.querySelector(".time-range-btn.border-accent")?.dataset.value ?? "1M",
        pid: get("pid-value")?.value || null,
    };
}

function saveFilters() {
    const filters = readFilters();
    localStorage.setItem("filters", JSON.stringify({
        maxDistance: filters.maxDistance === Infinity ? null : filters.maxDistance,
        noDistanceLimit: document.getElementById("no-distance-limit")?.checked ?? false,
        availability: [...filters.availability],
        strainTypes: [...filters.strainTypes],
        thcRange: filters.thcRange,
        priceRange: filters.priceRange,
        producers: [...filters.producers],
        timeRange: filters.timeRange,
        pid: filters.pid,
    }));
}

function restoreFilters() {
    const saved = localStorage.getItem("filters");
    if (!saved) return;
    const f = JSON.parse(saved);

    const maxDistanceSlider = document.getElementById("max-distance");
    const noLimitCheckbox = document.getElementById("no-distance-limit");
    const display = document.getElementById("max-distance-display");

    if (maxDistanceSlider && f.maxDistance != null) {
        maxDistanceSlider.value = f.maxDistance;
        if (display) display.textContent = `${f.maxDistance} km`;
    }
    if (noLimitCheckbox && f.noDistanceLimit) {
        noLimitCheckbox.checked = true;
        if (maxDistanceSlider) maxDistanceSlider.disabled = true;
        if (display) display.textContent = "∞";
    }
    if (f.availability) {
        document.querySelectorAll(".availability-checkbox").forEach(cb => {
            cb.checked = f.availability.includes(cb.value);
        });
    }
    if (f.strainTypes) {
        document.querySelectorAll(".strainTypes-checkbox").forEach(cb => {
            cb.checked = f.strainTypes.includes(cb.value);
        });
    }
    if (f.producers) {
        document.querySelectorAll(".producer-checkbox").forEach(cb => {
            cb.checked = f.producers.includes(cb.value);
        });
    }
    const thcMin = document.getElementById("thcRange-min");
    const thcMax = document.getElementById("thcRange-max");
    if (thcMin && f.thcRange) {
        thcMin.value = f.thcRange[0];
        thcMax.value = f.thcRange[1];
        document.getElementById("thcRange-display").textContent = `${f.thcRange[0]} – ${f.thcRange[1]}`;
    }
    const priceMin = document.getElementById("priceRange-min");
    const priceMax = document.getElementById("priceRange-max");
    if (priceMin && f.priceRange) {
        priceMin.value = f.priceRange[0];
        priceMax.value = f.priceRange[1];
        document.getElementById("priceRange-display").textContent = `${f.priceRange[0]} – ${f.priceRange[1]}`;
    }
    if (f.timeRange) {
        document.querySelectorAll(".time-range-btn").forEach(btn => {
            const isActive = btn.dataset.value === f.timeRange;
            btn.className = `time-range-btn text-xs px-2 py-1 rounded border ${isActive ? "border-accent text-accent" : "border-border text-muted"} hover:border-accent transition`;
        });
    }
}
