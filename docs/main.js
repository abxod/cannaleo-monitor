import {SUPABASE_URL, SUPABASE_ANON_KEY, BUCKETS, FILES} from "./config.js";
import {fetchFile, haversine, getUserLocation, STRAIN_TYPE_NORMALIZATION_MAP} from "./utils.js";

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
    const products = await fetchFile(BUCKETS.products, FILES.products)
    const vendors = await fetchFile(BUCKETS.vendors, FILES.vendors)
    const inventories = await fetchFile(BUCKETS.inventories, FILES.inventories)
    // const pidToVendors = await fetchFile(BUCKETS.inventories, FILES.pidToVendors)

    document.getElementById("output").textContent = JSON.stringify(products, null, 2);
} catch (error) {
    document.getElementById("output").textContent = `Error: ${error.message}`;
}
