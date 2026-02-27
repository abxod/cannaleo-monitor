import { SUPABASE_URL, SUPABASE_ANON_KEY, BUCKETS, FILES } from "./config.js";

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

  document.getElementById("output").textContent = JSON.stringify(products, null, 2);
} catch (error) {
  document.getElementById("output").textContent = `Error: ${error.message}`;
}
