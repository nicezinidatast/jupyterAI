FROM node:20-alpine AS build
WORKDIR /app
# Plotly + Mantine push Vite past the 2GB default heap on alpine builds.
ENV NODE_OPTIONS="--max-old-space-size=4096"
COPY units/admin-unit/analyst-workspace/package.json ./
RUN npm install --no-fund --no-audit
COPY units/admin-unit/analyst-workspace/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html/analyst
COPY units/admin-unit/analyst-workspace/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
