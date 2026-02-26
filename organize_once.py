import os
import time
import re
import shutil
import subprocess
from pathlib import Path

# ================= 🔧 配置区域 =================

# 1. 扫描目录：脚本运行的当前目录
SCAN_DIR = os.getcwd()

# 2. NAS 连接配置
NAS_IP = "192.168.0.180"
NAS_SHARE_NAME = "案件"   

# 3. 拼接出根路径
NAS_ROOT = fr"\\{NAS_IP}\{NAS_SHARE_NAME}"

# 4. 关键字映射
TYPE_MAPPING = {
    "临鉴字": "1.法医临床",
    "精鉴字": "2.法医精神",
    "物鉴字": "3.法医物证", 
}

# ==============================================

def connect_nas():
    """连接到 NAS 共享目录"""
    print(f"🔌 正在连接共享目录: {NAS_ROOT} ...")

    # 先清理该服务器已有连接，避免 Windows 1219（同一服务器多凭据冲突）
    list_result = subprocess.run("net use", shell=True, capture_output=True, text=True)
    if list_result.returncode == 0:
        # 匹配所有指向该 NAS IP 的共享路径，例如 \\192.168.0.180\案件
        pattern = re.compile(rf"(\\\\{re.escape(NAS_IP)}\\\S+)")
        shares = set(pattern.findall(list_result.stdout))
        for share in shares:
            subprocess.run(
                f'net use "{share}" /delete /y',
                shell=True,
                capture_output=True,
                text=True,
            )

    # 建立新连接（使用 Windows 已保存的凭据）
    cmd = f'net use "{NAS_ROOT}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ NAS 连接成功！")
        return True
    else:
        print(f"❌ 连接失败: {NAS_ROOT}")
        error_text = (result.stderr or result.stdout).strip()
        print(f"错误信息: {error_text}")
        return False

def process_files():
    """扫描并处理当前目录下的所有文件"""
    print(f"📂 正在扫描目录: {SCAN_DIR}")
    
    # 获取目录下所有文件
    files = [f for f in os.listdir(SCAN_DIR) if os.path.isfile(os.path.join(SCAN_DIR, f))]
    
    if not files:
        print("   当前目录下没有文件。")
        return

    # 正则匹配
    pattern = re.compile(r"(\d{4}).*?(临鉴字|精鉴字|物鉴字).*?第?(\d+)号")
    
    processed_count = 0

    for filename in files:
        # 跳过脚本自己和exe文件
        if filename == os.path.basename(__file__) or filename.endswith('.exe'):
            continue

        file_path = os.path.join(SCAN_DIR, filename)
        match = pattern.search(filename)

        if match:
            print(f"\n🔍 处理文件: {filename}")
            
            year = match.group(1)      # 2025
            key_word = match.group(2)  # 物鉴字
            number = match.group(3)    # 4
            
            category_folder = TYPE_MAPPING.get(key_word)
            
            if category_folder:
                # 1. 构建文件夹名 (如需全角括号请修改此处: f"（{year}）...")
                case_folder_name = f"({year}){key_word}第{number}号"
                
                # 2. 特殊路径逻辑: 3.法医物证 -> 增加 "鉴定" 子目录
                if category_folder == "3.法医物证":
                    target_dir = Path(NAS_ROOT) / year / category_folder / "鉴定" / case_folder_name
                else:
                    target_dir = Path(NAS_ROOT) / year / category_folder / case_folder_name
                
                target_file = target_dir / filename
                print(f"   📂 目标: {target_dir}")

                try:
                    # 创建目录
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 复制
                    print("   🚀 上传中...")
                    shutil.copy2(file_path, target_file)
                    
                    # 校验与删除
                    if target_file.exists():
                        if os.path.getsize(file_path) == os.path.getsize(target_file):
                            os.remove(file_path)
                            print(f"   ✅ 成功！本地文件已删除。")
                            processed_count += 1
                        else:
                            print(f"   ⚠️ 大小不一致，已保留本地文件。")
                    else:
                        print("   ❌ 上传失败。")
                        
                except Exception as e:
                    print(f"   ❌ 出错: {e}")
            else:
                print(f"   ⚠️ 未知分类，跳过。")
        else:
            # 不符合规则的文件直接静默跳过，或者你可以取消注释下面这行来查看
            # print(f"   跳过非目标文件: {filename}")
            pass

    print("-" * 30)
    print(f"🎉 处理完毕！共成功归档 {processed_count} 个文件。")

if __name__ == "__main__":
    try:
        if connect_nas():
            process_files()
    except Exception as e:
        print(f"发生未预期的错误: {e}")
    
    # 这一行很重要，防止双击运行后窗口瞬间关闭
    input("\n按回车键退出程序...")
