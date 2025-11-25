```markdown
# Trendyol Ürün Filtreleme Servisi - filterProducts (Tam ve Eksiksiz Dokümantasyon)

## Genel Bilgi
- **Servis Adı**: `filterProducts`
- **Amaç**: Mağazanızdaki tüm ürünleri (onaylı/onaysız, arşivli, satışta olan vb.) filtreleyerek listelemek
- **Method**: `GET`
- **Maksimum Sayfa Boyutu (size)**: 200 (Trendyol resmi limiti, 200’den büyük kabul edilmez)
- **Maksimum Page Değeri**: 2500 (0’dan başlar, 2499’a kadar gidebilir)
- **Paginasyon**: Zorunlu – tüm ürünleri tek seferde çekemezsiniz!

## Endpointler
**PROD**  
`https://apigw.trendyol.com/integration/product/sellers/{sellerId}/products`

**STAGE**  
`https://stageapigw.trendyol.com/integration/product/sellers/{sellerId}/products`

## Tüm Query Parametreleri (Güncel 2025)

| Parametre              | Tip        | Zorunlu? | Açıklama                                                                                           | Örnek Değer                              |
|-----------------------|------------|----------|----------------------------------------------------------------------------------------------------|------------------------------------------|
| `approved`            | boolean    | Hayır    | Onaylanmış ürünleri getirir → `true`                                                              | `true`                                   |
| `barcode`             | string     | Hayır    | Tek bir barkod sorgusu                                                                             | `BARKOD123`                              |
| `startDate`           | long       | Hayır    | Belirtilen tarihten sonra oluşturulan/güncellenen ürünleri getirir (timestamp ms)                 | `1672527600000` (01.01.2023 00:00)       |
| `endDate`             | long       | Hayır    | Belirtilen tarihe kadar olan ürünleri getirir (timestamp ms)                                      | `1704067199000`                          |
| `dateQueryType`       | string     | Hayır    | `CREATED_DATE` veya `LAST_MODIFIED_DATE` (startDate/endDate ile birlikte zorunlu)                 | `CREATED_DATE`                           |
| `page`                | int        | Hayır    | Sayfalama (0’dan başlar)                                                                           | `0`, `1`, `45`                           |
| `size`                | int        | Hayır    | Bir sayfada getirilecek ürün adedi (maks 200)                                                      | `200` (önerilen)                         |
| `stockCode`           | string     | Hayır    | Kendi stok kodunuza göre filtreleme                                                               | `STK-12345`                              |
| `productMainId`       | string     | Hayır    | Ana ürün koduna (varyant grubu) göre filtreleme                                                    | `ANA-001`                                |
| `archived`            | boolean    | Hayır    | Arşivlenmiş ürünleri getirir → `true`                                                              | `true`                                   |
| `onSale`              | boolean    | Hayır    | Satışta olan (aktif listelenen) ürünleri getirir → `true`                                          | `true`                                   |
| `rejected`            | boolean    | Hayır    | Reddedilmiş ürünleri getirir → `true`                                                              | `true`                                   |
| `blacklisted`         | boolean    | Hayır    | Kara listeye alınmış ürünleri getirir → `true`                                                     | `true`                                   |
| `brandIds`            | array      | Hayır    | Virgülle ayrılmış marka ID’leri (örnek: `brandIds=123,456,789`)                                    | `brandIds=1791,969490`                   |

## En Sık Kullanılan Kombinasyonlar

| İhtiyaç                                   | Kullanılacak Parametreler                                                                 |
|-------------------------------------------|---------------------------------------------------------------------------------------------------|
| Tüm onaylı ve satışta olan ürünleri çek   | `approved=true&onSale=true&size=200&page=0`                                                       |
| Son 7 gündeki değişiklikleri çek          | `startDate=1733956800000&dateQueryType=LAST_MODIFIED_DATE&size=200&page=0`                        |
| Sadece arşivlenmiş ürünleri çek           | `archived=true&size=200&page=0`                                                                   |
| Belirli bir markanın tüm ürünlerini çek  | `brandIds=1791&approved=true&size=200&page=0`                                                     |
| Stok kodu ile tek ürün bul                | `stockCode=STK-12345`                                                                             |
| Reddedilmiş ürünleri bul                  | `rejected=true&size=200&page=0`                                                                   |

## Örnek Servis Cevabı (Kısaltılmış)

```json
{
  "totalElements": 42078,
  "totalPages": 210,
  "page": 0,
  "size": 200,
  "content": [
    {
      "id": "1f8eef1aeef3cbfaad2f0ec207945d9f",
      "barcode": "BARKOD12345",
      "title": "Kadın Elbise Yazlık",
      "productMainId": "ELB-001",
      "stockCode": "STK-ELB001",
      "brand": "TrendyolMilla",
      "brandId": 969490,
      "quantity": 15,
      "listPrice": 499.90,
      "salePrice": 299.90,
      "vatRate": 20,
      "approved": true,
      "archived": false,
      "onSale": true,
      "locked": false,
      "rejected": false,
      "blacklisted": false,
      "dimensionalWeight": 3,
      "categoryName": "Elbise",
      "gender": "Kadın / Kız",
      "color": "Pudra",
      "size": "M",
      "productContentId": 42733553,
      "images": [
        { "url": "https://cdn.trendyol.com/.../image1.jpg" },
        { "url": "https://cdn.trendyol.com/.../image2.jpg" }
      ],
      "attributes": [
        { "attributeId": 47, "attributeName": "Renk", "attributeValue": "Pudra" },
        { "attributeId": 338, "attributeName": "Beden", "attributeValue": "M" }
      ],
      "deliveryOption": {
        "deliveryDuration": 1,
        "fastDeliveryType": "SAME_DAY_SHIPPING"
      },
      "createDateTime": 1698765432000,
      "lastUpdateDate": 1736123456789
    }
    // ... diğer 199 ürün
  ]
}
```

## Pratik Kullanım Önerileri

1. **Her zaman `size=200` kullanın** → maksimum verim.
2. **Tüm ürünleri çekmek için döngü yazın**:
   ```python
   page = 0
   while True:
       response = get(f"...&page={page}&size=200")
       data = response.json()
       if not data["content"]:
           break
       for product in data["content"]:
           process(product)
       page += 1
   ```
3. `totalElements` ve `totalPages` alanlarını loglayarak ilerlemenizi takip edin.
4. Tarih filtrelemesi yapıyorsanız mutlaka `dateQueryType` ekleyin, yoksa çalışmaz!

## Son Kontrol Listesi
- [ ] `size` maksimum 200 mü?
- [ ] Tarih kullanıyorsan `dateQueryType` ekledin mi?
- [ ] `brandIds` birden fazlaysa virgülle ayırdın mı?
- [ ] Tüm sayfaları çekecek paginasyon döngün var mı?
- [ ] Hatalı ürün tespiti için `rejected=true` ve `blacklisted=true` sorguları periyodik çalışıyor mu?

Bu doküman Trendyol’un resmi `filterProducts` servisi için 2025 itibarıyla tam, eksiksiz ve günceldir.
```