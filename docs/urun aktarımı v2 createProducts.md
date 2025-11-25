```markdown
# Trendyol Ürün Aktarma v2 (createProducts) - Tam ve Eksiksiz Dokümantasyon

## Genel Bilgi
- **Servis Adı**: Ürün Aktarımı v2 (`createProducts`)
- **Desteklenen İşlem**: Tekli ve çoklu (toplu) ürün aktarımı
- **Maksimum ürün sayısı (tek istekte)**: 1.000 adet
- **Endpoint (PROD)**:  
  `https://apigw.trendyol.com/integration/product/sellers/{sellerId}/products`
- **Endpoint (STAGE)**:  
  `https://stageapigw.trendyol.com/integration/product/sellers/{sellerId}/products`
- **Method**: `POST`

### Önemli Notlar (Kesinlikle Okuyun)
- Ürün aktarmadan önce mutlaka şu servislerden bilgi alınmalı:
  - Marka listesi → `GET /brands`
  - Kategori ve kategori özellikleri → `GET /categories` ve `GET /category-attributes`
- `fastDeliveryType` kullanılabilmesi için `deliveryOption.deliveryDuration` alanı **1** olmalıdır.
- `stockCode` → Trendyol sisteminde sipariş paketlerinde görünen `merchantSku` değeridir. `getShipmentPackages` servisi ile kontrol edilebilir.
- İşlem tamamlandıktan sonra dönen `batchRequestId` ile mutlaka `getBatchRequestResult` servisi üzerinden toplu işlem sonucu kontrol edilmelidir.

## Parametreler ve Kurallar

| Parametre                | Zorunlu | Açıklama                                                                                              | Veri Tipi       | Max Karakter / Limit                          |
|--------------------------|---------|-------------------------------------------------------------------------------------------------------|-----------------|-----------------------------------------------|
| `barcode`                | Evet    | Özel karakter sadece `.`, `-`, `_` olabilir. Türkçe karakter kullanılabilir. Boşluklar birleştirilir. | string          | 40                                            |
| `title`                  | Evet    | Ürün adı                                                                                              | string          | 100                                           |
| `productMainId`          | Evet    | Satıcı tarafından belirlenen ana ürün kodu (varyantlar için aynı olmalı)                               | string          | 40                                            |
| `brandId`                | Evet    | Trendyol marka ID’si                                                                                  | integer         | -                                             |
| `categoryId`             | Evet    | Trendyol kategori ID’si                                                                               | integer         | -                                             |
| `quantity`               | Evet    | Stok adedi                                                                                            | integer         | -                                             |
| `stockCode`              | Evet    | Tedarikçinin kendi sistemindeki benzersiz stok kodu                                                   | string          | 100                                           |
| `dimensionalWeight`      | Evet    | Desi (hacimsel ağırlık)                                                                               | number          | -                                             |
| `description`            | Evet    | Ürün açıklaması (HTML destekler)                                                                      | string          | 30.000                                        |
| `currencyType`           | Evet    | Para birimi (genelde "TRY")                                                                           | string          | -                                             |
| `listPrice`              | Evet    | Liste fiyatı (PSF - üstü çizilen fiyat)                                                               | number          | -                                             |
| `salePrice`              | Evet    | Satış fiyatı (TSF)                                                                                    | number          | -                                             |
| `vatRate`                | Evet    | KDV oranı (0, 1, 10, 20 gibi)                                                                         | integer         | -                                             |
| `cargoCompanyId`         | Evet    | Trendyol kargo firması ID’si                                                                          | integer         | -                                             |
| `deliveryDuration`       | Hayır   | Sevkiyat süresi (1 = aynı gün / ertesi gün kargo için zorunlu)                                        | integer         | -                                             |
| `fastDeliveryType`       | Hayır   | `SAME_DAY_SHIPPING` veya `FAST_DELIVERY` (deliveryDuration 1 olmalı)                                 | string          | -                                             |
| `images`                 | Evet    | Görsel URL listesi (HTTPS zorunlu, max 8 adet, önerilen boyut: 1200x1800, 96dpi)                       | array of objects| 8 adet görsel                                 |
| `attributes`             | Evet    | Kategoriye özel özellikler (attributeId + attributeValueId veya customAttributeValue)                 | array           | Renk max 50 karakter                          |
| `shipmentAddressId`      | Hayır   | Çoklu depo kullanıyorsanız zorunlu                                                                    | integer         | -                                             |
| `returningAddressId`     | Hayır   | İade depo adresi ID’si                                                                                | integer         | -                                             |
| `lotNumber`              | Hayır   | Parti/Lot/SKT bilgisi (bazı kategorilerde zorunlu olabilir)                                           | string          | 100 (sadece A-Z, 0-9, ",", "-", ".", ":", "/")|

## Varyantlama Kuralları (Çok Önemli!)

- Aynı ürünün farklı varyantları (renk, beden, hafıza vb.) için **`productMainId` aynı olmalı**
- Sadece `attributes` kısmı farklı olmalı
- **Slicer**: Ürünü ayrı içeriklerde açar (genelde renk, bazen hafıza). Kategoride `slicer: true` olan özellikler
- **Varianted**: Aynı içerik üzerinde farklı beden vb. gösterir. Bir kategoride sadece **1 tane** varianter olabilir

## Örnek İstekler

### 1. Tek Ürün (Tek Depo)
```json
{
  "items": [
    {
      "barcode": "BARKOD123",
      "title": "Bebek Takımı Pamuklu 5'li Set",
      "productMainId": "BTK-001",
      "brandId": 1791,
      "categoryId": 411,
      "quantity": 100,
      "stockCode": "STK-001",
      "dimensionalWeight": 2,
      "description": "<p>Pamuklu bebek takımı açıklaması...</p>",
      "currencyType": "TRY",
      "listPrice": 299.90,
      "salePrice": 149.90,
      "vatRate": 20,
      "cargoCompanyId": 10,
      "deliveryOption": {
        "deliveryDuration": 1,
        "fastDeliveryType": "SAME_DAY_SHIPPING"
      },
      "images": [
        { "url": "https://example.com/images/urun1-1.jpg" },
        { "url": "https://example.com/images/urun1-2.jpg" }
      ],
      "attributes": [
        { "attributeId": 338, "attributeValueId": 6980 },
        { "attributeId": 47,  "customAttributeValue": "PUDRA" },
        { "attributeId": 346, "attributeValueId": 4290 }
      ]
    }
  ]
}
```

### 2. Çoklu Depo Kullanıyorsanız (shipmentAddressId zorunlu)
```json
{
  "items": [
    {
      "... aynı alanlar ...",
      "shipmentAddressId": 12345,
      "returningAddressId": 12346
    }
  ]
}
```

### 3. Aynı Ürünün 2 Varyantı (Farklı Renk - Slicer)
```json
{
  "items": [
    {
      "barcode": "BARKOD123-PUDRA",
      "title": "Bebek Takımı Pamuklu",
      "productMainId": "BTK-001",
      "quantity": 50,
      "images": [{ "url": "https://ornek.com/pudra.jpg" }],
      "attributes": [
        { "attributeId": 338, "attributeValueId": 6980 },  // Renk: Pudra
        { "attributeId": 343, "attributeValueId": 4294 }
      ]
    },
    {
      "barcode": "BARKOD123-BEYAZ",
      "title": "Bebek Takımı Pamuklu",
      "productMainId": "BTK-001",
      "quantity": 75,
      "images": [{ "url": "https://ornek.com/beyaz.jpg" }],
      "attributes": [
        { "attributeId": 338, "attributeValueId": 6981 },  // Renk: Beyaz
        { "attributeId": 343, "attributeValueId": 4294 }
      ]
    }
  ]
}
```

## Servis Cevap Kodları

| Status Code | Açıklama                                                                                          |
|-------------|---------------------------------------------------------------------------------------------------|
| 200         | Başarılı. Dönen `batchRequestId` ile `getBatchRequestResult` servisine giderek sonucu kontrol edin |
| 400         | Parametre hatası. Dokümantasyonu tekrar kontrol edin                                              |
| 401         | API kimlik bilgileri yanlış (supplierId, username, password)                                     |
| 404         | Yanlış URL                                                                                        |
| 500         | Sunucu hatası. Birkaç dakika bekleyin, düzelmezse destek talebi açın                             |

## Son Kontrol Listesi (Göndermeden Önce)
- [ ] Marka ID doğru mu?
- [ ] Kategori ID ve attribute’lar doğru mu?
- [ ] Görseller HTTPS ve 1200x1800 mi?
- [ ] Barkod formatı uygun mu? (max 40 karakter, özel karakter kısıtlaması)
- [ ] Varyantlı ürünlerde `productMainId` aynı mı?
- [ ] Hızlı kargo isteniyorsa `deliveryDuration: 1` ve `fastDeliveryType` var mı?
- [ ] Çoklu depo varsa `shipmentAddressId` ve `returningAddressId` ekli mi?
- [ ] İşlem sonrası `batchRequestId` ile sonucu kontrol edecek misiniz?

Bu doküman Trendyol’un resmi v2/createProducts endpoint’i için eksiksiz ve güncel (2025 itibarıyla) referanstır.
```
```