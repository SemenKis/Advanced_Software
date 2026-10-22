FROM nginx:alpine
COPY templates/ /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV INVENTORY_BACKEND_URL=http://inventory-service:5001
EXPOSE 80