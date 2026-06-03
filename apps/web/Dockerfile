FROM node:20-alpine AS base

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy monorepo root dependency files for layer caching
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy application code
COPY apps/web/ apps/web/

# Build the application
RUN pnpm --filter web build

EXPOSE 3000

# Run the application
CMD ["pnpm", "--filter", "web", "start"]
