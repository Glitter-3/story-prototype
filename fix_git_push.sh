#!/bin/bash
echo "🔧 修复 Git 推送问题..."

# 1. 修正远程仓库 URL
echo "📝 修正远程仓库 URL..."
git remote set-url origin https://github.com/Glitter-3/story-prototype.git

# 2. 验证修正
echo "✅ 当前远程仓库配置："
git remote -v

# 3. 提示下一步操作
echo ""
echo "🎯 接下来需要："
echo "1. 访问 https://github.com/settings/tokens 创建 Token"
echo "2. 运行：git push origin main"
echo "3. 用户名输入：Glitter-3"
echo "4. 密码输入：你的 Personal Access Token"
echo ""
echo "💡 或者配置 SSH 密钥免认证："
echo "   ssh-keygen -t ed25519 -C 'shenshuai1029@163.com'"
echo "   cat ~/.ssh/id_ed25519.pub"
