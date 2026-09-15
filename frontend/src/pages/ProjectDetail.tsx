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
    return <div className="text-primary-400 animate-blink">Loading mission...</div>
  }

  if (!project) {
    return <div className="text-gray-500">Mission not found</div>
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// {project.name}</h1>
        <p className="text-gray-400 mt-1">{project.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-6">
            <h2 className="text-sm font-bold text-primary-400 tracking-wider mb-4">OVERVIEW</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Status</p>
                <p className="font-medium capitalize text-gray-200">{project.status}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Priority</p>
                <p className="font-medium uppercase text-gray-200">{project.priority}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider">Category</p>
                <p className="font-medium capitalize text-gray-200">{project.category}</p>
              </div>
              {project.github_repo && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider">GitHub</p>
                  <a href={`https://github.com/${project.github_repo}`} target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">
                    {project.github_repo}
                  </a>
                </div>
              )}
            </div>
          </div>

          <div className="bg-bg-900 border border-bg-700 rounded-lg p-6">
            <h2 className="text-sm font-bold text-primary-400 tracking-wider mb-4">RECENT_COMMITS</h2>
            {commits && commits.length > 0 ? (
              <ul className="space-y-3">
                {commits.slice(0, 5).map((commit) => (
                  <li key={commit.sha} className="border-b border-bg-800 pb-2 last:border-0">
                    <a href={commit.url} target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline font-mono text-sm">
                      {commit.sha.slice(0, 8)}
                    </a>
                    <p className="text-gray-300 text-sm truncate">{commit.message}</p>
                    <p className="text-xs text-gray-500">{commit.author} — {new Date(commit.date).toLocaleDateString()}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500">No commits found</p>
            )}
          </div>

          <div className="bg-bg-900 border border-bg-700 rounded-lg p-6">
            <h2 className="text-sm font-bold text-primary-400 tracking-wider mb-4">PULL_REQUESTS</h2>
            {pulls && pulls.length > 0 ? (
              <ul className="space-y-3">
                {pulls.slice(0, 5).map((pr) => (
                  <li key={pr.id} className="border-b border-bg-800 pb-2 last:border-0">
                    <a href={pr.url} target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">
                      {pr.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-0.5 text-xs rounded-full border ${pr.state === 'open' ? 'bg-green-500/10 text-green-400 border-green-500/40' : 'bg-purple-500/10 text-purple-400 border-purple-500/40'}`}>
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

          <div className="bg-bg-900 border border-bg-700 rounded-lg p-6">
            <h2 className="text-sm font-bold text-primary-400 tracking-wider mb-4">ISSUES</h2>
            {issues && issues.length > 0 ? (
              <ul className="space-y-3">
                {issues.slice(0, 5).map((issue) => (
                  <li key={issue.id} className="border-b border-bg-800 pb-2 last:border-0">
                    <a href={issue.url} target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">
                      {issue.title}
                    </a>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-0.5 text-xs rounded-full border ${issue.state === 'open' ? 'bg-green-500/10 text-green-400 border-green-500/40' : 'bg-gray-500/10 text-gray-400 border-gray-500/40'}`}>
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
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-6">
            <h2 className="text-sm font-bold text-primary-400 tracking-wider mb-4">TECH_STACK</h2>
            {project.tech_stack?.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {project.tech_stack.map((tech: string) => (
                  <span key={tech} className="px-3 py-1 bg-bg-800 text-gray-300 rounded-full text-xs border border-bg-700">
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
