#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Prevent Conda's linker/library environment from leaking into the cross build.
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH LIBRARY_PATH COMPILER_PATH GCC_EXEC_PREFIX
if [[ -n "${ARM_TOOLCHAIN_BIN:-}" ]]; then
    export PATH="$ARM_TOOLCHAIN_BIN:/usr/bin:/bin:$PATH"
else
    export PATH="/usr/bin:/bin:$PATH"
fi
prefix="${CROSS_COMPILE:-arm-none-eabi-}"
for tool in gcc objcopy size; do
    if ! command -v "${prefix}${tool}" >/dev/null 2>&1; then
        echo "缺少 ${prefix}${tool}。Ubuntu可安装：" >&2
        echo "  sudo apt install --no-install-recommends gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi libnewlib-dev make" >&2
        echo "或设置 ARM_TOOLCHAIN_BIN=/绝对路径/工具链/bin" >&2
        exit 1
    fi
done
make -C "$project_dir/src" CROSS_COMPILE="$prefix" "$@"
