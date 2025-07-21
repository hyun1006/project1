# env_generate.py - 2단계: 프로필 기능 추가된 완전 버전
import os
import re
import requests
import json  # 🔧 2단계 추가
from datetime import datetime

class EnvGenerator:
    def __init__(self):
        self.project_root = os.getcwd()
        self.env_path = os.path.join(self.project_root, '.env')
        self.profiles_file = os.path.join(self.project_root, 'profiles.json')  # 🔧 2단계 추가
        self.ensure_profiles_file()  # 🔧 2단계 추가
    
    # 🔧 2단계 추가: profiles.json 파일 관리
    def ensure_profiles_file(self):
        """profiles.json 파일이 없으면 생성"""
        if not os.path.exists(self.profiles_file):
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump({"profiles": []}, f, ensure_ascii=False, indent=2)
    
    def get_all_profiles(self):
        """모든 프로필 목록 가져오기"""
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("profiles", [])
        except Exception as e:
            print(f"프로필 목록 로드 실패: {e}")
            return []
    
    def add_profile(self, profile_name):
        """새 프로필을 profiles.json에 추가"""
        if not profile_name:
            return False
            
        profiles = self.get_all_profiles()
        if profile_name not in profiles:
            profiles.append(profile_name)
            self.save_profiles(profiles)
            return True
        return False
    
    def save_profiles(self, profiles):
        """프로필 목록을 profiles.json에 저장"""
        try:
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump({"profiles": profiles}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"프로필 목록 저장 실패: {e}")
            return False
    
    # 기존 검증 메서드들 (변경 없음)
    def validate_token(self, token):
        """GitHub 토큰 실제 검증"""
        if not token:
            return False, "토큰을 입력해주세요."
        
        if not token.startswith(('ghp_', 'github_pat_')):
            return False, "올바른 GitHub 토큰 형식이 아닙니다."
        
        if len(token) < 20:
            return False, "토큰이 너무 짧습니다."
        
        try:
            headers = {"Authorization": f"token {token}"}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return True, f"토큰이 유효합니다. (사용자: {user_data.get('login', 'Unknown')})"
            elif response.status_code == 401:
                return False, "토큰이 만료되었거나 잘못되었습니다."
            else:
                return False, f"토큰 검증 실패 (상태 코드: {response.status_code})"
        except requests.exceptions.Timeout:
            return False, "토큰 검증 시간 초과. 인터넷 연결을 확인해주세요."
        except requests.exceptions.RequestException:
            return False, "네트워크 오류로 토큰 검증에 실패했습니다."
    
    def validate_username(self, username):
        """GitHub 사용자명 유효성 검사"""
        if not username:
            return False, "사용자명을 입력해주세요."
        
        if not re.match(r'^[a-zA-Z0-9\-]+$', username):
            return False, "사용자명은 영문, 숫자, 하이픈만 사용 가능합니다."
        
        return True, "사용자명이 올바릅니다."
    
    def validate_repo_name(self, repo_name):
        """저장소명 유효성 검사"""
        if not repo_name:
            return False, "저장소명을 입력해주세요."
        
        if not re.match(r'^[a-zA-Z0-9\-_\.]+$', repo_name):
            return False, "저장소명은 영문, 숫자, 하이픈, 언더바, 점만 사용 가능합니다."
        
        return True, "저장소명이 올바릅니다."
    
    def validate_folder_path(self, folder_path):
        """폴더 경로 유효성 검사"""
        if not folder_path:
            return False, "폴더 경로를 입력해주세요."
        
        try:
            normalized_path = os.path.normpath(os.path.expanduser(folder_path))
            
            if os.name == 'nt':  # Windows
                drive, path = os.path.splitdrive(normalized_path)
                if not drive:
                    return False, "Windows에서는 드라이브 문자가 필요합니다 (예: C:\\)"
            
            parent_dir = os.path.dirname(normalized_path)
            if parent_dir and not os.path.exists(parent_dir):
                return False, f"상위 폴더가 존재하지 않습니다: {parent_dir}"
            
            if os.path.exists(normalized_path):
                if not os.access(normalized_path, os.W_OK):
                    return False, "폴더에 쓰기 권한이 없습니다."
            
            return True, "폴더 경로가 올바릅니다."
            
        except Exception as e:
            return False, f"경로 검증 중 오류: {str(e)}"
    
    def validate_repository(self, token, username, repo_name):
        """저장소 존재 및 접근 권한 확인"""
        try:
            headers = {"Authorization": f"token {token}"}
            url = f"https://api.github.com/repos/{username}/{repo_name}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                permissions = repo_data.get('permissions', {})
                if permissions.get('push', False):
                    return True, "저장소 접근 및 업로드 권한이 확인되었습니다."
                else:
                    return False, "저장소에 업로드 권한이 없습니다."
            elif response.status_code == 404:
                return False, "저장소를 찾을 수 없습니다."
            elif response.status_code == 403:
                return False, "저장소 접근 권한이 없습니다."
            else:
                return False, f"저장소 확인 실패 (상태 코드: {response.status_code})"
        except:
            return False, "네트워크 오류로 저장소 확인에 실패했습니다."
    
    def validate_time_format(self, hour, minute):
        """시간 형식 유효성 검사"""
        try:
            hour = int(hour)
            minute = int(minute)
            
            if not (0 <= hour <= 23):
                return False, "시간은 0-23 사이여야 합니다."
            
            if not (0 <= minute <= 59):
                return False, "분은 0-59 사이여야 합니다."
            
            return True, f"시간 설정: {hour:02d}:{minute:02d}"
            
        except ValueError:
            return False, "시간과 분은 숫자여야 합니다."
    
    def validate_file_extensions(self, file_extensions):
        """파일 형식 유효성 검사"""
        if not file_extensions:
            return False, "파일 형식을 입력해주세요."
        
        try:
            # 쉼표로 분리하여 각 확장자 검사
            ext_list = [ext.strip().replace('*.', '').replace('*', '') for ext in file_extensions.split(',')]
            ext_list = [ext for ext in ext_list if ext]  # 빈 문자열 제거
            
            if not ext_list:
                return False, "유효한 파일 형식이 없습니다."
            
            # 각 확장자가 유효한지 검사
            for ext in ext_list:
                if not re.match(r'^[a-zA-Z0-9]+$', ext):
                    return False, f"'{ext}'는 유효하지 않은 파일 형식입니다. (영문, 숫자만 가능)"
            
            return True, f"파일 형식 설정: {', '.join(ext_list)}"
            
        except Exception as e:
            return False, f"파일 형식 검증 중 오류: {str(e)}"
    
    # 🔧 2단계 추가: 프로필별 .env 파일 생성 메서드
    def create_profile_env_file(self, profile_name, token, username, repo_name, 
                               folder_path, upload_mode, schedule_hour=None, 
                               schedule_minute=None, repeat_option="daily", 
                               file_extensions="py,txt,md,json,js,html,css"):
        """프로필별 .env 파일 생성"""
        try:
            print(f"\n🔧 2단계: '{profile_name}' 프로필 생성 시작...")
            
            # 기본 검증 (기존 로직 재사용)
            validations = [
                self.validate_token(token),
                self.validate_username(username),
                self.validate_repo_name(repo_name),
                self.validate_folder_path(folder_path),
                self.validate_file_extensions(file_extensions)
            ]
            
            for is_valid, message in validations:
                if not is_valid:
                    return False, message
            
            # 스케줄 설정 검증 (기존 로직 재사용)
            schedule_config = ""
            if upload_mode in ["schedule", "hybrid"]:
                if schedule_hour is None or schedule_minute is None:
                    return False, "시간 예약 모드에서는 시간을 설정해야 합니다."
                
                time_valid, time_msg = self.validate_time_format(schedule_hour, schedule_minute)
                if not time_valid:
                    return False, time_msg
                
                schedule_config = f"""
# 스케줄 설정
UPLOAD_MODE={upload_mode}
UPLOAD_TIME={schedule_hour:02d}:{schedule_minute:02d}
SCHEDULE_HOUR={schedule_hour}
SCHEDULE_MINUTE={schedule_minute}
REPEAT_OPTION={repeat_option}
"""
            else:
                schedule_config = f"""
# 스케줄 설정
UPLOAD_MODE={upload_mode}
UPLOAD_TIME=00:00
SCHEDULE_HOUR=0
SCHEDULE_MINUTE=0
REPEAT_OPTION={repeat_option}
"""
            
            # 저장소 검증
            repo_valid, repo_message = self.validate_repository(token, username, repo_name)
            if not repo_valid:
                return False, repo_message
            
            # 파일 형식 정리
            ext_list = [ext.strip().replace('*.', '').replace('*', '') for ext in file_extensions.split(',')]
            ext_list = [ext for ext in ext_list if ext]
            clean_file_extensions = ','.join(ext_list)
            
            # 프로필별 .env 파일 내용 생성
            normalized_path = os.path.normpath(folder_path)
            env_filename = f".env_{profile_name}"
            
            env_content = f"""# GitHub 자동 업로드 설정 - {profile_name}
# 생성 시간: {self.get_current_time()}

# GitHub 인증 정보
GITHUB_TOKEN={token}
GITHUB_USERNAME={username}
GITHUB_REPO={repo_name}

# 폴더 설정
WATCH_FOLDER={normalized_path}

# 파일 형식 설정
FILE_EXTENSIONS={clean_file_extensions}

# 기타 설정
BRANCH=main
COMMIT_MESSAGE_PREFIX=Auto-upload:
PROFILE_NAME={profile_name}
{schedule_config}
"""
            
            # .env_별명 파일 저장
            env_file_path = os.path.join(self.project_root, env_filename)
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            print(f"✅ {env_filename} 파일 생성 완료")
            
            # 프로필을 profiles.json에 추가
            profile_added = self.add_profile(profile_name)
            if profile_added:
                print(f"✅ profiles.json에 '{profile_name}' 추가 완료")
            else:
                print(f"ℹ️  '{profile_name}' 프로필이 이미 존재함")
            
            # 현재 .env로도 복사 (기본 동작)
            copy_success, copy_msg = self.copy_profile_to_current_env(profile_name)
            if copy_success:
                print(f"✅ 현재 활성 프로필로 설정 완료")
            
            # 감시할 폴더 생성
            if not os.path.exists(normalized_path):
                os.makedirs(normalized_path)
                folder_created = True
                print(f"📂 감시 폴더 생성: {normalized_path}")
            else:
                folder_created = False
                print(f"📂 기존 폴더 사용: {normalized_path}")
            
            # .gitignore 업데이트
            self.update_gitignore()
            print("🔒 .gitignore 업데이트 완료")
            
            # 성공 메시지 생성
            if upload_mode == "realtime":
                mode_message = "실시간 감시 모드로 설정되었습니다."
            elif upload_mode == "schedule":
                mode_message = f"매일 {schedule_hour:02d}:{schedule_minute:02d}에 업로드됩니다."
            elif upload_mode == "hybrid":
                mode_message = f"실시간 감시 + 매일 {schedule_hour:02d}:{schedule_minute:02d} 업로드로 설정되었습니다."
            else:
                mode_message = "업로드 모드 설정 완료"
            
            success_message = f"""✅ '{profile_name}' 프로필 생성 완료!
📁 프로필 파일: {env_filename}
📁 현재 활성: .env (자동 복사됨)
👀 감시 폴더: {normalized_path}
{f"📂 감시 폴더를 새로 생성했습니다." if folder_created else ""}
⏰ {mode_message}
📄 지원 파일 형식: {', '.join(ext_list)}
🔒 .gitignore에 .env 추가 완료"""
            
            print("🎉 프로필 생성 성공!")
            return True, success_message
            
        except Exception as e:
            print(f"❌ 프로필 생성 실패: {e}")
            return False, f"❌ 프로필 생성 실패: {str(e)}"
    
    # 🔧 2단계 추가: 프로필 전환 메서드
    def copy_profile_to_current_env(self, profile_name):
        """선택한 프로필을 현재 .env로 복사"""
        try:
            source_file = os.path.join(self.project_root, f".env_{profile_name}")
            target_file = self.env_path
            
            if not os.path.exists(source_file):
                return False, f"프로필 파일 '{source_file}'을 찾을 수 없습니다."
            
            # 내용 복사 (PROFILE_NAME 라인 제거)
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # PROFILE_NAME 라인 제거 후 .env에 저장
            lines = content.split('\n')
            filtered_lines = [line for line in lines if not line.startswith('PROFILE_NAME=')]
            
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(filtered_lines))
            
            return True, f"'{profile_name}' 프로필이 현재 활성화되었습니다."
            
        except Exception as e:
            return False, f"프로필 전환 실패: {str(e)}"
    
    # 🔧 2단계 추가: 프로필 정보 조회 메서드
    def get_profile_info(self, profile_name):
        """특정 프로필의 설정 정보 가져오기"""
        try:
            env_file = os.path.join(self.project_root, f".env_{profile_name}")
            if not os.path.exists(env_file):
                return None
            
            info = {}
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        info[key] = value
            
            return info
            
        except Exception as e:
            print(f"프로필 정보 로드 실패: {e}")
            return None
    
    # 🔧 2단계 추가: 프로필 삭제 메서드
    def delete_profile(self, profile_name):
        """프로필 삭제"""
        try:
            # .env_별명 파일 삭제
            env_file = os.path.join(self.project_root, f".env_{profile_name}")
            if os.path.exists(env_file):
                os.remove(env_file)
            
            # profiles.json에서 제거
            profiles = self.get_all_profiles()
            if profile_name in profiles:
                profiles.remove(profile_name)
                self.save_profiles(profiles)
            
            return True, f"'{profile_name}' 프로필이 삭제되었습니다."
            
        except Exception as e:
            return False, f"프로필 삭제 실패: {str(e)}"
    
    # 기존 메서드들 (변경 없음)
    def create_env_file_with_schedule(self, token, username, repo_name, folder_path, 
                                    upload_mode, schedule_hour=None, schedule_minute=None, 
                                    repeat_option="daily", file_extensions="py,txt,md,json,js,html,css"):
        """스케줄링 기능이 포함된 .env 파일 생성 (파일 형식 설정 포함) - 기존 호환성 유지"""
        try:
            # 기본 검증
            validations = [
                self.validate_token(token),
                self.validate_username(username),
                self.validate_repo_name(repo_name),
                self.validate_folder_path(folder_path),
                self.validate_file_extensions(file_extensions)
            ]
            
            for is_valid, message in validations:
                if not is_valid:
                    return False, message
            
            # 스케줄 설정 검증
            schedule_config = ""
            if upload_mode in ["schedule", "hybrid"]:
                if schedule_hour is None or schedule_minute is None:
                    return False, "시간 예약 모드에서는 시간을 설정해야 합니다."
                
                time_valid, time_msg = self.validate_time_format(schedule_hour, schedule_minute)
                if not time_valid:
                    return False, time_msg
                
                schedule_config = f"""
# 스케줄 설정
UPLOAD_MODE={upload_mode}
UPLOAD_TIME={schedule_hour:02d}:{schedule_minute:02d}
SCHEDULE_HOUR={schedule_hour}
SCHEDULE_MINUTE={schedule_minute}
REPEAT_OPTION={repeat_option}
"""
            else:
                schedule_config = f"""
# 스케줄 설정
UPLOAD_MODE={upload_mode}
UPLOAD_TIME=00:00
SCHEDULE_HOUR=0
SCHEDULE_MINUTE=0
REPEAT_OPTION={repeat_option}
"""
            
            # 저장소 검증
            repo_valid, repo_message = self.validate_repository(token, username, repo_name)
            if not repo_valid:
                return False, repo_message
            
            # 파일 형식 정리
            ext_list = [ext.strip().replace('*.', '').replace('*', '') for ext in file_extensions.split(',')]
            ext_list = [ext for ext in ext_list if ext]
            clean_file_extensions = ','.join(ext_list)
            
            # .env 파일 내용 생성
            normalized_path = os.path.normpath(folder_path)
            
            env_content = f"""# GitHub 자동 업로드 설정
# 생성 시간: {self.get_current_time()}

# GitHub 인증 정보
GITHUB_TOKEN={token}
GITHUB_USERNAME={username}
GITHUB_REPO={repo_name}

# 폴더 설정
WATCH_FOLDER={normalized_path}

# 파일 형식 설정
FILE_EXTENSIONS={clean_file_extensions}

# 기타 설정
BRANCH=main
COMMIT_MESSAGE_PREFIX=Auto-upload:
{schedule_config}
"""
            
            # 파일 저장
            with open(self.env_path, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            # 감시할 폴더 생성
            if not os.path.exists(normalized_path):
                os.makedirs(normalized_path)
                folder_created = True
            else:
                folder_created = False
            
            # .gitignore 업데이트
            self.update_gitignore()
            
            # 성공 메시지 생성
            if upload_mode == "realtime":
                mode_message = "실시간 감시 모드로 설정되었습니다."
            elif upload_mode == "schedule":
                mode_message = f"매일 {schedule_hour:02d}:{schedule_minute:02d}에 업로드됩니다."
            elif upload_mode == "hybrid":
                mode_message = f"실시간 감시 + 매일 {schedule_hour:02d}:{schedule_minute:02d} 업로드로 설정되었습니다."
            else:
                mode_message = "업로드 모드 설정 완료"
            
            success_message = f"""✅ .env 파일 생성 완료!
📁 저장 위치: {self.env_path}
👀 감시 폴더: {normalized_path}
{f"📂 감시 폴더를 새로 생성했습니다." if folder_created else ""}
⏰ {mode_message}
📄 지원 파일 형식: {', '.join(ext_list)}
🔒 .gitignore에 .env 추가 완료"""
            
            return True, success_message
            
        except Exception as e:
            return False, f"❌ .env 파일 생성 실패: {str(e)}"
    
    def update_gitignore(self):
        """gitignore 파일 업데이트"""
        gitignore_path = os.path.join(self.project_root, '.gitignore')
        
        gitignore_content = """# Environment Variables
.env
*.env
.env_*
.env.local
.env.production
.env.development

# Profile Management (개인 설정 파일들)
profiles.json
upload_history.json  # 🔧 추가
upload_process.pid

# Security (보안 관련 파일들)
token.txt
secrets/
*.key
*.pem

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db

# Logs
*.log
logs/
"""
        
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
    
    def get_current_time(self):
        """현재 시간 반환"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def load_existing_env(self):
        """기존 .env 파일이 있으면 내용 로드"""
        if os.path.exists(self.env_path):
            try:
                from dotenv import load_dotenv
                load_dotenv(self.env_path)
                return {
                    'token': os.getenv('GITHUB_TOKEN', ''),
                    'username': os.getenv('GITHUB_USERNAME', ''),
                    'repo_name': os.getenv('GITHUB_REPO', ''),
                    'folder_path': os.getenv('WATCH_FOLDER', ''),
                    'file_extensions': os.getenv('FILE_EXTENSIONS', 'py,txt,md,json,js,html,css')
                }
            except:
                return None
        return None