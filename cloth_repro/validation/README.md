# 本地 Mitsuba 运行验证

验证日期：2026-09-27。使用用户克隆的 Mitsuba 源码构建，没有安装 PyPI Mitsuba 替代它。本目录现位于 `mitsuba3/cloth_repro/validation/`。

## 结果

- 源码：`fd9c9ceb38deb511a5c3f8479c8b14c0b552167e`，Mitsuba `3.10.0.dev1`。
- Dr.Jit：随源码子模块构建的 `1.6.0.dev1`。
- MSVC Release 构建通过，最终日志 `build-final.log`。首次构建在资源复制阶段发现缺少 data 子模块，补齐后已完成。
- `scalar_rgb`：256×256、64 spp Cornell Box 渲染与 PNG/EXR 写入通过。
- `cuda_ad_rgb`：RTX 5070、驱动 610.88，相同场景渲染通过。
- Python 自定义 Lambert 材质：eval/pdf/sample 一致性通过；与内置 diffuse 在相同场景、seed 下的图像最大绝对误差为 `1.1920928955078125e-07`。
- 官方 `src/bsdfs/tests/test_diffuse.py`：3 passed。见 `pytest.log`。
- `llvm_ad_rgb`：编译完成，但本机缺少可用 LLVM 运行库（LLVM-C.dll），运行不可用。导入时可能出现 `LLVM API initialization failed`；不影响已验证的 scalar/CUDA 路径。没有安装全局 LLVM。

上述验证仅证明渲染环境及 Python 材质接口可用，不是 2022/2023 布料模型实现，也不是完整测试套件认证。测试 PNG 已实际查看。

## 重跑

在当前目录执行 `run.cmd`。它使用独立的 `.venv`，从 `../../build/Release/python` 加载本地库，并覆盖 `results/` 中的验证输出。失败返回非零退出码。

重新编译使用 `build.cmd`。脚本指定本机 Visual Studio 2022 与三个 RGB variants，并关闭 nanobind split mode；Python 为 3.12.14。依赖版本见 `requirements-lock.txt`，子模块记录见 `submodules.txt`。官方 tutorials 和可选 ITT profiler 子模块未初始化。

单独重跑官方测试，在 `mitsuba3` 根目录的 PowerShell 中执行：

```powershell
$env:PYTHONPATH = "$PWD/build/Release/python"
$env:DRJIT_CACHE_DIR = "$PWD/cloth_repro/validation/cache"
& ./cloth_repro/validation/.venv/Scripts/python.exe -m pytest src/bsdfs/tests/test_diffuse.py -q
```

后续实现优先使用 `cuda_ad_rgb`。库加载路径与数值结果见 `results/report.json`；计时包括加载/JIT/写图，不能用作严格 CPU/GPU 性能比较。

## 文件

- `verify.py`：渲染与 Python 插件验证脚本。
- `results/cornell_scalar_rgb.png` / `.exr`：CPU 渲染。
- `results/cornell_cuda_ad_rgb.png` / `.exr`：GPU 渲染。
- `results/custom_diffuse_cuda_ad_rgb.png` / `.exr`：Python 插件渲染。
- `results/report.json`：源码来源、版本、运行状态、误差与输出统计。

上游渲染器实现源码未修改；改动包括初始化依赖子模块、生成 `mitsuba3/build/`，以及本验证目录中的独立环境和脚本。早期构建日志中的旧绝对路径保留为历史记录；移动后重新建立虚拟环境、刷新 CMake 配置并验证运行。后续工作计划见 `../PLAN.md`。
