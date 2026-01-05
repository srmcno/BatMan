import axios, { AxiosError, AxiosInstance } from 'axios';
import { useAuthStore } from '../stores/authStore';

const API_BASE_URL = '/api/v1';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && originalRequest) {
      const refreshToken = useAuthStore.getState().refreshToken;

      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          useAuthStore.getState().updateTokens(access_token, refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch {
          useAuthStore.getState().logout();
          window.location.href = '/login';
        }
      } else {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// API methods
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),

  register: (email: string, password: string, fullName: string) =>
    api.post('/auth/register', { email, password, full_name: fullName }),

  getMe: () => api.get('/auth/me'),
};

export const projectsApi = {
  list: (page = 1, pageSize = 20) =>
    api.get('/projects', { params: { page, page_size: pageSize } }),

  get: (id: string) => api.get(`/projects/${id}`),

  create: (data: { name: string; description?: string }) =>
    api.post('/projects', data),

  update: (id: string, data: Partial<{ name: string; description: string; status: string }>) =>
    api.patch(`/projects/${id}`, data),

  delete: (id: string) => api.delete(`/projects/${id}`),

  getSummary: (id: string) => api.get(`/projects/${id}/summary`),

  // Sites
  listSites: (projectId: string) => api.get(`/projects/${projectId}/sites`),

  createSite: (projectId: string, data: {
    name: string;
    latitude: number;
    longitude: number;
    description?: string;
  }) => api.post(`/projects/${projectId}/sites`, data),

  getSite: (projectId: string, siteId: string) =>
    api.get(`/projects/${projectId}/sites/${siteId}`),

  updateSite: (projectId: string, siteId: string, data: Partial<{
    name: string;
    latitude: number;
    longitude: number;
    description: string;
  }>) => api.patch(`/projects/${projectId}/sites/${siteId}`, data),

  deleteSite: (projectId: string, siteId: string) =>
    api.delete(`/projects/${projectId}/sites/${siteId}`),
};

export const recordingsApi = {
  list: (siteId: string, page = 1, pageSize = 20, status?: string) =>
    api.get('/recordings', { params: { site_id: siteId, page, page_size: pageSize, status } }),

  get: (id: string) => api.get(`/recordings/${id}`),

  upload: (siteId: string, file: File, metadata?: {
    recorded_at?: string;
    latitude?: number;
    longitude?: number;
  }) => {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata?.recorded_at) formData.append('recorded_at', metadata.recorded_at);
    if (metadata?.latitude) formData.append('latitude', String(metadata.latitude));
    if (metadata?.longitude) formData.append('longitude', String(metadata.longitude));

    return api.post('/recordings/upload', formData, {
      params: { site_id: siteId },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (id: string) => api.delete(`/recordings/${id}`),

  reprocess: (id: string) => api.post(`/recordings/${id}/reprocess`),
};

export const classificationsApi = {
  list: (params: {
    recording_id?: string;
    site_id?: string;
    species_id?: string;
    vetting_status?: string;
    min_confidence?: number;
    page?: number;
    page_size?: number;
  }) => api.get('/classifications', { params }),

  get: (id: string) => api.get(`/classifications/${id}`),

  getPendingReview: (siteId?: string, page = 1, pageSize = 20) =>
    api.get('/classifications/pending-review', {
      params: { site_id: siteId, page, page_size: pageSize },
    }),

  vet: (id: string, data: {
    action: 'approve' | 'reject' | 'correct';
    corrected_species_id?: string;
    notes?: string;
  }) => api.post(`/classifications/${id}/vet`, data),

  getExplanation: (id: string) => api.get(`/classifications/${id}/explain`),

  getParameters: (id: string) => api.get(`/classifications/${id}/parameters`),
};

export const speciesApi = {
  list: (family?: string, endangeredOnly = false) =>
    api.get('/species', { params: { family, endangered_only: endangeredOnly } }),

  get: (id: string) => api.get(`/species/${id}`),

  getByCode: (code: string) => api.get(`/species/code/${code}`),

  getRegional: (latitude: number, longitude: number, month?: number) =>
    api.get('/species/regional', { params: { latitude, longitude, month } }),

  getExpectedRanges: (id: string) => api.get(`/species/${id}/expected-ranges`),
};

export const reportsApi = {
  getDiversity: (projectId: string, siteId?: string) =>
    api.get(`/reports/diversity/${projectId}`, { params: { site_id: siteId } }),

  getActivity: (projectId: string) => api.get(`/reports/activity/${projectId}`),

  exportNabat: (projectId: string) =>
    api.get(`/reports/export/${projectId}/nabat`, { responseType: 'blob' }),

  exportSummary: (projectId: string) =>
    api.get(`/reports/export/${projectId}/summary`, { responseType: 'blob' }),
};

export const batchApi = {
  start: (projectId: string, siteId: string, options?: Record<string, unknown>) =>
    api.post('/batch/process', { project_id: projectId, site_id: siteId, options }),

  getStatus: (jobId: string) => api.get(`/batch/${jobId}`),

  cancel: (jobId: string) => api.post(`/batch/${jobId}/cancel`),

  list: (status?: string, limit = 20) =>
    api.get('/batch', { params: { status, limit } }),
};

export default api;
