import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface Memory {
  id: string
  title: string
  content: string
  category: string
  created_at: string
  updated_at: string
}

const categoryColors: Record<string, string> = {
  general: 'text-gray-400 border-gray-500/40 bg-gray-500/10',
  project: 'text-neon-400 border-neon-500/40 bg-neon-500/10',
  decision: 'text-primary-400 border-primary-500/40 bg-primary-500/10',
  preference: 'text-purple-400 border-purple-500/40 bg-purple-500/10',
}

export default function UserMemory() {
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [category, setCategory] = useState('general')
  const [editingId, setEditingId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const { data: memories } = useQuery<Memory[]>({
    queryKey: ['memories'],
    queryFn: () => api.get('/api/v1/memories/').then(res => res.data),
  })

  const createMemory = useMutation({
    mutationFn: (data: any) => api.post('/api/v1/memories/', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] })
      setShowForm(false)
      setTitle('')
      setContent('')
      setCategory('general')
    },
  })

  const updateMemory = useMutation({
    mutationFn: ({ id, data }: { id: string, data: any }) => api.put(`/api/v1/memories/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memories'] })
      setShowForm(false)
      setEditingId(null)
      setTitle('')
      setContent('')
    },
  })

  const deleteMemory = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/memories/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memories'] }),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !content.trim()) return
    if (editingId) {
      updateMemory.mutate({ id: editingId, data: { title, content, category } })
    } else {
      createMemory.mutate({ title, content, category })
    }
  }

  const startEdit = (mem: Memory) => {
    setEditingId(mem.id)
    setTitle(mem.title)
    setContent(mem.content)
    setCategory(mem.category)
    setShowForm(true)
  }

  return (
    <div className="hack-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-bg-950 border-b border-bg-700">
        <span className="text-xs text-gray-500">// user_memory — {user?.username || 'operator'}</span>
        <button
          onClick={() => { setShowForm(!showForm); setEditingId(null); setTitle(''); setContent(''); }}
          className="text-xs text-primary-400 hover:text-primary-300"
        >
          {showForm ? '[ cerrar ]' : '[ + recordar ]'}
        </button>
      </div>

      <div className="p-4">
        {showForm && (
          <form onSubmit={handleSubmit} className="mb-4 space-y-3 bg-bg-950 border border-bg-800 rounded-lg p-3">
            <div>
              <label className="block text-xs font-medium text-primary-400 mb-1">$ titulo</label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="hack-input text-sm"
                placeholder="Ej: Decisión sobre stack tecnológico"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-primary-400 mb-1">$ contenido</label>
              <textarea
                value={content}
                onChange={e => setContent(e.target.value)}
                rows={3}
                className="hack-input text-sm"
                placeholder="Lo que querés recordar..."
                required
              />
            </div>
            <div className="flex items-center justify-between">
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                className="hack-select text-xs"
              >
                <option value="general">general</option>
                <option value="project">project</option>
                <option value="decision">decision</option>
                <option value="preference">preference</option>
              </select>
              <button
                type="submit"
                className="px-4 py-1.5 bg-primary-600/90 text-bg-950 font-bold rounded text-xs hover:bg-primary-500 transition-all"
              >
                {editingId ? '[ GUARDAR ]' : '[ GUARDAR ]'}
              </button>
            </div>
          </form>
        )}

        {memories && memories.length > 0 ? (
          <ul className="space-y-3">
            {memories.map((mem) => (
              <li key={mem.id} className="border border-bg-800 rounded-lg p-3 hover:border-primary-500/30 transition-colors">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium text-gray-200">{mem.title}</p>
                  <span className={`px-2 py-0.5 text-[10px] rounded-full ${categoryColors[mem.category] || categoryColors.general}`}>
                    {mem.category}
                  </span>
                </div>
                <p className="text-xs text-gray-500 whitespace-pre-wrap">{mem.content}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-[10px] text-gray-700">
                    updated {new Date(mem.updated_at).toLocaleDateString()}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => startEdit(mem)}
                      className="text-[10px] text-neon-400 hover:text-neon-300"
                    >
                      [editar]
                    </button>
                    <button
                      onClick={() => deleteMemory.mutate(mem.id)}
                      className="text-[10px] text-alert-400 hover:text-alert-300"
                    >
                      [borrar]
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-600 text-sm">
            No memories yet. <span className="text-primary-500">[ + recordar ]</span> para guardar tu contexto.
          </p>
        )}
      </div>
    </div>
  )
}
