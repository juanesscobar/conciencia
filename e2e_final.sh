#!/bin/bash
# E2E Lead Hunter + Conciencia — test completo
API=http://localhost/api/v1
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"MC-uJbdyOucfynT#Qz"}' | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')

echo "=== 1. INTAKE WEBHOOK (simula quiz de conciencia-software) ==="
curl -s -X POST $API/leads/intake -H 'Content-Type: application/json' -d '{
  "company": "Cooperativa San Blas Ltda.",
  "contact_name": "María González",
  "email": "maria@sanblas.coop.py",
  "phone": "+595 981 555 123",
  "industry": "Cooperativa",
  "notes": "Diagnóstico: CRM a medida — proyecto ágil",
  "metadata": {
    "source": "conciencia",
    "situacionActual": "Planillas de cálculo (Excel/Sheets)",
    "necesidad": "Ventas, clientes o cobranzas (CRM)",
    "usuarios": "De 11 a 50",
    "horizonte": "En 1 a 3 meses",
    "diagnosis": "CRM a medida",
    "scale": "proyecto por fases, con módulos priorizados"
  }
}'
echo; echo

echo "=== 2. LISTA LEADS ==="
curl -s "$API/leads/?page_size=5" -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d = json.load(sys.stdin)
print("total:", d["total"])
for l in d["items"]:
    print(f"- {l[\"company\"]} | {l[\"source\"]} | score={l[\"score\"]} | {l[\"status\"]} | email={l[\"email\"]}")'

echo "=== 3. STATS ==="
curl -s $API/leads/stats -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo "=== 4. CREAR PROYECTO Conciencia Software ==="
curl -s -X POST $API/projects/ -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
  "name": "Conciencia Software",
  "description": "Landing/CTA del software factory — desarrollo de software, IA y ciberseguridad en Paraguay. Diagnóstico gratuito que genera leads.",
  "status": "active",
  "priority": "p1",
  "category": "core",
  "github_repo": "juanesscobar/conciencia-software-",
  "tech_stack": ["Next.js", "TypeScript", "Tailwind", "Vercel", "Resend"]
}' | python3 -c 'import sys,json; d=json.load(sys.stdin); print("CREATED:", d.get("id"), d.get("name"), d.get("github_repo"))'

echo "=== 5. SYNC CONCIENCIA (github) ==="
PID=$(curl -s $API/projects/ -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; ps=[p for p in json.load(sys.stdin) if "onciencia" in p["name"]]; print(ps[0]["id"] if ps else "")')
curl -s -X POST $API/integrations/github/sync/$PID -H "Authorization: Bearer $TOKEN" | head -c 300; echo

echo "=== 6. ENRICH LEAD CON IA (DeepSeek) ==="
LID=$(curl -s "$API/leads/?search=sanblas" -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; print(json.load(sys.stdin)["items"][0]["id"])')
curl -s -X POST $API/leads/$LID/enrich -H "Authorization: Bearer $TOKEN" | python3 -c '
import sys,json
d = json.load(sys.stdin)
print("lead:", d["company"], "| score:", d["score"])
notes = d.get("notes") or ""
print("IA notes:", notes[:300].replace(chr(10), " "), "...")'

echo "=== 7. AGENTE DEV RUN (real) ==="
AID=$(curl -s $API/agents/ -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json; [print(a["id"]) for a in json.load(sys.stdin) if a["role"]=="dev"]' | head -1)
curl -s -X POST $API/agents/$AID/run -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"task_text":"Proponé una arquitectura técnica para el proyecto Conciencia Software (Next.js en Vercel) que reciba leads y los envíe a Mission Control. Breve."}' | python3 -c '
import sys,json
d = json.load(sys.stdin)
print("status:", d.get("status"), "| simulated:", d.get("simulated"), "| model:", d.get("model"))
print("output:", (d.get("output") or "")[:400].replace(chr(10), " "), "...")'

echo "DONE"
