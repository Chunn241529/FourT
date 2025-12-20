import subprocess
import sys
import os
import platform
import argparse
import re

# --- Cấu hình ---
VENV_DIR = ".venv"
PYTHON_MIN_VERSION = (3, 8)

def run_command(command, check=True, cwd=None, capture_output=False):
    """Thực thi một lệnh shell và xử lý lỗi nếu có. Hỗ trợ capture output."""
    try:
        print(f"Đang chạy lệnh: {' '.join(command)}")
        result = subprocess.run(command, check=check, shell=False, cwd=cwd or os.getcwd(), capture_output=capture_output, text=True)
        if capture_output:
            return result.stdout.strip() if result.returncode == 0 else None
        return True
    except subprocess.CalledProcessError as e:
        if capture_output:
            return None
        print(f"LỖI: Lệnh {' '.join(command)} thất bại với mã lỗi {e.returncode}")
        return False
    except FileNotFoundError:
        if capture_output:
            return None
        print(f"LỖI: Không tìm thấy lệnh '{command[0]}'. Hãy đảm bảo nó đã được cài đặt và có trong PATH.")
        return False
    return True

def get_python_executable(venv_path):
    """Lấy đường dẫn đến file thực thi python trong venv cho HĐH hiện tại."""
    if platform.system() == "Windows":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else: # Linux, macOS, etc.
        return os.path.join(venv_path, "bin", "python")

def detect_cuda_version():
    """Phát hiện phiên bản CUDA từ nvidia-smi."""
    try:
        output = run_command(["nvidia-smi"], capture_output=True)
        if output:
            # Tìm phiên bản CUDA trong output, ví dụ: CUDA Version: 12.1
            match = re.search(r'CUDA Version:\s*(\d+\.\d+)', output)
            if match:
                cuda_ver = match.group(1)
                major_minor = cuda_ver.replace('.', '')  # e.g., 12.1 -> 121
                if major_minor in ['118', '121', '130']:
                    return f'cuda{major_minor}'
                elif float(cuda_ver) >= 12.1:
                    return 'cuda121'  # Mặc định cho CUDA >=12.1
                elif float(cuda_ver) >= 11.8:
                    return 'cuda118'
                else:
                    print(f"Cảnh báo: Phiên bản CUDA {cuda_ver} không được hỗ trợ trực tiếp, sử dụng CPU.")
                    return 'cpu'
        print("Không phát hiện NVIDIA GPU hoặc nvidia-smi không khả dụng, sử dụng CPU.")
        return 'cpu'
    except Exception as e:
        print(f"Lỗi khi phát hiện CUDA: {e}. Sử dụng CPU.")
        return 'cpu'


def get_python_by_version(version_choice):
    """
    Tìm Python executable theo phiên bản yêu cầu.
    
    Args:
        version_choice: 'auto', '3.11', '3.12', '3.10'
    
    Returns:
        Path to python executable or None
    """
    if platform.system() != "Windows":
        # Trên Linux/Mac, dùng python3.X trực tiếp
        if version_choice == 'auto':
            for ver in ['3.11', '3.10', '3.12']:
                try:
                    result = subprocess.run([f'python{ver}', '--version'], capture_output=True, text=True)
                    if result.returncode == 0:
                        return f'python{ver}'
                except:
                    pass
            return None
        else:
            return f'python{version_choice}'
    
    # Windows - dùng py launcher
    try:
        # Liệt kê các Python đã cài
        result = subprocess.run(['py', '--list'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Không tìm thấy py launcher")
            return None
        
        available_versions = result.stdout
        print(f"Các phiên bản Python có sẵn:\n{available_versions}")
        
        if version_choice == 'auto':
            # Ưu tiên 3.11 > 3.10 > 3.12 (vì tensorflow)
            for ver in ['3.11', '3.10', '3.12']:
                if f'-{ver}' in available_versions or f'-V:{ver}' in available_versions:
                    print(f"Tự động chọn Python {ver}")
                    return ['py', f'-{ver}']
            return None
        else:
            # Kiểm tra version được chọn có tồn tại không
            if f'-{version_choice}' in available_versions or f'-V:{version_choice}' in available_versions:
                return ['py', f'-{version_choice}']
            else:
                print(f"Không tìm thấy Python {version_choice}")
                return None
                
    except FileNotFoundError:
        print("Không tìm thấy py launcher. Hãy cài Python từ python.org")
        return None
    except Exception as e:
        print(f"Lỗi khi tìm Python: {e}")
        return None

def main():
    """Hàm chính để thiết lập môi trường và cài đặt dependencies."""
    parser = argparse.ArgumentParser(
        description="Script cài đặt môi trường cho dự án.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--pytorch', 
        default='auto',
        choices=['auto', 'cpu', 'cuda118', 'cuda121', 'cuda130'],
        help="Chọn phiên bản PyTorch để cài đặt:\n"
             "  - auto:    Tự động tìm phiên bản tốt nhất (kiểm tra GPU và CUDA).\n"
             "  - cpu:     Chỉ cài đặt phiên bản cho CPU.\n"
             "  - cuda118: Cài đặt cho NVIDIA GPU với CUDA 11.8.\n"
             "  - cuda121: Cài đặt cho NVIDIA GPU với CUDA 12.1 (khuyên dùng cho driver mới)."
    )
    parser.add_argument(
        '--skip-requirements',
        action='store_true',
        help="Bỏ qua cài đặt requirements.txt nếu có lỗi"
    )
    parser.add_argument(
        '--python',
        default='auto',
        choices=['auto', '3.11', '3.12', '3.10'],
        help="Chọn phiên bản Python để tạo venv:\n"
             "  - auto: Tự động chọn (ưu tiên 3.11 cho tensorflow)\n"
             "  - 3.11: Dùng Python 3.11 (khuyên dùng cho basic-pitch/tensorflow)\n"
             "  - 3.12: Dùng Python 3.12\n"
             "  - 3.10: Dùng Python 3.10"
    )
    parser.add_argument(
        '--recreate-venv',
        action='store_true',
        help="Xóa và tạo lại virtual environment"
    )
    args = parser.parse_args()

    # Lấy đường dẫn tuyệt đối của thư mục hiện tại
    current_dir = os.path.abspath(os.getcwd())
    venv_full_path = os.path.join(current_dir, VENV_DIR)
    
    print(f"Thiết lập môi trường tại: {current_dir}")
    print(f"Virtual environment sẽ được tạo tại: {venv_full_path}")

    # Xác định Python executable dựa trên lựa chọn
    python_executable = get_python_by_version(args.python)
    if python_executable:
        print(f"Sử dụng Python: {python_executable}")
    else:
        python_executable = sys.executable
        print(f"Sử dụng Python mặc định: {python_executable}")

    # 1. Kiểm tra phiên bản Python
    if sys.version_info < PYTHON_MIN_VERSION:
        print(f"Yêu cầu Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]} trở lên.")
        sys.exit(1)
    
    print("Bắt đầu quá trình cài đặt môi trường...")

    # 2. Xóa venv cũ nếu recreate
    if args.recreate_venv and os.path.exists(venv_full_path):
        print(f"Đang xóa virtual environment cũ...")
        import shutil
        shutil.rmtree(venv_full_path)

    # 3. Tạo/Kiểm tra virtual environment
    if not os.path.exists(venv_full_path):
        print(f"Đang tạo virtual environment tại '{venv_full_path}'...")
        # Handle both string (sys.executable) and list (['py', '-3.11']) formats
        if isinstance(python_executable, list):
            venv_cmd = python_executable + ["-m", "venv", venv_full_path]
        else:
            venv_cmd = [python_executable, "-m", "venv", venv_full_path]
        if not run_command(venv_cmd):
            sys.exit(1)
    else:
        print(f"Virtual environment đã tồn tại tại '{venv_full_path}'")
    
    python_in_venv = get_python_executable(venv_full_path)
    
    if not os.path.exists(python_in_venv):
        print(f"LỖI: Không tìm thấy file thực thi Python tại '{python_in_venv}'.")
        sys.exit(1)

    # Hiển thị version trong venv
    version_output = run_command([python_in_venv, "--version"], capture_output=True)
    print(f"Sử dụng Python interpreter từ venv: {python_in_venv}")
    if version_output:
        print(f"Phiên bản: {version_output}")

    # 3. Cập nhật pip
    print("\nĐang cập nhật pip...")
    if not run_command([python_in_venv, "-m", "pip", "install", "--upgrade", "pip"]):
        print("Cảnh báo: Không thể cập nhật pip, tiếp tục cài đặt...")
    # pip install --upgrade certifi pip
    if not run_command([python_in_venv, "-m", "pip", "install", "--upgrade", "certifi"]):
        print("Cảnh báo: Không thể cập nhật certifi, tiếp tục cài đặt...")

    # 4. Cài đặt PyTorch TRƯỚC requirements (để basic-pitch, easyocr có thể resolve đúng)
    print(f"\nĐang cài đặt PyTorch (phiên bản đã chọn: {args.pytorch})...")
    
    base_command = [python_in_venv, "-m", "pip", "install", "torch", "torchvision", "torchaudio"]
    
    if args.pytorch == 'auto':
        detected = detect_cuda_version()
        print(f"Phát hiện hệ thống: {detected}")
        args.pytorch = detected
    
    if args.pytorch == 'cuda121':
        install_command = base_command + ["--index-url", "https://download.pytorch.org/whl/cu121"]
    elif args.pytorch == 'cuda118':
        install_command = base_command + ["--index-url", "https://download.pytorch.org/whl/cu118"]
    elif args.pytorch == 'cuda130':
        install_command = base_command + ["--index-url", "https://download.pytorch.org/whl/cu130"]
    elif args.pytorch == 'cpu':
        install_command = base_command + ["--index-url", "https://download.pytorch.org/whl/cpu"]
    else:
        install_command = base_command

    if not run_command(install_command):
        print("⚠️  Có lỗi khi cài đặt PyTorch, thử cài đặt không version...")
        run_command([python_in_venv, "-m", "pip", "install", "torch", "torchvision", "torchaudio"], check=False)

    # 5. Cài đặt các thư viện từ requirements.txt (sau khi đã có PyTorch)
    requirements_file = os.path.join(current_dir, "requirements.txt")
    if os.path.exists(requirements_file) and not args.skip_requirements:
        print(f"\nĐang cài đặt các thư viện từ {requirements_file}...")
        if not run_command([python_in_venv, "-m", "pip", "install", "-r", requirements_file], check=False):
            print("⚠️  Có lỗi khi cài đặt requirements.txt")
            print("Nguyên nhân có thể do xung đột phiên bản giữa các package")
            print("Thử cài đặt từng package quan trọng thủ công...")
            
            # Thử cài đặt các package cơ bản
            basic_packages = ["numpy", "pillow", "opencv-python-headless", "requests", "basic-pitch"]
            for package in basic_packages:
                print(f"Thử cài đặt {package}...")
                run_command([python_in_venv, "-m", "pip", "install", package], check=False)
    else:
        if args.skip_requirements:
            print(f"\nBỏ qua cài đặt requirements.txt theo lựa chọn")
        else:
            print(f"\nKhông tìm thấy {requirements_file}, bỏ qua bước cài đặt requirements")

    
    print("\n✅ Quá trình cài đặt hoàn tất!")
    print(f"Môi trường đã được thiết lập tại: {current_dir}")
    print(f"Để kích hoạt môi trường ảo, hãy chạy lệnh sau:")
    if platform.system() == "Windows":
        print(f"   .\\{VENV_DIR}\\Scripts\\activate")
    else:
        print(f"   source {VENV_DIR}/bin/activate")
    
    print("\n📝 Lưu ý: Nếu có package bị lỗi, bạn có thể:")
    print("   1. Chạy lại với: python setup.py --skip-requirements")
    print("   2. Cài đặt thủ công các package bị thiếu")
    print("   3. Kiểm tra lại file requirements.txt")

if __name__ == "__main__":
    main()
