FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
# 输出在 /app/dist，由 docker-compose 挂载到 nginx
