FROM node:20-alpine AS build
WORKDIR /app
COPY units/admin-unit/auditor-console/package.json ./
RUN npm install --no-fund --no-audit
COPY units/admin-unit/auditor-console/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html/auditor
COPY units/admin-unit/auditor-console/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
