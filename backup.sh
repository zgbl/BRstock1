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
# -a: 归档模式
# -v: 显示过程
# --exclude: 排除项
rsync -av --progress ./ "$TARGET_DIR" \
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
    --exclude "docs/"

echo "✅ Backup completed successfully at $TARGET_DIR"
