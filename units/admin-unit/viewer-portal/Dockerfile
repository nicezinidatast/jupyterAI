FROM node:20-alpine AS build
WORKDIR /app
ENV NODE_OPTIONS="--max-old-space-size=4096"
COPY units/admin-unit/viewer-portal/package.json ./
RUN npm install --no-fund --no-audit
COPY units/admin-unit/viewer-portal/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html/viewer
COPY units/admin-unit/viewer-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
