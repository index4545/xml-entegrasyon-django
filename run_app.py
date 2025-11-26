import os
import sys
import threading
import webbrowser
import time
import tkinter as tk
from tkinter import messagebox
from waitress import serve
from django.core.management import call_command
import django
from django.contrib.auth import get_user_model

# PyInstaller console=False hatası için düzeltme (Stdout/Stderr yönlendirme)
class NullWriter:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

# Django ortamını ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def start_server():
    from core.wsgi import application
    serve(application, host='127.0.0.1', port=8000, threads=4)

def open_browser():
    time.sleep(2) # Sunucunun başlaması için bekle
    webbrowser.open('http://127.0.0.1:8000/dashboard/')

def setup_application():
    try:
        # Veritabanı Migrations
        status_label.config(text="Veritabanı güncelleniyor...")
        root.update()
        call_command('migrate', interactive=False)
        
        # Static Files (Eğer gerekirse, ama whitenoise ile exe içine gömülebilir)
        # call_command('collectstatic', interactive=False)

        # Superuser Kontrolü
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            status_label.config(text="Yönetici hesabı oluşturuluyor...")
            root.update()
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            messagebox.showinfo("Kurulum Tamamlandı", "Yönetici Hesabı Oluşturuldu:\nKullanıcı Adı: admin\nŞifre: admin")
        
        status_label.config(text="Uygulama Başlatılıyor...")
        root.update()
        
        # Sunucuyu Thread olarak başlat
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Tarayıcıyı aç
        threading.Thread(target=open_browser).start()
        
        # Pencereyi gizle veya kapat (Sunucu arka planda çalışsın istiyorsak gizle)
        # root.withdraw() 
        # Ancak waitress main thread'i bloklamazsa GUI açık kalabilir.
        # Waitress bloklar. O yüzden thread'e aldık.
        
        status_label.config(text="Uygulama Çalışıyor.\nTarayıcınız açıldı.\nKapatmak için pencereyi kapatın.")
        start_button.config(state='disabled')
        
    except Exception as e:
        messagebox.showerror("Hata", f"Kurulum sırasında hata oluştu:\n{str(e)}")
        status_label.config(text="Hata oluştu.")

# GUI Oluştur
root = tk.Tk()
root.title("XML Entegrasyon Başlatıcı")
root.geometry("400x250")

header = tk.Label(root, text="XML Entegrasyon Paneli", font=("Helvetica", 16, "bold"))
header.pack(pady=20)

info_text = "Bu uygulama yerel sunucuyu başlatacak ve\ntarayıcınızda yönetim panelini açacaktır."
info_label = tk.Label(root, text=info_text, font=("Helvetica", 10))
info_label.pack(pady=10)

status_label = tk.Label(root, text="Hazır", fg="blue")
status_label.pack(pady=5)

start_button = tk.Button(root, text="Uygulamayı Başlat / Kur", command=setup_application, bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"), padx=20, pady=10)
start_button.pack(pady=20)

root.mainloop()
