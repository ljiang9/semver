"""semver: 语义化版本比较与递增小工具。

纯标准库实现，严格遵循 SemVer 2.0.0 规范
(https://semver.org/lang/zh-CN/)：
  - 版本格式: X.Y.Z，可带前置标签 (1.0.0-alpha) 与构建元数据 (1.0.0+build)
  - 比较规则: 先比较主/次/修订号；有前置标签的版本 < 同编号无标签版本；
    前置标签按点分隔标识符逐个比较（纯数字按数值，否则按 ASCII 排序）。
"""

import argparse
import json
import re
import sys

# SemVer 2.0.0 正则（允许可选的 v 前缀，由 parse 统一剥离）
_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class SemVer:
    """一个解析好的语义化版本。"""

    def __init__(self, major, minor, patch, prerelease=(), build=""):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease  # tuple[str]
        self.build = build

    @property
    def core(self):
        return (self.major, self.minor, self.patch)

    def __str__(self):
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += "-" + ".".join(self.prerelease)
        if self.build:
            s += "+" + self.build
        return s

    def _prerelease_key(self):
        """前置标签比较键。返回 (无标签?, 标识符序列)。"""
        key = []
        for ident in self.prerelease:
            if ident.isdigit():
                # 纯数字标识符 < 非数字标识符；数值比较
                key.append((0, int(ident), ""))
            else:
                key.append((1, 0, ident))
        # 无前置标签的版本 > 有前置标签的同编号版本
        return (1 if not self.prerelease else 0, key)

    def compare(self, other):
        """比较两个版本。返回 -1 / 0 / 1。构建元数据不参与比较。"""
        if self.core != other.core:
            return -1 if self.core < other.core else 1
        a, b = self._prerelease_key(), other._prerelease_key()
        if a == b:
            return 0
        return -1 if a < b else 1


def parse(version):
    """解析版本字符串，允许可选的 v/V 前缀。失败抛 ValueError。"""
    text = version.strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    m = _SEMVER_RE.match(text)
    if not m:
        raise ValueError(f"不是合法的语义化版本：{version!r}（应为 X.Y.Z 格式，如 1.2.3）")
    pre = tuple(m.group("prerelease").split(".")) if m.group("prerelease") else ()
    return SemVer(
        int(m.group("major")),
        int(m.group("minor")),
        int(m.group("patch")),
        prerelease=pre,
        build=m.group("build") or "",
    )


def cmd_compare(args):
    try:
        a = parse(args.a)
        b = parse(args.b)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    result = a.compare(b)
    if args.json:
        print(json.dumps(
            {"a": str(a), "b": str(b), "result": result},
            ensure_ascii=False, indent=2))
    else:
        print(result)
        if result < 0:
            print(f"{b} 更新（{a} < {b}）")
        elif result > 0:
            print(f"{a} 更新（{a} > {b}）")
        else:
            print(f"两者相等（{a} == {b}）")
    # 退出码恒为 0（比较结果印在输出里，方便管道/脚本读取）
    return 0


def cmd_bump(args):
    try:
        v = parse(args.version)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    major, minor, patch = v.core
    if args.part == "major":
        major, minor, patch = major + 1, 0, 0
    elif args.part == "minor":
        minor, patch = minor + 1, 0
    else:  # patch
        # 前置标签版本 bump patch 直接"转正"：1.2.3-rc.1 -> 1.2.3
        # （这也是 npm version patch 的行为）
        if not v.prerelease:
            patch = patch + 1
    bumped = SemVer(major, minor, patch)
    if args.json:
        print(json.dumps(
            {"from": str(v), "to": str(bumped), "part": args.part},
            ensure_ascii=False, indent=2))
    else:
        print(bumped)
    return 0


def cmd_sort(args):
    versions = []
    for raw in args.versions:
        try:
            versions.append((parse(raw), raw))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    # 用 compare 保证与 compare 命令完全一致的排序语义（稳定排序）
    from functools import cmp_to_key
    versions.sort(key=cmp_to_key(lambda x, y: x[0].compare(y[0])),
                  reverse=args.reverse)
    if args.json:
        print(json.dumps([str(v) for v, _ in versions], ensure_ascii=False))
    else:
        for v, _ in versions:
            print(v)
    return 0


def cmd_valid(args):
    try:
        parse(args.version)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not args.json:
        print(f"{args.version.strip()} 合法")
    else:
        print(json.dumps({"version": args.version.strip(), "valid": True},
                         ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="semver",
        description="语义化版本（SemVer 2.0.0）比较与递增小工具。")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compare", help="比较两个版本，输出 -1/0/1")
    p.add_argument("a", help="版本 A")
    p.add_argument("b", help="版本 B")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("bump", help="递增版本号")
    p.add_argument("part", choices=["major", "minor", "patch"], help="递增哪一段")
    p.add_argument("version", help="原版本号")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.set_defaults(func=cmd_bump)

    p = sub.add_parser("sort", help="版本排序（升序）")
    p.add_argument("versions", nargs="+", help="待排序的版本列表")
    p.add_argument("--reverse", action="store_true", help="降序")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.set_defaults(func=cmd_sort)

    p = sub.add_parser("valid", help="校验版本是否合法（CI 用：合法 exit 0）")
    p.add_argument("version", help="待校验的版本")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    p.set_defaults(func=cmd_valid)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
