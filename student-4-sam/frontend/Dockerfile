FROM nginx:alpine

COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY index.html /usr/share/nginx/html/index.html
COPY css /usr/share/nginx/html/css
ENV TRANSPORT_BACKEND_URL=http://host.docker.internal:5004

EXPOSE 80