@echo off
chcp 65001 >nul
title VocabMaster 一键部署工具
color 0A

echo ============================================
echo    VocabMaster 阿里云部署脚本
echo    版本: v2.0 (含教师验证码系统)
echo ============================================
echo.

:: 配置区（修改这些变量）
set SERVER_IP=47.101.195.225
set SERVER_USER=root
set SERVER_PASS=你的服务器密码
set PROJECT_PATH=/www/wwwroot/vocabmaster

echo [配置信息]
echo 服务器: %SERVER_IP%
echo 用户: %SERVER_USER%
echo 项目路径: %PROJECT_PATH%
echo.

:: 检查是否安装 plink (PuTTY 工具)
where plink >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 plink (PuTTY SSH工具)
    echo 请先安装 PuTTY: https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html
    echo 或将 plink.exe 放在本脚本同目录下
    pause
    exit /b 1
)

echo [1/6] 正在连接服务器并备份数据...
plink -batch -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "cd %PROJECT_PATH% && cp db.sqlite3 db.sqlite3.backup.$(date +%%Y%%m%%d) 2>nul; echo 备份完成"

echo.
echo [2/6] 正在拉取最新代码...
plink -batch -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "cd %PROJECT_PATH% && git pull origin main || echo Git拉取失败，使用本地代码"

echo.
echo [3/6] 安装依赖并迁移数据库...
plink -batch -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "cd %PROJECT_PATH% && source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple && python manage.py makemigrations && python manage.py migrate"

echo.
echo [4/6] 收集静态文件...
plink -batch -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "cd %PROJECT_PATH% && source venv/bin/activate && python manage.py collectstatic --noinput"

echo.
echo [5/6] 重启 Gunicorn 服务...
plink -batch -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "pkill gunicorn 2>/dev/null; cd %PROJECT_PATH% && source venv/bin/activate && nohup gunicorn myproject.wsgi:application --bind 0.0.0.0:8000 --workers 3 --daemon && echo '服务已启动'"

echo.
echo [6/6] 检查服务状态...
plink -batch -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "sleep 2 && netstat -tlnp | grep :8000 && echo '? 部署成功！访问: http://%SERVER_IP%:8000' || echo '? 端口未监听，请检查日志'"

echo.
echo ============================================
echo    部署完成！
echo ============================================
echo 访问地址: http://%SERVER_IP%:8000
echo 教师后台: http://%SERVER_IP%:8000/teacher/
echo.
echo 查看实时日志:
echo   plink -pw %SERVER_PASS% %SERVER_USER%@%SERVER_IP% "tail -f %PROJECT_PATH%/logs/error.log"
echo.
pause