# Built from the repository root so the workspace contracts package is available:
#   docker build -f apps/web/Dockerfile .
FROM node:22-alpine AS build

RUN corepack enable

WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/contracts/package.json packages/contracts/
COPY apps/web/package.json apps/web/

RUN pnpm install --frozen-lockfile

COPY packages/contracts packages/contracts
COPY apps/web apps/web

RUN pnpm --filter @incident-commander/web build

FROM node:22-alpine

RUN corepack enable
WORKDIR /repo
COPY --from=build /repo ./

EXPOSE 3000
WORKDIR /repo/apps/web
CMD ["npx", "next", "start", "-p", "3000"]
