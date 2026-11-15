# syntax=docker/dockerfile:1
# Multi-stage image for the Next.js frontend (apps/web).
# Build context is the repo root: docker build -f apps/web/Dockerfile .
#
# NEXT_PUBLIC_* values are inlined into the client and server bundles at
# build time by Next.js, not read at container start -- so the backend URLs
# are build args here, not runtime env vars on the Container App (apps.tf).
# Defaults match apps/web/next.config.js's local-dev fallback.

FROM node:20-alpine AS deps
WORKDIR /build
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /build
COPY --from=deps /build/node_modules ./node_modules
COPY apps/web ./

ARG NEXT_PUBLIC_API_URL=http://localhost:8003
ARG NEXT_PUBLIC_IDENTITY_URL=http://localhost:8001
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_IDENTITY_URL=${NEXT_PUBLIC_IDENTITY_URL} \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:20-alpine AS runtime

# The runtime only ever runs `node server.js` (see CMD below), never `npm`/`npx`.
# Strip npm's bundled global install -- it drags in its own vendored deps (e.g.
# tar) whose CVEs would otherwise show up in container scans for a tool we
# never invoke here.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx \
 && addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# .next/standalone is a self-contained server (only the deps Next traced as
# actually used); static assets and public/ are copied in separately because
# standalone output deliberately excludes them (ADR: next.config.js output).
COPY --from=builder /build/public ./public
COPY --from=builder --chown=nextjs:nodejs /build/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /build/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:3000/api/health').then(r=>{if(!r.ok)throw new Error(r.status)}).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
