# 🧩 部會業務子模組庫 (Modules Directory)

本目錄存放該部會下各獨立業務子模組（例如 `x10_[name]_db`）。

## 📁 建立新子模組 SOP
當需要新增一個業務子模組時，請複製 `template_blueprint/` 目錄：
```bash
cp -r modules/template_blueprint modules/x10_[submodule_name]_db
```
並完成內部 `SPECIFICATION.md` 與 `commands.py` 擴充。
