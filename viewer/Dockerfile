# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# VITE_API_URL / VITE_CATALOGUE_URL are baked in at build time (Vite env vars
# are resolved at build, not at container runtime). Override at build with:
#   docker build --build-arg VITE_API_URL=https://api.example.com/api/v1 .
ARG VITE_API_URL=http://localhost:4000/api/v1
ARG VITE_CATALOGUE_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_CATALOGUE_URL=$VITE_CATALOGUE_URL

RUN npm run build

# --- serve stage ---
FROM nginx:alpine AS serve
COPY --from=build /app/dist /usr/share/nginx/html

# Single-page app: fall back to index.html for client-side routes.
RUN printf 'server {\n\
  listen 80;\n\
  server_name _;\n\
  root /usr/share/nginx/html;\n\
  location / {\n\
    try_files $uri $uri/ /index.html;\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
