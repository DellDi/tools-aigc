#!/bin/bash
# 数据库初始化脚本 - 用于开发和生产环境

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印带颜色的信息
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境变量
if [ -z "$DATABASE_URL" ]; then
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
        info "从 .env 文件加载 DATABASE_URL"
    else
        error "未设置 DATABASE_URL 环境变量且 .env 文件不存在"
        exit 1
    fi
fi

# 提取数据库连接信息
DB_URL=${DATABASE_URL#*://}
DB_USER=$(echo $DB_URL | cut -d':' -f1)
DB_PASS=$(echo $DB_URL | cut -d':' -f2 | cut -d'@' -f1)
DB_HOST=$(echo $DB_URL | cut -d'@' -f2 | cut -d':' -f1)
DB_PORT=$(echo $DB_URL | cut -d':' -f3 | cut -d'/' -f1)
DB_NAME=$(echo $DB_URL | cut -d'/' -f2 | cut -d'?' -f1)

info "数据库信息:"
info "  用户: $DB_USER"
info "  主机: $DB_HOST"
info "  端口: $DB_PORT"
info "  数据库名: $DB_NAME"

# 检查 PostgreSQL 客户端是否安装
if ! command -v psql &> /dev/null; then
    warn "PostgreSQL 客户端未安装，跳过数据库创建检查"
    warn "如果数据库不存在，后续迁移可能会失败"
else
    # 检查数据库是否存在
    if PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
        info "数据库 '$DB_NAME' 已存在"
    else
        info "创建数据库 '$DB_NAME'..."
        PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME;"
        info "数据库 '$DB_NAME' 创建成功"
    fi
fi

# 运行数据库迁移
info "应用数据库迁移..."
uv run -m alembic upgrade head

info "数据库初始化完成!"
