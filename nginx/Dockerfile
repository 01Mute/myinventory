FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine

# Goes to templates/ rather than conf.d/ so the entrypoint renders ${DOMAIN}
# into it at startup. A file dropped straight into conf.d/ is served verbatim
# and the placeholder would reach nginx unsubstituted.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

EXPOSE 80
