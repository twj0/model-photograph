# 模型科研繪圖專案文件（model-plot）

本文件說明本專案的技術棧、專案結構、安裝與使用方式（含 uv 套件管理）、配置檔說明與常見問題。

## 技術棧概覽

- Python >= 3.13（`pyproject.toml` 指定）
- 套件：
  - `pyvista`: 以 VTK 為基礎的 3D 視覺化與渲染，用於離屏渲染與截圖
  - `meshio`: 多網格格式讀寫轉換（.stl、.msh、.vtu 等），在非 `.msh` 時做降階轉換
  - `pyyaml`: 讀取 YAML 組態
- 建置/打包：`setuptools`
- 專案模組：`main.py`（以 CLI 方式執行）
- 網格與資源：`mesh/` 內含 `.stl`、`.mph` 等；輸出圖像於 `fig/`

## 專案結構

- `main.py`: 進入點，讀取設定、載入網格、建立繪圖器、配置相機/光照/材質並截圖
- `config/config.yaml`: 預設配置（可被 CLI 參數覆蓋）
- `mesh/`: 網格檔案目錄（例如 `model-stl.stl`）
- `fig/`: 預設輸出圖像目錄（例如 `model-stl.png`）
- `pyproject.toml`: Python 版本與依賴宣告

## 執行流程概述

`main.py` 的主要流程：
1. 讀取 YAML 組態（若不存在，採用空組態並使用預設）
2. 解析路徑參數與相對/絕對路徑
3. 載入網格：
   - 優先以 `pyvista.read()` 讀取
   - 若失敗且副檔名不是 `.msh`，使用 `meshio` 轉為臨時 `.vtu` 再由 `pyvista` 載入
4. 建立 `pyvista.Plotter(off_screen=True)` 以進行離屏渲染
5. 根據組態：
   - 背景（漸層或單色）
   - 光照模式與自訂光源陣列
   - 抗鋸齒（如 `msaa`）
   - 網格渲染參數（顏色、PBR、邊線、粗糙度/金屬度等）
   - 相機位置（或使用 `iso`）
6. 截圖至輸出路徑並關閉繪圖器

## 設定檔說明（config/config.yaml）

範例（專案內預設）：

```yaml
mesh_path: "mesh/model-stl.stl"
output_path: "fig/model-stl.png"
render:
  window_size: [2400, 1800]
  lighting_mode: "light kit"  # 可用：default/on/true、light kit/physically based、off
  background: { bottom: "#ffffff", top: "#ffffff" }
  parallel_projection: true
  eye_dome_lighting: true
  anti_aliasing: "msaa"
  image_scale: 2
  transparent_background: false
  camera_position:
    - [1.8, 1.8, 1.8]   # 相機位置（近似等角）
    - [0, 0, 0]         # 注視點
    - [0, 0, 1]         # 上方向
  camera_zoom: 1.2
  lighting:
    key_light: { position: [5, 5, 5], intensity: 1.2, color: "#ffffff" }
    fill_light: { position: [-5, -5, 2], intensity: 0.6, color: "#ffffff" }
  mesh:
    color: "#d9d9d9"
    pbr: false
    show_edges: true
    edge_color: "#666666"
    line_width: 1.0
    smooth_shading: true
  axes:
    enabled: false
```

鍵值對照：
- `mesh_path`: 網格檔路徑，支援 `.stl`、`.msh` 等
- `output_path`: 輸出影像路徑（PNG）
- `render.window_size`: 視窗大小（像素），離屏渲染亦影響輸出尺寸
- `render.lighting_mode`: 光照模式：
  - `default`/`on`/`true`: 使用預設光源
  - `light kit`/`physically based`: 嘗試啟用 PyVista 的光照套件或物理式光照
  - `off`/`false`/`none`: 取消所有光源
- `render.background.bottom/top`: 漸層背景色；只設 `bottom` 則為單色背景
- `render.camera_position`: `[position, focal_point, view_up]`
- `render.parallel_projection` (bool): 平行投影，避免透視變形，學術圖強烈建議
- `render.eye_dome_lighting` (bool): 啟用 EDL 增強深度知覺，對表面模型友善
- `render.image_scale` (int): 輸出截圖超取樣倍率（例如 2 代表 2×）
- `render.transparent_background` (bool): 輸出背景透明（適合疊在期刊模板）
- `render.camera_zoom` (float): 相機縮放，>1 拉近，<1 推遠
- `render.lighting`: 多盞光（以鍵名分組），每組支援 `position`、`intensity`、`color`
- `render.mesh`: 網格材質與邊線等參數，會傳入 `plotter.add_mesh()`
- `render.anti_aliasing`: 例如 `msaa`（傳至 `enable_anti_aliasing`）

## 命令列使用（使用 uv）

本專案使用 `uv` 管理 Python 環境與依賴。

### 安裝 uv
- 參考官方安裝指引（Windows 可用 `pipx install uv` 或發行版提供的安裝器）

### 建立與安裝依賴
```bash
uv venv --python 3.13
uv pip install -e .
```
- 若需鎖定檔案：`uv pip compile -o uv.lock pyproject.toml`
- 安裝鎖定依賴：`uv pip sync uv.lock`

### 執行
- 使用預設配置：
```bash
uv run python main.py
```
- 指定自訂配置或網格/輸出：
```bash
uv run python main.py --config config/config.yaml
uv run python main.py --mesh mesh/model-stl.stl --output fig/model-stl.png
```

## Windows / 顯示環境注意事項
- PyVista 離屏渲染在無頭環境通常可行；若遇到 OpenGL/驅動問題，請更新顯示驅動或安裝支援的 OpenGL 實作
- 若無法離屏渲染，可嘗試移除 `off_screen=True` 測試是否為環境問題
- 影像尺寸取決於 `window_size` 與高 DPI 設定；結果不如預期時可明確設定 `window_size`

## 常見問題（FAQ）
- STL 載入錯誤：
  - 確認檔案存在且路徑正確
  - 嘗試讓 `meshio` 轉檔（對非 `.msh` 副檔名會自動嘗試）
- 光照過暗或過曝：
  - 調整 `lighting_mode` 或自訂 `lighting` 各燈 `intensity`
- 齒鋸邊明顯：
  - 啟用 `anti_aliasing: msaa` 或提高輸出解析度
- 材質沒有 PBR 效果：
  - 確認使用 `render.mesh.pbr: true`，並適當調整 `metallic`、`roughness`

## 版本與相容性
- Python: `>=3.13`
- 依賴：`pyvista`、`meshio`、`pyyaml`（詳見 `pyproject.toml` 與 `uv.lock`）

---
如需進階自定義（如相機路徑動畫、批量渲染），可在 `main.py` 基礎上擴展 `configure_plotter` 與呼叫流程。
