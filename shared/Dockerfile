FROM nginx:alpine
COPY frontend/ /usr/share/nginx/html/
COPY frontend/runtime-config.js.template /etc/nginx/templates/runtime-config.js.template
ENV NGINX_ENVSUBST_OUTPUT_DIR=/usr/share/nginx/html
ENV INVENTORY_URL=/inventory/
ENV ORDERS_URL=/orders/
ENV WAREHOUSE_URL=/warehouse/
ENV TRANSPORTATION_URL=/transportation/
EXPOSE 80
