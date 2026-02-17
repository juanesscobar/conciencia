const agents = [
  { name: 'Dev', emoji: '👨‍💻', role: 'Developer', status: 'active' },
  { name: 'Ops', emoji: '🚀', role: 'DevOps', status: 'active' },
  { name: 'QA', emoji: '🧪', role: 'Quality Assurance', status: 'active' },
  { name: 'PM', emoji: '📊', role: 'Product Manager', status: 'active' },
  { name: 'R&D', emoji: '📚', role: 'Research & Development', status: 'active' },
  { name: 'Comms', emoji: '🎨', role: 'Communications', status: 'active' },
  { name: 'Fin', emoji: '💰', role: 'Finance', status: 'active' },
  { name: 'Admin', emoji: '🎯', role: 'Administration', status: 'active' },
]

export default function Agents() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Agents</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map((agent) => (
          <div key={agent.name} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <span className="text-3xl mr-3">{agent.emoji}</span>
              <div>
                <h3 className="font-semibold text-gray-900">{agent.name}</h3>
                <p className="text-sm text-gray-500">{agent.role}</p>
              </div>
            </div>
            <div className="mt-4">
              <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                {agent.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
