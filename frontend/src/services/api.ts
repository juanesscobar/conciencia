import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Global error interceptor
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('mc_token')
      delete api.defaults.headers.common['Authorization']
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const projectsApi = {
  getAll: () => api.get('/api/v1/projects/'),
  getById: (id: string) => api.get(`/api/v1/projects/${id}`),
  create: (data: any) => api.post('/api/v1/projects/', data),
  update: (id: string, data: any) => api.patch(`/api/v1/projects/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/projects/${id}`),
}

export const tasksApi = {
  getAll: (projectId?: string) => {
    const params = projectId ? { project_id: projectId } : {}
    return api.get('/api/v1/tasks/', { params })
  },
  getById: (id: string) => api.get(`/api/v1/tasks/${id}`),
  create: (data: any) => api.post('/api/v1/tasks/', data),
  update: (id: string, data: any) => api.put(`/api/v1/tasks/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/tasks/${id}`),
}

export const activitiesApi = {
  getAll: (projectId?: string) => {
    const url = projectId
      ? `/api/v1/projects/${projectId}/activity`
      : '/api/v1/activities/'
    return api.get(url)
  },
}

export const githubApi = {
  getRepos: () => api.get('/api/v1/integrations/github/repos'),
  getCommits: (repoName: string) =>
    api.get(`/api/v1/integrations/github/commits/${repoName}`),
  syncProject: (projectId: string) =>
    api.post(`/api/v1/integrations/github/sync/${projectId}`),
}

export const agentsApi = {
  getAll: () => api.get('/api/v1/agents/'),
  getById: (id: string) => api.get(`/api/v1/agents/${id}`),
  getTasks: (id: string) => api.get(`/api/v1/agents/${id}/tasks`),
  getActivity: (id: string) => api.get(`/api/v1/agents/${id}/activity`),
  getFiles: (id: string) => api.get(`/api/v1/agents/${id}/files`),
  run: (id: string, data: any) => api.post(`/api/v1/agents/${id}/run`, data),
}

export const metricsApi = {
  getAll: (projectId?: string) => {
    const url = projectId
      ? `/api/v1/projects/${projectId}/metrics/`
      : '/api/v1/metrics/'
    return api.get(url)
  },
  create: (data: any) => api.post('/api/v1/metrics/', data),
  getDashboard: () => api.get('/api/v1/metrics/dashboard'),
  getIndustry: () => api.get('/api/v1/metrics/industry'),
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post('/api/v1/auth/login', { username, password }),
  register: (email: string, username: string, password: string) =>
    api.post('/api/v1/auth/register', { email, username, password }),
  me: () => api.get('/api/v1/auth/me'),
}

export const deliverablesApi = {
  getAll: (params?: any) => api.get('/api/v1/deliverables', { params }),
  getById: (id: string) => api.get(`/api/v1/deliverables/${id}`),
  create: (data: any) => api.post('/api/v1/deliverables', data),
  update: (id: string, data: any) => api.put(`/api/v1/deliverables/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/deliverables/${id}`),
}

export const reportsApi = {
  sprint: (sprintId: string) => api.get(`/api/v1/reports/sprint/${sprintId}`),
  summary: () => api.get('/api/v1/reports/summary'),
}

export const sprintsApi = {
  getAll: () => api.get('/api/v1/sprints/'),
  getById: (id: string) => api.get(`/api/v1/sprints/${id}`),
}
