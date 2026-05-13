#!/bin/bash

# 获取当前时间，格式为 yyyymmddhhmm
TIMESTAMP=$(date +"%Y%m%d%H%M")

# 定义备份目标根目录 (项目根目录下的 release 文件夹)
BACKUP_ROOT="./release"
TARGET_DIR="$BACKUP_ROOT/$TIMESTAMP"

echo "🚀 Starting backup to $TARGET_DIR..."

# 创建备份目录
mkdir -p "$TARGET_DIR"

# 使用 rsync 进行备份，排除不需要的文件
rsync -av ./ "$TARGET_DIR" \
    --exclude "release" \
    --exclude ".git" \
    --exclude "__pycache__" \
    --exclude ".pytest_cache" \
    --exclude "*.pyc" \
    --exclude ".DS_Store" \
    --exclude ".gemini" \
    --exclude ".vscode" \
    --exclude "node_modules" \
    --exclude "Data/" \
    --exclude "docs/" \
    --exclude "API/" \
    --exclude "deploy/moomoo_opend/data/" \
    --exclude ".env" \
    --exclude "*.log"

echo "✅ Backup completed successfully at $TARGET_DIR"
echo "📊 Backup size: $(du -sh "$TARGET_DIR" | cut -f1)"
