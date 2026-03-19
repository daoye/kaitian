# KaiTian CLI 设计说明

KaiTian CLI 是各原子模块（auth/browser/downloader/validator/publisher/discovery）的统一命令入口层，职责是编排和参数处理，不承载站点业务细节。

## 研究结论

当前仓库已存在 `apps/cli`，技术栈为 Typer，入口是 `kaitian = cli.main:main`。现状只有 `hello` 测试命令，尚未形成面向模块的命令分组与错误语义。

结合项目约束（简单优先、模块原子化、最小依赖）与框架对比：

- `argparse`：标准库、零额外依赖，但命令组织和测试体验在中型项目中偏重。
- `click`：成熟稳定、控制力高，适合复杂 CLI；样板代码相对更重。
- `typer`：基于 Click，类型提示友好，命令分组与测试（CliRunner）足够，且项目已在使用。

结论：CLI 模块继续使用 Typer，不更换框架。

参考文档：

- Typer: https://typer.tiangolo.com/
- Click: https://click.palletsprojects.com/
- argparse: https://docs.python.org/3/library/argparse.html

## 设计目标

1. 保持 CLI 仅做编排，不侵入各模块内部实现。
2. 命令分组与包结构一一对应，降低认知成本。
3. 错误输出和退出码可预期，便于脚本化集成。
4. 先交付最小可用命令集，再迭代扩展。

## 模块结构设计

建议采用以下结构：

```text
apps/cli/src/cli/
  main.py                  # 根 app 与子命令注册
  __init__.py
  __version__.py
  commands/
    auth.py                # auth 分组命令
    browser.py             # browser 分组命令
    downloader.py          # downloader 分组命令
    validator.py           # validator 分组命令
    publisher.py           # publisher 分组命令
    discovery.py           # discovery 分组命令
```

约束：命令文件只调用公开 API（如 `AuthManager`、`BrowserManager`），不直接耦合站点私有细节。

## 命令模型设计

根命令：`kaitian`

一级命令按模块分组：

- `kaitian auth ...`
- `kaitian browser ...`
- `kaitian downloader ...`
- `kaitian validator ...`
- `kaitian publisher ...`
- `kaitian discovery ...`

P0 最小命令集（先落地 auth + 基础诊断）：

- `kaitian version`
- `kaitian doctor`
- `kaitian auth login --site znzmo --account <id> --mode sms|password`
- `kaitian auth verify --site znzmo --account <id>`
- `kaitian auth logout --site znzmo --account <id>`

说明：`auth login` 的短信模式复用当前 `verification_code_provider`，当未传 `sms_code` 时进入人工输入等待流程。

## 错误与退出码设计

为避免过度设计，仅定义稳定最小集合：

- `0`：成功
- `2`：参数错误（Typer/Click 默认）
- `10`：认证失败（`AuthError`）
- `11`：站点不支持（`SiteNotSupportedError`）
- `20`：浏览器启动/上下文失败
- `30`：下载/校验/发布流程失败
- `99`：未知异常

输出策略：

- 正常结果输出到 stdout。
- 错误信息输出到 stderr，并返回非 0 退出码。

## 测试策略

使用 `typer.testing.CliRunner` 做命令级单元测试：

1. `--help` 可用性。
2. 参数缺失与非法值。
3. 认证成功/失败返回码。
4. 短信登录等待人工输入路径可被注入 provider 验证。

## 迭代路径

- P0：完成根命令、auth 子命令、version/doctor、基本退出码。
- P1：补齐 browser/downloader/validator/publisher/discovery 子命令骨架。
- P2：增加流水线命令（workflow），串联原子模块但不内嵌站点细节。

## 安装与使用

```bash
pip install -e .
kaitian --help
# or
$ uv run kaitian --hel
```


