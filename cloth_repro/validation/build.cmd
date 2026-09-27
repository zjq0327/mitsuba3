@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 exit /b %errorlevel%
set "PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake -S "%~dp0..\.." -B "%~dp0..\..\build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DMI_SPLIT_MODE=OFF -DMI_DEFAULT_VARIANTS=scalar_rgb,cuda_ad_rgb,llvm_ad_rgb -DPython_EXECUTABLE="%~dp0.venv\Scripts\python.exe"
if errorlevel 1 exit /b %errorlevel%
cmake --build "%~dp0..\..\build" --parallel 8
exit /b %errorlevel%
