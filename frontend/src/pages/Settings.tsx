import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi, whatsappApi } from '../services/api'
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

const PROVIDERS = [
  { id: 'deepseek', label: 'DeepSeek', defaultModel: 'deepseek-chat', defaultBase: 'https://api.deepseek.com' },
  { id: 'openai', label: 'OpenAI', defaultModel: 'gpt-4o-mini', defaultBase: 'https://api.openai.com/v1' },
  { id: 'openrouter', label: 'OpenRouter', defaultModel: 'deepseek/deepseek-chat', defaultBase: 'https://openrouter.ai/api/v1' },
  { id: 'ollama', label: 'Ollama (local)', defaultModel: 'llama3.2', defaultBase: 'http://localhost:11434/v1' },
]

function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-bg-900 border border-bg-700 rounded-lg p-5">
      <h2 className="text-sm font-bold text-primary-400 tracking-wider">// {title}</h2>
      {subtitle && <p className="text-xs text-gray-500 mt-1 mb-4">{subtitle}</p>}
      {!subtitle && <div className="mb-4" />}
      {children}
    </div>
  )
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${ok ? 'text-primary-400 border-primary-500/40 bg-primary-500/10' : 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-primary-400' : 'bg-yellow-400'} animate-blink`}></span>
      {label}
    </span>
  )
}

export default function Settings() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'ceo' || user?.role === 'owner'

  const { data: integrations } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => settingsApi.integrations().then(res => res.data),
  })

  // ---- GitHub ----
  const [ghToken, setGhToken] = useState('')
  const [ghMsg, setGhMsg] = useState('')
  const saveGh = useMutation({
    mutationFn: () => settingsApi.set('GITHUB_TOKEN', ghToken),
    onSuccess: () => { setGhToken(''); setGhMsg('Token GitHub guardado'); queryClient.invalidateQueries({ queryKey: ['integrations'] }); setTimeout(() => setGhMsg(''), 4000) },
    onError: (e: any) => { setGhMsg(e.response?.data?.detail || 'Error al guardar'); setTimeout(() => setGhMsg(''), 5000) },
  })
  const testGh = useMutation({
    mutationFn: () => settingsApi.githubTest(),
    onSuccess: (r: any) => setGhMsg(r.data.ok ? `GitHub OK: @${r.data.login}` : `GitHub: ${r.data.error}`),
  })

  // ---- LLM ----
  const [provider, setProvider] = useState('deepseek')
  const [llmKey, setLlmKey] = useState('')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [llmMsg, setLlmMsg] = useState('')
  const [llmTestResult, setLlmTestResult] = useState<any>(null)

  const saveLlm = useMutation({
    mutationFn: async () => {
      const p = PROVIDERS.find(x => x.id === provider)!
      await settingsApi.set('LLM_PROVIDER', provider)
      if (llmKey.trim()) await settingsApi.set('LLM_API_KEY', llmKey.trim())
      await settingsApi.set('LLM_MODEL', model.trim() || p.defaultModel)
      await settingsApi.set('LLM_BASE_URL', baseUrl.trim() || p.defaultBase)
    },
    onSuccess: () => { setLlmKey(''); setLlmMsg('Proveedor IA configurado'); queryClient.invalidateQueries({ queryKey: ['integrations'] }); setTimeout(() => setLlmMsg(''), 4000) },
    onError: (e: any) => { setLlmMsg(e.response?.data?.detail || 'Error al guardar'); setTimeout(() => setLlmMsg(''), 5000) },
  })

  const testLlm = useMutation({
    mutationFn: () => settingsApi.llmTest({
      provider,
      api_key: llmKey.trim() || undefined,
      model: model.trim() || undefined,
      base_url: baseUrl.trim() || undefined,
    }),
    onSuccess: (r: any) => setLlmTestResult(r.data),
    onError: (e: any) => setLlmTestResult({ ok: false, error: e.response?.data?.detail || 'Error de conexión' }),
  })

  // ---- Lead Hunter ----
  const [lhCron, setLhCron] = useState('')
  const [lhBbox, setLhBbox] = useState('')
  const [lhScope, setLhScope] = useState('bbox')
  const [lhMsg, setLhMsg] = useState('')
  const saveLh = useMutation({
    mutationFn: () => Promise.all([
      settingsApi.set('LEADHUNTER_CRON', lhCron.trim()),
      settingsApi.set('LEADHUNTER_BBOX', lhBbox.trim()),
      settingsApi.set('LEADHUNTER_SCOPE', lhScope),
    ]),
    onSuccess: () => { setLhMsg('Config de Lead Hunter guardada'); queryClient.invalidateQueries({ queryKey: ['integrations'] }); setTimeout(() => setLhMsg(''), 4000) },
    onError: (e: any) => { setLhMsg(e.response?.data?.detail || 'Error al guardar'); setTimeout(() => setLhMsg(''), 5000) },
  })

  // ---- Email (SMTP) ----
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState('')
  const [smtpUser, setSmtpUser] = useState('')
  const [smtpPass, setSmtpPass] = useState('')
  const [smtpFrom, setSmtpFrom] = useState('')
  const [smtpMsg, setSmtpMsg] = useState('')
  const [smtpTestResult, setSmtpTestResult] = useState<any>(null)

  const saveSmtp = useMutation({
    mutationFn: () => Promise.all([
      settingsApi.set('SMTP_HOST', smtpHost.trim()),
      settingsApi.set('SMTP_PORT', smtpPort.trim() || '587'),
      settingsApi.set('SMTP_USER', smtpUser.trim()),
      settingsApi.set('SMTP_FROM', smtpFrom.trim()),
      ...(smtpPass.trim() ? [settingsApi.set('SMTP_PASS', smtpPass.trim())] : []),
    ]),
    onSuccess: () => { setSmtpPass(''); setSmtpMsg('Configuración de email guardada'); queryClient.invalidateQueries({ queryKey: ['integrations'] }); setTimeout(() => setSmtpMsg(''), 4000) },
    onError: (e: any) => { setSmtpMsg(e.response?.data?.detail || 'Error al guardar'); setTimeout(() => setSmtpMsg(''), 5000) },
  })

  const testSmtp = useMutation({
    mutationFn: () => settingsApi.emailTest({ to_email: smtpFrom.trim() || undefined }),
    onSuccess: (r: any) => setSmtpTestResult(r.data),
    onError: (e: any) => setSmtpTestResult({ sent: false, error: e.response?.data?.detail || 'Error al probar' }),
  })

  // ---- WhatsApp Business ----
  const [waModal, setWaModal] = useState(false)
  const [waMsg, setWaMsg] = useState('')
  const { data: wa, refetch: waRefetch } = useQuery({
    queryKey: ['wa-status'],
    queryFn: () => whatsappApi.status().then(res => res.data),
    refetchInterval: waModal ? 2500 : 8000,
  })

  const waConnect = useMutation({
    mutationFn: () => whatsappApi.connect(),
    onSuccess: (r: any) => {
      if (r.data?.ok) { setWaModal(true); waRefetch() }
      else setWaMsg(r.data?.error || 'Error al conectar')
    },
  })

  const waDisconnect = useMutation({
    mutationFn: () => whatsappApi.disconnect(),
    onSuccess: () => { setWaModal(false); waRefetch() },
  })

  const gh = integrations?.github
  const llm = integrations?.llm
  const lh = integrations?.leadhunter
  const email = integrations?.email

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// CONFIGURACIÓN · INTEGRACIONES</h1>
        <p className="text-sm text-gray-500 mt-1">Conexiones por API agrupadas: GitHub, proveedor IA y Lead Hunter</p>
      </div>

      {!isAdmin && (
        <div className="bg-yellow-500/10 border border-yellow-500/40 text-yellow-400 text-sm rounded-lg p-4 mb-6">
          ⚠️ Solo el admin (Iron Toto) puede modificar integraciones.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* GitHub */}
        <Card title="GITHUB" subtitle="Sincronización de repos, commits y PRs">
          <div className="flex items-center justify-between mb-4">
            <StatusBadge ok={!!gh?.configured} label={gh?.configured ? `Conectado · @${gh?.username}` : 'Sin token'} />
            <button
              onClick={() => testGh.mutate()}
              disabled={!gh?.configured || testGh.isPending}
              className="text-xs px-3 py-1.5 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 transition-colors disabled:opacity-40"
            >
              {testGh.isPending ? 'Probando...' : 'Probar conexión'}
            </button>
          </div>
          <label className="text-xs text-gray-500 uppercase tracking-wider">Token (PAT)</label>
          <input
            type="password"
            value={ghToken}
            onChange={e => setGhToken(e.target.value)}
            placeholder="ghp_..."
            className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50"
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={() => saveGh.mutate()}
              disabled={!ghToken.trim() || saveGh.isPending || !isAdmin}
              className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
            >
              Guardar token
            </button>
          </div>
          {ghMsg && <p className="text-xs text-gray-400 mt-2">{ghMsg}</p>}
        </Card>

        {/* Proveedor IA */}
        <Card title="PROVEEDOR IA" subtitle="Motor de agentes y propuestas con IA (DeepSeek, OpenAI, OpenRouter, Ollama)">
          <div className="flex items-center gap-2 mb-4">
            <StatusBadge ok={!!llm?.configured} label={llm?.configured ? `Activo · ${llm?.provider} · ${llm?.model}` : 'Modo simulado'} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Proveedor</label>
              <select value={provider} onChange={e => setProvider(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Modelo</label>
              <input value={model} onChange={e => setModel(e.target.value)} placeholder={PROVIDERS.find(p => p.id === provider)?.defaultModel} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">API key</label>
              <input type="password" value={llmKey} onChange={e => setLlmKey(e.target.value)} placeholder="sk-..." className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Base URL</label>
              <input value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder={PROVIDERS.find(p => p.id === provider)?.defaultBase} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-3">
            <button
              onClick={() => testLlm.mutate()}
              disabled={testLlm.isPending || !isAdmin}
              className="px-4 py-2 text-sm rounded-lg border border-bg-600 text-primary-400 hover:border-primary-500/50 transition-colors disabled:opacity-40"
            >
              {testLlm.isPending ? 'Probando...' : 'Probar conexión'}
            </button>
            <button
              onClick={() => saveLlm.mutate()}
              disabled={saveLlm.isPending || !isAdmin}
              className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
            >
              Guardar
            </button>
          </div>
          {llmTestResult && (
            <div className={`mt-3 p-3 rounded-lg border text-xs font-mono ${llmTestResult.ok ? 'text-primary-400 border-primary-500/40 bg-primary-500/5' : 'text-alert-400 border-alert-500/40 bg-alert-500/5'}`}>
              {llmTestResult.ok
                ? `✓ ${llmTestResult.provider} · modelo ${llmTestResult.model} · ${llmTestResult.latency_ms}ms · "${llmTestResult.reply}"`
                : `✗ ${llmTestResult.provider}: ${llmTestResult.error}`}
            </div>
          )}
          {llmMsg && <p className="text-xs text-gray-400 mt-2">{llmMsg}</p>}
        </Card>

        {/* Email (SMTP) */}
        <Card title="EMAIL (SMTP)" subtitle="Envía propuestas por correo real desde tu cuenta">
          <div className="flex items-center justify-between mb-4">
            <StatusBadge ok={!!email?.smtp_configured} label={email?.smtp_configured ? `Conectado · ${email?.host}` : 'Sin configurar'} />
            <button
              onClick={() => testSmtp.mutate()}
              disabled={testSmtp.isPending || !isAdmin}
              className="text-xs px-3 py-1.5 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50 transition-colors disabled:opacity-40"
            >
              {testSmtp.isPending ? 'Enviando test...' : 'Enviar email de prueba'}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Host SMTP</label>
              <input value={smtpHost} onChange={e => setSmtpHost(e.target.value)} placeholder={email?.host || 'smtp.gmail.com'} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Puerto</label>
              <input value={smtpPort} onChange={e => setSmtpPort(e.target.value)} placeholder="587" className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Usuario</label>
              <input value={smtpUser} onChange={e => setSmtpUser(e.target.value)} placeholder="tu@email.com" className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Contraseña / App password</label>
              <input type="password" value={smtpPass} onChange={e => setSmtpPass(e.target.value)} placeholder="••••••••" className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
            <div className="md:col-span-3">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Remitente (From)</label>
              <input value={smtpFrom} onChange={e => setSmtpFrom(e.target.value)} placeholder={email?.from || 'tu@email.com'} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50" />
            </div>
          </div>
          <div className="flex justify-end mt-3">
            <button
              onClick={() => saveSmtp.mutate()}
              disabled={!smtpHost.trim() || saveSmtp.isPending || !isAdmin}
              className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
            >
              Guardar
            </button>
          </div>
          {smtpTestResult && (
            <div className={`mt-3 p-3 rounded-lg border text-xs font-mono ${smtpTestResult.sent ? 'text-primary-400 border-primary-500/40 bg-primary-500/5' : 'text-alert-400 border-alert-500/40 bg-alert-500/5'}`}>
              {smtpTestResult.sent
                ? `✓ Email enviado por SMTP a ${smtpTestResult.to}`
                : `✗ ${smtpTestResult.error || 'SMTP no configurado — revisá host/usuario/contraseña'}`}
            </div>
          )}
          {smtpMsg && <p className="text-xs text-gray-400 mt-2">{smtpMsg}</p>}
          <p className="text-xs text-gray-600 mt-3">
            💡 Gmail: usá una <span className="text-gray-400">App password</span> (2FA activado). Cuando no hay SMTP, las propuestas se envían vía mailto.
          </p>
        </Card>

        {/* WhatsApp Business */}
        <Card title="WHATSAPP BUSINESS" subtitle="Conectá tu número escaneando un QR y enviá propuestas por chat">
          <div className="flex items-center justify-between mb-4">
            <StatusBadge ok={wa?.state === 'connected'} label={
              wa?.state === 'connected' ? `Conectado · ${wa?.phone ? `+${wa.phone}` : 'WhatsApp'}`
                : wa?.state === 'qr' ? 'Escaneá el QR para conectar'
                : wa?.state === 'error' ? 'Error de conexión'
                : 'Desconectado'
            } />
            <div className="flex gap-2">
              {wa?.state === 'connected' ? (
                <button
                  onClick={() => { if (confirm('¿Cerrar sesión de WhatsApp?')) waDisconnect.mutate() }}
                  disabled={waDisconnect.isPending || !isAdmin}
                  className="text-xs px-3 py-1.5 rounded border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 transition-colors disabled:opacity-40"
                >
                  Desconectar
                </button>
              ) : (
                <button
                  onClick={() => waConnect.mutate()}
                  disabled={waConnect.isPending || !isAdmin}
                  className="text-xs px-3 py-1.5 rounded border border-primary-500/40 text-primary-400 hover:bg-primary-500/10 transition-colors disabled:opacity-40"
                >
                  {waConnect.isPending ? 'Conectando...' : wa?.state === 'qr' ? 'Ver QR' : 'Conectar con QR'}
                </button>
              )}
            </div>
          </div>
          {wa?.state === 'error' && wa?.error && (
            <p className="text-xs text-alert-400 mb-3">⚠️ {wa.error}</p>
          )}
          {waMsg && <p className="text-xs text-gray-400 mb-2">{waMsg}</p>}
          <p className="text-xs text-gray-600">
            💡 Se conecta a <span className="text-gray-400">WhatsApp Web</span> (multi-dispositivo) con whatsapp-web.js. Si tu número es una cuenta Business, esta es tu vía oficial. La sesión queda guardada localmente.
          </p>
        </Card>

        {/* Lead Hunter */}
        <Card title="LEAD HUNTER" subtitle="Configuración del descubrimiento automático de leads">
          <div className="flex items-center gap-2 mb-4">
            <StatusBadge ok={!!lh?.cron} label={`Cron: ${lh?.cron || 'deshabilitado'}`} />
            <StatusBadge ok={lh?.scope === 'country'} label={`Scope: ${lh?.scope}`} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Cron (5 campos)</label>
              <input value={lhCron} onChange={e => setLhCron(e.target.value)} placeholder={lh?.cron || '0 9 * * 1'} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50 font-mono" />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase tracking-wider">Scope de búsqueda</label>
              <select value={lhScope} onChange={e => setLhScope(e.target.value)} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50">
                <option value="bbox">Gran Asunción (bbox)</option>
                <option value="country">Todo Paraguay</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 uppercase tracking-wider">Bounding box (sur,oeste,norte,este)</label>
              <input value={lhBbox} onChange={e => setLhBbox(e.target.value)} placeholder={lh?.bbox} className="w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50 font-mono" />
            </div>
          </div>
          <div className="flex justify-end mt-3">
            <button
              onClick={() => saveLh.mutate()}
              disabled={saveLh.isPending || !isAdmin}
              className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
            >
              Guardar
            </button>
          </div>
          {lhMsg && <p className="text-xs text-gray-400 mt-2">{lhMsg}</p>}
          <p className="text-xs text-gray-600 mt-3">
            💡 Scope «Todo Paraguay» busca en todo el país sin restricción geográfica local.
            El cron vacío deshabilita la caza automática.
          </p>
        </Card>

        {/* Pipeline */}
        <Card title="PIPELINE END-TO-END" subtitle="De lead a propuesta validada">
          <ol className="text-sm text-gray-300 space-y-2 list-none">
            {[
              ['🔎', 'Cazar', 'Overpass/OSM o import CSV — dedupe automático'],
              ['🛰️', 'Enriquecer', 'Website (email/tel) y IA (score, sector, preguntas)'],
              ['📞', 'Contactar', 'Primer acercamiento con nota en timeline'],
              ['✔️', 'Calificar', 'Lead validado como prospecto real'],
              ['📄', 'Propuesta', 'Generada con IA o manual — se marca enviada'],
              ['🤝', 'Ganar / Perder', 'Cierre con motivo registrado'],
            ].map(([icon, step, desc]) => (
              <li key={step} className="flex items-start gap-3">
                <span className="text-base">{icon}</span>
                <span><span className="text-primary-400 font-medium">{step}</span> — <span className="text-gray-500">{desc}</span></span>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      {/* Modal QR WhatsApp */}
      {waModal && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setWaModal(false)}>
          <div className="bg-bg-900 border border-bg-700 rounded-lg p-6 w-full max-w-sm text-center shadow-neon" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-bold text-primary-400 tracking-wider mb-1">// CONECTAR WHATSAPP</h3>
            <p className="text-xs text-gray-500 mb-4">Escaneá el QR con WhatsApp → Dispositivos vinculados → Vincular dispositivo</p>
            <div className="flex justify-center mb-4">
              {wa?.state === 'qr' && wa?.qr ? (
                <img src={wa.qr} alt="QR WhatsApp" className="w-56 h-56 rounded-lg bg-white p-2" />
              ) : wa?.state === 'connected' ? (
                <div className="text-primary-400 text-5xl py-10">✓</div>
              ) : wa?.state === 'error' ? (
                <div className="text-alert-400 text-sm py-10 px-6">{wa?.error || 'Error de conexión'}</div>
              ) : (
                <div className="text-gray-500 text-sm py-10 animate-blink">Conectando…</div>
              )}
            </div>
            <p className="text-xs text-gray-600 mb-4">
              {wa?.state === 'qr' && 'El QR se actualiza solo. Esperá a que diga «Conectado».'}
              {wa?.state === 'connected' && `Listo ✅ Número conectado: +${wa?.phone || ''}`}
              {wa?.state === 'starting' && 'Iniciando el cliente de WhatsApp…'}
            </p>
            <button onClick={() => setWaModal(false)} className="px-4 py-2 text-xs rounded-lg border border-bg-600 text-gray-300 hover:text-primary-300 transition-colors">
              Cerrar
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
