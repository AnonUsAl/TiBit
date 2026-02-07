# TChain Studio

简明文档（中文版）

## 项目简介

`TChain Studio` 是一个基于 Python + `tkinter` 的轻量级区块链/挖矿模拟器（教育/演示用途）。界面允许创建钱包、提交交易、单次或持续挖矿，并将链数据保存为 JSON 文件。

## 依赖

- Python 3.7+
- 标准库：`hashlib`, `json`, `time`, `random`, `os`, `sys`, `tkinter` 等（无需额外 pip 包）

在 Windows 下运行时，`tkinter` 通常随 Python 安装；若报错请 重新安装`tkinter`。

## 快速开始

1. 克隆仓库或把代码放在某目录（示例：`D:\tmsimple`）。
2. 进入项目目录并运行脚本：

```bash
python ..\tm\Tb_Minner.py
```

3. 程序第一次运行会在当前工作目录下生成 `password_hash.txt`（存放密码的 SHA-256 哈希）和 `improved_tcoin_chain.json`（区块链数据）。

默认密码为 `12345678`（程序会写入其哈希），启动时需要输入密码验证。

## 密码存储与更改

- 密码以 SHA-256 哈希形式存储在 `password_hash.txt`（位于程序的当前工作目录）。
- 在程序中使用“🔒更改密码”按钮可以设置新密码，程序会把新密码的 SHA-256 写入 `password_hash.txt`。
- 如果想重置为默认密码，删除 `password_hash.txt` 后重新运行程序，程序会写入默认密码的哈希。

## 文件名或程序名修改

如果要重命名脚本文件：

1. 在文件系统中改名（例如 `Tb_Minner.py` -> `tchain_studio.py`）。
2. 在 git 中执行重命名并提交：

```bash
git mv Tb_Minner.py tchain_studio.py
git add password_hash.txt improved_tcoin_chain.json
git commit -m "Rename main script to tchain_studio.py"
git push origin <branch>
```

如果其他模块或脚本引用了旧文件名，记得更新引用处。

## 保存/退出

- 使用界面上的“💾保存区块链”或“🛡️安全退出”按钮，程序会把当前链保存到 `improved_tcoin_chain.json`。

## 开发与贡献（Git 工作流建议）

1. 创建分支：

```bash
git checkout -b feature/your-feature
```

2. 修改代码、运行测试/手动验证UI。
3. 提交并推送：

```bash
git add .
git commit -m "描述你的改动"
git push origin feature/your-feature
```

4. 在远端仓库发起 Pull Request，描述改动与测试步骤。

## 常见问题

- 程序弹窗提示 `Button object is not callable`：通常因为把按钮变量名与函数同名或误把按钮当成函数调用，查看 `.pack()` 和回调函数定义。
- 无法显示界面：确认 `tkinter` 可用或检查是否在无 GUI 的环境中运行（例如某些服务器）。

---

如需把文档放到 `docs/` 目录，或需要英文版 README，我可以帮你生成并添加到仓库。