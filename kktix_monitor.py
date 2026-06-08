from seleniumbase import SB
import time
import random
from datetime import datetime
import requests
import psutil  
import logging      

# ================= 參數設定區 =================
DISCORD_WEBHOOK_URL = ''
EVENT_URL = 'https://kktix.com/events/f385d2b5/registrations/new'
# ==============================================

# ================= 日誌 (Log) 設定區 =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        # 1. 寫入到檔案 (採用 utf-8 編碼避免中文亂碼)
        logging.FileHandler("kktix_bot.log", encoding='utf-8'),
        # 2. 同時輸出到原本的終端機黑色視窗
        logging.StreamHandler()
    ]
)
# =====================================================

def send_discord_notify(message):
    data = {"content": message, "username": "KKTIX 搶票眼線"}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        pass

def main():
    print("啟動 KKTIX 餘票監測系統 (動態計數穩定版)...")
    print("請確保 Discord 有開啟通知聲音！")
    print("-" * 30)

    with SB(uc=True) as sb:

        print("🔧 正在注入記憶體優化設定...")
        
        # 1. 強制禁用網路快取 (最核心防線)
        # 讓每次 F5 都是乾淨的讀取，避免暫存檔越疊越高把 RAM 塞爆
        sb.driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
        
        # 2. 啟動網路攔截功能，阻擋所有圖片載入
        # 網頁還是會正常加載，但圖片會變成破圖或空白，能大幅降低渲染負擔
        sb.driver.execute_cdp_cmd("Network.enable", {})
        sb.driver.execute_cdp_cmd("Network.setBlockedURLs", {
            "urls": ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp", "*.svg"]
        })
        
        print("✅ 優化完成！前往 KKTIX 準備登入...")


        sb.open("https://kktix.com/")
        
        print("\n" + "="*40)
        print("🛑 程式已暫停！")
        print("👉 請在彈出的 Chrome 視窗中，手動點擊右上角完成 KKTIX 登入。")
        print("👉 登入成功後，請回到這個黑色視窗 (PowerShell)，按下鍵盤的 [Enter] 鍵！")
        print("="*40 + "\n")
        
        input() 

        print("🚀 收到確認，開始前往目標頁面並進行基準線測試...")
        sb.open(EVENT_URL)
        
        baseline_sold_out = 0
        while True:
            time.sleep(2) # 等待網頁完全載入
            page_text = sb.get_text("body")
            baseline_sold_out = page_text.count("已售完")
            
            if baseline_sold_out > 0:
                print(f"✅ 基準線設定完成！目前畫面上共有 {baseline_sold_out} 個區域「已售完」。")
                break
            else:
                print("⚠️ 尚未讀取到票種列表，等待重試...")
                sb.refresh()

	# 開始無限迴圈監測
        while True:
            try:
                # 📊 1. 記憶體健康檢查
                memory_usage = psutil.virtual_memory().percent
                if memory_usage > 85:
                    logging.warning(f"記憶體飆高至 {memory_usage}%，進入 30 秒冷卻模式釋放資源...")
                    time.sleep(30)
                
                time.sleep(4) 
                page_text = sb.get_text("body")
                
                if "Verify you are human" in page_text or "cloudflare" in page_text.lower():
                    logging.warning("🛡️ 遇到驗證卡關，請手動點擊！")
                    time.sleep(10)
                    continue

                current_sold_out = page_text.count("已售完")

                # 確保網頁有正常載入 (有 TWD)，且「已售完」數量比基準線少
                if "TWD" in page_text and current_sold_out < baseline_sold_out:
                    msg = f"@everyone @everyone\n🚨 **警告！有區域的「已售完」消失了，可能有餘票釋出！**\n趕快點擊連結搶票：\n{EVENT_URL}"
                    logging.info("🎉 發現餘票狀態改變！通知已發送！")
                    send_discord_notify(msg) 
                    time.sleep(600) 
                else:
                    display_count = current_sold_out if "TWD" in page_text else baseline_sold_out
                    logging.info(f"尚無餘票 (維持 {display_count} 個已售完) | 記憶體: {memory_usage}%，持續監測中...")

            except Exception as e:
                # exc_info=True 會把詳細的錯誤追蹤程式碼一起存進 Log 檔
                logging.error("讀取網頁發生錯誤，稍後重試。", exc_info=True)

            sleep_time = random.randint(6, 12)
            time.sleep(sleep_time)
            sb.refresh()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # 這裡的錯誤是最致命的（例如找不到 Chrome 或驅動程式過期）
        logging.error("發生了致命錯誤導致程式崩潰！", exc_info=True)
        print("\n" + "!"*40)
        print("❌ 程式已崩潰，請查看 kktix_bot.log 檔案了解詳細死因。")
        print("!"*40 + "\n")
        input("按 Enter 鍵結束...")