FROM nginx:alpine

# Static assets
COPY templates/ /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/

# Reverse-proxy config (proxies /api/ to order-service)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80