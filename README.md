# semver

语义化版本（[SemVer 2.0.0](https://semver.org/lang/zh-CN/)）的比较与递增小工具。

纯 Python 标准库，零依赖，本地运行。

## 安装

无需安装，把 `semver.py` 放到 PATH 里，或在项目目录下运行：

```bash
python3 -m semver compare 1.2.3 1.10.0
```

## 用法

### compare — 比较两个版本

输出 `-1` / `0` / `1`，并附一句人话结论。**退出码恒为 0**（除非输入非法），
比较结果印在标准输出里，方便脚本读取：

```bash
$ python3 -m semver compare 1.2.3 1.10.0
-1
1.10.0 更新（1.2.3 < 1.10.0）

$ python3 -m semver compare 2.0.0 2.0.0
0
两者相等（2.0.0 == 2.0.0）

$ python3 -m semver compare 1.0.0-alpha 1.0.0
-1
1.0.0 更新（1.0.0-alpha < 1.0.0）
```

前置标签版本 `<` 同编号正式版，这是 SemVer 规范的要求，不是 bug。

### bump — 递增版本号

```bash
$ python3 -m semver bump major 1.2.3
2.0.0
$ python3 -m semver bump minor 1.2.3
1.3.0
$ python3 -m semver bump patch 1.2.3
1.2.4
```

前置标签版本 `bump patch` 会直接"转正"（和 `npm version patch` 行为一致）：

```bash
$ python3 -m semver bump patch 1.2.3-rc.1
1.2.3
```

递增会丢弃前置标签和构建元数据——这是刻意设计：发版时旧标签本来就不该带过去。

### sort — 版本排序

```bash
$ python3 -m semver sort v1.10.0 v1.2.3 2.0.0 1.0.0-alpha 1.0.0
1.0.0-alpha
1.0.0
1.2.3
1.10.0
2.0.0
```

- `v` 前缀会被自动剥离（输出时不保留前缀）；
- `--reverse` 降序；`--json` 输出 JSON 数组。

### valid — 校验版本合法性（给 CI 用）

```bash
$ python3 -m semver valid 1.2.3; echo $?
1.2.3 合法
0
$ python3 -m semver valid 1.2; echo $?
error: 不是合法的语义化版本：'1.2'（应为 X.Y.Z 格式，如 1.2.3）
1
```

## 比较规则（诚实说明）

- 严格 SemVer 2.0.0：`1.2`、`01.2.3`（前导零）、`1.2.3-` 都判非法；
- 前置标签标识符：纯数字按数值比（`alpha.2 < alpha.10`），数字 < 非数字；
- 构建元数据（`+build`）**不参与**比较，`1.2.3+a` 与 `1.2.3+b` 视为相等；
- 注意 `sort -V` 不是语义化版本排序：它把 `1.0.0` 排在 `1.0.0-alpha`
  前面（规范要求相反），`v` 前缀也会干扰它的排序。本工具严格按规范来。

## 已知局限

- 只做严格语义化版本；`1.2`、`2024.01` 这类"宽松版本"不支持——这是设计取舍，不是 bug；
- `sort` 的排序语义与 `compare` 完全一致（同一套比较函数）；
- 比较忽略构建元数据，这是 SemVer 规范本身的规定。
