import { useQuery, useMutation } from '@tanstack/react-query'
import { emailApi } from '../services/api'
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

const PROVIDER_META: Record<string, { label: string; icon: string; hint: string; link?: { text: string; url: string } }> = {
  gmail: {
    label: 'Gmail',
    icon: '✉',
    hint: 'Necesitás una App password (2FA activado). No uses tu contraseña normal.',
    link: { text: 'Crear App password →', url: 'https://myaccount.google.com/apppasswords' },
  },
  outlook: {
    label: 'Outlook / Office 365',
    icon: '❖',
    hint: 'Usá tu contraseña normal o App password si tenés MFA activo.',
  },
  generic: {
    label: 'IMAP/SMTP genérico',
    icon: '▤',
    hint: 'Cualquier proveedor con IMAP + SMTP: completá hosts y puertos manualmente.',
  },
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded border ${ok ? 'text-primary-400 border-primary-500/40 bg-primary-500/10' : 'text-yellow-400 border-yellow-500/40 bg-yellow-500/10'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-primary-400' : 'bg-yellow-400'} animate-blink`}></span>
      {label}
    </span>
  )
}

export default function Email() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'ceo' || user?.role === 'owner'

  const { data: providers } = useQuery({
    queryKey: ['email-providers'],
    queryFn: () => emailApi.providers().then(res => res.data),
  })
  const { data: accounts, refetch: refetchAccounts } = useQuery({
    queryKey: ['email-accounts'],
    queryFn: () => emailApi.accounts().then(res => res.data),
  })

  // ---- Wizard de conexión ----
  const [form, setForm] = useState({
    provider: 'gmail',
    name: '',
    email: '',
    password: '',
    username: '',
    from_name: '',
    imap_host: '',
    imap_port: '993',
    smtp_host: '',
    smtp_port: '587',
  })
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const flash = (ok: boolean, text: string) => {
    setMsg({ ok, text })
    setTimeout(() => setMsg(null), 6000)
  }

  const connect = useMutation({
    mutationFn: async () => {
      const payload: any = {
        name: form.name.trim() || form.email.split('@')[0],
        provider: form.provider,
        email: form.email.trim(),
        password: form.password,
        username: form.username.trim() || undefined,
        from_name: form.from_name.trim() || undefined,
      }
      if (form.provider === 'generic') {
        payload.imap_host = form.imap_host.trim()
        payload.imap_port = parseInt(form.imap_port) || 993
        payload.smtp_host = form.smtp_host.trim()
        payload.smtp_port = parseInt(form.smtp_port) || 587
      }
      const { data: acc } = await emailApi.create(payload)
      // probar conexión inmediatamente después de guardar
      const test = await emailApi.test(acc.id)
      return { acc, test: test.data }
    },
    onSuccess: ({ acc, test }) => {
      const ok = test?.imap && test?.smtp
      flash(
        ok,
        ok
          ? `✓ Cuenta "${acc.name}" conectada — IMAP + SMTP funcionando`
          : `⚠ Cuenta guardada pero la prueba falló: ${test?.error || 'revisá credenciales'}`
      )
      setForm({ ...form, password: '', username: '', imap_host: '', smtp_host: '' })
      refetchAccounts()
    },
    onError: (e: any) => flash(false, e.response?.data?.detail || 'Error al conectar la cuenta'),
  })

  // ---- Acciones por cuenta ----
  const [testResults, setTestResults] = useState<Record<string, any>>({})
  const [openInbox, setOpenInbox] = useState<string | null>(null)
  const [openComposer, setOpenComposer] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [composer, setComposer] = useState({ to: '', subject: '', body: '' })
  const [sendResults, setSendResults] = useState<Record<string, any>>({})

  const testAcc = useMutation({
    mutationFn: (id: string) => emailApi.test(id),
    onSuccess: (r: any, id: string) => setTestResults(prev => ({ ...prev, [id]: r.data })),
    onError: (e: any, id: string) => setTestResults(prev => ({ ...prev, [id]: { imap: false, smtp: false, error: e.response?.data?.detail || 'Error' } })),
  })

  const deleteAcc = useMutation({
    mutationFn: (id: string) => emailApi.delete(id),
    onSuccess: () => { setOpenInbox(null); setOpenComposer(null); refetchAccounts() },
  })

  const sendMail = useMutation({
    mutationFn: ({ id }: { id: string }) => emailApi.send(id, composer),
    onSuccess: (r: any, { id }) => {
      setSendResults(prev => ({ ...prev, [id]: r.data }))
      setComposer({ to: '', subject: '', body: '' })
      setOpenComposer(null)
    },
    onError: (e: any, { id }) => setSendResults(prev => ({ ...prev, [id]: { error: e.response?.data?.detail || 'Error al enviar' } })),
  })

  const { data: inboxData } = useQuery({
    queryKey: ['email-inbox', openInbox],
    queryFn: () => emailApi.inbox(openInbox!, 20).then(res => res.data),
    enabled: !!openInbox,
  })

  const meta = PROVIDER_META[form.provider]
  const isGeneric = form.provider === 'generic'

  const inputCls = 'w-full mt-1 px-3 py-2 bg-bg-950 border border-bg-700 rounded text-sm text-gray-200 focus:outline-none focus:border-primary-500/50'
  const labelCls = 'text-xs text-gray-500 uppercase tracking-wider'

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-primary-400 tracking-wider">// CORREO · CONEXIÓN DIRECTA</h1>
        <p className="text-sm text-gray-500 mt-1">Conectá tu casilla (Gmail, Outlook o IMAP genérico) — envío por SMTP y lectura por IMAP, cifrado en la DB</p>
      </div>

      {!isAdmin && (
        <div className="bg-yellow-500/10 border border-yellow-500/40 text-yellow-400 text-sm rounded-lg p-4 mb-6">
          ⚠️ Solo el admin (Iron Toto) puede conectar cuentas de correo.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Wizard de conexión */}
        <div className="bg-bg-900 border border-bg-700 rounded-lg p-5">
          <h2 className="text-sm font-bold text-primary-400 tracking-wider">// 1 · CONECTAR CASILLA</h2>
          <p className="text-xs text-gray-500 mt-1 mb-4">Elegí el proveedor, pegá tus credenciales y probamos la conexión al guardar.</p>

          <div className="flex gap-2 mb-4">
            {(providers || []).map((p: any) => {
              const m = PROVIDER_META[p.id] || { label: p.label, icon: '✉', hint: '' }
              return (
                <button
                  key={p.id}
                  onClick={() => setForm({ ...form, provider: p.id })}
                  disabled={!isAdmin}
                  className={`flex-1 px-3 py-2 text-sm rounded-lg border transition-all disabled:opacity-40 ${form.provider === p.id ? 'bg-primary-500/20 text-primary-400 border-primary-500/50' : 'border-bg-600 text-gray-500 hover:border-primary-500/30'}`}
                >
                  {m.icon} {m.label}
                </button>
              )
            })}
          </div>

          <div className="mb-4 text-xs bg-bg-950/60 border border-bg-800 rounded-lg p-3 text-gray-400">
            {meta.hint}
            {meta.link && (
              <a href={meta.link.url} target="_blank" rel="noreferrer" className="block mt-1 text-primary-400 hover:underline">
                {meta.link.text}
              </a>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="md:col-span-2">
              <label className={labelCls}>Casilla (email)</label>
              <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="tu@gmail.com" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Nombre de la cuenta</label>
              <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Personal / Ventas" className={inputCls} />
            </div>
            <div>
              <label className={labelCls}>Nombre visible (From)</label>
              <input value={form.from_name} onChange={e => setForm({ ...form, from_name: e.target.value })} placeholder="Iron Toto" className={inputCls} />
            </div>
            <div className={isGeneric ? '' : 'md:col-span-2'}>
              <label className={labelCls}>{isGeneric ? 'Usuario IMAP/SMTP (login)' : 'Contraseña / App password'}</label>
              <input
                type="password"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                placeholder={isGeneric ? 'login' : '16 letras, sin espacios'}
                className={inputCls}
              />
            </div>
            {isGeneric && (
              <>
                <div>
                  <label className={labelCls}>App password</label>
                  <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="••••••••" className={inputCls} />
                </div>
                <div className="md:col-span-2">
                  <label className={labelCls}>Usuario (login) — si difiere del email</label>
                  <input value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} placeholder="usuario" className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>IMAP host</label>
                  <input value={form.imap_host} onChange={e => setForm({ ...form, imap_host: e.target.value })} placeholder="imap.tuproveedor.com" className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>IMAP puerto</label>
                  <input value={form.imap_port} onChange={e => setForm({ ...form, imap_port: e.target.value })} placeholder="993" className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>SMTP host</label>
                  <input value={form.smtp_host} onChange={e => setForm({ ...form, smtp_host: e.target.value })} placeholder="smtp.tuproveedor.com" className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>SMTP puerto</label>
                  <input value={form.smtp_port} onChange={e => setForm({ ...form, smtp_port: e.target.value })} placeholder="587" className={inputCls} />
                </div>
              </>
            )}
          </div>

          <div className="flex justify-end mt-4">
            <button
              onClick={() => connect.mutate()}
              disabled={!form.email.trim() || !form.password.trim() || connect.isPending || !isAdmin}
              className="px-4 py-2 text-sm bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded-lg hover:bg-primary-500/20 transition-all disabled:opacity-40"
            >
              {connect.isPending ? 'Conectando y probando…' : '🔌 Conectar y probar'}
            </button>
          </div>
          {msg && (
            <p className={`mt-3 text-xs font-mono p-3 rounded-lg border ${msg.ok ? 'text-primary-400 border-primary-500/40 bg-primary-500/5' : 'text-alert-400 border-alert-500/40 bg-alert-500/5'}`}>
              {msg.text}
            </p>
          )}
        </div>

        {/* Cuentas conectadas */}
        <div className="bg-bg-900 border border-bg-700 rounded-lg p-5">
          <h2 className="text-sm font-bold text-primary-400 tracking-wider">// 2 · CASILLAS CONECTADAS</h2>
          <p className="text-xs text-gray-500 mt-1 mb-4">Test de conexión, inbox y envío directo desde acá.</p>

          {!accounts?.length ? (
            <p className="text-xs text-gray-600">Sin cuentas todavía. Completá el wizard de la izquierda 👈</p>
          ) : (
            <div className="space-y-3 max-h-[560px] overflow-auto pr-1">
              {accounts.map((acc: any) => {
                const test = testResults[acc.id]
                const ok = test ? test.imap && test.smtp : undefined
                return (
                  <div key={acc.id} className="bg-bg-950/60 border border-bg-800 rounded-lg p-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div>
                        <p className="text-sm text-gray-200 font-medium">
                          {acc.name} <span className="text-gray-600">· {acc.provider}</span>
                        </p>
                        <p className="text-xs text-gray-500">{acc.email}{acc.from_name ? ` (${acc.from_name})` : ''}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {ok !== undefined && (
                          <StatusBadge ok={!!ok} label={ok ? 'IMAP+SMTP OK' : 'FALLA'} />
                        )}
                        <button onClick={() => testAcc.mutate(acc.id)} disabled={testAcc.isPending} className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50">
                          {testAcc.isPending ? '…' : 'Test'}
                        </button>
                        <button onClick={() => setOpenInbox(openInbox === acc.id ? null : acc.id)} className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50">
                          Inbox
                        </button>
                        <button onClick={() => { setOpenComposer(openComposer === acc.id ? null : acc.id); setComposer({ to: '', subject: '', body: '' }) }} className="text-xs px-2 py-1 rounded border border-bg-600 text-primary-400 hover:border-primary-500/50">
                          ✎ Enviar
                        </button>
                        <button
                          onClick={() => { if (confirm(`¿Eliminar la cuenta "${acc.name}"?`)) deleteAcc.mutate(acc.id) }}
                          disabled={!isAdmin}
                          className="text-xs px-2 py-1 rounded border border-alert-500/40 text-alert-400 hover:bg-alert-500/10 disabled:opacity-40"
                        >
                          ✕
                        </button>
                      </div>
                    </div>

                    {test && !ok && (
                      <p className="mt-2 text-xs font-mono text-alert-400">{test.error}</p>
                    )}
                    {sendResults[acc.id] && (
                      <p className={`mt-2 text-xs font-mono ${sendResults[acc.id].ok ? 'text-primary-400' : 'text-alert-400'}`}>
                        {sendResults[acc.id].ok ? `✓ Enviado a ${sendResults[acc.id].to}` : `✗ ${sendResults[acc.id].error}`}
                      </p>
                    )}

                    {openComposer === acc.id && (
                      <div className="mt-3 border-t border-bg-800 pt-3 space-y-2">
                        <input value={composer.to} onChange={e => setComposer({ ...composer, to: e.target.value })} placeholder="destinatario@email.com" className="w-full px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50" />
                        <input value={composer.subject} onChange={e => setComposer({ ...composer, subject: e.target.value })} placeholder="Asunto" className="w-full px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50" />
                        <textarea value={composer.body} onChange={e => setComposer({ ...composer, body: e.target.value })} placeholder="Cuerpo del mensaje…" rows={4} className="w-full px-3 py-1.5 bg-bg-950 border border-bg-700 rounded text-xs text-gray-200 focus:outline-none focus:border-primary-500/50 resize-y" />
                        <div className="flex justify-end">
                          <button
                            onClick={() => sendMail.mutate({ id: acc.id })}
                            disabled={!composer.to.trim() || !composer.subject.trim() || sendMail.isPending}
                            className="px-3 py-1.5 text-xs bg-primary-500/10 text-primary-400 border border-primary-500/40 rounded hover:bg-primary-500/20 transition-all disabled:opacity-40"
                          >
                            {sendMail.isPending ? 'Enviando…' : 'Enviar'}
                          </button>
                        </div>
                      </div>
                    )}

                    {openInbox === acc.id && (
                      <div className="mt-3 border-t border-bg-800 pt-2 max-h-64 overflow-auto">
                        {!inboxData?.messages?.length ? (
                          <p className="text-xs text-gray-600">Inbox vacío o sin acceso.</p>
                        ) : (
                          inboxData.messages.map((m: any, i: number) => (
                            <div key={i} className="text-xs py-2 border-b border-bg-800/50 last:border-0">
                              <div className="flex items-center justify-between gap-2 cursor-pointer" onClick={() => setExpanded(expanded === `${acc.id}-${i}` ? null : `${acc.id}-${i}`)}>
                                <span className="text-gray-400 truncate">{String(m.from || '').split('<')[0].trim()}</span>
                                <span className="text-gray-600 shrink-0">{String(m.date || '').slice(0, 16)}</span>
                              </div>
                              <p className="text-gray-300 mt-0.5">{m.subject}</p>
                              {expanded === `${acc.id}-${i}` && (
                                <pre className="mt-2 text-[11px] text-gray-500 whitespace-pre-wrap font-mono bg-bg-900/60 rounded p-2 max-h-48 overflow-auto">{m.body || '(sin cuerpo)'}</pre>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-gray-600 mt-6">
        🔒 Las contraseñas se guardan <span className="text-gray-400">cifradas (Fernet/SECRET_KEY)</span> — nunca en texto plano. Los agentes acceden a estas cuentas vía MCP tools (<span className="font-mono">email_send</span>, <span className="font-mono">email_inbox</span>) desde el Tool Registry.
      </p>
    </div>
  )
}
