import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const routeApiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

export const analyzeRoutes = async (payload) => {
  const response = await routeApiClient.post('/api/v1/routes/analyze/', payload);
  return response.data;
};

export const fetchLocationSuggestions = async (query) => {
  const cleanQuery = query?.trim();
  if (!cleanQuery || cleanQuery.length < 2) return [];

  try {
    const res = await axios.get('https://photon.komoot.io/api/', {
      params: {
        q: cleanQuery,
        limit: 5,
        lang: 'en',
      },
      timeout: 5000,
    });

    const features = res.data?.features || [];
    return features.map((f, idx) => {
      const p = f.properties || {};
      const name = p.name || p.city || p.state || '';
      const parts = [p.city, p.state, p.country].filter(
        (part) => part && part !== name
      );
      const subtext = parts.join(', ');
      const label = subtext ? `${name}, ${subtext}` : name;

      return {
        id: `${p.osm_id || idx}-${name}`,
        name,
        subtext,
        label,
        coordinates: f.geometry?.coordinates, // [lon, lat]
      };
    });
  } catch (err) {
    console.warn('Location suggestion lookup error:', err);
    return [];
  }
};

export default routeApiClient;
