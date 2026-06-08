import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, githubApi } from '../services/api'

interface Commit {
  sha: string
  message: string
  author: string
  date: string
  url: string
}

interface Pull {
  id: number
  title: string
  state: string
  user: { login: string }
  created_at: string
  url: string
}

interface Issue {
  id: number
  title: string
  state: string
  user: { login: string }
  created_at: string
  url: string
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  
  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.get(`/api/v1/projects/${id}`).then(res => res.data)
  })

  const { data: commits } = useQuery<Commit[]>({
    queryKey: ['commits', project?.github_repo],
    queryFn: () => githubApi.getCommits(project.github_repo.split('/')[1]).then(res => res.data.commits),
    enabled: !!project?.github_repo
  })

  const { data: pulls } = useQuery<Pull[]>({
    queryKey: ['pulls', project?.github_repo],
    queryFn: () => api.get(`/api/v1/integrations/github/pulls/${project.github_repo.split('/')[1]}`).then(res => res.data.pulls),
    enabled: !!project?.github_repo
  })

  const { data: issues } = useQuery<Issue[]>({
    queryKey: ['issues', project?.github_repo],
    queryFn: () => api.get(`/api/v1/integrations/github/issues/${project.github_repo.split('/')[1]}`).then(res => res.data.issues),
    enabled: !!project?.github_repo
  })

  if (projectLoading) {
    return <div>Loading project...</div>
  }

  if (!project) {
    return <div>Project not found</div>
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
        <p className="text-gray-600 mt-1">{project.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Overview</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Status</p>
                <p className="font-medium capitalize">{project.status}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Priority</p>
                <p className="font-medium uppercase">{project.priority}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="font-medium capitalize">{project.category}</p>
              </div>
              {project.github_repo && (
                <div>
                  <p className="text-sm text-gray-500">GitHub</p>
                  <a href={`https://github.com/${project.github_repo}`} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                    {project.github_repo}
                  </a>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Recent Commits</h2>
            {commits && commits.length > 0 ? (
              <ul className="space-y-3">
                {commits.slice(0, 5).map((commit) => (
                  <li key={commit.sha} className="border-b pb-2 last:border-0">
                    <a href={commit.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline font-mono text-sm">
                      {commit.sha}
                    </a>
                    <p className="text-gray-700 text-sm truncate">{commit.message}</p>
                    <p className="text-xs text-gray-500">{commit.author} - {new Date(commit.date).toLocaleDateString()}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No commits found</p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Pull Requests</h2>
            {pulls && pulls.length > 0 ? (
              <ul className="space-y-3">
                {pulls.slice(0, 5).map((pr) => (
                  <li key={pr.id} className="border-b pb-2 last:border-0">
                    <a href={pr.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                      {pr.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${pr.state === 'open' ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800'}`}>
                        {pr.state}
                      </span>
                      <span className="text-xs text-gray-500">by {pr.user.login}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No pull requests found</p>
            )}
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Issues</h2>
            {issues && issues.length > 0 ? (
              <ul className="space-y-3">
                {issues.slice(0, 5).map((issue) => (
                  <li key={issue.id} className="border-b pb-2 last:border-0">
                    <a href={issue.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                      {issue.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${issue.state === 'open' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                        {issue.state}
                      </span>
                      <span className="text-xs text-gray-500">by {issue.user.login}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No issues found</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Tech Stack</h2>
            {project.tech_stack?.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {project.tech_stack.map((tech: string) => (
                  <span key={tech} className="px-3 py-1 bg-gray-100 rounded-full text-sm">
                    {tech}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No tech stack defined</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
