FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy frontend assets to nginx public folder
COPY . /usr/share/nginx/html

# Expose port 80 (internal to the container, mapped to 3000 in compose)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
