"""stealth 脚本加载器."""

import pathlib
from typing import Final

# 脚本目录路径
SCRIPTS_DIR: Final[pathlib.Path] = pathlib.Path(__file__).parent


def load_script(name: str) -> str:
    """加载 JS 脚本文件.

    Args:
        name: 脚本文件名（不含 .js 后缀）

    Returns:
        脚本内容字符串

    Raises:
        FileNotFoundError: 脚本文件不存在
    """
    script_path = SCRIPTS_DIR / f"{name}.js"
    return script_path.read_text(encoding="utf-8")


def load_script_with_vars(name: str, variables: dict[str, str | int | float]) -> str:
    """加载 JS 脚本并替换模板变量.

    Args:
        name: 脚本文件名（不含 .js 后缀）
        variables: 模板变量字典，key 为模板中的 {{KEY}}

    Returns:
        替换变量后的脚本内容
    """
    content = load_script(name)

    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        content = content.replace(placeholder, str(value))

    return content


# 预加载所有脚本（性能优化）
def get_available_scripts() -> list[str]:
    """获取所有可用的脚本名称列表."""
    return [f.stem for f in SCRIPTS_DIR.glob("*.js") if f.is_file()]
