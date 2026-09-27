"""Smoke-test the locally built Mitsuba, never a PyPI substitute."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
(HERE / "cache").mkdir(exist_ok=True)
os.environ["DRJIT_CACHE_DIR"] = str(HERE / "cache")
SOURCE = HERE.parents[1]
BUILD = SOURCE / "build"
sys.path.insert(0, str(BUILD / "Release" / "python"))
_dll_dirs = []
for path in [BUILD / "Release", BUILD / "bin", BUILD / "Release" / "python" / "drjit"]:
    if path.is_dir():
        _dll_dirs.append(os.add_dll_directory(str(path)))

import numpy as np
import drjit as dr
import mitsuba as mi

OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
report = {
    "source_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip(),
    "python": sys.version,
    "mitsuba_version": mi.__version__,
    "mitsuba_module": mi.__file__,
    "drjit_version": dr.__version__,
    "drjit_module": dr.__file__,
    "compiled_variants": mi.variants(),
    "checks": {},
}
assert Path(mi.__file__).resolve().is_relative_to(BUILD.resolve()), mi.__file__


def save_report():
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def save_image(image, name):
    array = np.array(image)
    assert np.isfinite(array).all(), "non-finite image"
    assert array.min() >= -1e-6, "negative radiance"
    assert array.max() > 0 and array.std() > 0.01, "empty or constant image"
    mi.Bitmap(image).write(str(OUT / (name + ".exr")))
    mi.Bitmap(image).convert(
        mi.Bitmap.PixelFormat.RGB, mi.Struct.Type.UInt8, srgb_gamma=True
    ).write(str(OUT / (name + ".png")))
    return {"shape": list(array.shape), "mean": float(array.mean()),
            "min": float(array.min()), "max": float(array.max())}


def render_cornell(variant):
    mi.set_variant(variant)
    desc = mi.cornell_box()
    desc["sensor"]["film"]["width"] = 256
    desc["sensor"]["film"]["height"] = 256
    start = time.perf_counter()
    img = mi.render(mi.load_dict(desc), seed=42, spp=64)
    dr.eval(img)
    stats = save_image(img, "cornell_" + variant)
    stats["seconds_including_load_compile_and_save"] = time.perf_counter() - start
    return stats


def custom_bsdf(variant):
    mi.set_variant(variant)

    class ValidationDiffuse(mi.BSDF):
        """A simple known BRDF to test Python plugin plumbing, not cloth."""
        def __init__(self, props):
            mi.BSDF.__init__(self, props)
            self.reflectance = mi.Color3f(0.35, 0.55, 0.75)
            self.m_flags = mi.BSDFFlags.DiffuseReflection | mi.BSDFFlags.FrontSide
            self.m_components = [self.m_flags]

        def sample(self, ctx, si, sample1, sample2, active=True):
            active = active & (mi.Frame3f.cos_theta(si.wi) > 0)
            bs = mi.BSDFSample3f()
            bs.wo = mi.warp.square_to_cosine_hemisphere(sample2)
            bs.pdf = dr.select(active, mi.warp.square_to_cosine_hemisphere_pdf(bs.wo), 0)
            bs.eta = 1.0
            bs.sampled_type = mi.UInt32(mi.BSDFFlags.DiffuseReflection)
            bs.sampled_component = 0
            return bs, dr.select(active & (bs.pdf > 0), self.reflectance, 0)

        def eval(self, ctx, si, wo, active=True):
            active = active & (mi.Frame3f.cos_theta(si.wi) > 0) & (wo.z > 0)
            return dr.select(active, self.reflectance * wo.z * dr.inv_pi, 0)

        def pdf(self, ctx, si, wo, active=True):
            active = active & (mi.Frame3f.cos_theta(si.wi) > 0) & (wo.z > 0)
            return dr.select(active, mi.warp.square_to_cosine_hemisphere_pdf(wo), 0)

        def eval_pdf(self, ctx, si, wo, active=True):
            return self.eval(ctx, si, wo, active), self.pdf(ctx, si, wo, active)

        def to_string(self):
            return "ValidationDiffuse[]"

    mi.register_bsdf("validation_diffuse", lambda props: ValidationDiffuse(props))
    custom = mi.load_dict({"type": "validation_diffuse"})
    builtin = mi.load_dict({"type": "diffuse", "reflectance": {
        "type": "rgb", "value": [0.35, 0.55, 0.75]}})
    si = mi.SurfaceInteraction3f()
    si.wi = mi.Vector3f(0, 0, 1)
    ctx = mi.BSDFContext()
    for angle in [0, 20, 50, 80]:
        theta = np.deg2rad(angle)
        wo = mi.Vector3f(float(np.sin(theta)), 0, float(np.cos(theta)))
        assert dr.allclose(custom.eval(ctx, si, wo), builtin.eval(ctx, si, wo), atol=1e-6)
        assert dr.allclose(custom.pdf(ctx, si, wo), builtin.pdf(ctx, si, wo), atol=1e-6)
    bs, weight = custom.sample(ctx, si, mi.Float(0.3), mi.Point2f(0.31, 0.67))
    assert dr.allclose(custom.pdf(ctx, si, bs.wo), bs.pdf, atol=1e-6)
    assert dr.allclose(weight * bs.pdf, custom.eval(ctx, si, bs.wo), atol=1e-6)

    def scene(use_custom):
        return mi.load_dict({
            "type": "scene", "integrator": {"type": "path", "max_depth": 4},
            "sensor": {"type": "perspective", "fov": 38,
                "to_world": mi.ScalarTransform4f().look_at(
                    origin=[0, 0, 4], target=[0, 0, 0], up=[0, 1, 0]),
                "film": {"type": "hdrfilm", "width": 160, "height": 160,
                    "pixel_format": "rgb", "rfilter": {"type": "box"}},
                "sampler": {"type": "independent"}},
            "environment": {"type": "constant", "radiance": 1.0},
            "object": {"type": "sphere", "bsdf": custom if use_custom else builtin}})

    reference = mi.render(scene(False), seed=17, spp=32)
    result = mi.render(scene(True), seed=17, spp=32)
    stats = save_image(result, "custom_diffuse_" + variant)
    error = float(np.max(np.abs(np.array(reference) - np.array(result))))
    assert error < 2e-5, f"Python/native BSDF image mismatch: {error}"
    stats["native_comparison_max_abs_error"] = error
    stats["eval_pdf_sample_consistency"] = "passed"
    return stats


for variant in ["scalar_rgb", "cuda_ad_rgb", "llvm_ad_rgb"]:
    try:
        backend = {"cuda_ad_rgb": dr.JitBackend.CUDA, "llvm_ad_rgb": dr.JitBackend.LLVM}.get(variant)
        if backend is not None and not dr.has_backend(backend):
            report["checks"][variant] = {"status": "unavailable", "reason": "JIT backend runtime not available"}
            print(variant, "UNAVAILABLE", flush=True)
            continue
        stats = render_cornell(variant)
        report["checks"][variant] = {"status": "passed", "cornell": stats}
        print(variant, "RENDER PASSED", stats, flush=True)
        if backend is not None:
            report["checks"][variant]["custom_bsdf"] = custom_bsdf(variant)
            print(variant, "CUSTOM BSDF PASSED", flush=True)
    except Exception:
        report["checks"][variant] = {"status": "failed", "traceback": traceback.format_exc()}
        print(report["checks"][variant]["traceback"], flush=True)
    finally:
        save_report()

assert report["checks"]["scalar_rgb"]["status"] == "passed"
assert report["checks"]["cuda_ad_rgb"]["status"] == "passed"
print("Validation complete:", OUT / "report.json", flush=True)
