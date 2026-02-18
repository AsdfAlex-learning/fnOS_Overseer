# fnOS Overseer

fnOS Overseer 是一个专为飞牛 NAS (fnOS) 设计的监控与安全审计工具。它提供硬件监控、每日报表、用户行为分析以及异常行为报警功能。

## ✨ 功能特性

- **📊 硬件监控**: 实时监控 CPU、内存、存储使用率以及基于 TDP 的功耗估算。
- **📧 每日报表**: 每天自动生成包含系统状态、功耗统计和用户行为的 HTML 报表，并通过邮件发送。
- **🛡️ 行为审计**: 
  - 监控用户文件上传行为。
  - **病毒检测**: 识别文件扩展名欺骗（如 `.exe` 伪装成 `.jpg`）。
  - **异常检测**: 识别疑似空脚本（极小文件）。
- **🔒 安全集成**: 
  - 支持 fnOS 超级管理员会话认证。
  - 运行时锁定（通过环境变量控制）。

---

## 🚀 快速开始 (小白友好版)

本指南将指导您在 fnOS 上部署此服务，无需深入了解 Docker 命令。

### 1. 准备工作

1.  **开启 SSH**: 在 fnOS 系统设置中开启 SSH 功能。
2.  **连接 SSH**: 使用终端工具（如 Windows 的 PowerShell 或 macOS 的 Terminal）连接到您的 NAS。
    ```bash
    ssh admin@<您的NAS_IP>
    # 输入密码登录
    ```
3.  **获取代码**:
    ```bash
    # 如果已安装 git
    git clone https://github.com/AsdfAlex-learning/fnOS_Overseer.git
    cd fnOS_Overseer
    
    # 或者下载 zip 包解压 (如果您是通过上传文件方式)
    # unzip fnOS_Overseer.zip
    # cd fnOS_Overseer
    ```

### 2. 配置 (最关键的一步)

在运行之前，您需要告诉程序如何连接到您的 fnOS 以及如何发送邮件。

#### 第一步：创建配置文件

复制示例配置文件：
```bash
cp .env.example .env
```

#### 第二步：获取 fnOS Token (FNOS_SUPER_TOKEN)

这是最重要的一步，请仔细操作：

1.  打开浏览器，登录您的 fnOS 管理页面。
2.  登录成功后，按键盘上的 **F12** 键打开“开发者工具”。
3.  在开发者工具中，找到 **"Application"** (应用) 标签页（Chrome/Edge）或 **"Storage"** (存储) 标签页（Firefox）。
4.  在左侧菜单中展开 **"Local Storage"** (本地存储) 或 **"Cookies"**。
5.  找到您的 fnOS 域名/IP。
6.  在列表中寻找名为 `token`、`access_token` 或 `authorization` 的键值。
    -   *提示：通常是一个很长的字符串，以 `ey` 开头。*
7.  复制这个值，这就是您的 `FNOS_SUPER_TOKEN`。

#### 第三步：编辑配置文件

使用 `nano` 或 `vim` 编辑 `.env` 文件：

```bash
nano .env
```

填入以下信息（使用方向键移动，输入完成后按 `Ctrl+O` 保存，`Enter` 确认，`Ctrl+X` 退出）：

```ini
# 邮件发送设置 (建议使用 QQ邮箱 或 Gmail)
# 以 QQ 邮箱为例：
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=123456@qq.com
# 注意：这里不是QQ登录密码，而是“授权码” (在QQ邮箱设置->账户->POP3/IMAP服务中生成)
SMTP_PASS=abcdefghijklmn
SMTP_TLS=true
EMAIL_FROM=fnOS_Overseer <123456@qq.com>
EMAIL_TO=您的接收邮箱@example.com

# fnOS 连接设置
# 刚刚获取的 Token 填在这里
FNOS_SUPER_TOKEN=eyAAABBBCCCC111222333...
```

### 3. 启动服务

在 `fnOS_Overseer` 目录下，执行以下命令即可一键启动：

```bash
docker compose up -d --build
```

- `up`: 启动服务
- `-d`: 后台运行（不会占用当前终端窗口）
- `--build`: 构建镜像（第一次运行必须加）

等待命令执行完成，如果看到 `Started` 字样，说明部署成功！

---

## 📖 使用指南

### 访问仪表盘

在浏览器输入：`http://<您的NAS_IP>:8000`

- **默认端口**: 8000
- **默认用户**: 无需登录（但在外网访问请务必配合 VPN 或反向代理使用）

### 查看日志

如果遇到问题，可以查看运行日志：

```bash
docker compose logs -f
```
(按 `Ctrl+C` 退出日志查看)

### 停止服务

```bash
docker compose down
```

---

## 🛠️ 高级配置

### 方式一：Web 界面配置 (推荐)

项目内置了可视化配置页面，您可以在浏览器中直接修改大部分设置：

1.  访问仪表盘首页 `http://<您的NAS_IP>:8000`。
2.  点击顶部导航栏的 **"配置"** 或首页的 **"打开配置页"** 按钮。
3.  在页面中修改参数（如报表时间、TDP 功耗参数、邮件设置等）。
4.  点击底部的 **"保存到 config.yaml"** 按钮。
    -   *注：修改保存后会自动更新配置文件，部分设置（如端口、调度时间）可能需要重启容器生效。*

### 方式二：手动修改配置文件

如果您更喜欢通过命令行操作，也可以手动编辑 `config.yaml` 文件：

```bash
cp config.yaml.example config.yaml
nano config.yaml
```

修改完成后，需要重启服务生效：
```bash
docker compose restart
```

---

## ⚠️ 常见问题

**Q: 邮件发送失败？**
A: 请检查 `SMTP_PASS` 是否为邮箱的**授权码**而不是登录密码。另外确认 `SMTP_PORT` 是否正确（SSL通常为465）。

**Q: 无法获取 fnOS 数据？**
A: 请确认 `FNOS_SUPER_TOKEN` 是否过期。如果 fnOS 重新登录，可能需要更新此 Token。

**Q: 功耗显示不准？**
A: 功耗是基于 TDP 的估算值。您可以在 `config.yaml` 中根据您的硬件型号调整 `hardware_tdp` 参数。

---

## 许可证

MIT License
