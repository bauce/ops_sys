# 部署到 Dokploy

本系统是**单容器应用**：FastAPI 同时提供 API 与前端静态页面，数据（SQLite + 上传照片）保存在容器内 `/app/backend/data`，必须挂载持久化卷、保持单副本。

仓库已包含：

- `Dockerfile`：Node 构建前端 → Python 运行后端（多阶段构建）
- `docker-compose.yml`：Dokploy Compose 方式可直接使用
- `.dockerignore`：排除本地虚拟环境、node_modules、本地数据，避免把测试数据打进镜像
- `.env.example`：环境变量示例

> 说明：当前开发机没有 Docker，未在本地执行镜像构建；请以 Dokploy 的构建日志为准。应用本身已在 Python 3.9 环境完整跑通，Docker 镜像使用 Python 3.12，依赖版本已固定。

---

## 一、准备代码仓库

Dokploy 从 Git 仓库拉取代码。先推送项目到 GitHub / Gitee / GitLab（私有仓库即可）：

```bash
cd "/Users/harv3y/Documents/work_space/物资管理"
git init
git add .
git commit -m "ops management system"
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
```

`.gitignore` 已排除 `.venv`、`node_modules`、`frontend/dist`、`backend/data`，不会把本机数据库和依赖提交上去；前端会在镜像构建时生成。

---

## 二、方式 A：Dokploy Application（推荐）

### 1. 新建应用

Dokploy → **Projects** → 新建/进入项目 → **Create Application**，名称如 `ops-management`。

### 2. 配置代码源

- **Provider**：GitHub / Gitee / GitLab / Git（按你的仓库类型）
- 选择仓库、分支 `main`
- **Build Type**：`Dockerfile`
- **Dockerfile Path**：`Dockerfile`
- **Docker Context Path**：`.`（项目根目录）

### 3. 端口

- **Port**：`8008`（容器内监听端口）

> 若是 Git 仓库放在国内，构建时 npm / pip 可能较慢，可在 **Build Args** 增加：
> `NPM_REGISTRY=https://registry.npmmirror.com`
> `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`

### 4. 环境变量

在 **Environment** 中添加：

| 变量 | 值 | 说明 |
| --- | --- | --- |
| `TZ` | `Asia/Shanghai` | 容器时区，影响工单时间与值班判断 |
| `OPS_DB` | `/app/backend/data/ops.db` | SQLite 路径（默认已是该值，可省略） |
| `OPS_PUBLIC_BASE_URL` | `https://ops.example.com` | 对外访问地址，二维码与邮件链接使用 |
| `OPS_TEST_MODE` | `0` | 测试环境设为 `1`：登录页免密、账号一键切换；**正式环境必须 0** |
| `OPS_SEED_TEST_DATA` | `0` | 测试环境设为 `1`：首次启动写入 24 条测试工单、6 台测试设备；重复启动不重复写入 |

### 5. 挂载持久化卷（必须）

**Mounts → Add Mount → Volume Mount**：

- **Volume Name**：`ops-data`（名称可自定，保持稳定）
- **Mount Path**：`/app/backend/data`

这个目录包含：

- `ops.db`（工单、账号、物资、设备、值班、配置，以及设备密码加密密钥）
- `uploads/`（报障现场照片）

不挂载卷 = 每次重新部署数据全部丢失。

### 6. 绑定域名与 HTTPS

**Domains → Add Domain**：

- **Host**：`ops.example.com`
- **Path**：`/`
- **Internal Port**：`8008`
- **HTTPS**：开启，证书选择 Let's Encrypt（先确保域名 A 记录已指向 Dokploy 服务器）

保存后点 **Deploy**。构建日志出现 `Uvicorn running on http://0.0.0.0:8008` 即启动成功；健康检查地址为 `/api/health`，正常返回 `{"ok":true,...}`。

---

## 三、方式 B：Dokploy Compose

如果习惯用 Compose：

1. 项目 → **Create Compose**
2. Provider 选择仓库、分支 `main`
3. **Compose Path**：`docker-compose.yml`
4. 在 Compose 服务的 **Domains** 中添加域名，容器端口填 `8008`
5. Environment 里可设置 `OPS_PUBLIC_BASE_URL`
6. Deploy

`docker-compose.yml` 已包含健康检查、`ops_data` 命名卷、`8008` 端口暴露；Dokploy 会通过 Traefik 把域名转发到该服务。

如需国内镜像，可在 Compose 的 build args 中传：

```yaml
build:
  args:
    NPM_REGISTRY: https://registry.npmmirror.com
    PIP_INDEX_URL: https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 测试环境（仅测试分支）

测试应用可在 Environment 中额外设置：

```text
OPS_TEST_MODE=1
OPS_SEED_TEST_DATA=1
```

部署后登录页会出现「测试环境 · 免密登录」，点击任意账号直接进入；首次启动自动生成模拟工单与设备。
**正式应用不要设置这两项**，否则任何人都可免密登录。

## 四、首次初始化

1. 打开 `https://ops.example.com`，用初始账号登录：
   - 管理员 `admin / admin123`
   - 受理员 `dispatcher / dispatch123`
   - 工程师 `zhangsan / lisi / wangwu`，密码 `eng123`
2. **立即修改默认密码**，并停用不需要的演示账号。
3. 进入「系统设置」：
   - 填写「二维码地址」为正式域名（若已设置 `OPS_PUBLIC_BASE_URL` 且未在页面填写，则自动使用环境变量）
   - 配置 SMTP 邮件通知并发送测试邮件
4. 进入「房间与二维码」，核对房间后批量打印标签并张贴。
5. 用手机扫码走一遍：报障 → 受理派单 → 处理 → 签字确认。

首次启动会自动建库并写入基础数据：8 个房间、13 种物资、8 台演示设备、9 类故障类型、4 个演示账号；**不会生成演示工单**。

---

## 五、数据备份与恢复

数据都在命名卷 `ops-data` 里。备份建议：

```bash
# 1. 查看卷名（Dokploy/Compose 可能带项目前缀）
docker volume ls | grep ops

# 2. 停容器后打包（保证 SQLite WAL 一致）
docker run --rm \
  -v <卷名>:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/ops-data-$(date +%F).tgz -C /data .
```

恢复：把压缩包解回同名卷后重新部署。也可使用 Dokploy 的 Volume Backup 功能做定时备份。

---

## 六、更新版本

```bash
git add .
git commit -m "update"
git push
```

Dokploy 中进入应用 → **Redeploy**。数据卷保持不变；启动时会自动执行数据库兼容迁移（补字段、补表），无需手工升级。

---

## 七、注意事项

1. **只能 1 个副本**：SQLite 适合单实例；不要开多副本/横向扩容，否则会出现写锁与数据不一致。
2. **必须挂载 `/app/backend/data`**：否则重启即丢数据。
3. **HTTPS 必须**：报障页涉及手机号、照片、设备管理密码，请通过域名 + 证书访问，不要长期用裸 IP + HTTP。
4. **端口只暴露 8008**：对外只开 80/443，数据库不对外。
5. **时区**：`TZ=Asia/Shanghai`，否则工单时间、值班判断、超时预警会偏差 8 小时。
6. **设备台账密码**：使用 Fernet 加密，密钥存在同一数据库的 `settings` 表；备份数据库即备份密钥，**丢失数据库将无法解密密码**。
7. **二维码地址**：打印前确认「系统设置 → 二维码地址」是手机可访问的正式域名，否则贴出去的码打不开。
8. **邮件**：Dokploy 服务器需能访问企业邮箱 SMTP 端口（25/465/587），否则派单邮件会静默失败；可用「发送测试邮件」排查。

---

## 八、常见问题

| 现象 | 排查 |
| --- | --- |
| 502 Bad Gateway | 容器未启动或端口不一致；确认应用 Port=8008，查看 Deploy Logs |
| 构建卡在 npm/pip | 配置 Build Args 国内镜像，或换 Gitee 仓库 |
| 部署后数据消失 | 未挂载 `/app/backend/data`，或卷名变化 |
| 二维码扫不开 | 二维码地址仍是 localhost/旧 IP；到系统设置修改后重新打印 |
| 时间差 8 小时 | 未设置 `TZ=Asia/Shanghai` |
| 上传照片 404 | 卷未包含 `uploads`（应在 `/app/backend/data/uploads`），或反向代理未放行 `/uploads` |
| 邮件发不出 | 检查 SMTP 主机/端口/加密方式/授权码；Dokploy 服务器出网与安全组 |

---

需要我直接操作你的 Dokploy（创建应用、配置域名/卷、触发部署）也可以，但需要你提供：

- Dokploy 访问地址与 API Token（或 SSH 登录方式）
- 已推送代码的 Git 仓库地址
- 计划使用的域名

否则按上面步骤操作即可。
