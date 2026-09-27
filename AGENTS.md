# 本地论文复现工作约定

- 用户要求后续新增文件全部放在 `mitsuba3/` 内。论文实现、计划、测试和输出集中放在 `cloth_repro/`；构建产物保留在 `build/`。
- 继续前阅读 `cloth_repro/PLAN.md`；当前任务是 2022《Woven Fabric Capture from a Single Photo》的最小正向实现，之后再进入 2023。
- 用户已要求从论文重新开始；旧 `stocking_precompute` 实验仅保留，不作为当前实现的依赖或验收基准。本阶段验收使用论文公式与受控布片场景，不宣称丝袜外观已经达标。
- 保留原论文 PDF 只读。需要新增下载、摘录或参考资料时，放在 `cloth_repro/references/`，不再新增工作区根目录的 scratch 文件。
- 优先使用 Python 自定义 BSDF；只有确定需要时才改动上游 Mitsuba C++。区分环境验证、公式验证和视觉验证，分别报告。
- 不把 2023/2024 的公式混入 2022；自行推导的几何参数化、数值稳定处理和经验近似必须记录。
- 环境入口为 `cloth_repro/validation/README.md`。当前可用 `scalar_rgb`、`cuda_ad_rgb`；LLVM 后端缺运行库。
