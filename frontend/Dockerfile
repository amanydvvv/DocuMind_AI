# Stage 1: Build React/Vite application
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Override with --build-arg VITE_API_URL=<your-backend-url> for other environments
ARG VITE_API_URL=https://kuerycore-ai-97t5.onrender.com
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Production web server using Nginx
FROM nginx:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
