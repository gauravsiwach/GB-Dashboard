import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Markets API
export const marketsApi = {
  getAll: () => api.get('/markets'),
  getById: (id) => api.get(`/markets/${id}`),
  create: (data) => api.post('/markets', data),
};

// Flags API
export const flagsApi = {
  getAll: (marketId) => api.get('/flags', { params: { market_id: marketId } }),
  create: (data) => api.post('/flags', data),
  update: (id, data) => api.put(`/flags/${id}`, data),
};

export default api;
