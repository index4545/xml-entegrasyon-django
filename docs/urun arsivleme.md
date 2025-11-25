Ürün Arşivleme
Ürün Arşivleme (v2/archiveProducts)
Ürünlerinizi Trendyol sisteminde arşivlemek veya arşivden çıkarmak için bu metod kullanılmaktadır. Tekli ve çoklu ürün arşivleme işlemlerini desteklemektedir.

Bu method ile ürün arşivleme işlemi sağlanmadan önce ürünlerinizin Trendyol sisteminde mevcut olması gerekmektedir.
Her bir istek içerisinde gönderilebilecek maksimum item sayısı 1.000'dir.
Arşivlenen ürünler Trendyol'da görünmez hale gelir ancak tamamen silinmez.
Arşivden çıkarılan ürünler tekrar aktif hale gelir.
Arşivlenen ürünlerin durumunu kontrol etmek için ürün listeleme servislerini kullanabilirsiniz. Response'larda archived field'ı bulunmaktadır.
TOPLU İŞLEM KONTROLU
Ürün arşivleme işlemi sonrasında response içerisinde yer alan batchRequestId ile ürünlerinizin ve arşivleme işleminin durumunu getBatchRequestResult servisi üzerinden kontrol etmeniz gerekmektedir.

PUT archiveProducts (Ürün Arşivleme)
PROD
https://apigw.trendyol.com/integration/product/sellers/{sellerId}/products/archive-state
STAGE
https://stageapigw.trendyol.com/integration/product/sellers/{sellerId}/products/archive-state
Parametre Açıklamaları & Kuralları

Parametre	Zorunluluk	Açıklama	Veri Tipi	Max. Karakter Sayısı
items	Evet	Arşivlenecek/arşivden çıkarılacak ürünlerin listesi	Array	-
barcode	Evet	Ürün barkodu. Özel karakter olarak yalnızca "." nokta , "-" tire , "_" alt tire kullanılabilir. Türkçe karakterlerin(ğ, Ğ, Ş, ş, İ, Ü vb) kullanılması uygundur. Barkodunuzun ortasında boşluk varsa birleştirilerek içeri alınır.	string	40
archived	Evet	Arşivleme durumu. true: ürünü arşivle, false: ürünü arşivden çıkar	boolean	-
Örnek Servis İsteği - Ürün Arşivleme

{
  "items": [
    {
      "barcode": "barkod-1234",
      "archived": true
    },
    {
      "barcode": "barkod-5678",
      "archived": true
    }
  ]
}

Örnek Servis İsteği - Ürün Arşivden Çıkarma

{
  "items": [
    {
      "barcode": "barkod-1234",
      "archived": false
    },
    {
      "barcode": "barkod-5678",
      "archived": false
    }
  ]
}

Örnek Servis İsteği - Karışık İşlem (Arşivleme ve Arşivden Çıkarma)

{
  "items": [
    {
      "barcode": "barkod-1234",
      "archived": true
    },
    {
      "barcode": "barkod-5678",
      "archived": false
    },
    {
      "barcode": "barkod-9012",
      "archived": true
    }
  ]
}

Servis Cevapları
Status Code	Açıklama
200	Gönderilen istek başarılı olmuştur. Tarafınıza dönen batchRequestId ile Toplu İşlem Kontrolü Servisine giderek işlem sonucunu görebilirsiniz.
400	URL içerisinde eksik veya hatalı parametre kullanılmaktadır. Dokümanı tekrar inceleyiniz.
401	İstek gönderirken kullandığınız supplierID, API Key, API Secure Key bilgilerinden birisi eksik ya da yanlıştır. Mağazanız için doğru bilgilere Trendyol Satıcı Paneli üzerinden ulaşabilirsiniz.
404	İstek gönderilen url bilgisi hatalıdır. Dokümanı tekrar inceleyiniz.
500	Anlık bir hata yaşanmış olabilir. Bir kaç dakika bekleyerek durumun düzelmemesi durumunda kullanılan endpoint, gönderilen istek ve cevap ile beraber "API Entegrasyon Destek Talebi" başlığından talep oluşturunuz.
Örnek Hata Cevapları
Geçersiz Barkod Hatası:

{
  "errors": [
    {
      "key": "invalid.barcode",
      "message": "Barkod formatı geçersiz",
      "errorCode": "400"
    }
  ]
}

Ürün Bulunamadı Hatası:

{
  "errors": [
    {
      "key": "product.not.found",
      "message": "Ürün sistemde bulunamadı",
      "errorCode": "404"
    }
  ]
}