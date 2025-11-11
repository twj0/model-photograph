# 效果其实是不如CFD的软件，只是玩具而已
[网格图片](https://telegraph.ttwwjj.ddns-ip.net/file/AgACAgUAAyEGAAShY8_eAAOYaRKWRQURkV9uQNypjpbpGfkmdC4AAvcLaxugfZFUOl2GqCPmkygBAAMCAAN3AAM2BA.png)

## 工具概览
本工具依赖 `PyVista` 与 `meshio`，用于加载 `mesh/model-stl.stl` 等网格文件，输出科研风格的高质量截图，并支持实时交互预览。

## 配置文件 `config/config.yaml`
- **mesh_path**：默认网格路径，可改为其他 `*.stl`/`*.msh` 文件。
- **output_path**：静态渲染输出的基准文件名。程序会自动在文件名末尾追加时间戳。
- **render.window_size**：渲染窗口宽高，推荐设置较高以便后期降采样。
- **render.background**：上下背景色，可用十六进制颜色值。
- **render.parallel_projection**：是否开启正交投影，科研插图常用。
- **render.eye_dome_lighting**：增强深度感的 EDL。
- **render.anti_aliasing**：抗锯齿模式，如 `msaa`。
- **render.image_scale**：截图时的超采样倍数，可提升边缘清晰度。
- **render.transparent_background**：是否输出透明背景。
- **render.camera_position**：相机位置、焦点与上向量。本项目默认采用南西方向俯视并聚焦模型中心。
- **render.camera_zoom**：相机缩放倍数，数值越大越接近模型。
- **render.lighting**：配置主光、辅光位置与强度。
- **render.mesh**：网格颜色、是否显示边缘等。
- **render.quality**：高质量渲染选项，可启用 `ssao`、`depth_peeling`、`fxaa`，若运行环境不支持会自动忽略。
- **timestamp_format**（根节点，可选）：自定义输出文件的时间戳格式，默认为 `%Y%m%d-%H%M%S`。

## 快速开始
```bash
# 可选：激活虚拟环境（若存在）
.venv\Scripts\Activate.ps1
```
```python
pip install -r requirements.txt
```
```uv
# 如果使用uv: 使用uv 进行同步
uv sync
```
```python
# 进入交互模式
python main.py --interactive
```

键盘点击**E**就可以导出图片


```python
# 指定不同网格或输出目录
python main.py --mesh path/to/mesh.stl --output fig/custom.png
```

## 输出结果说明
- 静态渲染会保存到 `fig/` 目录，文件名形式为 `<基准名>_<时间戳>.png`。
- 通过调整 `config/config.yaml` 中的 `window_size`、`image_scale` 以及 `quality`，可提高图片分辨率和细节表现。

## 交互模式操作
- **鼠标左键拖动**：旋转模型。
- **鼠标右键拖动**：平移视图。
- **鼠标滚轮**：缩放。
- **键盘 E**: 导出图片。
关闭窗口即可退出交互模式，期间不会写入静态截图。

## 常见问题
- 若截图过大导致内存占用高，可适当降低 `window_size` 或 `image_scale`。
- 若需透明背景，将 `transparent_background` 设为 `true` 并确保目标格式支持 Alpha 通道。
- 若启用 `quality` 中的高级特性但无效果，可能是当前 GPU/驱动不支持，对结果无副作用。
