import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.get(`/api/v1/projects/${id}`).then(res => res.data)
  })

  if (isLoading) {
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
            <h2 className="text-lg font-semibold mb-4">Activity</h2>
            <p className="text-gray-500">Activity feed coming soon...</p>
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
