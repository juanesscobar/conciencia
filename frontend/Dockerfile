# ============================================================
# FRONTEND — BUILD DE PRODUCCIÓN (multi-stage)
# Stage 1: compila con Vite → Stage 2: nginx sirve el estático
# ============================================================
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source
COPY . .

# API base URL (vacía = relativa, misma origin que nginx: /api se proxya al backend)
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}

# Build estático
RUN npm run build

# ---- Servidor estatico ----
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
