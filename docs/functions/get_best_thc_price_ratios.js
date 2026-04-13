import {STRAIN_TYPE_NORMALIZATION_MAP} from "../utils.js";

export function getBestThcPriceRatios(products, pidToVendorOffers, filteredVendorIds, availabilityFilter, strainFilter, thcRange = [1, 37], producers = 'all') {
    // TODO: Caller of this function has to sanitize the inputs of availabilityOptions, strainTypes, productCount. First two should be check-boxes, productCount and maxDistance a slider/textbox
    // TODO: maxDistance should only be calculated once the function is executed.
    // TODO: Get users' coordinates: Display error if user coordinates not available. If user presses a button that prompts him for his location after which his coordinates are calculated, then function can proceed.
    // TODO: Should we filter
    const bestRatios = []

    for (const [pid, offers] of Object.entries(pidToVendorOffers)) {
        const product = products[pid];
        if (!product) continue;

        // Discard non-desired strains
        const key = `${product.genetic}|${product.dominance}`;
        const strainType = STRAIN_TYPE_NORMALIZATION_MAP[key];
        if (!strainFilter.has(strainType)) continue;

        // Discard non-desired THC percent
        const [minThc, maxThc] = thcRange;
        if (product.thc < minThc || product.thc > maxThc) continue;

        // Discard non-desired producers
        if (!producers.has(product.producer_name)) continue;

        // Discard incorrectly categorized CBD products
        if (product.thc < 10 || product.cbd > 1) continue;

        // Find best valid offer for this PID
        let bestOffer = null;
        for (const offer of offers) {
            if (!filteredVendorIds.has(offer.vendor_id)) continue;
            if (!availabilityFilter.has(offer.availability)) continue;

            if (bestOffer == null || offer.price < bestOffer.price) {
                bestOffer = offer;
            }
        }

        if (bestOffer == null) continue;

        if (bestOffer.price === 0) continue;

        const ratio = product.thc / bestOffer.price;
        bestRatios.push({
            ratio,
            pid,
            name: product.name,
            url: product.url,
            vendorId: String(bestOffer.vendor_id),
            price: bestOffer.price,
            thc: product.thc,
            availability: bestOffer.availability
        });
    }

    bestRatios.sort((a, b) => b.ratio - a.ratio);
    return bestRatios;
}
