import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const projectsApi = {
  getAll: () => api.get('/api/v1/projects/'),
  getById: (id: string) => api.get(`/api/v1/projects/${id}`),
  create: (data: any) => api.post('/api/v1/projects/', data),
  update: (id: string, data: any) => api.patch(`/api/v1/projects/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/projects/${id}`),
}

export const tasksApi = {
  getAll: (projectId?: string) => {
    const url = projectId 
      ? `/api/v1/projects/${projectId}/tasks/`
      : '/api/v1/tasks/'
    return api.get(url)
  },
  getById: (id: string) => api.get(`/api/v1/tasks/${id}`),
  create: (data: any) => api.post('/api/v1/tasks/', data),
  update: (id: string, data: any) => api.patch(`/api/v1/tasks/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/tasks/${id}`),
}

export const activitiesApi = {
  getAll: (projectId?: string) => {
    const url = projectId
      ? `/api/v1/projects/${projectId}/activities/`
      : '/api/v1/activities/'
    return api.get(url)
  },
}

export const githubApi = {
  getRepos: () => api.get('/api/v1/integrations/github/repos'),
  getCommits: (repoName: string) => api.get(`/api/v1/integrations/github/commits/${repoName}`),
  syncProject: (projectId: string) => api.post(`/api/v1/integrations/github/sync/${projectId}`),
}

export const agentsApi = {
  getAll: () => api.get('/api/v1/agents/'),
  getById: (id: string) => api.get(`/api/v1/agents/${id}`),
}

export const metricsApi = {
  getAll: (projectId?: string) => {
    const url = projectId
      ? `/api/v1/projects/${projectId}/metrics/`
      : '/api/v1/metrics/'
    return api.get(url)
  },
}
