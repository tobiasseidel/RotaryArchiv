FROM node:22-alpine AS build
WORKDIR /app
COPY rotary-frontend/package*.json ./
RUN npm ci
COPY rotary-frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html/
