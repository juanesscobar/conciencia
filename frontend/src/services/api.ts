import axios from 'axios'

// API relativa por defecto (misma origin: nginx proxya /api al backend).
// En dev local se puede setear VITE_API_URL=http://localhost:8000
const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

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
  fromGithub: (fullName: string) => api.post('/api/v1/projects/from-github', null, { params: { full_name: fullName } }),
  fromLead: (leadId: string) => api.post(`/api/v1/projects/from-lead/${leadId}`),
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

export const leadsApi = {
  getAll: (params?: any) => api.get('/api/v1/leads/', { params }),
  getById: (id: string) => api.get(`/api/v1/leads/${id}`),
  create: (data: any) => api.post('/api/v1/leads/', data),
  update: (id: string, data: any) => api.patch(`/api/v1/leads/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/leads/${id}`),
  stats: () => api.get('/api/v1/leads/stats'),
  enrich: (id: string) => api.post(`/api/v1/leads/${id}/enrich`),
  enrichWebsite: (id: string) => api.post(`/api/v1/leads/${id}/enrich-website`),
  huntRun: (params?: any) => api.post('/api/v1/leads/hunt/run', null, { params }),
  huntSources: () => api.get('/api/v1/leads/hunt/sources'),
  huntRuns: () => api.get('/api/v1/leads/hunt/runs', { params: { limit: 5 } }),
  regions: () => api.get('/api/v1/leads/regions'),
  searches: () => api.get('/api/v1/leads/searches'),
  searchSave: (data: any) => api.post('/api/v1/leads/searches', data),
  searchDelete: (id: string) => api.delete(`/api/v1/leads/searches/${id}`),
  lists: () => api.get('/api/v1/leads/lists'),
  listCreate: (data: any) => api.post('/api/v1/leads/lists', data),
  listDelete: (id: string) => api.delete(`/api/v1/leads/lists/${id}`),
  listDetail: (id: string) => api.get(`/api/v1/leads/lists/${id}/leads`),
  listAddLead: (id: string, leadId: string) => api.post(`/api/v1/leads/lists/${id}/leads`, { lead_id: leadId }),
  listRemoveLead: (id: string, leadId: string) => api.delete(`/api/v1/leads/lists/${id}/leads/${leadId}`),
  leadLists: (leadId: string) => api.get(`/api/v1/leads/${leadId}/lists`),
  importCsv: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/v1/leads/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  action: (id: string, action: string, data?: any) => api.post(`/api/v1/leads/${id}/${action}`, data || {}),
  events: (id: string) => api.get(`/api/v1/leads/${id}/events`),
  proposals: (id: string) => api.get(`/api/v1/leads/${id}/proposals`),
  proposalGenerate: (id: string) => api.post(`/api/v1/leads/${id}/proposal/generate`),
  proposalCreate: (id: string, data: any) => api.post(`/api/v1/leads/${id}/proposal`, data),
  proposalSend: (proposalId: string, data?: any) => api.post(`/api/v1/leads/proposals/${proposalId}/send`, data || {}),
  proposalDeliver: (proposalId: string) => api.get(`/api/v1/leads/proposals/${proposalId}/deliver`),
  proposalPdf: (proposalId: string) => api.get(`/api/v1/leads/proposals/${proposalId}/pdf`, { responseType: 'blob' }),
}

export const workflowsApi = {
  getAll: () => api.get('/api/v1/workflows/'),
  getById: (id: string) => api.get(`/api/v1/workflows/${id}`),
  create: (data: any) => api.post('/api/v1/workflows/', data),
  run: (id: string) => api.post(`/api/v1/workflows/${id}/run`),
  getRuns: (id: string) => api.get(`/api/v1/workflows/${id}/runs`),
  getRun: (runId: string) => api.get(`/api/v1/workflows/runs/${runId}`),
  pendingApprovals: () => api.get('/api/v1/workflows/runs/pending'),
  approve: (runId: string, approved: boolean) =>
    api.post(`/api/v1/workflows/runs/${runId}/approve`, { approved }),
  pause: (runId: string) => api.post(`/api/v1/workflows/runs/${runId}/pause`),
  cancel: (runId: string) => api.post(`/api/v1/workflows/runs/${runId}/cancel`),
}

export const settingsApi = {
  integrations: () => api.get('/api/v1/settings/integrations'),
  getProviders: () => api.get('/api/v1/settings/providers'),
  set: (key: string, value: string) => api.put(`/api/v1/settings/${key}`, { value }),
  remove: (key: string) => api.delete(`/api/v1/settings/${key}`),
  llmStatus: () => api.get('/api/v1/settings/llm'),
  llmTest: (data: any) => api.post('/api/v1/settings/llm/test', data),
  githubTest: () => api.post('/api/v1/settings/github/test'),
  emailTest: (data?: any) => api.post('/api/v1/settings/email/test', data || {}),
}

export const whatsappApi = {
  status: () => api.get('/api/v1/whatsapp/status'),
  connect: () => api.post('/api/v1/whatsapp/connect'),
  disconnect: () => api.post('/api/v1/whatsapp/disconnect'),
  send: (to: string, message: string) => api.post('/api/v1/whatsapp/send', { to, message }),
}

export const emailApi = {
  providers: () => api.get('/api/v1/email/providers'),
  accounts: () => api.get('/api/v1/email/accounts'),
  create: (data: any) => api.post('/api/v1/email/accounts', data),
  update: (id: string, data: any) => api.patch(`/api/v1/email/accounts/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/email/accounts/${id}`),
  test: (id: string) => api.post(`/api/v1/email/accounts/${id}/test`),
  inbox: (id: string, limit = 15) => api.get(`/api/v1/email/accounts/${id}/inbox`, { params: { limit } }),
  send: (id: string, data: any) => api.post(`/api/v1/email/accounts/${id}/send`, data),
}

export const mcpApi = {
  servers: () => api.get('/api/v1/mcp/servers'),
  tools: (name: string) => api.get(`/api/v1/mcp/servers/${name}/tools`),
  call: (name: string, tool: string, arguments_: any) => api.post(`/api/v1/mcp/servers/${name}/call`, { tool, arguments: arguments_ }),
}

export const costsApi = {
  summary: () => api.get('/api/v1/costs/summary'),
  records: (limit = 50) => api.get('/api/v1/costs/records', { params: { limit } }),
}

export const policiesApi = {
  getAll: () => api.get('/api/v1/policies/'),
  create: (data: any) => api.post('/api/v1/policies/', data),
  delete: (id: string) => api.delete(`/api/v1/policies/${id}`),
  agents: () => api.get('/api/v1/policies/agents'),
}

export const tracesApi = {
  getAll: (limit = 60) => api.get('/api/v1/traces/', { params: { limit } }),
}

export const auditApi = {
  getAll: (params?: any) => api.get('/api/v1/audit/', { params }),
}

export const decisionsApi = {
  getAll: () => api.get('/api/v1/decisions/'),
  get: (id: string) => api.get(`/api/v1/decisions/${id}`),
  create: (data: any) => api.post('/api/v1/decisions/', data),
  delete: (id: string) => api.delete(`/api/v1/decisions/${id}`),
}

export const contextPacksApi = {
  getAll: () => api.get('/api/v1/context-packs/'),
  get: (id: string) => api.get(`/api/v1/context-packs/${id}`),
  create: (data: any) => api.post('/api/v1/context-packs/', data),
  generate: (data: any) => api.post('/api/v1/context-packs/generate', data),
  delete: (id: string) => api.delete(`/api/v1/context-packs/${id}`),
  export: (id: string, format = 'markdown') => api.get(`/api/v1/context-packs/${id}/export`, { params: { format } }),
  targets: () => api.get('/api/v1/context-packs/targets'),
  decisionsForPack: (id: string) => api.get(`/api/v1/decisions/pack/${id}`),
}

export const assistantApi = {
  ask: (query: string, context?: any) => api.post('/api/v1/assistant/ask', { query, context }),
}
