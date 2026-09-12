# Stage 1 — build
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build && npm sbom --sbom-format=cyclonedx > frontend.cdx.json

# Stage 2 — serve
FROM nginx:stable-alpine
# Bounded retries for transient CDN failures; TLS and repository checks stay on.
RUN apk upgrade --no-cache || apk upgrade --no-cache || apk upgrade --no-cache
COPY --from=builder /app/dist /usr/share/nginx/html
COPY package.json package-lock.json /usr/share/agent-trust-inventory/
COPY --from=builder /app/frontend.cdx.json /usr/share/agent-trust-inventory/frontend.cdx.json
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]
