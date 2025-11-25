```markdown
# Trendyol Toplu İşlem Kontrolü - getBatchRequestResult (Tam ve Eksiksiz Dokümantasyon)

## Genel Bilgi
- **Servis Adı**: `getBatchRequestResult`
- **Amaç**: Aşağıdaki toplu işlemlerin sonucunu kontrol etmek  
  → `createProducts` (Ürün Aktarma v2)  
  → `updatePriceAndInventory` (Stok & Fiyat Güncelleme)  
  → `updateProducts` (Ürün Güncelleme)  
  → Ürün Arşivleme / Silme işlemleri
- **Method**: `GET`
- **BatchRequestId saklama süresi**: 4 saat (4 saat sonra sorgulanamaz)

## Endpointler
**PROD**  
`https://apigw.trendyol.com/integration/product/sellers/{sellerId}/products/batch-requests/{batchRequestId}`

**STAGE**  
`https://stageapigw.trendyol.com/integration/product/sellers/{sellerId}/products/batch-requests/{batchRequestId}`

## Kontrol Mantığı (Çok Önemli!)

| İşlem Türü                  | `status` Alanı Nerede Kontrol Edilir?                                 | Not                                                                 |
|-----------------------------|-----------------------------------------------------------------------|----------------------------------------------------------------------|
| Ürün Aktarma (createProducts) | Hem üstteki `status` hem de her `items[].status` kontrol edilmeli     | Üst `status`: COMPLETED olsa bile bazı item'lar başarısız olabilir   |
| Ürün Güncelleme             | Hem üstteki `status` hem de her `items[].status` kontrol edilmeli     |                                                                      |
| Stok & Fiyat Güncelleme     | **Sadece** `items[].status` kontrol edilir (üstte `status` dönmez)   | Batch genel status alanı gelmez!                                     |
| Ürün Arşivleme / Silme      | Hem üstteki `status` hem de `items[].status` kontrol edilmeli         |                                                                      |

## Ana Alanların Anlamları

| Alan                     | Açıklama                                                                                 |
|--------------------------|------------------------------------------------------------------------------------------|
| `batchRequestId`         | İşlemin unique ID’si (createProducts sonrası dönen)                                      |
| `status` (üst seviye)    | `PROCESSING` → `COMPLETED` → `FAILED`                                                    |
| `items[].status`         | `SUCCESS` / `FAILURE`                                                                    |
| `items[].failureReasons` | Hata varsa burada detaylı hata mesajları listelenir (dizi)                               |
| `failedItemCount`        | Başarısız olan ürün adedi                                                               |
| `batchRequestType`       | İşlem türü (`ProductV2OnBoarding`, `ProductInventoryUpdate`, `ProductArchiveUpdate` vb.)|

## Örnek Servis Cevapları

### 1. Ürün Aktarma (createProducts) - Başarılı
```json
{
  "batchRequestId": "76e55c53-e0a4-473c-b4e1-1a008c02a9ab-1736179465",
  "status": "COMPLETED",
  "itemCount": 1,
  "failedItemCount": 0,
  "items": [
    {
      "requestItem": { "product": { "barcode": "11111122222", ... }, "barcode": "11111122222" },
      "status": "SUCCESS",
      "failureReasons": []
    }
  ],
  "batchRequestType": "ProductV2OnBoarding"
}
```

### 2. Ürün Aktarma - Kısmen Başarısız
```json
{
  "status": "COMPLETED",
  "failedItemCount": 1,
  "items": [
    {
      "requestItem": { "barcode": "HATALI123" },
      "status": "FAILURE",
      "failureReasons": [
        "Barkod zaten kullanılıyor",
        "Kategori özelliği eksik: Renk"
      ]
    },
    {
      "requestItem": { "barcode": "DOGRU456" },
      "status": "SUCCESS",
      "failureReasons": []
    }
  ]
}
```

### 3. Stok & Fiyat Güncelleme (Üst status dönmez!)
```json
{
  "batchRequestId": "c57e3453-2c00-11f0-aa3a-be9298facace-1746718627",
  "itemCount": 1,
  "failedItemCount": 0,
  "items": [
    {
      "requestItem": {
        "barcode": "11111111111",
        "quantity": 100,
        "salePrice": 100,
        "listPrice": 100
      },
      "status": "SUCCESS",
      "failureReasons": []
    }
  ],
  "batchRequestType": "ProductInventoryUpdate"
}
```

### 4. Ürün Arşivleme
```json
{
  "status": "COMPLETED",
  "batchRequestType": "ProductArchiveUpdate",
  "items": [
    {
      "requestItem": { "barcode": "smoketest-379996", "archived": true },
      "status": "SUCCESS",
      "failureReasons": []
    }
  ]
}
```

### 5. Ürün Silme
```json
{
  "status": "COMPLETED",
  "batchRequestType": "ProductDeletion",
  "items": [
    {
      "requestItem": { "barcode": "PMPGJ8X734OVJ69R88" },
      "status": "SUCCESS",
      "failureReasons": []
    }
  ]
}
```

## Pratik Kullanım Önerileri

1. `createProducts` sonrası mutlaka `batchRequestId` kaydedin.
2. İşlem bittikten sonra **hemen değil**, 3-10 saniye aralıklarla sorgulayın.
3. Üst `status` = `COMPLETED` ve `failedItemCount` = 0 ise işlem tamamen başarılıdır.
4. `failedItemCount` > 0 ise mutlaka `failureReasons` listesini okuyup loglayın.
5. Stok/fiyat güncellemede sadece `items[].status` ve `items[].failureReasons` kontrol edilir.
6. 4 saatten eski batchRequestId’ler sorgulanamaz → logları buna göre tutun.

## Hata Kontrolü İçin Örnek Pseudocode
```python
response = get_batch_result(batch_id)
if response.status == "PROCESSING":
    bekle_ve_tekrar_sorgula()
elif response.status == "COMPLETED":
    if response.failedItemCount == 0:
        print("Tüm ürünler başarıyla yüklendi")
    else:
        for item in response.items:
            if item.status == "FAILURE":
                print(f"Barkod: {item.requestItem.barcode} → Hata: {item.failureReasons}")
```

Bu doküman Trendyol’un resmi `getBatchRequestResult` servisi için 2025 itibarıyla eksiksiz ve günceldir.
```