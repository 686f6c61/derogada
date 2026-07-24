FROM nginx:alpine

# Sitio estático: sin build. Se sirve tal cual.
COPY index.html tecnica.html og.png /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
