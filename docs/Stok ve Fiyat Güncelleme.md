Stok ve Fiyat Güncelleme (updatePriceAndInventory)
Ürün Stok ve Fiyat Güncellemesi
Trendyol'a aktarılan ve onaylanan ürünlerin fiyat ve stok bilgileri eş zamana yakın güncellenir. Stok ve fiyat bligilerini istek içerisinde ayrı ayrı gönderebilirsiniz.

Stok-fiyat güncelleme işlemlerinde request body içerisinde değişiklik yapmadan aynı isteği tekrar atmanız halinde, sizlere hata mesajı dönecektir. Hata mesajı olarak "15 dakika boyunca aynı isteği tekrarlı olarak atamazsınız!" göreceksiniz. Sadece değişen stok-fiyatlarınızı istek atacak şekilde sistemlerinizi düzeltmeniz gerekmektedir.
Quantity alanında gönderdiğiniz stok , satılabilir stok bilgisidir. Satılabilir stok bilgisi sipariş alındığında ya da tarafınızdan yeniden stok gönderildiğinde güncellenir.
Stok-fiyat update işlemlerinde maksimum 1000 item(sku) güncellemesi yapabilirsiniz.
Ürünleriniz için maksimum 20 Bin adet stok ekleyebilirsiniz.
TOPLU İŞLEM KONTROLU
Bu method kullanarak yaptığınız işlemlerin durumunu getBatchRequestResult üzerinden kontrol etmelisiniz.

POST updatePriceAndInventory
PROD
https://apigw.trendyol.com/integration/inventory/sellers/{sellerId}/products/price-and-inventory
STAGE
https://stageapigw.trendyol.com/integration/inventory/sellers/{sellerId}/products/price-and-inventory
Örnek Servis İsteği

{
  "items": [
    {
      "barcode": "8680000000",
      "quantity": 100,
      "salePrice": 112.85,
      "listPrice": 113.85
    }
  ]
}

Örnek Servis Cevabı

{
    "batchRequestId": "fa75dfd5-6ce6-4730-a09e-97563500000-1529854840"
}