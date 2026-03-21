FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install
ARG VITE_API_BASE_URL=
ENV NEXT_PUBLIC_API_URL=$VITE_API_BASE_URL
COPY . .
RUN mkdir -p public && npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public 2>/dev/null || true
EXPOSE 3000
CMD ["node", "server.js"]