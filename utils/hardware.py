"""
Cross-Platform Hardware Detection
==================================
Detects system hardware and recommends the optimal inference backend.
"""

import os
import sys
import platform
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class Platform(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class GPUVendor(Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    APPLE = "apple"
    INTEL = "intel"
    NONE = "none"


class Backend(Enum):
    LLAMA_CPP = "llama.cpp"
    MLX = "mlx"
    TRANSFORMERS = "transformers"
    VLLM = "vllm"


@dataclass
class GPUInfo:
    vendor: GPUVendor = GPUVendor.NONE
    name: str = "None"
    vram_gb: float = 0.0
    cuda_available: bool = False
    cuda_version: Optional[str] = None
    metal_available: bool = False


@dataclass
class HardwareInfo:
    platform: Platform = Platform.UNKNOWN
    platform_version: str = ""
    cpu_brand: str = "Unknown"
    cpu_cores: int = 1
    ram_gb: float = 0.0
    available_ram_gb: float = 0.0
    gpu: GPUInfo = field(default_factory=GPUInfo)
    recommended_backend: Backend = Backend.LLAMA_CPP
    recommended_model_size_gb: float = 4.0
    python_version: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform.value,
            "platform_version": self.platform_version,
            "cpu_brand": self.cpu_brand,
            "cpu_cores": self.cpu_cores,
            "ram_gb": self.ram_gb,
            "available_ram_gb": self.available_ram_gb,
            "gpu": {
                "vendor": self.gpu.vendor.value,
                "name": self.gpu.name,
                "vram_gb": self.gpu.vram_gb,
                "cuda_available": self.gpu.cuda_available,
                "cuda_version": self.gpu.cuda_version,
                "metal_available": self.gpu.metal_available,
            },
            "recommended_backend": self.recommended_backend.value,
            "recommended_model_size_gb": self.recommended_model_size_gb,
            "python_version": self.python_version,
        }


def _get_platform() -> tuple[Platform, str]:
    """Detect the operating system."""
    system = platform.system().lower()
    version = platform.version()
    
    if system == "windows":
        return Platform.WINDOWS, version
    elif system == "linux":
        return Platform.LINUX, version
    elif system == "darwin":
        return Platform.MACOS, platform.mac_ver()[0]
    else:
        return Platform.UNKNOWN, version


def _get_cpu_info() -> tuple[str, int]:
    """Get CPU brand and core count."""
    cores = os.cpu_count() or 1
    
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True
            )
            brand = result.stdout.strip()
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        brand = line.split(":")[1].strip()
                        break
                else:
                    brand = platform.processor()
        elif platform.system() == "Windows":
            brand = platform.processor()
        else:
            brand = platform.processor() or "Unknown"
    except Exception:
        brand = platform.processor() or "Unknown"
    
    return brand, cores


def get_ram_info() -> tuple[float, float]:
    """Get total and available RAM in GB."""
    import re
    
    try:
        if platform.system() == "Darwin":
            # Total RAM
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True
            )
            total_bytes = int(result.stdout.strip())
            total_gb = total_bytes / (1024 ** 3)
            
            # Get detailed memory stats using vm_stat
            result = subprocess.run(
                ["vm_stat"],
                capture_output=True, text=True
            )
            
            vm_lines = result.stdout.split('\n')
            
            # Get page size
            page_size = 4096 # Default
            if "page size of" in vm_lines[0]:
                match = re.search(r'page size of (\d+) bytes', vm_lines[0])
                if match:
                    page_size = int(match.group(1))
            
            pages_free = 0
            pages_inactive = 0
            pages_speculative = 0
            
            for line in vm_lines:
                if "Pages free" in line:
                    pages_free = int(re.search(r'\d+', line).group())
                elif "Pages inactive" in line:
                    pages_inactive = int(re.search(r'\d+', line).group())
                elif "Pages speculative" in line:
                    pages_speculative = int(re.search(r'\d+', line).group())
            
            # Available = (Free + Inactive + Speculative) * Page Size
            # Inactive/Speculative memory is file cache that can be reclaimed
            available_bytes = (pages_free + pages_inactive + pages_speculative) * page_size
            available_gb = available_bytes / (1024 ** 3)
            
        elif platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0])  # KB
                        meminfo[key] = value
            
            total_gb = meminfo.get("MemTotal", 0) / (1024 ** 2)
            available_gb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0)) / (1024 ** 2)
            
        elif platform.system() == "Windows":
            import ctypes
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            
            total_gb = stat.ullTotalPhys / (1024 ** 3)
            available_gb = stat.ullAvailPhys / (1024 ** 3)
        else:
            total_gb = 8.0
            available_gb = 4.0
            
    except Exception:
        total_gb = 8.0
        available_gb = 4.0
    
    return round(total_gb, 1), round(available_gb, 1)


def _get_nvidia_gpu() -> Optional[GPUInfo]:
    """Detect NVIDIA GPU via nvidia-smi or WMI on Windows."""
    nvidia_smi_path = None
    
    # Check if nvidia-smi is in PATH
    if shutil.which("nvidia-smi"):
        nvidia_smi_path = "nvidia-smi"
    
    # Windows: Check common NVIDIA driver locations
    if nvidia_smi_path is None and platform.system() == "Windows":
        common_paths = [
            r"C:\Windows\System32\nvidia-smi.exe",
            r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
            os.path.expandvars(r"%ProgramFiles%\NVIDIA Corporation\NVSMI\nvidia-smi.exe"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                nvidia_smi_path = path
                break
    
    # Try nvidia-smi if found
    if nvidia_smi_path:
        try:
            result = subprocess.run(
                [nvidia_smi_path, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().split('\n')[0]
                parts = line.split(',')
                name = parts[0].strip()
                vram_mb = float(parts[1].strip())
                
                # Check CUDA version
                result = subprocess.run(
                    [nvidia_smi_path, "--query-gpu=driver_version", "--format=csv,noheader"],
                    capture_output=True, text=True
                )
                cuda_version = result.stdout.strip().split('\n')[0] if result.returncode == 0 else None
                
                return GPUInfo(
                    vendor=GPUVendor.NVIDIA,
                    name=name,
                    vram_gb=round(vram_mb / 1024, 1),
                    cuda_available=True,
                    cuda_version=cuda_version,
                )
        except Exception:
            pass
    
    # Windows fallback: Use WMI to detect GPU
    if platform.system() == "Windows":
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "path", "win32_videocontroller", "get", "name,adapterram", "/format:csv"],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                for line in lines[1:]:  # Skip header
                    parts = line.split(',')
                    if len(parts) >= 3:
                        vram_bytes = int(parts[1]) if parts[1].isdigit() else 0
                        gpu_name = parts[2]
                        
                        if 'nvidia' in gpu_name.lower() or 'geforce' in gpu_name.lower() or 'rtx' in gpu_name.lower():
                            return GPUInfo(
                                vendor=GPUVendor.NVIDIA,
                                name=gpu_name,
                                vram_gb=round(vram_bytes / (1024 ** 3), 1) if vram_bytes > 0 else 0,
                                cuda_available=True,  # Assume CUDA available if NVIDIA detected
                            )
                        elif 'amd' in gpu_name.lower() or 'radeon' in gpu_name.lower():
                            return GPUInfo(
                                vendor=GPUVendor.AMD,
                                name=gpu_name,
                                vram_gb=round(vram_bytes / (1024 ** 3), 1) if vram_bytes > 0 else 0,
                            )
                        elif 'intel' in gpu_name.lower():
                            return GPUInfo(
                                vendor=GPUVendor.INTEL,
                                name=gpu_name,
                                vram_gb=round(vram_bytes / (1024 ** 3), 1) if vram_bytes > 0 else 0,
                            )
        except Exception:
            pass
    
    return None



def _get_apple_gpu() -> Optional[GPUInfo]:
    """Detect Apple Silicon GPU."""
    if platform.system() != "Darwin":
        return None
    
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True
        )
        cpu_brand = result.stdout.strip()
        
        if "Apple" in cpu_brand:
            # Get unified memory (shared with GPU)
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True
            )
            total_bytes = int(result.stdout.strip())
            unified_memory_gb = total_bytes / (1024 ** 3)
            
            # GPU can use most of unified memory
            gpu_available = unified_memory_gb * 0.75
            
            return GPUInfo(
                vendor=GPUVendor.APPLE,
                name=cpu_brand + " GPU",
                vram_gb=round(gpu_available, 1),
                metal_available=True,
            )
    except Exception:
        pass
    
    return None


def _recommend_backend(hw: HardwareInfo) -> Backend:
    """Recommend the best backend based on hardware."""
    # Apple Silicon: prefer MLX
    if hw.gpu.vendor == GPUVendor.APPLE and hw.gpu.metal_available:
        return Backend.MLX
    
    # NVIDIA GPU: llama.cpp with CUDA
    if hw.gpu.vendor == GPUVendor.NVIDIA and hw.gpu.cuda_available:
        # vLLM for Linux with good NVIDIA GPUs
        if hw.platform == Platform.LINUX and hw.gpu.vram_gb >= 8:
            return Backend.VLLM
        return Backend.LLAMA_CPP
    
    # Default: llama.cpp (CPU)
    return Backend.LLAMA_CPP


def _recommend_model_size(hw: HardwareInfo) -> float:
    """Recommend max model size based on available memory."""
    # Use GPU VRAM if available, otherwise RAM
    if hw.gpu.vendor != GPUVendor.NONE and hw.gpu.vram_gb > 0:
        available = hw.gpu.vram_gb
    else:
        available = hw.available_ram_gb
    
    # Leave headroom for system/KV cache
    return max(1.0, available * 0.7)


def detect_hardware() -> HardwareInfo:
    """
    Detect system hardware and return comprehensive information.
    
    Returns:
        HardwareInfo: Complete hardware information with recommendations
    """
    hw = HardwareInfo()
    
    # Platform
    hw.platform, hw.platform_version = _get_platform()
    hw.python_version = platform.python_version()
    
    # CPU
    hw.cpu_brand, hw.cpu_cores = _get_cpu_info()
    
    # RAM
    hw.ram_gb, hw.available_ram_gb = get_ram_info()
    
    # GPU detection (priority order)
    gpu = _get_nvidia_gpu()
    if gpu is None:
        gpu = _get_apple_gpu()
    if gpu is None:
        gpu = GPUInfo()  # No GPU
    hw.gpu = gpu
    
    # Recommendations
    hw.recommended_backend = _recommend_backend(hw)
    hw.recommended_model_size_gb = _recommend_model_size(hw)
    
    return hw


def print_hardware_info(hw: HardwareInfo) -> None:
    """Print formatted hardware information."""
    print("\n" + "=" * 60)
    print("[SYSTEM]  HARDWARE DETECTION")
    print("=" * 60)
    print(f"  Platform:     {hw.platform.value.capitalize()} {hw.platform_version}")
    print(f"  CPU:          {hw.cpu_brand}")
    print(f"  CPU Cores:    {hw.cpu_cores}")
    print(f"  Total RAM:    {hw.ram_gb:.1f} GB")
    print(f"  Available:    {hw.available_ram_gb:.1f} GB")
    print("-" * 60)
    print(f"  GPU Vendor:   {hw.gpu.vendor.value.capitalize()}")
    print(f"  GPU Name:     {hw.gpu.name}")
    if hw.gpu.vram_gb > 0:
        print(f"  GPU VRAM:     {hw.gpu.vram_gb:.1f} GB")
    if hw.gpu.cuda_available:
        print(f"  CUDA:         [OK] Available (v{hw.gpu.cuda_version})")
    if hw.gpu.metal_available:
        print(f"  Metal:        [OK] Available")
    print("-" * 60)
    print(f"  Recommended Backend: {hw.recommended_backend.value}")
    print(f"  Max Model Size:      {hw.recommended_model_size_gb:.1f} GB")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    hw = detect_hardware()
    print_hardware_info(hw)
