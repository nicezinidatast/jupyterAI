FROM node:20-alpine AS build
WORKDIR /app

# Lockfile-less install for the demo. Production builds against pnpm-lock.yaml.
COPY units/admin-unit/admin-console/package.json ./
RUN npm install --no-fund --no-audit

COPY units/admin-unit/admin-console/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html/admin
COPY units/admin-unit/admin-console/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
