import {SUPABASE_ANON_KEY, SUPABASE_URL} from "./config.js";

export async function fetchFile(bucket, filename) {
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


export const STRAIN_TYPE_NORMALIZATION_MAP = {
  "Hybrid|null": "Hybrid",
  "Hybrid|Indica": "Indica_dominant",
  "Hybrid|Sativa": "Sativa_dominant",
  "Indica|null": "Indica",
  "Sativa|null": "Sativa",
  "Indica|Indica": "Pure Indica",
  "Sativa|Indica": "Indica_dominant",
  "null|Sativa": "Sativa_dominant",
  "hybrid|null": "Hybrid"
};

export function haversine(lon1, lat1, lon2, lat2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) *
    Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(a));
}

export function getUserLocation() {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      position => resolve({
        lat: position.coords.latitude,
        lon: position.coords.longitude
      }),
      error => reject(error)
    );
  });
}

export function getVendorsWithinDistance() {

}
