from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.sauth_capture import capture_sauth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="从本机 Minecraft.Windows.exe 内存捕获 sauth")
    parser.add_argument("--pid", type=int, default=None, help="目标进程 PID；省略时自动查找")
    parser.add_argument("--process-name", default=None, help="指定进程名；省略时依次尝试启动器和游戏")
    parser.add_argument("--max-bytes", type=int, default=1024 * 1024 * 1024)
    parser.add_argument("--output", type=Path, default=ROOT.parent / "data" / "sauth.json")
    args = parser.parse_args()

    result = capture_sauth(args.pid, args.process_name, args.max_bytes)
    if result is None:
        print("未找到发烧启动器或 Minecraft 进程，请先启动官方客户端并完成登录。", file=sys.stderr)
        return 2
    if not result.sauth:
        print(
            f"已扫描 {result.scanned_bytes / 1024 / 1024:.1f} MiB，但未找到完整 sauth。"
            "请确认游戏已经登录，并尝试以管理员身份运行。",
            file=sys.stderr,
        )
        return 3
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.sauth, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"已从 {result.process_name} (pid={result.pid}) 捕获 sauth，"
        f"匹配 {result.matched_offsets} 组，写入 {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
