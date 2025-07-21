# main_gui.py - 트레이 기능 통합 완성 버전
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog
import subprocess
import os
import sys
import psutil
import threading
import time
import importlib
import json
from datetime import datetime
from dotenv import load_dotenv
from env_generate import EnvGenerator
from upload_history import UploadHistoryManager

# 트레이 기능 import
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("⚠️  트레이 기능을 사용하려면 다음 패키지를 설치하세요:")
    print("   pip install pystray Pillow")

class GitHubAutoUploadMain:
    def __init__(self):
        self.root = tk.Tk()
        self.env_generator = EnvGenerator()
        self.history_manager = UploadHistoryManager()
        self.current_profile = tk.StringVar()
        
        # 업로드 프로세스 관리 변수들
        self.upload_process = None
        self.upload_pid_file = "upload_process.pid"
        self.is_upload_running = False
        
        # 트레이 관련 변수들
        self.tray_icon = None
        self.is_tray_mode = False
        
        self.setup_ui()
        self.check_required_packages()
        self.load_profiles()
        self.update_status()
        self.check_upload_process()
        self.start_process_monitor()
        
    # 🔧 패키지 설치 관련 메서드들 (기존과 동일)
    def check_required_packages(self):
        """필수 패키지 설치 상태 체크"""
        required_packages = [
            'PyGithub', 'python-dotenv', 'watchdog', 'schedule', 
            'requests', 'beautifulsoup4', 'psutil'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                if package == 'PyGithub':
                    importlib.import_module('github')
                elif package == 'python-dotenv':
                    importlib.import_module('dotenv')
                elif package == 'beautifulsoup4':
                    importlib.import_module('bs4')
                else:
                    importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.show_package_install_dialog(missing_packages)
    
    def detect_environment_type(self):
        """현재 Python 환경 타입 감지"""
        python_path = sys.executable
        
        if 'conda' in python_path.lower() or 'miniconda' in python_path.lower() or 'anaconda' in python_path.lower():
            if 'envs' in python_path:
                env_name = python_path.split('envs')[1].split(os.sep)[1] if 'envs' in python_path else 'unknown'
                return f"🐍 Conda 가상환경 ({env_name})"
            else:
                return "🐍 Conda 기본환경"
        
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_name = os.path.basename(sys.prefix)
            return f"🔧 가상환경 ({venv_name})"
        
        return "💻 시스템 Python"
    
    def get_environment_message(self, env_type):
        """환경별 안내 메시지"""
        if "Conda" in env_type:
            return "✅ Conda 환경에서 실행 중입니다. 안전하게 설치됩니다!"
        elif "가상환경" in env_type:
            return "✅ 가상환경에서 실행 중입니다. 안전하게 설치됩니다!"
        else:
            return "⚠️  시스템 Python에서 실행 중입니다. 가상환경 사용을 권장합니다."
    
    def show_package_install_dialog(self, missing_packages):
        """패키지 설치 다이얼로그 표시"""
        install_window = tk.Toplevel(self.root)
        install_window.title("📦 패키지 설치 필요")
        install_window.geometry("600x550")
        install_window.resizable(False, False)
        install_window.grab_set()
        
        main_frame = tk.Frame(install_window, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        title_label = tk.Label(main_frame, text="📦 필수 패키지 설치", 
                              font=("Arial", 16, "bold"), fg="navy")
        title_label.pack(pady=(0, 15))
        
        env_frame = tk.LabelFrame(main_frame, text="🐍 현재 Python 환경", 
                                 font=("Arial", 11, "bold"), padx=15, pady=10)
        env_frame.pack(fill='x', pady=(0, 15))
        
        python_path = sys.executable
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        env_type = self.detect_environment_type()
        
        tk.Label(env_frame, text=f"Python 버전: {python_version}", 
                font=("Arial", 10), anchor='w').pack(fill='x', pady=2)
        tk.Label(env_frame, text=f"환경 타입: {env_type}", 
                font=("Arial", 10, "bold"), anchor='w', fg="blue").pack(fill='x', pady=2)
        tk.Label(env_frame, text=f"설치 경로: {python_path}", 
                font=("Arial", 8), anchor='w', fg="gray", wraplength=550).pack(fill='x', pady=2)
        
        env_message = self.get_environment_message(env_type)
        tk.Label(env_frame, text=env_message, 
                font=("Arial", 10), fg="darkgreen", wraplength=550).pack(fill='x', pady=(8, 0))
        
        desc_label = tk.Label(main_frame, 
                             text="프로그램 실행에 필요한 패키지를 현재 환경에 설치합니다.\n아래 버튼을 클릭하여 자동 설치하세요.", 
                             font=("Arial", 11), justify='center')
        desc_label.pack(pady=(0, 15))
        
        if missing_packages:
            missing_frame = tk.LabelFrame(main_frame, text="설치할 패키지", 
                                         font=("Arial", 10, "bold"), padx=10, pady=10)
            missing_frame.pack(fill='x', pady=(0, 15))
            
            for package in missing_packages:
                tk.Label(missing_frame, text=f"• {package}", 
                        font=("Arial", 10), fg="red").pack(anchor='w')
        
        install_btn = tk.Button(main_frame, text="🚀 현재 환경에 설치", 
                               width=25, height=2,
                               font=("Arial", 12, "bold"),
                               bg="green", fg="white",
                               command=lambda: self.install_packages(install_window))
        install_btn.pack(pady=15)
        
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        
        close_btn = tk.Button(button_frame, text="❌ 나중에 설치", 
                             command=install_window.destroy,
                             font=("Arial", 10))
        close_btn.pack()
    
    def install_packages(self, parent_window):
        """패키지 자동 설치"""
        progress_window = tk.Toplevel(parent_window)
        progress_window.title("📦 패키지 설치 중...")
        progress_window.geometry("700x500")
        progress_window.resizable(False, False)
        progress_window.grab_set()
        
        progress_frame = tk.Frame(progress_window, padx=20, pady=20)
        progress_frame.pack(fill='both', expand=True)
        
        title_frame = tk.Frame(progress_frame)
        title_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(title_frame, text="📦 패키지 설치 중...", 
                font=("Arial", 14, "bold")).pack()
        
        env_type = self.detect_environment_type()
        tk.Label(title_frame, text=f"설치 환경: {env_type}", 
                font=("Arial", 10), fg="blue").pack(pady=(5, 0))
        
        progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress_bar.pack(fill='x', pady=(0, 15))
        progress_bar.start()
        
        log_frame = tk.LabelFrame(progress_frame, text="설치 진행 상황", font=("Arial", 10, "bold"))
        log_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9))
        log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        status_label = tk.Label(progress_frame, text="설치 준비 중...", 
                               font=("Arial", 11, "bold"), fg="blue")
        status_label.pack()
        
        def update_log(text):
            log_text.insert(tk.END, text + '\n')
            log_text.see(tk.END)
            progress_window.update()
        
        def install_thread():
            try:
                update_log("=" * 50)
                update_log("🚀 GitHub 자동 업로드 시스템 - 패키지 설치")
                update_log("=" * 50)
                
                status_label.config(text="requirements.txt 설치 중...", fg="orange")
                
                cmd = [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade']
                process = subprocess.Popen(cmd, 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.STDOUT, 
                                         text=True, 
                                         universal_newlines=True,
                                         cwd=os.getcwd())
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        update_log(output.strip())
                
                return_code = process.wait()
                progress_bar.stop()
                
                if return_code == 0:
                    status_label.config(text="✅ 설치 완료!", fg="green")
                    
                    def close_and_continue():
                        progress_window.destroy()
                        parent_window.destroy()
                        messagebox.showinfo("설치 완료", 
                                          "✅ 패키지 설치가 완료되었습니다!")
                    
                    button_frame = tk.Frame(progress_frame)
                    button_frame.pack(pady=10)
                    
                    complete_btn = tk.Button(button_frame, text="✅ 완료", 
                                           command=close_and_continue,
                                           bg="green", fg="white", 
                                           font=("Arial", 12, "bold"),
                                           width=15, height=2)
                    complete_btn.pack()
                
            except Exception as e:
                progress_bar.stop()
                status_label.config(text="❌ 설치 중 오류 발생", fg="red")
        
        threading.Thread(target=install_thread, daemon=True).start()
    
    def manual_package_install(self):
        self.show_package_install_dialog([])
    
    def check_package_status(self):
        status_window = tk.Toplevel(self.root)
        status_window.title("📦 패키지 상태")
        status_window.geometry("500x600")
        status_window.resizable(False, False)
        
        main_frame = tk.Frame(status_window, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        tk.Label(main_frame, text="📦 패키지 설치 상태", 
                font=("Arial", 14, "bold")).pack(pady=(0, 10))
        
        status_text = scrolledtext.ScrolledText(main_frame, height=20, font=("Consolas", 10))
        status_text.pack(fill='both', expand=True, pady=(0, 20))
        
        required_packages = [
            ('PyGithub', 'github'),
            ('python-dotenv', 'dotenv'),
            ('watchdog', 'watchdog'),
            ('schedule', 'schedule'),
            ('requests', 'requests'),
            ('beautifulsoup4', 'bs4'),
            ('psutil', 'psutil'),
            ('pystray', 'pystray'),
            ('Pillow', 'PIL')
        ]
        
        status_text.insert(tk.END, "📦 필수 패키지 설치 상태\n")
        status_text.insert(tk.END, "=" * 40 + "\n\n")
        
        all_installed = True
        for package_name, import_name in required_packages:
            try:
                module = importlib.import_module(import_name)
                version = getattr(module, '__version__', 'Unknown')
                status_text.insert(tk.END, f"✅ {package_name:<20} 버전: {version}\n")
            except ImportError:
                status_text.insert(tk.END, f"❌ {package_name:<20} 설치되지 않음\n")
                all_installed = False
        
        status_text.insert(tk.END, "\n" + "=" * 40 + "\n")
        if all_installed:
            status_text.insert(tk.END, "🎉 모든 패키지가 정상적으로 설치되어 있습니다!\n")
        else:
            status_text.insert(tk.END, "⚠️  일부 패키지가 설치되지 않았습니다.\n")
        
        tk.Button(main_frame, text="닫기", command=status_window.destroy).pack()
    
    def setup_ui(self):
        self.root.title("🚀 GitHub 자동 업로드")
        self.root.geometry("550x700")
        self.root.resizable(True, True)
        
        # 창 닫기 이벤트 바인딩
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 스크롤 가능한 메인 프레임 생성
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        main_frame = tk.Frame(self.scrollable_frame, padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        title_label = tk.Label(main_frame, text="🚀 GitHub Auto Upload", 
                              font=("Arial", 20, "bold"), fg="navy")
        title_label.pack(pady=(0, 20))
        
        self.create_profile_section(main_frame)
        self.create_status_frame(main_frame)
        self.create_function_buttons(main_frame)
        self.create_package_management_section(main_frame)
        self.create_exit_button(main_frame)
        
        self.bind_mousewheel()
    
    def bind_mousewheel(self):
        """마우스 휠로 스크롤 가능하게 하기"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")
        
        self.canvas.bind('<Enter>', bind_to_mousewheel)
        self.canvas.bind('<Leave>', unbind_from_mousewheel)
    
    def create_package_management_section(self, parent):
        package_frame = tk.LabelFrame(parent, text="📦 패키지 관리", 
                                     font=("Arial", 11, "bold"), 
                                     padx=15, pady=10)
        package_frame.pack(fill='x', pady=(15, 0))
        
        package_btn_frame = tk.Frame(package_frame)
        package_btn_frame.pack(pady=5)
        
        install_btn = tk.Button(package_btn_frame, text="📦 패키지 설치/업데이트", 
                               width=18, height=1,
                               font=("Arial", 10),
                               bg="lightgreen", fg="darkgreen",
                               command=self.manual_package_install)
        install_btn.pack(side='left', padx=5)
        
        check_btn = tk.Button(package_btn_frame, text="🔍 패키지 상태 확인", 
                             width=18, height=1,
                             font=("Arial", 10),
                             bg="lightblue", fg="darkblue",
                             command=self.check_package_status)
        check_btn.pack(side='left', padx=5)
    
    def create_profile_section(self, parent):
        profile_frame = tk.LabelFrame(parent, text="🏷️ 프로필 선택", 
                                     font=("Arial", 12, "bold"), 
                                     padx=20, pady=15)
        profile_frame.pack(fill='x', pady=(0, 20))
        
        selection_frame = tk.Frame(profile_frame)
        selection_frame.pack(fill='x', pady=5)
        
        tk.Label(selection_frame, text="현재 프로필:", 
                font=("Arial", 11, "bold")).pack(side='left')
        
        self.profile_combobox = ttk.Combobox(selection_frame, 
                                           textvariable=self.current_profile,
                                           state="readonly", 
                                           width=20, 
                                           font=("Arial", 11))
        self.profile_combobox.pack(side='left', padx=(10, 10))
        self.profile_combobox.bind('<<ComboboxSelected>>', self.on_profile_change)
        
        refresh_profiles_btn = tk.Button(selection_frame, text="🔄", 
                                       command=self.load_profiles,
                                       font=("Arial", 10), width=3)
        refresh_profiles_btn.pack(side='left', padx=5)
        
        self.profile_info_label = tk.Label(profile_frame, 
                                          text="프로필을 선택하세요", 
                                          font=("Arial", 10), 
                                          fg="gray")
        self.profile_info_label.pack(anchor='w', pady=(10, 0))
    
    def load_profiles(self):
        try:
            profiles = self.env_generator.get_all_profiles()
            
            if profiles:
                self.profile_combobox['values'] = profiles
                current = self.current_profile.get()
                if not current or current not in profiles:
                    self.current_profile.set(profiles[0])
                    self.on_profile_change()
                
                self.profile_info_label.config(
                    text=f"사용 가능한 프로필: {len(profiles)}개", 
                    fg="darkgreen"
                )
            else:
                self.profile_combobox['values'] = []
                self.current_profile.set("")
                self.profile_info_label.config(
                    text="저장된 프로필이 없습니다. 환경설정에서 프로필을 생성하세요.", 
                    fg="orange"
                )
            
            print(f"📋 프로필 목록 로드: {profiles}")
            
        except Exception as e:
            print(f"❌ 프로필 로드 실패: {e}")
            self.profile_info_label.config(text="프로필 로드 실패", fg="red")
    
    def on_profile_change(self, event=None):
        selected_profile = self.current_profile.get()
        if not selected_profile:
            return
        
        try:
            print(f"🔄 프로필 전환: {selected_profile}")
            success, message = self.env_generator.copy_profile_to_current_env(selected_profile)
            
            if success:
                print(f"✅ 프로필 전환 성공: {message}")
                profile_info = self.env_generator.get_profile_info(selected_profile)
                if profile_info:
                    repo = profile_info.get('GITHUB_REPO', 'Unknown')
                    username = profile_info.get('GITHUB_USERNAME', 'Unknown')
                    self.profile_info_label.config(
                        text=f"활성 프로필: {selected_profile} → {username}/{repo}", 
                        fg="darkblue"
                    )
                self.update_status()
            else:
                print(f"❌ 프로필 전환 실패: {message}")
                messagebox.showerror("프로필 전환 실패", message)
                
        except Exception as e:
            print(f"❌ 프로필 변경 중 오류: {e}")
            messagebox.showerror("오류", f"프로필 변경 중 오류가 발생했습니다: {e}")
    
    def create_status_frame(self, parent):
        status_frame = tk.LabelFrame(parent, text="📊 현재 상태", 
                                    font=("Arial", 12, "bold"), 
                                    padx=20, pady=15)
        status_frame.pack(fill='x', pady=(0, 20))
        
        self.status_label = tk.Label(status_frame, text="⚙️ 설정 확인 중...", 
                                    font=("Arial", 11), fg="orange")
        self.status_label.pack(anchor='w', pady=5)
        
        self.folder_label = tk.Label(status_frame, text="📁 감시 폴더: 확인 중...", 
                                    font=("Arial", 10), fg="gray")
        self.folder_label.pack(anchor='w', pady=2)
        
        self.repo_label = tk.Label(status_frame, text="📂 저장소: 확인 중...", 
                                  font=("Arial", 10), fg="gray")
        self.repo_label.pack(anchor='w', pady=2)
        
        self.mode_label = tk.Label(status_frame, text="🔧 업로드 모드: 확인 중...", 
                                  font=("Arial", 10), fg="gray")
        self.mode_label.pack(anchor='w', pady=2)
        
        self.upload_status_label = tk.Label(status_frame, text="🚀 업로드 상태: 중지됨", 
                                           font=("Arial", 10, "bold"), fg="red")
        self.upload_status_label.pack(anchor='w', pady=2)
    
    def create_function_buttons(self, parent):
        button_frame = tk.Frame(parent)
        button_frame.pack(pady=20)
        
        first_row = tk.Frame(button_frame)
        first_row.pack(pady=10)
        
        baekjoon_btn = tk.Button(first_row, text="📚\n백준 문제\n풀기", 
                                width=12, height=4,
                                font=("Arial", 11, "bold"),
                                bg="lightblue", fg="navy",
                                command=self.open_baekjoon)
        baekjoon_btn.pack(side='left', padx=20)
        
        setup_btn = tk.Button(first_row, text="⚙️\n환경설정", 
                             width=12, height=4,
                             font=("Arial", 11, "bold"),
                             bg="lightgreen", fg="darkgreen",
                             command=self.open_setup)
        setup_btn.pack(side='left', padx=20)
        
        second_row = tk.Frame(button_frame)
        second_row.pack(pady=10)
        
        self.upload_btn = tk.Button(second_row, text="🚀\n업로드\n시작", 
                                   width=12, height=4,
                                   font=("Arial", 11, "bold"),
                                   bg="orange", fg="white",
                                   command=self.toggle_upload)
        self.upload_btn.pack(side='left', padx=20)
        
        history_btn = tk.Button(second_row, text="📊\n업로드\n기록", 
                               width=12, height=4,
                               font=("Arial", 11, "bold"),
                               bg="lightgray", fg="black",
                               command=self.show_history)
        history_btn.pack(side='left', padx=20)
        
        # 🔧 백그라운드 모드 버튼 추가
        third_row = tk.Frame(button_frame)
        third_row.pack(pady=10)
        
        if TRAY_AVAILABLE:
            tray_btn = tk.Button(third_row, text="🌙\n백그라운드\n모드", 
                                width=12, height=4,
                                font=("Arial", 11, "bold"),
                                bg="purple", fg="white",
                                command=self.switch_to_tray_mode)
            tray_btn.pack(side='left', padx=20)
        else:
            tray_btn = tk.Button(third_row, text="🌙\n백그라운드\n(설치 필요)", 
                                width=12, height=4,
                                font=("Arial", 9, "bold"),
                                bg="gray", fg="white",
                                state="disabled")
            tray_btn.pack(side='left', padx=20)
        
        refresh_btn = tk.Button(button_frame, text="🔄 상태 새로고침", 
                               width=20, height=1,
                               font=("Arial", 10),
                               bg="lightcyan", fg="darkblue",
                               command=self.update_status)
        refresh_btn.pack(pady=10)
    
    def create_exit_button(self, parent):
        exit_btn = tk.Button(parent, text="종료", width=10, height=2,
                            font=("Arial", 11),
                            command=self.on_exit)
        exit_btn.pack(pady=20)
    
    # 🔧 트레이 관련 메서드들
    def switch_to_tray_mode(self):
        """백그라운드 모드로 전환"""
        if not TRAY_AVAILABLE:
            messagebox.showerror(
                "기능 없음", 
                "트레이 기능을 사용하려면 다음 패키지를 설치하세요:\n\n"
                "pip install pystray Pillow"
            )
            return
            
        result = messagebox.askyesno(
            "백그라운드 모드", 
            "백그라운드 모드로 전환하시겠습니까?\n\n"
            "창이 닫히고 시스템 트레이에서 실행됩니다.\n"
            "트레이 아이콘을 우클릭하여 다시 열 수 있습니다."
        )
        
        if result:
            self.minimize_to_tray()
    
    def minimize_to_tray(self):
        """트레이로 최소화"""
        try:
            self.root.withdraw()  # 창 숨기기
            self.is_tray_mode = True
            self.create_tray_icon()
            print("🌙 백그라운드 모드로 전환됨")
        except Exception as e:
            messagebox.showerror("오류", f"트레이 모드 전환 실패: {e}")
            # 실패시 창 다시 보이기
            self.root.deiconify()
            self.is_tray_mode = False
    
    def create_tray_icon(self):
        """트레이 아이콘 생성"""
        if self.tray_icon or not TRAY_AVAILABLE:
            return
        
        try:
            image = self.create_tray_image()
            menu = self.create_tray_menu()
            
            self.tray_icon = pystray.Icon(
                "GitHub Auto Upload",
                image,
                "GitHub 자동 업로드",
                menu
            )
            
            # 별도 스레드에서 실행
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
        except Exception as e:
            print(f"트레이 아이콘 생성 실패: {e}")
            self.root.deiconify()
            self.is_tray_mode = False
    
    def create_tray_image(self):
        """트레이 아이콘 이미지 생성"""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # GitHub 스타일 아이콘
        draw.ellipse([8, 8, 56, 56], fill='black')
        draw.ellipse([16, 16, 48, 48], fill='white')
        draw.ellipse([24, 24, 40, 40], fill='black')
        
        # 상태 표시
        if self.is_upload_running:
            draw.rectangle([50, 8, 58, 16], fill='green')
        
        return image
    
    def create_tray_menu(self):
        """트레이 메뉴 생성"""
        upload_text = "⏹️ 업로드 중지" if self.is_upload_running else "▶️ 업로드 시작"
        
        return pystray.Menu(
            # 제목
            pystray.MenuItem("🚀 GitHub 자동 업로드", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            
            # 메인 기능
            pystray.MenuItem("📋 GUI 열기", self.show_window_from_tray),
            pystray.MenuItem(upload_text, self.toggle_upload_from_tray),
            
            # 프로필 관리
            pystray.MenuItem("📋 프로필 선택", self.create_profile_submenu()),
            
            pystray.Menu.SEPARATOR,
            
            # 다른 창들
            pystray.MenuItem("⚙️ 환경설정", self.open_setup_from_tray),
            pystray.MenuItem("📚 백준 문제", self.open_baekjoon_from_tray),
            
            pystray.Menu.SEPARATOR,
            
            # 기록 및 통계  
            pystray.MenuItem("📊 업로드 기록", self.show_history_from_tray),
            pystray.MenuItem("📈 상태 정보", self.show_status_from_tray),
            
            pystray.Menu.SEPARATOR,
            
            # 종료
            pystray.MenuItem("❌ 완전 종료", self.quit_from_tray)
        )
    
    def show_window_from_tray(self, icon=None, item=None):
        """트레이에서 창 다시 보이기"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_tray_mode = False
            
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
                
            print("📋 GUI 모드로 전환됨")
            
        except Exception as e:
            print(f"창 복원 실패: {e}")
    
    def toggle_upload_from_tray(self, icon, item):
        """트레이에서 업로드 토글"""
        self.toggle_upload()
        
        if self.tray_icon:
            self.tray_icon.menu = self.create_tray_menu()
            self.tray_icon.icon = self.create_tray_image()
    
    def create_profile_submenu(self):
        """프로필 선택 서브메뉴"""
        profiles = self.env_generator.get_all_profiles()
        
        if not profiles:
            return pystray.Menu(
                pystray.MenuItem("저장된 프로필이 없습니다", lambda: None, enabled=False)
            )
        
        profile_items = []
        for profile in profiles:
            profile_items.append(
                pystray.MenuItem(f"📋 {profile}", 
                               lambda p=profile: self.switch_profile_from_tray(p))
            )
        
        return pystray.Menu(*profile_items)
    
    def switch_profile_from_tray(self, profile_name):
        """트레이에서 프로필 전환"""
        if self.is_upload_running:
            self.stop_upload()
            time.sleep(1)
        
        success, message = self.env_generator.copy_profile_to_current_env(profile_name)
        
        if success:
            self.current_profile.set(profile_name)
            self.update_status()
            self.show_tray_notification(f"프로필 전환: {profile_name}")
        else:
            self.show_tray_notification(f"프로필 전환 실패: {message}")
    
    def open_setup_from_tray(self, icon, item):
        """트레이에서 환경설정 열기"""
        self.open_setup()
    
    def open_baekjoon_from_tray(self, icon, item):
        """트레이에서 백준 열기"""
        self.open_baekjoon()
    
    def show_history_from_tray(self, icon, item):
        """트레이에서 기록 보기"""
        self.show_window_from_tray()
        self.root.after(500, self.show_history)
    
    def show_status_from_tray(self, icon, item):
        """트레이에서 상태 정보 표시"""
        try:
            stats = self.history_manager.get_statistics()
            
            profile = self.current_profile.get() or "없음"
            status = "실행 중" if self.is_upload_running else "중지됨"
            
            recent = stats['recent_activity'][:3]
            recent_text = ""
            for record in recent:
                time_str = record.get('timestamp', '').split(' ')[1][:5]
                file_name = record.get('file_name', '')[:15]
                status_icon = "✅" if record.get('status') == 'success' else "❌"
                recent_text += f"\n{status_icon} {time_str} {file_name}"
            
            message = f"""📊 GitHub 자동 업로드 상태

👤 프로필: {profile}
🚀 업로드: {status}

📈 통계:
- 총 기록: {stats['total_records']}개
- 성공: {stats['successful_uploads']}개
- 실패: {stats['failed_uploads']}개

📋 최근 기록:{recent_text}"""
            
            self.show_tray_notification(message)
            
        except Exception as e:
            self.show_tray_notification(f"상태 조회 실패: {e}")
    
    def show_tray_notification(self, message):
        """트레이 알림 표시"""
        if self.tray_icon:
            try:
                self.tray_icon.notify(message, "GitHub 자동 업로드")
            except:
                print(f"📢 {message}")
    
    def quit_from_tray(self, icon, item):
        """트레이에서 완전 종료"""
        if self.is_upload_running:
            self.stop_upload()
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.quit()
    
    def on_closing(self):
        """창 닫기 이벤트"""
        if self.is_tray_mode:
            self.root.withdraw()
            return
        
        if TRAY_AVAILABLE:
            result = messagebox.askyesnocancel(
                "종료 방식 선택", 
                "어떻게 종료하시겠습니까?\n\n"
                "예: 백그라운드 모드로 전환\n"
                "아니오: 완전 종료\n"
                "취소: 창 유지"
            )
            
            if result == True:  # 백그라운드 모드
                self.minimize_to_tray()
            elif result == False:  # 완전 종료
                self.on_exit()
        else:
            # 트레이 기능이 없으면 기존 방식
            if self.is_upload_running:
                result = messagebox.askyesno(
                    "종료 확인", 
                    "업로드가 실행 중입니다.\n업로드를 중지하고 종료하시겠습니까?"
                )
                if result:
                    self.stop_upload()
                    self.root.quit()
            else:
                self.root.quit()
    
    # 🔧 업로드 기록 관련 메서드들 (기존과 동일)
    def show_history(self):
        """업로드 기록 창 표시"""
        history_window = tk.Toplevel(self.root)
        history_window.title("📊 업로드 기록")
        history_window.geometry("1000x700")
        history_window.resizable(True, True)
        
        main_frame = tk.Frame(history_window, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        title_label = tk.Label(main_frame, text="📊 GitHub 업로드 기록", 
                              font=("Arial", 16, "bold"), fg="navy")
        title_label.pack(pady=(0, 20))
        
        self.create_history_toolbar(main_frame, history_window)
        self.create_statistics_section(main_frame)
        self.create_history_table(main_frame)
        self.create_history_buttons(main_frame, history_window)

    def create_history_toolbar(self, parent, window):
        """기록 필터링/검색 툴바"""
        toolbar_frame = tk.LabelFrame(parent, text="🔍 필터 및 검색", 
                                     font=("Arial", 11, "bold"), padx=10, pady=10)
        toolbar_frame.pack(fill='x', pady=(0, 20))
        
        first_row = tk.Frame(toolbar_frame)
        first_row.pack(fill='x', pady=5)
        
        # 검색
        tk.Label(first_row, text="검색:", font=("Arial", 10)).pack(side='left')
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(first_row, textvariable=self.search_var, width=20, font=("Arial", 10))
        search_entry.pack(side='left', padx=(5, 10))
        
        tk.Button(first_row, text="🔍 검색", command=self.search_history,
                 bg="lightblue", font=("Arial", 9)).pack(side='left', padx=5)
        
        # 상태 필터
        tk.Label(first_row, text="상태:", font=("Arial", 10)).pack(side='left', padx=(20, 5))
        self.status_filter = tk.StringVar(value="전체")
        status_combo = ttk.Combobox(first_row, textvariable=self.status_filter,
                                   values=["전체", "success", "failed", "skipped"],
                                   state="readonly", width=10, font=("Arial", 9))
        status_combo.pack(side='left', padx=5)
        status_combo.bind('<<ComboboxSelected>>', self.filter_history)
        
        # 새로고침 버튼
        tk.Button(first_row, text="🔄 새로고침", command=self.refresh_history,
                 bg="lightgreen", font=("Arial", 9)).pack(side='right', padx=5)

    def create_statistics_section(self, parent):
        """통계 정보 섹션"""
        stats_frame = tk.LabelFrame(parent, text="📈 통계", 
                                   font=("Arial", 11, "bold"), padx=10, pady=10)
        stats_frame.pack(fill='x', pady=(0, 20))
        
        stats = self.history_manager.get_statistics()
        
        stats_row = tk.Frame(stats_frame)
        stats_row.pack(fill='x')
        
        left_stats = tk.Frame(stats_row)
        left_stats.pack(side='left', fill='x', expand=True)
        
        tk.Label(left_stats, text=f"📄 총 기록: {stats['total_records']}개", 
                font=("Arial", 10)).pack(anchor='w')
        tk.Label(left_stats, text=f"✅ 성공: {stats['successful_uploads']}개", 
                font=("Arial", 10), fg="green").pack(anchor='w')
        tk.Label(left_stats, text=f"❌ 실패: {stats['failed_uploads']}개", 
                font=("Arial", 10), fg="red").pack(anchor='w')
        
        right_stats = tk.Frame(stats_row)
        right_stats.pack(side='right', fill='x', expand=True)
        
        file_size_mb = stats['total_files_size'] / (1024 * 1024) if stats['total_files_size'] > 0 else 0
        tk.Label(right_stats, text=f"💾 총 용량: {file_size_mb:.1f}MB", 
                font=("Arial", 10)).pack(anchor='e')
        
        success_rate = (stats['successful_uploads'] / max(stats['total_records'], 1)) * 100
        tk.Label(right_stats, text=f"📊 성공률: {success_rate:.1f}%", 
                font=("Arial", 10)).pack(anchor='e')

    def create_history_table(self, parent):
        """기록 테이블 생성"""
        table_frame = tk.LabelFrame(parent, text="📋 업로드 기록", 
                                   font=("Arial", 11, "bold"), padx=10, pady=10)
        table_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        columns = ("시간", "파일명", "작업", "상태", "크기", "프로필")
        
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        self.history_tree.heading("시간", text="시간")
        self.history_tree.heading("파일명", text="파일명")
        self.history_tree.heading("작업", text="작업")
        self.history_tree.heading("상태", text="상태")
        self.history_tree.heading("크기", text="크기")
        self.history_tree.heading("프로필", text="프로필")
        
        self.history_tree.column("시간", width=150)
        self.history_tree.column("파일명", width=250)
        self.history_tree.column("작업", width=80)
        self.history_tree.column("상태", width=80)
        self.history_tree.column("크기", width=100)
        self.history_tree.column("프로필", width=120)
        
        history_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.pack(side='left', fill='both', expand=True)
        history_scrollbar.pack(side='right', fill='y')
        
        self.history_tree.bind('<Double-1>', self.show_record_detail)
        
        self.refresh_history()

    def create_history_buttons(self, parent, window):
        """하단 버튼들"""
        button_frame = tk.Frame(parent)
        button_frame.pack(fill='x', pady=10)
        
        left_buttons = tk.Frame(button_frame)
        left_buttons.pack(side='left')
        
        tk.Button(left_buttons, text="📄 상세보기", command=self.show_record_detail,
                 font=("Arial", 10), bg="lightblue").pack(side='left', padx=5)
        
        tk.Button(left_buttons, text="🗑️ 기록 정리", command=self.clean_old_records,
                 font=("Arial", 10), bg="orange").pack(side='left', padx=5)
        
        right_buttons = tk.Frame(button_frame)
        right_buttons.pack(side='right')
        
        tk.Button(right_buttons, text="💾 내보내기", command=self.export_history,
                 font=("Arial", 10), bg="lightgray").pack(side='left', padx=5)
        
        tk.Button(right_buttons, text="❌ 닫기", command=window.destroy,
                 font=("Arial", 10)).pack(side='left', padx=5)

    def refresh_history(self):
        """기록 테이블 새로고침"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        records = self.history_manager.get_all_records()
        self.update_history_table(records)

    def search_history(self):
        """기록 검색"""
        keyword = self.search_var.get().strip()
        if not keyword:
            self.refresh_history()
            return
        
        records = self.history_manager.search_records(keyword)
        self.update_history_table(records)

    def filter_history(self, event=None):
        """기록 필터링"""
        status_filter = self.status_filter.get()
        
        records = self.history_manager.get_all_records()
        
        if status_filter != "전체":
            records = [r for r in records if r.get('status') == status_filter]
        
        self.update_history_table(records)

    def update_history_table(self, records):
        """테이블 데이터 업데이트"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        for record in records:
            file_size = record.get('file_size', 0)
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f}MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f}KB"
            else:
                size_str = f"{file_size}B"
            
            status = record.get('status', '')
            if status == 'success':
                status_display = "✅ 성공"
            elif status == 'failed':
                status_display = "❌ 실패"
            elif status == 'skipped':
                status_display = "⏭️ 건너뜀"
            else:
                status_display = status
            
            action = record.get('action', '')
            if action == 'upload':
                action_display = "📤 업로드"
            elif action == 'update':
                action_display = "🔄 업데이트"
            elif action == 'delete':
                action_display = "🗑️ 삭제"
            else:
                action_display = action
            
            self.history_tree.insert('', 'end', values=(
                record.get('timestamp', ''),
                record.get('file_name', ''),
                action_display,
                status_display,
                size_str,
                record.get('profile_name', '')
            ), tags=(record.get('id', ''),))

    def show_record_detail(self, event=None):
        """기록 상세보기"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("선택 없음", "상세보기할 기록을 선택해주세요.")
            return
        
        item = self.history_tree.item(selection[0])
        record_id = item['tags'][0] if item['tags'] else ""
        
        records = self.history_manager.get_all_records()
        record = next((r for r in records if r.get('id') == record_id), None)
        
        if not record:
            messagebox.showerror("오류", "기록을 찾을 수 없습니다.")
            return
        
        detail_window = tk.Toplevel()
        detail_window.title("📄 업로드 기록 상세")
        detail_window.geometry("600x500")
        detail_window.resizable(False, False)
        
        main_frame = tk.Frame(detail_window, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        tk.Label(main_frame, text="📄 업로드 기록 상세 정보", 
                font=("Arial", 14, "bold")).pack(pady=(0, 20))
        
        details_text = scrolledtext.ScrolledText(main_frame, height=20, font=("Consolas", 10))
        details_text.pack(fill='both', expand=True, pady=(0, 20))
        
        detail_content = f"""📋 기본 정보
{'='*50}
🆔 기록 ID: {record.get('id', 'N/A')}
⏰ 업로드 시간: {record.get('timestamp', 'N/A')}
👤 프로필: {record.get('profile_name', 'N/A')}

📁 파일 정보
{'='*50}
📄 파일명: {record.get('file_name', 'N/A')}
📂 경로: {record.get('file_path', 'N/A')}
💾 크기: {record.get('file_size', 0)} bytes

🔧 작업 정보
{'='*50}
🎯 작업: {record.get('action', 'N/A')}
📊 상태: {record.get('status', 'N/A')}
🔗 커밋 해시: {record.get('commit_hash', 'N/A')}

❌ 오류 정보
{'='*50}
{record.get('error_message', '오류 없음')}
"""
        
        details_text.insert(tk.END, detail_content)
        details_text.config(state='disabled')
        
        tk.Button(main_frame, text="닫기", command=detail_window.destroy).pack()

    def clean_old_records(self):
        """오래된 기록 정리"""
        result = messagebox.askyesno(
            "기록 정리", 
            "30일 이전의 기록을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다."
        )
        
        if result:
            deleted_count = self.history_manager.clear_old_records(30)
            messagebox.showinfo("완료", f"{deleted_count}개의 오래된 기록을 삭제했습니다.")
            self.refresh_history()

    def export_history(self):
        """기록 내보내기"""
        file_path = filedialog.asksaveasfilename(
            title="기록 내보내기",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                records = self.history_manager.get_all_records()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({"export_date": datetime.now().isoformat(), 
                              "records": records}, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("완료", f"기록을 성공적으로 내보냈습니다!\n\n저장 위치: {file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"내보내기 실패: {e}")
    
    # 업로드 관련 메서드들 (기존과 동일)
    def toggle_upload(self):
        if self.is_upload_running:
            self.stop_upload()
        else:
            self.start_upload()
    
    def start_upload(self):
        try:
            if self.is_upload_running:
                messagebox.showwarning("경고", "업로드가 이미 실행 중입니다!")
                return
            
            self.upload_process = subprocess.Popen([sys.executable, 'main_upload.py'])
            
            with open(self.upload_pid_file, 'w') as f:
                f.write(str(self.upload_process.pid))
            
            self.is_upload_running = True
            self.update_upload_button()
            
            current_profile = self.current_profile.get()
            if current_profile:
                message_text = f"GitHub 자동 업로드가 시작되었습니다!\n\n현재 프로필: {current_profile}"
            else:
                message_text = "GitHub 자동 업로드가 시작되었습니다!"
            
            if self.is_tray_mode:
                self.show_tray_notification(message_text)
            else:
                messagebox.showinfo("시작", message_text)
            
            print(f"✅ 업로드 프로세스 시작됨 (PID: {self.upload_process.pid})")
            
        except FileNotFoundError:
            error_msg = "main_upload.py 파일을 찾을 수 없습니다!"
            if self.is_tray_mode:
                self.show_tray_notification(error_msg)
            else:
                messagebox.showerror("오류", error_msg)
        except Exception as e:
            error_msg = f"업로드 프로그램을 시작할 수 없습니다: {e}"
            if self.is_tray_mode:
                self.show_tray_notification(error_msg)
            else:
                messagebox.showerror("오류", error_msg)
            self.is_upload_running = False
            self.update_upload_button()
    
    def stop_upload(self):
        try:
            if self.upload_process and self.upload_process.poll() is None:
                try:
                    parent = psutil.Process(self.upload_process.pid)
                    children = parent.children(recursive=True)
                    
                    for child in children:
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    
                    parent.terminate()
                    
                    gone, still_alive = psutil.wait_procs([parent] + children, timeout=3)
                    for p in still_alive:
                        try:
                            p.kill()
                        except psutil.NoSuchProcess:
                            pass
                    
                    print(f"✅ 업로드 프로세스 종료됨 (PID: {self.upload_process.pid})")
                    
                except psutil.NoSuchProcess:
                    print("ℹ️  프로세스가 이미 종료되었습니다")
                except Exception as e:
                    print(f"⚠️  프로세스 종료 중 오류: {e}")
                    self.upload_process.terminate()
            
            if os.path.exists(self.upload_pid_file):
                os.remove(self.upload_pid_file)
            
            self.upload_process = None
            self.is_upload_running = False
            self.update_upload_button()
            
            message = "GitHub 자동 업로드가 중지되었습니다!"
            if self.is_tray_mode:
                self.show_tray_notification(message)
            else:
                messagebox.showinfo("중지", message)
            
        except Exception as e:
            error_msg = f"업로드 프로그램을 중지할 수 없습니다: {e}"
            if self.is_tray_mode:
                self.show_tray_notification(error_msg)
            else:
                messagebox.showerror("오류", error_msg)
            print(f"❌ 업로드 중지 실패: {e}")
    
    def update_upload_button(self):
        if self.is_upload_running:
            self.upload_btn.config(
                text="⏹️\n업로드\n중지",
                bg="red",
                fg="white"
            )
            self.upload_status_label.config(
                text="🚀 업로드 상태: 실행 중",
                fg="green"
            )
        else:
            self.upload_btn.config(
                text="🚀\n업로드\n시작",
                bg="orange",
                fg="white"
            )
            self.upload_status_label.config(
                text="🚀 업로드 상태: 중지됨",
                fg="red"
            )
        
        # 트레이 아이콘도 업데이트
        if self.is_tray_mode and self.tray_icon:
            self.tray_icon.icon = self.create_tray_image()
            self.tray_icon.menu = self.create_tray_menu()
    
    def check_upload_process(self):
        try:
            if os.path.exists(self.upload_pid_file):
                with open(self.upload_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    try:
                        process = psutil.Process(pid)
                        if 'python' in process.name().lower():
                            self.is_upload_running = True
                            self.upload_process = subprocess.Popen([], shell=False)
                            self.upload_process.pid = pid
                            print(f"ℹ️  기존 업로드 프로세스 발견 (PID: {pid})")
                        else:
                            os.remove(self.upload_pid_file)
                    except psutil.NoSuchProcess:
                        os.remove(self.upload_pid_file)
                else:
                    os.remove(self.upload_pid_file)
            
            self.update_upload_button()
            
        except Exception as e:
            print(f"⚠️  프로세스 상태 체크 실패: {e}")
            self.is_upload_running = False
            self.update_upload_button()
    
    def start_process_monitor(self):
        def monitor():
            while True:
                try:
                    if self.is_upload_running and self.upload_process:
                        if self.upload_process.poll() is not None:
                            self.is_upload_running = False
                            self.upload_process = None
                            
                            if os.path.exists(self.upload_pid_file):
                                os.remove(self.upload_pid_file)
                            
                            self.root.after(0, self.update_upload_button)
                            print("ℹ️  업로드 프로세스가 종료되어 버튼 상태를 업데이트했습니다")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️  프로세스 모니터링 오류: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def update_status(self):
        try:
            print("🔄 상태 업데이트 중...")
            
            if os.path.exists('.env'):
                load_dotenv(override=True)
                
                token = os.getenv('GITHUB_TOKEN')
                username = os.getenv('GITHUB_USERNAME')
                repo = os.getenv('GITHUB_REPO')
                folder = os.getenv('WATCH_FOLDER')
                mode = os.getenv('UPLOAD_MODE', 'realtime')
                
                if all([token, username, repo, folder]):
                    current_profile = self.current_profile.get()
                    if current_profile:
                        self.status_label.config(
                            text=f"✅ 설정 완료 - 업로드 준비됨 (프로필: {current_profile})", 
                            fg="green"
                        )
                    else:
                        self.status_label.config(text="✅ 설정 완료 - 업로드 준비됨", fg="green")
                    
                    self.folder_label.config(text=f"📁 감시 폴더: {folder}", fg="black")
                    self.repo_label.config(text=f"📂 저장소: {username}/{repo}", fg="black")
                    
                    mode_text = {
                        "realtime": "실시간 감시",
                        "schedule": "시간 예약", 
                        "hybrid": "실시간 + 예약"
                    }
                    self.mode_label.config(text=f"🔧 업로드 모드: {mode_text.get(mode, mode)}", fg="black")
                    
                    if not self.is_upload_running:
                        self.upload_btn.config(state='normal')
                    
                    print("✅ 설정 완료!")
                else:
                    self.status_label.config(text="⚠️ 설정 불완전 - 환경설정 필요", fg="orange")
                    if not self.is_upload_running:
                        self.upload_btn.config(state='disabled', bg="gray")
                    print("⚠️ 설정 불완전")
            else:
                self.status_label.config(text="❌ 설정 없음 - 환경설정 필요", fg="red")
                self.folder_label.config(text="📁 감시 폴더: 설정되지 않음", fg="gray")
                self.repo_label.config(text="📂 저장소: 설정되지 않음", fg="gray")
                self.mode_label.config(text="🔧 업로드 모드: 설정되지 않음", fg="gray")
                if not self.is_upload_running:
                    self.upload_btn.config(state='disabled', bg="gray")
                print("❌ .env 파일 없음")
                
        except Exception as e:
            self.status_label.config(text="❌ 설정 오류 발생", fg="red")
            if not self.is_upload_running:
                self.upload_btn.config(state='disabled', bg="gray")
            print(f"❌ 에러: {e}")
    
    def open_baekjoon(self):
        try:
            subprocess.Popen([sys.executable, 'baekjoon_gui.py'])
        except FileNotFoundError:
            messagebox.showerror("오류", "baekjoon_gui.py 파일을 찾을 수 없습니다!")
        except Exception as e:
            messagebox.showerror("오류", f"백준 문제 창을 열 수 없습니다: {e}")
    
    def open_setup(self):
        try:
            process = subprocess.Popen([sys.executable, 'setup_gui.py'])
            
            def wait_and_update():
                process.wait()
                self.root.after(100, self.load_profiles)
                self.root.after(200, self.update_status)
            
            threading.Thread(target=wait_and_update, daemon=True).start()
            
        except FileNotFoundError:
            messagebox.showerror("오류", "setup_gui.py 파일을 찾을 수 없습니다!")
        except Exception as e:
            messagebox.showerror("오류", f"환경설정 창을 열 수 없습니다: {e}")
    
    def on_exit(self):
        if self.is_upload_running:
            result = messagebox.askyesno(
                "종료 확인", 
                "업로드가 실행 중입니다.\n업로드를 중지하고 종료하시겠습니까?"
            )
            if result:
                self.stop_upload()
                if self.tray_icon:
                    self.tray_icon.stop()
                self.root.quit()
        else:
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.quit()

if __name__ == "__main__":
    print("🚀 GitHub 자동 업로드 메인 GUI 시작...")
    app = GitHubAutoUploadMain()
    app.root.mainloop()
    print("👋 메인 GUI 종료")