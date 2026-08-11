# --- Build stage --------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Copy lockfile + package manifest first so the install layer is cached
# independently of source changes.
COPY package.json ./
RUN npm install --no-audit --no-fund

COPY . .
RUN npm run build

# --- Runtime stage ------------------------------------------------------
FROM nginx:1.27-alpine

# Replace the default nginx site with our M01 SPA-friendly config that
# also serves the API reverse-proxy at /api/*.
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx:alpine already ships wget for healthcheck; no extra install.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
