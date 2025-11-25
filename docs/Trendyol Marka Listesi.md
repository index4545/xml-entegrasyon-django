Trendyol Marka Listesi (getBrands)
Trendyol Marka Bilgileri
createProduct V2 servisine yapılacak isteklerde gönderilecek brandId bilgisi bu servis kullanılarak alınacaktır.

Bir sayfada minumum 1000 adet brand bilgisi alınabilmektedir.
Marka araması yaparken servise page parametresini kullanarak query oluşturmanız gerekmektedir.
GET getBrands
PROD
https://apigw.trendyol.com/integration/product/brands
STAGE
https://stageapigw.trendyol.com/integration/product/brands
Filtre Parametreleri

Parametre	Açıklama
page	Servis cevabınında hangi sayfadaki markaların getirileceği bilgisi
size	Bir servis cevabında yer alacak Marka sayısı
Örnek Servis Cevabı

{
  "brands": [
    {
      "id": 10,
      "name": "TrendyolMilla"
    },
    {
      "id": 19,
      "name": "Milla"
    },
    {
      "id": 20,
      "name": "Trendyol"
    }
    ]
}

GET getBrandsName
BÜYÜK / küçük harf ayrımına dikkat etmelisiniz.
PROD
https://apigw.trendyol.com/integration/product/brands/by-name?name={brand-name}
STAGE
https://stageapigw.trendyol.com/integration/product/brands/by-name?name={brand-name}
Örnek Servis Cevabı

[
  {
    id: 40,
    name: "TRENDYOLMİLLA",
  },
];

Önceki