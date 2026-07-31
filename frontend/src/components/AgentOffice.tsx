import { useState, useEffect } from 'react'

interface Agent {
  id: string
  name: string
  role: string
  emoji: string
  status: 'working' | 'idle' | 'meeting' | 'break'
  currentTask?: string
  productivity: number
}

// Agentes predefinidos según SOUL.md
const DEFAULT_AGENTS: Agent[] = [
  { id: '1', name: 'Dev', role: 'Developer', emoji: '👨‍💻', status: 'working', currentTask: 'Code review', productivity: 95 },
  { id: '2', name: 'Ops', role: 'DevOps', emoji: '🚀', status: 'working', currentTask: 'Deploy to prod', productivity: 88 },
  { id: '3', name: 'QA', role: 'Tester', emoji: '🧪', status: 'idle', currentTask: undefined, productivity: 75 },
  { id: '4', name: 'PM', role: 'Project Manager', emoji: '📊', status: 'meeting', currentTask: 'Sprint planning', productivity: 82 },
  { id: '5', name: 'R&D', role: 'Researcher', emoji: '📚', status: 'working', currentTask: 'AI research', productivity: 91 },
  { id: '6', name: 'Comms', role: 'Communications', emoji: '🎨', status: 'break', currentTask: undefined, productivity: 70 },
  { id: '7', name: 'Fin', role: 'Finance', emoji: '💰', status: 'working', currentTask: 'Budget report', productivity: 85 },
  { id: '8', name: 'Admin', role: 'Admin', emoji: '🎯', status: 'working', currentTask: 'Scheduling', productivity: 90 },
]

export default function AgentOffice() {
  const [agents, setAgents] = useState<Agent[]>(DEFAULT_AGENTS)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [time, setTime] = useState(new Date())

  // Reloj de la oficina
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Simular cambios de estado de agentes
  useEffect(() => {
    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => {
        // 10% chance de cambiar estado
        if (Math.random() > 0.9) {
          const statuses: Array<'working' | 'idle' | 'meeting' | 'break'> = 
            ['working', 'working', 'working', 'idle', 'meeting', 'break']
          const newStatus = statuses[Math.floor(Math.random() * statuses.length)]
          return { ...agent, status: newStatus }
        }
        return agent
      }))
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const workingCount = agents.filter(a => a.status === 'working').length
  const totalProductivity = Math.round(agents.reduce((acc, a) => acc + a.productivity, 0) / agents.length)

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl shadow-2xl p-6 text-white overflow-hidden relative">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            🏢 Mission Control HQ
          </h2>
          <p className="text-slate-400 text-sm">Iron Toto Software Factory</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-3xl font-mono font-bold text-cyan-400">
              {time.toLocaleTimeString('es-PY', { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div className="text-xs text-slate-500">Asunción, PY (GMT-3)</div>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex gap-4 mb-6">
        <StatBox label="Agentes Activos" value={`${workingCount}/8`} color="green" />
        <StatBox label="Productividad" value={`${totalProductivity}%`} color="cyan" />
        <StatBox label="En Reunión" value={agents.filter(a => a.status === 'meeting').length} color="yellow" />
        <StatBox label="En Pausa" value={agents.filter(a => a.status === 'break').length} color="purple" />
      </div>

      {/* Office Layout - Grid de escritorios */}
      <div className="relative bg-slate-950/50 rounded-xl p-6 border border-slate-700/50">
        {/* Pared fondo */}
        <div className="absolute top-0 left-0 right-0 h-4 bg-gradient-to-b from-slate-700/30 to-transparent rounded-t-xl" />
        
        {/* Ventanas */}
        <div className="flex justify-center gap-8 mb-8">
          <Window time={time} />
          <Window time={time} />
          <Window time={time} />
        </div>

        {/* Grid de escritorios */}
        <div className="grid grid-cols-4 gap-6">
            {agents.map((agent) => (
            <Desk 
              key={agent.id} 
              agent={agent} 
              onClick={() => setSelectedAgent(agent)}
              isSelected={selectedAgent?.id === agent.id}
            />
          ))}
        </div>

        {/* Piso */}
        <div className="mt-6 h-8 bg-gradient-to-t from-slate-800/50 to-transparent rounded-b-xl" />
      </div>

      {/* Panel de detalle del agente seleccionado */}
      {selectedAgent && (
        <div className="mt-6 bg-slate-800/80 rounded-xl p-4 border border-slate-600 animate-fadeIn">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="text-5xl">{selectedAgent.emoji}</div>
              <div>
                <h3 className="text-xl font-bold">{selectedAgent.name}</h3>
                <p className="text-slate-400">{selectedAgent.role}</p>
                <div className="flex items-center gap-2 mt-2">
                  <StatusDot status={selectedAgent.status} />
                  <span className="text-sm capitalize">{selectedAgent.status}</span>
                  {selectedAgent.currentTask && (
                    <>
                      <span className="text-slate-600">•</span>
                      <span className="text-sm text-cyan-400">{selectedAgent.currentTask}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            <button 
              onClick={() => setSelectedAgent(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          
          {/* Barra de productividad */}
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-400">Productividad</span>
              <span className="font-bold">{selectedAgent.productivity}%</span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all duration-500 ${
                  selectedAgent.productivity > 90 ? 'bg-green-500' :
                  selectedAgent.productivity > 75 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${selectedAgent.productivity}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Desk({ agent, onClick, isSelected }: { 
  agent: Agent
  onClick: () => void
  isSelected: boolean 
}) {
  const [isTyping, setIsTyping] = useState(false)

  useEffect(() => {
    if (agent.status === 'working') {
      const interval = setInterval(() => {
        setIsTyping(true)
        setTimeout(() => setIsTyping(false), 500)
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [agent.status])

  return (
    <div 
      onClick={onClick}
      className={`relative cursor-pointer transition-all duration-300 hover:scale-105 ${
        isSelected ? 'scale-105 z-10' : ''
      }`}
    >
      {/* Escritorio */}
      <div className={`bg-slate-800 rounded-lg p-3 border-2 transition-all duration-300 ${
        isSelected ? 'border-cyan-500 shadow-lg shadow-cyan-500/20' : 'border-slate-700 hover:border-slate-600'
      }`}>
        {/* Monitor */}
        <div className="bg-slate-900 rounded-t-md h-12 mb-2 relative overflow-hidden">
          <div className={`absolute inset-0 opacity-50 ${
            agent.status === 'working' ? 'bg-green-500/20' :
            agent.status === 'idle' ? 'bg-yellow-500/20' :
            agent.status === 'meeting' ? 'bg-blue-500/20' :
            'bg-purple-500/20'
          }`} />
          {/* Pantalla con código/animación */}
          <div className="absolute inset-2 flex gap-0.5 flex-wrap content-start">
            {[...Array(8)].map((_, i) => (
              <div 
                key={i} 
                className={`h-1 rounded-full ${isTyping && i < 4 ? 'bg-green-400 w-4' : 'bg-slate-700 w-2'}`}
              />
            ))}
          </div>
        </div>
        
        {/* Teclado */}
        <div className="bg-slate-700 h-3 rounded-sm mb-2" />
        
        {/* Agente */}
        <div className="flex justify-center">
          <div className={`text-4xl transition-transform duration-300 ${
            agent.status === 'working' && isTyping ? 'scale-110' : ''
          } ${agent.status === 'break' ? 'grayscale' : ''}`}>
            {agent.emoji}
          </div>
        </div>
        
        {/* Nombre y estado */}
        <div className="mt-2 text-center">
          <div className="text-xs font-bold truncate">{agent.name}</div>
          <div className="flex justify-center mt-1">
            <StatusDot status={agent.status} />
          </div>
        </div>
      </div>
      
      {/* Silla */}
      <div className="mx-auto w-8 h-6 bg-slate-700 rounded-b-lg mt-1" />
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors = {
    working: 'bg-green-500 animate-pulse',
    idle: 'bg-yellow-500',
    meeting: 'bg-blue-500 animate-pulse',
    break: 'bg-purple-500',
  }
  return (
    <div className={`w-2.5 h-2.5 rounded-full ${colors[status as keyof typeof colors] || colors.idle}`} />
  )
}

function StatBox({ label, value, color }: { label: string, value: string | number, color: 'green' | 'cyan' | 'yellow' | 'purple' }) {
  const colors = {
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  }
  
  return (
    <div className={`flex-1 rounded-lg p-3 border ${colors[color]}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-80">{label}</div>
    </div>
  )
}

function Window({ time }: { time: Date }) {
  const hour = time.getHours()
  const isDay = hour >= 6 && hour < 18
  const isSunset = hour >= 17 && hour < 19
  
  return (
    <div className="w-24 h-32 bg-slate-800 rounded-lg border-4 border-slate-700 relative overflow-hidden">
      {/* Cielo */}
      <div className={`absolute inset-0 transition-all duration-1000 ${
        isDay ? 'bg-gradient-to-b from-blue-400 to-blue-200' :
        isSunset ? 'bg-gradient-to-b from-orange-500 to-purple-600' :
        'bg-gradient-to-b from-slate-900 to-slate-800'
      }`}>
        {/* Sol/Luna */}
        {isDay && (
          <div className="absolute top-3 right-3 w-6 h-6 bg-yellow-300 rounded-full shadow-lg shadow-yellow-300/50" />
        )}
        {!isDay && !isSunset && (
          <div className="absolute top-3 right-3 w-5 h-5 bg-slate-200 rounded-full shadow-lg" />
        )}
        
        {/* Nubes */}
        {isDay && (
          <>
            <div className="absolute top-6 left-2 w-8 h-3 bg-white/60 rounded-full" />
            <div className="absolute top-10 right-4 w-6 h-2 bg-white/40 rounded-full" />
          </>
        )}
        
        {/* Estrellas */}
        {!isDay && (
          <>
            <div className="absolute top-4 left-4 w-1 h-1 bg-white rounded-full animate-pulse" />
            <div className="absolute top-8 right-6 w-0.5 h-0.5 bg-white rounded-full" />
            <div className="absolute top-12 left-8 w-1 h-1 bg-white rounded-full animate-pulse" />
          </>
        )}
      </div>
      
      {/* Marco de ventana */}
      <div className="absolute inset-y-0 left-1/2 w-1 bg-slate-700 -translate-x-1/2" />
      <div className="absolute inset-x-0 top-1/2 h-1 bg-slate-700 -translate-y-1/2" />
    </div>
  )
}
