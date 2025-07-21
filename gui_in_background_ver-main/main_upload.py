# main_upload.py - 업로드 기록 기능 포함 완성 버전
import os
import time
import schedule
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
import requests
import base64
import threading
import json
from pathlib import Path
from upload_history import UploadHistoryManager

class GitHubUploader:
    def __init__(self):
        # 환경변수 로드
        load_dotenv()
        
        # GitHub 설정
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_username = os.getenv('GITHUB_USERNAME')
        self.github_repo = os.getenv('GITHUB_REPO')
        self.branch = os.getenv('BRANCH', 'main')
        self.commit_message_prefix = os.getenv('COMMIT_MESSAGE_PREFIX', 'Auto-upload:')
        
        # 폴더 및 파일 설정
        self.watch_folder = os.getenv('WATCH_FOLDER')
        self.file_extensions = os.getenv('FILE_EXTENSIONS', 'py,txt,md,json,js,html,css').split(',')
        self.file_extensions = [ext.strip() for ext in self.file_extensions]
        
        # 업로드 모드 설정
        self.upload_mode = os.getenv('UPLOAD_MODE', 'realtime')
        self.schedule_hour = int(os.getenv('SCHEDULE_HOUR', '14'))
        self.schedule_minute = int(os.getenv('SCHEDULE_MINUTE', '30'))
        self.repeat_option = os.getenv('REPEAT_OPTION', 'daily')
        
        # 프로필 정보
        self.profile_name = os.getenv('PROFILE_NAME', 'default')
        
        # 기록 관리자
        self.history_manager = UploadHistoryManager()
        
        # API 헤더
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 업로드 상태 추적
        self.uploaded_files = set()
        self.is_running = False
        
        print("🚀 GitHub 자동 업로드 시스템 초기화 완료")
        print(f"📂 감시 폴더: {self.watch_folder}")
        print(f"📄 지원 파일: {', '.join(self.file_extensions)}")
        print(f"🔧 업로드 모드: {self.upload_mode}")
        print(f"👤 프로필: {self.profile_name}")
    
    def validate_settings(self):
        """설정 검증"""
        if not self.github_token:
            print("❌ GitHub 토큰이 설정되지 않았습니다.")
            return False
        
        if not self.github_username:
            print("❌ GitHub 사용자명이 설정되지 않았습니다.")
            return False
        
        if not self.github_repo:
            print("❌ GitHub 저장소가 설정되지 않았습니다.")
            return False
        
        if not self.watch_folder or not os.path.exists(self.watch_folder):
            print(f"❌ 감시 폴더가 존재하지 않습니다: {self.watch_folder}")
            return False
        
        return True
    
    def test_github_connection(self):
        """GitHub 연결 테스트"""
        try:
            url = f"https://api.github.com/repos/{self.github_username}/{self.github_repo}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                print("✅ GitHub 연결 테스트 성공")
                return True
            else:
                print(f"❌ GitHub 연결 테스트 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ GitHub 연결 테스트 오류: {e}")
            return False
    
    def should_upload_file(self, file_path):
        """파일 업로드 여부 판단"""
        # 파일 확장자 확인
        file_ext = Path(file_path).suffix[1:].lower()  # .py -> py
        if file_ext not in [ext.lower() for ext in self.file_extensions]:
            return False
        
        # 숨김 파일 제외
        if os.path.basename(file_path).startswith('.'):
            return False
        
        # 파일 크기 확인 (100MB 제한)
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 100 * 1024 * 1024:  # 100MB
                print(f"⚠️  파일이 너무 큽니다 (100MB 초과): {file_path}")
                return False
        except:
            return False
        
        return True
    
    def get_file_content(self, file_path):
        """파일 내용 읽기 (Base64 인코딩)"""
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
                return base64.b64encode(content).decode('utf-8')
        except Exception as e:
            print(f"❌ 파일 읽기 실패: {file_path} - {e}")
            return None
    
    def get_github_file_sha(self, github_path):
        """GitHub에서 기존 파일의 SHA 값 가져오기"""
        try:
            url = f"https://api.github.com/repos/{self.github_username}/{self.github_repo}/contents/{github_path}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json().get('sha')
            else:
                return None
        except Exception as e:
            print(f"❌ SHA 값 조회 실패: {github_path} - {e}")
            return None
    
    def upload_file_to_github(self, file_path):
        """파일을 GitHub에 업로드"""
        try:
            # 파일 정보
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            relative_path = os.path.relpath(file_path, self.watch_folder)
            github_path = relative_path.replace('\\', '/')  # Windows 경로 변환
            
            print(f"📤 업로드 시작: {github_path}")
            
            # 파일 내용 읽기
            content = self.get_file_content(file_path)
            if content is None:
                raise Exception("파일 내용을 읽을 수 없습니다")
            
            # 기존 파일 SHA 확인
            existing_sha = self.get_github_file_sha(github_path)
            action = "update" if existing_sha else "upload"
            
            # 커밋 메시지 생성
            commit_message = f"{self.commit_message_prefix} {github_path}"
            
            # GitHub API 요청 데이터
            data = {
                'message': commit_message,
                'content': content,
                'branch': self.branch
            }
            
            if existing_sha:
                data['sha'] = existing_sha
            
            # API 요청
            url = f"https://api.github.com/repos/{self.github_username}/{self.github_repo}/contents/{github_path}"
            response = requests.put(url, headers=self.headers, json=data, timeout=30)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                commit_hash = response_data.get('commit', {}).get('sha', '')
                
                # 성공 기록 추가
                self.history_manager.add_record(
                    file_path=file_path,
                    action=action,
                    status="success",
                    commit_hash=commit_hash,
                    file_size=file_size,
                    profile_name=self.profile_name
                )
                
                self.uploaded_files.add(file_path)
                print(f"✅ 업로드 성공: {github_path} ({action})")
                return True
                
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)
                
        except Exception as e:
            error_message = str(e)
            print(f"❌ 업로드 실패: {github_path} - {error_message}")
            
            # 실패 기록 추가
            self.history_manager.add_record(
                file_path=file_path,
                action=action if 'action' in locals() else "upload",
                status="failed",
                error_message=error_message,
                file_size=file_size if 'file_size' in locals() else 0,
                profile_name=self.profile_name
            )
            
            return False
    
    def upload_all_files(self):
        """감시 폴더의 모든 파일 업로드"""
        print(f"\n🔍 {self.watch_folder} 폴더 스캔 중...")
        
        uploaded_count = 0
        failed_count = 0
        skipped_count = 0
        
        for root, dirs, files in os.walk(self.watch_folder):
            for file in files:
                file_path = os.path.join(root, file)
                
                if self.should_upload_file(file_path):
                    if file_path not in self.uploaded_files:
                        if self.upload_file_to_github(file_path):
                            uploaded_count += 1
                        else:
                            failed_count += 1
                        
                        # API 제한 고려하여 잠시 대기
                        time.sleep(1)
                    else:
                        skipped_count += 1
                        # 건너뜀 기록 추가
                        self.history_manager.add_record(
                            file_path=file_path,
                            action="upload",
                            status="skipped",
                            error_message="이미 업로드된 파일",
                            file_size=os.path.getsize(file_path),
                            profile_name=self.profile_name
                        )
        
        print(f"\n📊 업로드 완료:")
        print(f"   ✅ 성공: {uploaded_count}개")
        print(f"   ❌ 실패: {failed_count}개")
        print(f"   ⏭️  건너뜀: {skipped_count}개")
        
        return uploaded_count, failed_count, skipped_count

class FileWatcher(FileSystemEventHandler):
    def __init__(self, uploader):
        self.uploader = uploader
        self.last_modified = {}
        
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # 중복 이벤트 방지 (1초 내 같은 파일 수정 이벤트 무시)
        current_time = time.time()
        if file_path in self.last_modified:
            if current_time - self.last_modified[file_path] < 1:
                return
        
        self.last_modified[file_path] = current_time
        
        # 파일 업로드 여부 확인
        if self.uploader.should_upload_file(file_path):
            print(f"\n🔔 파일 변경 감지: {os.path.basename(file_path)}")
            
            # 파일이 완전히 쓰여질 때까지 잠시 대기
            time.sleep(2)
            
            # 파일 업로드
            self.uploader.upload_file_to_github(file_path)
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        if self.uploader.should_upload_file(file_path):
            print(f"\n🆕 새 파일 생성: {os.path.basename(file_path)}")
            
            # 파일이 완전히 생성될 때까지 잠시 대기
            time.sleep(2)
            
            # 파일 업로드
            self.uploader.upload_file_to_github(file_path)

def scheduled_upload():
    """스케줄된 업로드 실행"""
    print(f"\n⏰ 예약된 업로드 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    uploader = GitHubUploader()
    if uploader.validate_settings():
        uploader.upload_all_files()
    else:
        print("❌ 설정 오류로 인해 업로드를 건너뜁니다.")

def setup_schedule(uploader):
    """스케줄 설정"""
    schedule_time = f"{uploader.schedule_hour:02d}:{uploader.schedule_minute:02d}"
    
    if uploader.repeat_option == "daily":
        schedule.every().day.at(schedule_time).do(scheduled_upload)
        print(f"📅 매일 {schedule_time}에 업로드 예약")
    elif uploader.repeat_option == "weekdays":
        schedule.every().monday.at(schedule_time).do(scheduled_upload)
        schedule.every().tuesday.at(schedule_time).do(scheduled_upload)
        schedule.every().wednesday.at(schedule_time).do(scheduled_upload)
        schedule.every().thursday.at(schedule_time).do(scheduled_upload)
        schedule.every().friday.at(schedule_time).do(scheduled_upload)
        print(f"📅 평일 {schedule_time}에 업로드 예약")
    elif uploader.repeat_option == "weekends":
        schedule.every().saturday.at(schedule_time).do(scheduled_upload)
        schedule.every().sunday.at(schedule_time).do(scheduled_upload)
        print(f"📅 주말 {schedule_time}에 업로드 예약")

def run_scheduler():
    """스케줄러 실행"""
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 GitHub 자동 업로드 시스템 시작")
    print("=" * 60)
    
    # 업로더 초기화
    uploader = GitHubUploader()
    
    # 설정 검증
    if not uploader.validate_settings():
        print("❌ 설정 오류로 인해 프로그램을 종료합니다.")
        input("Press Enter to exit...")
        return
    
    # GitHub 연결 테스트
    if not uploader.test_github_connection():
        print("❌ GitHub 연결 실패로 인해 프로그램을 종료합니다.")
        input("Press Enter to exit...")
        return
    
    uploader.is_running = True
    
    # 업로드 모드에 따른 실행
    if uploader.upload_mode == "realtime":
        print("\n🔄 실시간 감시 모드로 시작합니다...")
        
        # 초기 업로드
        print("\n📤 초기 파일 업로드를 시작합니다...")
        uploader.upload_all_files()
        
        # 파일 감시 시작
        event_handler = FileWatcher(uploader)
        observer = Observer()
        observer.schedule(event_handler, uploader.watch_folder, recursive=True)
        observer.start()
        
        print(f"\n👀 파일 감시 시작: {uploader.watch_folder}")
        print("파일을 추가하거나 수정하면 자동으로 업로드됩니다.")
        print("Ctrl+C를 눌러 종료하세요.")
        
        try:
            while uploader.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  사용자가 중단했습니다.")
        finally:
            observer.stop()
            observer.join()
    
    elif uploader.upload_mode == "schedule":
        print(f"\n⏰ 시간 예약 모드로 시작합니다...")
        
        # 스케줄 설정
        setup_schedule(uploader)
        
        print("스케줄러가 실행 중입니다.")
        print("Ctrl+C를 눌러 종료하세요.")
        
        try:
            run_scheduler()
        except KeyboardInterrupt:
            print("\n\n⏹️  사용자가 중단했습니다.")
    
    elif uploader.upload_mode == "hybrid":
        print("\n🔄⏰ 혼합 모드로 시작합니다...")
        
        # 초기 업로드
        print("\n📤 초기 파일 업로드를 시작합니다...")
        uploader.upload_all_files()
        
        # 스케줄 설정
        setup_schedule(uploader)
        
        # 스케줄러를 별도 스레드에서 실행
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # 파일 감시 시작
        event_handler = FileWatcher(uploader)
        observer = Observer()
        observer.schedule(event_handler, uploader.watch_folder, recursive=True)
        observer.start()
        
        print(f"\n👀 실시간 감시 시작: {uploader.watch_folder}")
        print("파일 변경 시 즉시 업로드 + 예약된 시간에 전체 업로드")
        print("Ctrl+C를 눌러 종료하세요.")
        
        try:
            while uploader.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  사용자가 중단했습니다.")
        finally:
            observer.stop()
            observer.join()
    
    else:
        print(f"❌ 알 수 없는 업로드 모드: {uploader.upload_mode}")
        input("Press Enter to exit...")
        return
    
    print("\n🏁 GitHub 자동 업로드 시스템 종료")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n💥 예상치 못한 오류 발생: {e}")
        input("Press Enter to exit...")