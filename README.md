# fnOS Overseer

fnOS Overseer 是一个专为飞牛 NAS (fnOS) 设计的监控与安全审计工具。它提供硬件监控、每日报表、用户行为分析以及异常行为报警功能。

## 功能特性

- **硬件监控**: 实时监控 CPU、内存、存储使用率以及基于 TDP 的功耗估算。
- **每日报表**: 每天自动生成包含系统状态、功耗统计和用户行为的 HTML 报表，并通过邮件发送。
- **行为审计**: 
  - 监控用户文件上传行为。
  - **病毒检测**: 识别文件扩展名欺骗（如 `.exe` 伪装成 `.jpg`）。
  - **异常检测**: 识别疑似空脚本（极小文件）。
- **安全集成**: 
  - 支持 fnOS 超级管理员会话认证。
  - 运行时锁定（通过环境变量控制）。

## 快速开始

### 1. 环境准备

- Python 3.9+
- fnOS 系统（或兼容的 Linux 环境）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置文件

复制示例配置文件：

```bash
cp .env.example .env
cp config.yaml.example config.yaml
```

**编辑 `.env`**:
配置敏感信息，如 SMTP 邮件服务器、fnOS Token 等。

```ini
SMTP_HOST=smtp.example.com
SMTP_USER=user@example.com
SMTP_PASS=password
FNOS_SUPER_TOKEN=your_token_here
```

**编辑 `config.yaml`**:
配置应用参数，如报表发送时间、TDP 功耗参数等。

### 4. 运行服务

```bash
# 启动 Web 服务 (默认端口 5000)
python3 web/backend/main.py
```

访问 `http://localhost:5000` 查看仪表盘。

## 开发指南

- **后端**: Flask + APScheduler
- **前端**: 原生 HTML/CSS/JS (无构建步骤)
- **代码审查**: 查看 [CODE_REVIEW.md](CODE_REVIEW.md) 了解项目状态和已知问题。

## 许可证

MIT License
