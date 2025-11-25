Trendyol Kategori Listesi (getCategoryTree)
Trendyol Kategori Bilgileri
createProduct V2 servisine yapılacak isteklerde gönderilecek categoryId bilgisi bu servis kullanılarak alınacaktır.

createProduct yapmak için en alt seviyedeki kategori ID bilgisi kullanılmalıdır. Seçtiğiniz kategorinin alt kategorileri var ise bu kategori bilgisi ile ürün aktarımı yapamazsınız.
Yeni kategoriler eklenebileceği sebebiyle güncel kategori listesini haftalık olarak almanızı öneririz.
ipucu
Ürün kategori ağacı belirli aralıklarla güncellenmektedir. Güncel olmayan bir kategori ağacı kullanmanız durumunda eksik veya hatalı veri girişi yapabilirsiniz. Bu sebep ile her işlem öncesinde en güncel kategori ağacını kullanmanız gerekmektedir.

GET getCategoryTree
PROD
https://apigw.trendyol.com/integration/product/product-categories
STAGE
https://stageapigw.trendyol.com/integration/product/product-categories
Örnek Servis Cevabı

              {
                    "id": 1162,
                    "name": "Atkı & Bere & Eldiven",
                    "parentId": 368,
                    "subCategories": [
                        {
                            "id": 382,
                            "name": "Atkı",
                            "parentId": 1162,
                            "subCategories": []
                        },
                        {
                            "id": 1805,
                            "name": "Atkı & Bere & Eldiven Set",
                            "parentId": 1162,
                            "subCategories": []
                        },
                        {
                            "id": 384,
                            "name": "Bere",
                            "parentId": 1162,
                            "subCategories": []
                        },
                        {
                            "id": 962,
                            "name": "Boyunluk",
                            "parentId": 1162,
                            "subCategories": []
                        },
                        {
                            "id": 385,
                            "name": "Eldiven",
                            "parentId": 1162,
                            "subCategories": []
                        }
                    ]
                }
            ...
            ..

Filtre Parametreleri

Parametre	Açıklama
Id	Kategorinin Trendyol sistemindeki ID bilgisi
ParentId	Kategorinin bağlı olduğu bir üst kategori bilgisi
Name	Kategorinin adı
SubCategories	Eğer alt kategori yoksa SubCategories:false olur



