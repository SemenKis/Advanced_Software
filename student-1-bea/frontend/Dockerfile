FROM nginx:alpine

# Static assets
COPY templates/ /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/

# Reverse-proxy config (proxies /api/ to order-service)
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV ORDER_BACKEND_URL=http://order-backend:5001

EXPOSE 80