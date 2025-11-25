Ürün Silme
Ürün Silme
Ürünleriniz Trendyol sisteminden kaldırırken bu metod kullanılmaktadır. Tekli ve çoklu ürün silme işlemini desteklemektedir. Onay bekleyen ürünlerinizi ve arşivde bir günden fazla bulunmuş, Trendyol tarafından satışa durdurulmamış onaylı ürünlerinizi silebilirsiniz.

Delete methodunu kullanmanız gerekmektedir.
TOPLU İŞLEM KONTROLU
Ürün silme işlemi sonrasında response içerisinde yer alan batchRequestId ile yaptığınız işleminin durumunu getBatchRequestResult servisi üzerinden kontrol etmeniz gerekmektedir.

DELETE
PROD
https://apigw.trendyol.com/integration/product/sellers/{sellerId}/products
STAGE
https://stageapigw.trendyol.com/integration/product/sellers/{sellerId}/products
Örnek Servis İsteği

{
    "items":[
        {
            "barcode": "test123"
        },
        {
            "barcode": "test456"
        }
    ]
}

Örnek Servis Cevabı

{
    "batchRequestId": "c0bd29e1-003d-455a-9d74-3a00d868ce9d-1678194595"
}