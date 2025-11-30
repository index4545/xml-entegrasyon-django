# XML Entegrasyon ve Trendyol Aktarım Sistemi

Bu sistem, belirtilen XML kaynağından ürünleri çeker ve Trendyol'a aktarılmasını sağlar.

## 📁 Repository
[GitHub Repository](https://github.com/index4545/xml-entegrasyon-django)

## Kurulum ve Çalıştırma

1.  **Sanal Ortamı Aktifleştirin:**
    ```powershell
    .\venv\Scripts\activate
    ```

2.  **Sunucuyu Başlatın:**
    ```powershell
    python manage.py runserver
    ```

3.  **Yönetim Paneline Erişin:**
    *   Tarayıcıda `http://127.0.0.1:8000/admin` adresine gidin.
    *   Kullanıcı adı: `admin`
    *   Şifre: `admin`

## Kullanım Adımları

### 1. Trendyol Ayarlarını Yapılandırma
*   Admin panelinde **Trendyol Ayarları** (Integrations > Trendyol settings) bölümüne gidin.
*   "Add Trendyol settings" butonuna tıklayın.
*   Kullanıcıyı seçin (admin).
*   Trendyol'dan aldığınız **API Key**, **API Secret** ve **Satıcı ID (Supplier ID)** bilgilerini girin.
*   "Aktif" kutucuğunu işaretleyip kaydedin.

### 2. XML'den Ürün Çekme
Ürünleri XML'den çekmek için terminalden şu komutu çalıştırın:
```powershell
python manage.py fetch_xml <TEDARIKCI_ID>
```
*Not: Test tedarikçisinin ID'si muhtemelen 1'dir.*

### 3. Ürünleri Trendyol'a Gönderme
*   Admin panelinde **Ürünler** (Products > Ürünler) bölümüne gidin.
*   Trendyol'a göndermek istediğiniz ürünleri listeden seçin.
*   "Action" (Eylem) menüsünden **"Seçili ürünleri Trendyol'a gönder"** seçeneğini seçin.
*   "Go" butonuna tıklayın.
*   İşlem sonucu ekranın üst kısmında mesaj olarak görünecektir.

## Notlar
*   **Kategori ve Marka Eşleşmesi:** Şu anki entegrasyon, örnek amaçlı sabit Kategori ID ve Marka ID kullanmaktadır. Gerçek kullanımda, ürünlerin kategorilerine göre Trendyol kategori ID'lerinin eşleştirilmesi gerekmektedir.
*   **Otomatik Güncelleme:** `fetch_xml` komutu Windows Görev Zamanlayıcı veya Cron ile belirli aralıklarla çalıştırılarak stok ve fiyat güncellemeleri otomatikleştirilebilir.
