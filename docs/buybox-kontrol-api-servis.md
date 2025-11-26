Ürün Buybox Kontrol Servisi
Ürün Buybox Kontrol Servisi
Bu servis üzerinden Trendyol'daki ürünlerinizin buybox bilgisini öğrenebilirsiniz. Servis response'unda barcode'ların:

Buybox'taki sırasını
Ürünün buybox fiyatını
Ürünün birden fazla satıcısı olup olmadığı bilgisini elde edebileceksiniz.
Bu servis üzerinden maksimum 10 barcode için sorgu atabilirsiniz. Servis limiti 1000 req/min'dir
POST Ürün Buybox Kontrol Servisi
PROD
https://apigw.trendyol.com/integration/product/sellers/{sellerId}/products/buybox-information
STAGE
https://stageapigw.trendyol.com/integration/product/sellers/{sellerId}/products/buybox-information
Örnek Servis İsteği

{
    "barcodes": [
        "1111111111111",
        "2222222222",
        "3333333333"
    ]
}

Örnek Servis Cevabı

{
  "buyboxInfo": [
    {
      "barcode": "1111111111111",
      "buyboxOrder": 1,
      "buyboxPrice": 600,
      "hasMultipleSeller": false
    },
    {
      "barcode": "2222222222",
      "buyboxOrder": 3,
      "buyboxPrice": 299.9,
      "hasMultipleSeller": true
    },
    {
      "barcode": "3333333333",
      "buyboxOrder": 47,
      "buyboxPrice": 340,
      "hasMultipleSeller": true
    }
  ]
}