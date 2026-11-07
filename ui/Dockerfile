FROM nginxinc/nginx-unprivileged:1.31.7-alpine3.24
USER root
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html
USER 101:101
EXPOSE 8080
# Bypass entrypoint scripts that attempt to edit /etc on a read-only root.
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
