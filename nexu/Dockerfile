# ── Stage 1: build ──────────────────────────────────────────────
FROM node:22-slim AS builder

WORKDIR /app

# Set CI=true to prevent pnpm from aborting in non-interactive environments
ENV CI=true

# Install pnpm
RUN npm install -g pnpm@10

# Copy package files first for better layer caching
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/controller/package.json ./apps/controller/
COPY apps/web/package.json ./apps/web/
COPY packages/shared/package.json ./packages/shared/
COPY openclaw-runtime/package.json openclaw-runtime/package-lock.json ./openclaw-runtime/

# Install all dependencies (excluding scripts for now, as we only have package.json files)
RUN pnpm install --frozen-lockfile --ignore-scripts

# Copy source
COPY . .

# Now that we have all scripts, run pnpm install again to trigger postinstall scripts
RUN pnpm install --frozen-lockfile

# Build in dependency order
RUN pnpm --filter @nexu/shared build
RUN pnpm --filter @nexu/web build
RUN pnpm --filter @nexu/controller build


# ── Stage 2: production image ────────────────────────────────────
FROM node:22-slim

WORKDIR /app

# Set CI=true for consistency in production stage as well
ENV CI=true

RUN npm install -g pnpm@10

# Copy package files
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/controller/package.json ./apps/controller/
COPY packages/shared/package.json ./packages/shared/
COPY openclaw-runtime/package.json openclaw-runtime/package-lock.json ./openclaw-runtime/

# Install production deps only (no devDependencies)
# Skip scripts because root postinstall depends on files we haven't copied yet
# (and the artifacts are copied from builder stage anyway)
RUN pnpm install --frozen-lockfile --prod --ignore-scripts

# Copy built artifacts from builder stage
COPY --from=builder /app/apps/controller/dist ./apps/controller/dist
COPY --from=builder /app/apps/controller/static ./apps/controller/static
COPY --from=builder /app/apps/web/dist ./apps/web/dist
COPY --from=builder /app/openclaw-runtime ./openclaw-runtime
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist

# Data directory (config, OpenClaw state) lives here — mount as a volume to persist
VOLUME /root/.nexu

EXPOSE 3010

ENV NODE_ENV=production

CMD ["node", "apps/controller/dist/index.js"]
