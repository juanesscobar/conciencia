# LLM Harness — Documentación Técnica

> Harness engineering aplicado al motor de agentes de Conciencia.
> Proveedor-agnóstico · fallback automático · cost tracking · **modo eficiencia de tokens**.

## 1. Arquitectura

```
app/services/llm_harness/
├── base.py              → contratos: ProviderAdapter, HarnessConfig, UsageMetrics, HarnessResult
├── harness.py           → run_with_harness(): fallback chain + retry + cost recording
├── cost_tracker.py      → CostTracker: registros, presupuestos (daily/weekly/monthly), alertas
├── routing.py           → (reservado) routing inteligente
├── token_budget.py      → 🆕 TokenOptimizer: eficiencia de tokens (context budget + cost guard)
└── providers/
    ├── deepseek.py · openai_provider.py · anthropic.py · google.py · ollama.py · openrouter.py
```

Capa de compatibilidad: `app/services/llm.py` (`run_agent()`) — usada por LeadHunter,
proposals, agentes, etc. Lee config de: DB (settings) → env → defaults.

## 2. Modo eficiencia de tokens (TokenOptimizer)

Activado por defecto (`efficient_mode=True`). Antes de llamar al provider:

1. **Estimación de tokens** (heurística ~4 chars/token, sin dependencias externas).
2. **Context window budget** (`LLM_MAX_CONTEXT_TOKENS`):
   - Siempre conserva el system prompt.
   - Poda los mensajes más viejos primero.
   - Si podar no alcanza, compacta el medio del historial con un placeholder
     (`[historial compactado: N mensajes...]`).
3. **Output cap** (`LLM_MAX_OUTPUT_TOKENS`, default 2000) → se pasa como
   `max_tokens` al provider.
4. **Cost guard pre-flight** (`LLM_BUDGET_USD`): estima el costo con el pricing del
   provider ANTES de llamar; si excede el presupuesto, poda el historial y si aun así
   excede, la llamada se hace con el mínimo contexto (nunca se reporta éxito falso).

Estadísticas por ejecución devueltas en `result.metadata["token_stats"]`:
`original_tokens, final_tokens, pruned_messages, compacted_messages, cost_guard_triggered`.

## 3. Variables de entorno / settings (tabla `settings` de la DB)

| Variable | Default | Descripción |
|---|---|---|
| `LLM_PROVIDER` | `deepseek` | Provider activo |
| `DEEPSEEK_API_KEY` | — | Key del provider |
| `LLM_MODEL` | por provider | Modelo activo |
| `LLM_FALLBACK_PROVIDERS` | `[]` | JSON array, ej: `["openrouter","ollama"]` |
| `LLM_EFFICIENT_MODE` | `true` | Activa TokenOptimizer |
| `LLM_MAX_CONTEXT_TOKENS` | `0` (off) | Presupuesto de contexto; 0 = historial completo |
| `LLM_MAX_OUTPUT_TOKENS` | `2000` | Cap de salida |
| `LLM_BUDGET_USD` | — | Cost guard pre-flight por llamada |

## 4. Uso

```python
from app.services.llm_harness import run_with_harness, HarnessConfig

config = HarnessConfig(
    provider="deepseek", model="deepseek-chat", api_key=key,
    fallback_providers=["openrouter"], budget_usd=0.05,
    max_context_tokens=8000, max_output_tokens=1500,
)
result = run_with_harness(messages, config)
print(result.output, result.metadata.get("token_stats"))
```

O vía capa de compatibilidad: `run_agent("dev", system_prompt, task, context)`.

## 5. Principios (harness engineering)

1. **Nunca reportar éxito si falló** — el harness lanza `HarnessError` cuando todos los
   providers fallan; `llm.py` lo convierte en `{output: None, error: ...}`.
2. **Provider/runtime agnóstico** — Conciencia no se acopla a un solo LLM.
3. **Tokens como recurso medible** — cada llamada registra uso y costo
   (`CostTracker`), y ahora también tokens ahorrados por optimización.
4. **Presupuestos en cascada** — global → scope (proyecto/agente) → por llamada.
