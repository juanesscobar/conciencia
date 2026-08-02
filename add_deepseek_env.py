import re

path = "backend/.env"
with open(path) as f:
    content = f.read()

if "DEEPSEEK_API_KEY" not in content:
    content += "\n# LLM / Agent Engine\nDEEPSEEK_API_KEY=\nDEEPSEEK_BASE_URL=https://api.deepseek.com\nDEEPSEEK_MODEL=deepseek-chat\n"
    with open(path, "w") as f:
        f.write(content)
    print(".env: DEEPSEEK config agregada")
else:
    print(".env: DEEPSEEK ya presente")

# Mostrar lineas relevantes sin exponer valores
for line in content.splitlines():
    if line.startswith("DEEPSEEK") or line.startswith("ENVIRONMENT"):
        print(" ", line)
