#!/bin/bash

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${RED}正在停止所有服务...${NC}"

# 停止 Celery Worker 和 Beat
echo "停止 Celery 进程..."
pkill -f 'celery worker'
pkill -f 'celery beat'

# 停止 Redis
echo "停止 Redis 服务..."
brew services stop redis

echo -e "${GREEN}所有服务已停止${NC}"
