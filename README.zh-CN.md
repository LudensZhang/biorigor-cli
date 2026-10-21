# biorigor-cli

**自建 BioRigor 论文审查服务的命令行客户端。**
[English README](README.md)

BioRigor 对一篇科研论文做四维审查（思路创新性、干实验方法、湿实验图片、源数据取证），
产出带风险评级的 HTML 报告。这个 CLI 让你不开浏览器也能用它，或者把它接进自己的脚本。

```console
$ biorigor submit paper.pdf
queued: abc123def456
  main: paper.pdf
  next: biorigor wait abc123def456 --download ./reports

$ biorigor wait abc123def456 --download ./reports
  .. abc123def456  running    reviewing methods
  OK abc123def456  done       risk MEDIUM    paper.pdf
  report saved: ./reports/abc123def456.html (48.2KB)
```

**单文件、只用 Python 标准库**，不需要 `pip install`。

> ⚠️ 这是**客户端**，不是服务端。你需要有一个已部署的 BioRigor 服务。
> 客户端**不内置任何默认地址** —— 地址由你填。

---

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/LudensZhang/biorigor-cli/main/biorigor -o biorigor
chmod +x biorigor
sudo mv biorigor /usr/local/bin/
```

需要 **Python 3.8+**。

## 配置服务地址

```bash
biorigor login --host https://biorigor.example.org
```

登录前会先探一遍 `<URL>/api/health`，地址写错会立刻报错，不会把错误配置存下来。

凭据存在 `~/.config/biorigor/config.json`，权限 `0600`。
用 `BIORIGOR_CONF_DIR` 可以换位置。

非交互场景：

```bash
# 每次会话指定
export BIORIGOR_HOST=https://biorigor.example.org

# CI：直接给 token，跳过登录
export BIORIGOR_HOST=https://biorigor.example.org
export BIORIGOR_TOKEN=<token>

# 密码从 stdin 读（写脚本时用）
printf '%s\n' "$PW" | biorigor login --host https://biorigor.example.org -u alice --password-stdin
```

## 命令

| 命令 | 作用 |
|---|---|
| `login [--host URL]` | 登录，保存 token |
| `logout` | 删除本地凭据 |
| `whoami` | 当前用户 / 角色 / 服务地址 |
| `ping [URL...]` | 探测 `/api/health` |
| `models` | 列出模型、引擎、支持的组合 |
| `submit MAIN [-s SUPP]...` | 提交一篇 |
| `batch PATTERN... [--wait]` | 批量提交（支持 glob）|
| `list [--limit N]` | 我的任务 |
| `status [ID...]` | 不给 ID 时看活跃任务 |
| `wait ID... [--download DIR]` | 阻塞等待完成 |
| `report ID [-o DIR]` | 下载 HTML 报告 |
| `cancel ID...` / `cancel all` | 终止任务 |
| `delete ID...` | 删除记录与产物 |

## 脚本化

所有命令都支持 `--json`，退出码有语义：

| 退出码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | 审查失败或未正常结束（`wait` / `batch` 用）|
| `2` | 用法、认证、网络问题 |

### 取 taskId

```bash
TID=$(biorigor submit paper.pdf --json \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["taskId"])')
```

### 逐篇处理一个目录

```bash
#!/usr/bin/env bash
set -uo pipefail
OUT=./reports; mkdir -p "$OUT"

for pdf in ~/papers/*.pdf; do
  echo "== $(basename "$pdf")"
  TID=$(biorigor submit "$pdf" --json \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["taskId"])') || continue
  biorigor wait "$TID" --interval 120 --download "$OUT" --json >> "$OUT/tasks.jsonl"
done
```

### 先批量提交，之后再统一等

```bash
biorigor batch 'papers/*.pdf' --json > submitted.json

biorigor wait $(python3 -c '
import json
d = json.load(open("submitted.json"))
print(" ".join(x["taskId"] for x in d["submitted"]))') --download ./reports
```

### 定时巡检活跃任务

```bash
biorigor status --json | python3 -c '
import json, sys
for t in json.load(sys.stdin):
    print(t["id"], t["status"], t["stage"])'
```

更多示例见 [`examples/`](examples/)。

## 选模型和引擎

```bash
biorigor models
```

`--model` / `--harness` 不填就用服务端配置里的默认值。
远程/付费模型需要 `--key`。
**有哪些模型、引擎叫什么名字，都由你自己的部署决定**，不是客户端写死的。

## 一次审查要多久

| 输入量 | 大约 |
|---|---|
| 只有正文 PDF | 20–60 分钟 |
| 正文 + 补充材料 + 源数据 | 1–2.5 小时 |

服务端**串行**处理任务，多提交会排队。
单次运行有时间上限（参考部署默认 4 小时）；被中断时部分报告会保留，
`report` 会标注为不完整。

## 排错

```bash
biorigor ping                      # 服务能连上吗
biorigor ping https://other.host   # 换一个地址试试
biorigor whoami                    # token 还有效吗
```

| 现象 | 处理 |
|---|---|
| `no server configured` | 用 `--host` 指定，或 `export BIORIGOR_HOST=...` |
| `does not look like a BioRigor server` | URL / 协议写错，或 `/api/health` 被代理挡了 |
| `HTTP 401` | token 过期，`biorigor logout && biorigor login` |
| `HTTP 403` | 只能操作自己的任务（管理员可操作全部）|
| 任务变成 `error` | `biorigor status <id>` 会打印 `error` 字段 |

## 开发

整个客户端就是一个文件，没有构建步骤、没有依赖：

```bash
git clone git@github.com:LudensZhang/biorigor-cli.git
cd biorigor-cli
./biorigor --help
python3 -m py_compile biorigor
```

## 许可

MIT，见 [LICENSE](LICENSE)。
