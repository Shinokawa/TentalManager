# 使用官方Python镜像作为基础镜像
FROM python:3.9-slim

# 设置环境变量
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 复制项目代码
COPY . /app/

# 运行命令（由docker-compose.yml中的command覆盖）
CMD ["gunicorn", "rental_management.wsgi:application", "--bind", "0.0.0.0:8000"]