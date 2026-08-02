import re

path = "docker-compose.yml"
with open(path) as f:
    content = f.read()

old = "    volumes:\n      - ./backend:/app\n"
new = "    volumes:\n      - ./backend:/app\n      - ./agents:/app/agents\n"

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("docker-compose.yml: volumen ./agents:/app/agents agregado")
else:
    print("Patron no encontrado, contenido actual:")
    for line in content.splitlines():
        if "backend" in line or "volumes" in line or "./backend" in line:
            print("  ", line)
