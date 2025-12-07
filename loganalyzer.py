import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple, Set, Dict, Optional

class LogAnalyzer:
    
    def __init__(self):
        self.user_data: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set)) # 透過defaultdict簡化init

    def parse_line(self, line: str) -> Tuple[Optional[datetime.date], Optional[str], Optional[str]]:
        """
        解析log
        """
        parts = line.strip().split()
        
        if len(parts) < 3:
            return None, None, None
            
        timestamp_str, page, username = parts[0], parts[1], parts[2]
        
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.date(), page, username
        except ValueError:
            return None, None, None

    def load_logs(self, file_path: str) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    visit_date, page, username = self.parse_line(line)
                    if username and visit_date and page:
                        self.user_data[username][visit_date].add(page)
        except FileNotFoundError:
            print(f"錯誤：找不到檔案 {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"讀取檔案時發生未預期錯誤: {e}")
            sys.exit(1)

    def identify_loyal_customers(self) -> List[str]:
        loyal_customers = []

        for username, dates_map in self.user_data.items():
            sorted_dates = sorted(dates_map.keys()) # 避免日期沒按順序
            
            if len(sorted_dates) < 3: # 至少有三天才可能連續
                continue
            
            for i in range(len(sorted_dates) - 2): # 開長度為3的檢查窗
                day1 = sorted_dates[i]
                day2 = sorted_dates[i+1]
                day3 = sorted_dates[i+2]
                
                if (day2 - day1 == timedelta(days=1)) and (day3 - day2 == timedelta(days=1)): # 確認日期連續

                    # 每天的頁面
                    pages_day1 = dates_map[day1]
                    pages_day2 = dates_map[day2]
                    pages_day3 = dates_map[day3]
                    
                    unique_pages = pages_day1 | pages_day2 | pages_day3 # 三天內所有查看過的頁面
                    
                    if len(unique_pages) > 4: # 三天內查看過超過4個不同頁面
                        loyal_customers.append(username)
                        break 
                        
        return loyal_customers

if __name__ == "__main__":
    target_log_file = "server_mock.log"
    
    print(f"開始分析 {target_log_file}...")
    analyzer = LogAnalyzer()
    analyzer.load_logs(target_log_file)
    print(f"有{len(analyzer.user_data)} 位不重複使用者。")
    print(analyzer.user_data)
    loyal_customer_list = analyzer.identify_loyal_customers()
    print(f"Loyal Customer List (共 {len(loyal_customer_list)} 位):")
    for user in loyal_customer_list:
        print(f" - {user}")