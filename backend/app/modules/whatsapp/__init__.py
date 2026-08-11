"""Módulo WhatsApp Business — conexión por QR a WhatsApp Web.

Arquitectura: la sesión real vive en un sidecar Node (wa-bridge/) que usa
whatsapp-web.js. El backend Python solo administra/proxya ese proceso y expone
la API REST (status / QR / send). Si el sidecar no puede correr, todo degrada
con gracia: las propuestas se siguen enviando por deep link wa.me.
"""

from .router import router  # noqa: F401
