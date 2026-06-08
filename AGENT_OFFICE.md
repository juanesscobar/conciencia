# 🏢 Mission Control — Agent Office Dashboard

**Panel visual interactivo de los 8 agentes trabajando en la oficina.**

## 🚀 Quick Start

```bash
# 1. Backend (terminal 1)
cd backend
uvicorn app.main:app --reload

# 2. Frontend (terminal 2)
cd frontend
npm run dev

# 3. Abrir http://localhost:5173
```

## 🎯 Nuevo Feature: AgentOffice Component

Ubicación: `frontend/src/components/AgentOffice.tsx`

### Características
- **8 escritorios** con agentes animados
- **Monitores** con código parpadeante
- **Ventanas** con cielo dinámico (día/noche)
- **Estados visuales**: working, idle, meeting, break
- **Click para detalles**: productividad, tarea actual
- **Stats en tiempo real**: agentes activos, productividad promedio

### Agentes incluidos
| Emoji | Nombre | Rol | Estado default |
|-------|--------|-----|----------------|
| 👨‍💻 | Dev | Developer | working |
| 🚀 | Ops | DevOps | working |
| 🧪 | QA | Tester | idle |
| 📊 | PM | Project Manager | meeting |
| 📚 | R&D | Researcher | working |
| 🎨 | Comms | Communications | break |
| 💰 | Fin | Finance | working |
| 🎯 | Admin | Administrator | working |

## 🎨 Personalización

Los agentes están definidos en `AgentOffice.tsx` línea 17-26:

```typescript
const DEFAULT_AGENTS: Agent[] = [
  { id: '1', name: 'Dev', role: 'Developer', emoji: '👨‍💻', status: 'working', ... },
  // ...
]
```

## 🔄 Integración con API (TODO)

Actualmente usa datos simulados. Para conectar con API real:

```typescript
const { data: apiAgents } = useQuery({
  queryKey: ['agents'],
  queryFn: () => api.get('/api/v1/agents/').then(res => res.data),
  enabled: true // Cambiar a true
})
```

## 🖼️ Screenshot esperado

```
┌─────────────────────────────────────────────┐
│  🏢 Mission Control HQ          15:30 PY    │
│  Iron Toto Software Factory                 │
├─────────────────────────────────────────────┤
│  🟢 Activos: 6/8   📊 87%   🟡 1   🟣 1   │
├─────────────────────────────────────────────┤
│  🪟 🪟 🪟  (ventanas con cielo)            │
│                                             │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐               │
│  │💻👨‍💻│ │💻🚀 │ │💻🧪 │ │💻📊 │  (desks)  │
│  │Dev │ │Ops │ │QA  │ │PM  │               │
│  └────┘ └────┘ └────┘ └────┘               │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐               │
│  │💻📚│ │💻🎨│ │💻💰│ │💻🎯│               │
│  │R&D │ │Com │ │Fin │ │Adm │               │
│  └────┘ └────┘ └────┘ └────┘               │
└─────────────────────────────────────────────┘
```

---

**Creado:** 2026-02-27  
**Por:** Admin Agent para Iron Toto
