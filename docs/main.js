import { SUPABASE_URL, SUPABASE_ANON_KEY, BUCKETS, FILES } from "./config.js";
import { haversine, getUserLocation, STRAIN_TYPE_NORMALIZATION_MAP } from "./utils.js";
import { getBestThcPriceRatios } from "./functions/best_thc_price_ratios.js";

async function fetchFile(bucket, filename) {
  const url = `${SUPABASE_URL}/storage/v1/object/${bucket}/${filename}`;
  const response = await fetch(url, {
    headers: {
      "Authorization": `Bearer ${SUPABASE_ANON_KEY}`
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch ${filename}: ${response.status}`);
  }

  return response.json();
}

try {
  const products = await fetchFile(BUCKETS.products, FILES.products)
  const vendors = await fetchFile(BUCKETS.vendors, FILES.vendors)
  const inventories = await fetchFile(BUCKETS.inventories, FILES.inventories)
  const pidToVendors = await fetchFile(BUCKETS.inventories, FILES.pidToVendors)

  document.getElementById("output").textContent = JSON.stringify(products, null, 2);
} catch (error) {
  document.getElementById("output").textContent = `Error: ${error.message}`;
}

let userLocation = null;

document.getElementById("locate-btn").addEventListener("click", async () => {
  try {
    userLocation = await getUserLocation();
    document.getElementById("output").textContent = `Location saved: ${userLocation.lat}, ${userLocation.lon}`;
  } catch (error) {
    document.getElementById("output").textContent =`Location error: ${error.message}`;
  }
});
