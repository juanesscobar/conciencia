/**
 * WhatsApp Bridge — sidecar de whatsapp-web.js para Mission Control.
 *
 * Expone una API mínima en 127.0.0.1 (WA_BRIDGE_PORT, default 8123):
 *   GET  /health      → { ok: true }
 *   GET  /status      → { ok, state, qr?, phone?, error? }
 *   POST /connect     → inicia el cliente (QR queda en /status)
 *   POST /disconnect  → logout + borra sesión local
 *   POST /send        → { to, message } (requiere connected)
 *
 * Estados: disconnected | starting | qr | connecting | connected | error
 * La sesión se persiste en .wa-session/ (LocalAuth) — gitignored.
 */
const express = require('express')
const path = require('path')
const fs = require('fs')
const { Client, LocalAuth } = require('whatsapp-web.js')
const QRCode = require('qrcode')

const PORT = parseInt(process.env.WA_BRIDGE_PORT || '8123', 10)
const SESSION_DIR = path.join(__dirname, '.wa-session')

const app = express()
app.use(express.json())

let client = null
let state = 'disconnected'
let qrData = null
let phone = null
let lastError = null
let starting = false

function setState(s) {
  state = s
  if (s !== 'qr') qrData = null
  if (s === 'connected') lastError = null
  console.log(`[wa-bridge] state → ${s}${phone ? ` (${phone})` : ''}`)
}

function buildClient() {
  const cfg = {
    authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
    puppeteer: {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
    },
  }
  // Si hay un Chromium/Edge explícito, usarlo (evita el download de puppeteer)
  if (process.env.WA_CHROMIUM_PATH) {
    cfg.puppeteer.executablePath = process.env.WA_CHROMIUM_PATH
  }

  const c = new Client(cfg)

  c.on('qr', async (qr) => {
    try {
      qrData = await QRCode.toDataURL(qr, { width: 320, margin: 1 })
    } catch (e) {
      qrData = null
      lastError = String(e)
    }
    setState('qr')
  })

  c.on('authenticated', () => {
    if (state === 'qr' || state === 'starting') setState('connecting')
  })

  c.on('ready', () => {
    phone = c.info && c.info.wid ? c.info.wid.user : null
    setState('connected')
  })

  c.on('auth_failure', (msg) => {
    lastError = String(msg)
    setState('error')
  })

  c.on('disconnected', async (reason) => {
    lastError = String(reason)
    setState('disconnected')
    try { await c.destroy() } catch (e) { /* noop */ }
    client = null
  })

  return c
}

async function start() {
  if (client || starting) return
  starting = true
  setState('starting')
  try {
    client = buildClient()
    client.once('ready', () => { starting = false })
    await client.initialize()
  } catch (e) {
    lastError = String(e && e.message ? e.message : e)
    setState('error')
    starting = false
    client = null
  }
}

app.get('/health', (req, res) => res.json({ ok: true }))

app.get('/status', (req, res) => {
  res.json({ ok: true, state, qr: state === 'qr' ? qrData : null, phone, error: lastError })
})

app.post('/connect', async (req, res) => {
  try {
    await start()
    res.json({ ok: true, state })
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) })
  }
})

app.post('/disconnect', async (req, res) => {
  try {
    if (client) {
      await client.logout()
      await client.destroy()
      client = null
    }
    // Limpiar sesión persistida
    fs.rmSync(SESSION_DIR, { recursive: true, force: true })
    setState('disconnected')
    res.json({ ok: true, state })
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) })
  }
})

app.post('/send', async (req, res) => {
  const { to, message } = req.body || {}
  if (!to || !message) return res.status(400).json({ ok: false, error: 'to y message son requeridos' })
  if (!client || state !== 'connected') {
    return res.status(409).json({ ok: false, error: 'WhatsApp no conectado' })
  }
  try {
    const chatId = to.includes('@c.us') ? to : `${to}@c.us`
    await client.sendMessage(chatId, String(message))
    res.json({ ok: true, to, state })
  } catch (e) {
    res.status(502).json({ ok: false, error: String(e && e.message ? e.message : e) })
  }
})

app.listen(PORT, '127.0.0.1', () => console.log(`[wa-bridge] escuchando en 127.0.0.1:${PORT}`))

process.on('SIGTERM', async () => {
  try { if (client) await client.destroy() } catch (e) { /* noop */ }
  process.exit(0)
})
