#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}正在启动服务...${NC}"

# 检查并启动 Redis
echo -e "${GREEN}检查 Redis 服务...${NC}"
if ! pgrep -x "redis-server" > /dev/null
then
    echo "启动 Redis..."
    brew services start redis
else
    echo "Redis 已在运行"
fi

# 激活 Anaconda 环境
echo -e "${GREEN}激活 Conda 环境...${NC}"
source ~/anaconda3/etc/profile.d/conda.sh
conda activate managest

# 创建日志目录
mkdir -p logs

# 启动 Celery Worker
echo -e "${GREEN}启动 Celery Worker...${NC}"
celery -A rental_management worker -l info --logfile=./logs/celery_worker.log --detach

# 启动 Celery Beat
echo -e "${GREEN}启动 Celery Beat...${NC}"
celery -A rental_management beat -l info --logfile=./logs/celery_beat.log --detach

# 启动 Django 开发服务器
echo -e "${GREEN}启动 Django 开发服务器...${NC}"
python manage.py runserver 0.0.0.0:8000

# 捕获 Ctrl+C 信号
trap cleanup SIGINT

# 清理函数
cleanup() {
    echo -e "${RED}正在停止服务...${NC}"
    pkill -f 'celery worker'
    pkill -f 'celery beat'
    brew services stop redis
    exit 0
}
