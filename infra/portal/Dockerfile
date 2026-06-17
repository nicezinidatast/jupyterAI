# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────
# Production portal: build all 4 SPAs to STATIC assets and serve them from
# nginx, plus proxy /api → backend and /jupyter → jupyter.
#
# Why: the dev compose runs each SPA as a Vite dev server (4 node containers,
# ~1 GB RAM, and an `npm install` at every boot — needs network). For a small
# on-prem box this image instead bakes the built static files once (build it
# where the npm proxy is reachable, then just run the image — no runtime npm).
#
# Build context = repo root (so it can reach units/admin-unit/* and
# infra/portal/*). Each SPA's vite.config.ts already sets the right `base`
# (/admin/, /auditor/, /analyst/, /login/) so asset URLs resolve under nginx.
# ─────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /build
# The analyst bundle (plotly + mantine + sourcemaps) blows the default 2 GB
# Node heap during `vite build`; give it headroom (matches the dev compose).
# Set here (before the heavy builds) so the small admin/auditor layers stay
# cache-valid across rebuilds.
ENV NODE_OPTIONS=--max-old-space-size=4096

COPY units/admin-unit/admin-console/ ./admin-console/
RUN cd admin-console && npm install --no-fund --no-audit && npm run build

COPY units/admin-unit/auditor-console/ ./auditor-console/
RUN cd auditor-console && npm install --no-fund --no-audit && npm run build

COPY units/admin-unit/analyst-workspace/ ./analyst-workspace/
RUN cd analyst-workspace && npm install --no-fund --no-audit && npm run build

COPY units/admin-unit/platform-login/ ./platform-login/
RUN cd platform-login && npm install --no-fund --no-audit && npm run build

FROM nginx:alpine
COPY infra/portal/nginx.prod.conf /etc/nginx/conf.d/default.conf
COPY infra/portal/index.html      /usr/share/nginx/html/index.html
COPY --from=build /build/admin-console/dist/     /usr/share/nginx/html/admin/
COPY --from=build /build/auditor-console/dist/   /usr/share/nginx/html/auditor/
COPY --from=build /build/analyst-workspace/dist/ /usr/share/nginx/html/analyst/
COPY --from=build /build/platform-login/dist/    /usr/share/nginx/html/login/
