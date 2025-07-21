# baekjoon_gui.py - 백준 문제 GUI (백준 코드 + GUI 통합)
import tkinter as tk
from tkinter import messagebox, ttk
import requests
from bs4 import BeautifulSoup
import webbrowser
import threading

class BaekjoonProblemSolver:
    def __init__(self):
        self.root = tk.Tk()
        self.problems = []
        self.current_class = None
        self.setup_ui()
    
    def setup_ui(self):
        self.root.title("📚 백준 문제 풀이 도우미")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # 메인 프레임
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # 제목
        title_label = tk.Label(main_frame, text="📚 백준 solved.ac 문제 풀이", 
                              font=("Arial", 16, "bold"), fg="navy")
        title_label.pack(pady=(0, 20))
        
        # 클래스 입력 섹션
        self.create_class_input_section(main_frame)
        
        # 문제 목록 섹션
        self.create_problem_list_section(main_frame)
        
        # 버튼 섹션
        self.create_button_section(main_frame)
        
        # 상태 표시
        self.status_label = tk.Label(main_frame, text="클래스를 선택해주세요.", 
                                    font=("Arial", 10), fg="blue")
        self.status_label.pack(pady=10)
    
    def create_class_input_section(self, parent):
        # 클래스 입력 프레임
        class_frame = tk.LabelFrame(parent, text="🎓 solved.ac 클래스 선택", 
                                   font=("Arial", 12, "bold"), 
                                   padx=15, pady=15)
        class_frame.pack(fill='x', pady=(0, 20))
        
        # 클래스 선택 설명
        info_label = tk.Label(class_frame, 
                             text="📘 Class 1~10 중에서 선택하세요 (Class 1이 가장 쉽고, Class 10이 가장 어려움)",
                             font=("Arial", 10), fg="gray")
        info_label.pack(anchor='w', pady=(0, 10))
        
        # 클래스 입력 프레임
        input_frame = tk.Frame(class_frame)
        input_frame.pack(anchor='w')
        
        tk.Label(input_frame, text="클래스 번호:", 
                font=("Arial", 11)).pack(side='left', padx=(0, 10))
        
        # 클래스 선택 콤보박스
        self.class_var = tk.StringVar(value="1")
        self.class_combo = ttk.Combobox(input_frame, textvariable=self.class_var,
                                       values=[str(i) for i in range(1, 11)],
                                       width=5, state="readonly")
        self.class_combo.pack(side='left', padx=(0, 10))
        
        # 문제 가져오기 버튼
        self.fetch_btn = tk.Button(input_frame, text="📥 문제 가져오기", 
                                  command=self.fetch_problems_threaded,
                                  bg="lightblue", font=("Arial", 10, "bold"))
        self.fetch_btn.pack(side='left', padx=10)
    
    def create_problem_list_section(self, parent):
        # 문제 목록 프레임
        list_frame = tk.LabelFrame(parent, text="📝 문제 목록", 
                                  font=("Arial", 12, "bold"), 
                                  padx=15, pady=15)
        list_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        # 문제 목록 (Treeview 사용)
        columns = ('번호', '문제ID', '제목')
        self.problem_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 컬럼 설정
        self.problem_tree.heading('번호', text='번호')
        self.problem_tree.heading('문제ID', text='문제 ID')
        self.problem_tree.heading('제목', text='문제 제목')
        
        self.problem_tree.column('번호', width=60, anchor='center')
        self.problem_tree.column('문제ID', width=80, anchor='center')
        self.problem_tree.column('제목', width=400, anchor='w')
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.problem_tree.yview)
        self.problem_tree.configure(yscrollcommand=scrollbar.set)
        
        # 더블클릭 이벤트
        self.problem_tree.bind('<Double-1>', self.on_problem_double_click)
        
        # 패킹
        self.problem_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # 초기 메시지
        self.problem_tree.insert('', 'end', values=('', '', '클래스를 선택하고 문제를 가져오세요!'))
    
    def create_button_section(self, parent):
        button_frame = tk.Frame(parent)
        button_frame.pack(pady=10)
        
        # 문제 풀기 버튼
        self.solve_btn = tk.Button(button_frame, text="🎯 선택한 문제 풀기", 
                                  width=15, height=2,
                                  command=self.solve_selected_problem,
                                  bg="orange", fg="white", 
                                  font=("Arial", 11, "bold"),
                                  state='disabled')
        self.solve_btn.pack(side='left', padx=10)
        
        # 새 문제 가져오기 버튼
        self.refresh_btn = tk.Button(button_frame, text="🔄 새로고침", 
                                    width=12, height=2,
                                    command=self.fetch_problems_threaded,
                                    bg="lightgreen", font=("Arial", 11, "bold"))
        self.refresh_btn.pack(side='left', padx=10)
        
        # 닫기 버튼
        close_btn = tk.Button(button_frame, text="❌ 닫기", 
                             width=12, height=2,
                             command=self.root.quit,
                             bg="lightcoral", font=("Arial", 11, "bold"))
        close_btn.pack(side='left', padx=10)
    
    # ✅ 백준 원본 코드에서 가져온 크롤링 함수
    def fetch_class_problems(self, class_num):
        """solved.ac에서 클래스별 문제 크롤링 (원본 코드 그대로)"""
        url = f"https://solved.ac/class/{class_num}"
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        problems = []

        for row in soup.select("table tbody tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                problem_id = cols[0].text.strip()
                title = cols[1].text.strip()
                problems.append((problem_id, title))

        return problems
    
    def fetch_problems_threaded(self):
        """별도 스레드에서 문제 가져오기 (GUI 블로킹 방지)"""
        thread = threading.Thread(target=self.fetch_problems)
        thread.daemon = True
        thread.start()
    
    def fetch_problems(self):
        """문제 가져오기 메인 로직"""
        try:
            class_num = int(self.class_var.get())
            
            # UI 상태 업데이트
            self.root.after(0, lambda: self.status_label.config(
                text=f"🔍 Class {class_num} 문제를 불러오는 중...", fg="orange"))
            self.root.after(0, lambda: self.fetch_btn.config(state='disabled', text="불러오는 중..."))
            
            # ✅ 백준 원본 함수 호출
            problems = self.fetch_class_problems(class_num)
            
            if problems:
                self.problems = problems
                self.current_class = class_num
                
                # UI 업데이트 (메인 스레드에서 실행)
                self.root.after(0, lambda: self.update_problem_list(problems, class_num))
                self.root.after(0, lambda: self.status_label.config(
                    text=f"✅ Class {class_num} 문제 {len(problems)}개를 불러왔습니다!", fg="green"))
                self.root.after(0, lambda: self.solve_btn.config(state='normal'))
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text="⚠️ 문제를 가져오지 못했습니다.", fg="red"))
            
        except Exception as e:
            error_msg = f"❌ 오류 발생: {str(e)}"
            self.root.after(0, lambda: self.status_label.config(text=error_msg, fg="red"))
            self.root.after(0, lambda: messagebox.showerror("오류", f"문제를 가져오는 중 오류가 발생했습니다:\n{str(e)}"))
        
        finally:
            self.root.after(0, lambda: self.fetch_btn.config(state='normal', text="📥 문제 가져오기"))
    
    def update_problem_list(self, problems, class_num):
        """문제 목록 UI 업데이트"""
        # 기존 항목 삭제
        for item in self.problem_tree.get_children():
            self.problem_tree.delete(item)
        
        # 새 문제 목록 추가
        for idx, (problem_id, title) in enumerate(problems, 1):
            self.problem_tree.insert('', 'end', 
                                   values=(idx, problem_id, title))
    
    def on_problem_double_click(self, event):
        """문제 더블클릭시 문제 풀기"""
        self.solve_selected_problem()
    
    def solve_selected_problem(self):
        """선택한 문제 풀기 (원본 코드의 webbrowser.open 사용)"""
        selected = self.problem_tree.selection()
        if not selected:
            messagebox.showwarning("선택 오류", "문제를 선택해주세요!")
            return
        
        # 선택한 문제 정보 가져오기
        item = self.problem_tree.item(selected[0])
        values = item['values']
        
        if len(values) < 3 or not values[1]:  # 빈 항목 체크
            return
        
        problem_id = values[1]
        title = values[2]
        
        # ✅ 백준 원본 코드의 브라우저 열기 로직
        url = f"https://www.acmicpc.net/problem/{problem_id}"
        
        try:
            # ✅ 원본 코드에서 사용한 webbrowser.open
            webbrowser.open(url)
            
            self.status_label.config(
                text=f"🎯 '{title}' 문제를 브라우저에서 열었습니다!", fg="green")
            
            messagebox.showinfo("문제 열기", 
                               f"문제: {title} (ID: {problem_id})\n"
                               f"브라우저에서 백준 문제 페이지가 열렸습니다!\n\n"
                               f"URL: {url}")
        except Exception as e:
            messagebox.showerror("오류", f"브라우저를 열 수 없습니다: {e}")

# ✅ 백준 원본 코드의 main 함수를 GUI에서 실행
if __name__ == "__main__":
    try:
        app = BaekjoonProblemSolver()
        app.root.mainloop()
    except Exception as e:
        print(f"프로그램 실행 오류: {e}")