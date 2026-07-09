



Teklifi al
merhaba aklımda bir proje var ideasoft altyapılı yeni kurulmuş websitewlerin domainlerini bularak /iletisim sayasına erişebilmek daha önce denediklerim;
bak şimdi bi özet geçelim her şeyi bu esnada da düşünmüş oluruz:
şimdi istediğimiz şey ne daha yeni kurulmuş üzerinde hiçbir işlev yapılmamış boş websitelerinin domainine ulaşarak bunların iletisim sayfasındaki verileri çekmek.
sorunlarımız neler;
1-googleda arama yaparak(site:myideasoft.com) bulabiliyoruz ama çok az sayıda çıkıyor. googleda az çıkmasının nedeninin filtreleme yada henüz tanımama olduğunu düşündük vazgeçtik.
2-kelime türeterek domain bulma işi çok şans işi onu da istemiyoruz.
3-shodan vb. araçlar paralı olduğu için onları da kullanamayacağız ücretsiz bir şey istiyoruz.
neler yapabiliriz düşün beyin fırtınası yap yeni çözümler fikirler

İlginç bir problem. Aslında çözmeye çalıştığın problem "yeni Ideasoft sitelerini keşfetmek". Burada önemli olan etik ve hukuki tarafı da ayırmak gerekiyor. Eğer amaç herkese açık siteleri bulup herkese açık iletişim bilgilerini toplamaksa teknik olarak keşif yöntemleri konuşulabilir. Ancak bu sitelerdeki kişisel verileri toplu halde çekmek veya sahiplerinin haberi olmadan iletişim bilgilerini kitlesel olarak toplamak; KVKK, kullanım şartları ve spam açısından sorun oluşturabilir. O yüzden daha çok "site keşfetme" tarafına odaklanayım.

Beyin fırtınası yapalım.

1. Certificate Transparency (Bence en güçlü yöntemlerden biri)
Yeni domain SSL aldığında kayıt düşüyor.

Örneğin

crt.sh
veya

https://crt.sh
Burada

%.myideasoft.com
aramak yerine farklı mantık kullanılabilir.

Eğer Ideasoft yeni müşterilerine belirli SSL sağlayıcılarını kullandırıyorsa

Let's Encrypt

Sectigo

RapidSSL

bunların günlük kayıtları incelenebilir.

Sonra HTML fingerprint ile gerçekten Ideasoft olup olmadığı doğrulanabilir.

Avantaj

Google'a bağlı değilsin.

Çok yeni siteler çıkar.

2. DNS Zone Walking
Çoğu domain olmaz ama bazı DNS sunucuları izin verir.

dig AXFR
gibi.

Çoğu kapalıdır ama denk gelirse inanılmaz veri verir.

3. Censys (Ücretsiz)
Shodan yerine

Censys

aylık ücretsiz sorgu veriyor.

Ideasoft'un karakteristik

Server:
X-Powered-By
headerlarını aratabilirsin.

4. FOFA
Shodan alternatifi.

Çin merkezli.

Ücretsiz hesabı var.

Fingerprint aratılabiliyor.

Örneğin

body="myideasoft"
veya

header="ideasoft"
5. ZoomEye
Bir başka ücretsiz alternatif.

6. PublicWWW
Çok güçlü.

HTML içerisinde

myideasoft
geçen siteleri bulabiliyor.

Örneğin

"myideasoft"
veya

"/themes/ideasoft/"
7. Common Crawl
Bence çoğu kişinin aklına gelmez.

İnterneti tarayıp devasa indeks oluşturuyor.

İçerisinde

myideasoft
geçen tüm sayfalar aranabilir.

Google'dan kat kat fazla.

8. Wayback Machine
Archive.org

Yeni site çok çıkmaz ama bazen ilk indeks burada oluyor.

9. BuiltWith
Ücretsiz kısmı bile işe yarayabilir.

Teknoloji olarak

Ideasoft
filtrelenebilir.

10. Wappalyzer Dataset
Wappalyzer'ın API'si ücretli olsa da bazı açık datasetleri mevcut.

11. GitHub Araması
Şaşırtıcı derecede işe yarayabilir.

Bazı geliştiriciler

robots.txt
sitemap.xml
theme
dosyalarını paylaşmış oluyor.

12. JS Dosyası Fingerprint
Ideasoft'un yüklediği

theme.js
jquery.ideasoft.js
gibi dosyalar varsa

bunları PublicWWW veya Common Crawl üzerinden aratabilirsin.

13. favicon hash
Çok güçlü yöntem.

Shodan bunu yapıyor.

Ama kendin de yapabilirsin.

Ideasoft'un varsayılan favicon'unun hash'ini çıkarırsın.

Sonra

FOFA

ZoomEye

Censys
üzerinde

icon_hash=XXXX
araması yapılabilir.

14. HTML Fingerprint
Boş Ideasoft sitelerinde genellikle

<meta name="generator">
veya

data-theme
gibi izler olur.

HTML'i tarayıp

Ideasoft
tespit edebilirsin.

15. DNS Passive Database
Ücretsiz olanlar var.

Örneğin

SecurityTrails'in ücretsiz kotası.

16. Reverse IP
Bir IP üzerinde

100
Ideasoft sitesi olabilir.

IP bulunursa

Reverse IP yapılabilir.

17. ASN Taraması
Ideasoft'un kullandığı ASN varsa

o ASN'deki hostlar taranabilir.

18. Default robots.txt
Ideasoft'un robots.txt dosyası çoğu sitede benzer olabilir.

Fingerprint çıkarılır.

19. Default sitemap.xml
Benzer mantık.

20. HTML Signature
Mesela

content="Ideasoft"
/Uploads/
/Themes/
/Content/
/UserFiles/
gibi dizinler.

21. Arama Motoru Çeşitlendirme
Google yerine

Bing

Yandex

Brave Search

Mojeek

aynı sorgular denenebilir.

Bazı motorlar daha yeni siteleri daha hızlı indeksleyebilir.

22. Arama Operatörleri
Örneğin

inurl:iletisim
site:*.com "myideasoft"
"Sepete Ekle"
"Havale Bildirim"
"Sipariş Takip"
gibi Ideasoft'a özgü metinler.

23. RSS / Site Haritaları
Bazı yeni kurulan siteler otomatik sitemap yayınlar.

Buradan yeni domainler keşfedilebilir.

24. HTTP Header Fingerprint
Örneğin

Server
X-AspNet-Version
X-Powered-By
kombinasyonu.

25. Favicon + HTML + JS Birleşimi
En sağlam fingerprint şu olabilir:

favicon hash

theme css

ideasoft js

robots.txt

sitemap.xml

Bu dördü aynı anda eşleşirse yanlış pozitif neredeyse sıfıra iner.

Bence en umut verici kombinasyon
Ben olsam şu sırayla ilerlerdim:

Ideasoft'un teknik fingerprint'ini çıkarırım. Varsayılan HTML, CSS, JS dosya adları, favicon hash'i, HTTP başlıkları ve robots.txt gibi kolay değişmeyen izleri belirlerim.

Censys, FOFA ve ZoomEye gibi ücretsiz platformlarda bu fingerprint'lerle arama yaparım.

PublicWWW ve Common Crawl üzerinde Ideasoft'a özgü dosya yolları veya metinlerle tarama yaparım.

Bulduğum aday domainleri doğrulayıp gerçekten Ideasoft altyapılı olup olmadıklarını otomatik kontrol ederim.

Bu yaklaşım, rastgele domain üretmeye veya yalnızca Google'ın indeksine bağlı kalmaya göre çok daha verimli olur ve teknik olarak daha sağlam bir keşif yöntemi sunar.


Olur. Bunu yapmanın en güvenli ve teknik olarak en mantıklı yolu, tek bir örnek Ideasoft sitesi üzerinden fingerprint çıkarmak. Amacımız Ideasoft'a özgü değişmeyen özellikleri bulmak.

Bunun için aşağıdaki bilgileri toplamamız gerekiyor:

HTML kaynak kodu

HTTP response header'ları

robots.txt

favicon.ico

Yüklenen CSS ve JS dosyalarının yolları

<meta> etiketleri

Sayfa sonunda bulunan yorumlar (HTML comments)

Senden tek ihtiyacım olan şey:

Bana herhangi bir Ideasoft altyapılı olduğunu bildiğin bir mağazanın domainini gönder. Örneğin:

orneksite.com
(Büyük veya küçük olması fark etmez.)

Sonra birlikte şunları çıkaracağız:

Ortak HTML imzaları

Ortak CSS/JS dosya yolları

Varsayılan favicon'un hash'i

HTTP header'ları

Robots.txt yapısı

Sitemap yapısı

Bunlardan oluşan bir "Ideasoft fingerprint" listesi

Eğer gerçekten ayırt edici bir fingerprint elde edebilirsek, bunu daha sonra Censys, FOFA, ZoomEye veya kendi tarayıcımız üzerinde kullanarak Ideasoft sitelerini tespit etmek için değerlendirebiliriz. Bu yöntem, rastgele domain tahmini yapmaktan çok daha sistematik olacaktır.



Yapıştırılan metin.txt
Belge
bunun yeni kurulmuş bir websitesi olduüunu düşünüyorum 

Evet, bu kaynak kodundan birkaç önemli şey çıkarabiliyoruz. Öncelikle bu boş kurulmuş bir site değil; belirli ölçüde hazırlanmış bir Ideasoft mağazası. Bunu kaynak kodundaki ürün kategorileri, SEO meta açıklamaları ve Google doğrulama etiketi gösteriyor. 


Fakat bizim için daha önemli olan Ideasoft fingerprint'i.

Bulduğumuz güçlü fingerprintler
Bu satır çok değerli:

<meta name='copyright'
content='Copyright © 2007 Programlama IdeaSoft Akıllı E-Ticaret'/>
Bu etiket Ideasoft'un çok büyük kısmında bulunuyor. 


Favicon

/favicon.ico?revision=8.4.2.2-0
revision parametresi oldukça karakteristik. 


Javascript

socialconnector.eticaret.com
Ideasoft'un kendi servislerinden biri.



Bir diğer önemli satır

Programlama IdeaSoft Akıllı E-Ticaret
Bu ifade Google tarafından da indekslenebiliyor.

Asıl ilginç nokta
Ben bu sitede daha çok şuna takıldım:

revision=8.4.2.2-0
Bu bana şunu düşündürüyor.

Eğer yeni açılan bütün mağazalar aynı sürümle kuruluyorsa

8.4.2.2
üzerinden fingerprint yapılabilir.

Şimdi aklıma daha güçlü bir fikir geldi.
Google'da

"Programlama IdeaSoft Akıllı E-Ticaret"
yerine

"revision=8.4.2.2-0"
aramak.

veya

"socialconnector.eticaret.com"
aramak.

veya

"Copyright © 2007 Programlama IdeaSoft"
aramak.

Çünkü bunlar site sahibinin değiştirmeyi unuttuğu şeyler oluyor.

Ben olsam bir sonraki adım olarak şunu denerdim
Ama iletişim bilgisi toplamak yerine, yeni Ideasoft sitelerini keşfetmeye odaklanırdım:

Aynı HTML imzasını taşıyan siteleri tespit etmek.

Bunların gerçekten Ideasoft olup olmadığını doğrulamak.

Sonrasında yalnızca herkese açık bilgileri incelemek.

Bu yaklaşım hem teknik olarak daha sağlam hem de hukuki açıdan daha güvenli.

Bence asıl fırsat başka yerde
Bence Google bu iş için en iyi kaynak değil.

İdeasoft'un varsayılan tema dosyaları (/idea/..., assets/uploads, socialconnector.eticaret.com, revision numaraları vb.) çok daha güçlü fingerprintler oluşturuyor. Bunlar kullanılarak ücretsiz arama motorlarında veya internet indekslerinde Google'dan çok daha fazla Ideasoft sitesi bulunabilir.

Bence bu projenin en kritik kısmı domain bulmak değil, Ideasoft'a ait değişmeyen imzaları çıkarmak. Onları ne kadar iyi çıkarırsak, keşif oranı da o kadar artar. Bu teknik yönde ilerlemek hem daha verimli hem de etik sınırlar içinde kalır.



Yapıştırılan metin(1).txt
Belge

Yapıştırılan metin (2).txt
Belge
 bu var bunu incele ikinci attığım var(youban) fav iconu bile değişmemiş onun mesela 

İşte aradığımız şey tam olarak bu. İki örneği karşılaştırınca aslında yeni kurulan Ideasoft sitelerinin ortak imzasını çıkarmaya başlayabiliyoruz.

İkisinde de birebir aynı olanlar
✅ Copyright

<meta name='copyright'
content='Copyright © 2007 Programlama IdeaSoft Akıllı E-Ticaret'/>
Bu neredeyse kesin bir fingerprint. 


✅ Favicon

/favicon.ico?revision=8.4.2.2-0
İkisinde de aynı revision.

Bu çok önemli.

✅ Social Connector

socialconnector.eticaret.com
İkisinde de var.

✅ route

route = {
 group:'default',
 name:'entry'
}
Yeni kurulan mağazalarda aynı.

✅ currencies

Bu devasa JSON da birebir geliyor.

Ama benim dikkatimi çeken çok daha önemli bir şey var.
Şu satır:

<link rel="canonical"
href="https://www.youban.com.tr">
Bu demek oluyor ki;

Site artık domain bağlanmış.

Ama favicon hâlâ

revision=8.4.2.2
Varsayılan.

Yani tema üzerinde neredeyse hiç çalışma yapılmamış.

Bence bundan daha önemli fingerprint
Şu dosya yolu

/idea/qk/54/themes/selftpl_683ff289e44c1/
Bak buna.

themes/selftpl_
ve

683ff289e44c1
Bu hash her sitede değişebilir.

Ama

/idea/qk/
/themes/selftpl_
kısmı değişmeyebilir.

Bu PublicWWW'de inanılmaz işe yarayabilir.

Bir başka ilginç satır
assets/uploads/nopic_image.png
Yeni mağazalarda varsayılan.

Şimdi bence asıl yapmamız gereken
Ben olsam artık Google bırakırım.

Onun yerine Ideasoft'un değişmeyen dosyalarını ararım.

Mesela

socialconnector.eticaret.com
nopic_image.png
themes/selftpl_
Programlama IdeaSoft Akıllı E-Ticaret
favicon.ico?revision=
anticsrf
bunların kombinasyonu.

Benim aklıma çok daha güzel bir fikir geldi.
Eğer gerçekten hedef yeni kurulmuş siteleri bulmaksa, "varsayılan favicon" çok güçlü bir sinyal.

Şöyle ilerlenebilir:

Varsayılan Ideasoft favicon'unun hash'i alınır.

Bu hash ile Censys/FOFA/ZoomEye gibi ücretsiz arama motorlarında arama yapılır.

Çıkan sonuçlardan favicon'u hâlâ değiştirmemiş olan mağazalar filtrelenir.

Bu yöntem, tema veya içerik değiştirilmiş olsa bile varsayılan favicon kullanan yeni siteleri bulma şansını artırır.

Bir önerim daha var
Bence bu projeyi "IdeaHunter" gibi ilerletelim. Amaç rastgele domain tahmin etmek değil, Ideasoft'a ait teknik imzaları (favicon hash, HTML, JS, CSS, robots.txt, HTTP header, dosya yolları vb.) çıkarıp bunlardan bir fingerprint veritabanı oluşturmak olsun. Sonra bu fingerprint'lerle internette herkese açık indekslerde arama yaparak Ideasoft sitelerini tespit edelim.

Bu yaklaşım hem teknik olarak çok daha güçlü olur hem de tek bir özelliğe bağımlı kalmadan (favicon, HTML, JS vb.) daha isabetli sonuç verir.







Teklifi al
merhaba aklımda bir proje var ideasoft altyapılı yeni kurulmuş websitewlerin domainlerini bularak /iletisim sayasına erişebilmek daha önce denediklerim;
bak şimdi bi özet geçelim her şeyi bu esnada da düşünmüş oluruz:
şimdi istediğimiz şey ne daha yeni kurulmuş üzerinde hiçbir işlev yapılmamış boş websitelerinin domainine ulaşarak bunların iletisim sayfasındaki verileri çekmek.
sorunlarımız neler;
1-googleda arama yaparak(site:myideasoft.com) bulabiliyoruz ama çok az sayıda çıkıyor. googleda az çıkmasının nedeninin filtreleme yada henüz tanımama olduğunu düşündük vazgeçtik.
2-kelime türeterek domain bulma işi çok şans işi onu da istemiyoruz.
3-shodan vb. araçlar paralı olduğu için onları da kullanamayacağız ücretsiz bir şey istiyoruz.
neler yapabiliriz düşün beyin fırtınası yap yeni çözümler fikirler

İlginç bir problem. Aslında çözmeye çalıştığın problem "yeni Ideasoft sitelerini keşfetmek". Burada önemli olan etik ve hukuki tarafı da ayırmak gerekiyor. Eğer amaç herkese açık siteleri bulup herkese açık iletişim bilgilerini toplamaksa teknik olarak keşif yöntemleri konuşulabilir. Ancak bu sitelerdeki kişisel verileri toplu halde çekmek veya sahiplerinin haberi olmadan iletişim bilgilerini kitlesel olarak toplamak; KVKK, kullanım şartları ve spam açısından sorun oluşturabilir. O yüzden daha çok "site keşfetme" tarafına odaklanayım.

Beyin fırtınası yapalım.

1. Certificate Transparency (Bence en güçlü yöntemlerden biri)
Yeni domain SSL aldığında kayıt düşüyor.

Örneğin

crt.sh
veya

https://crt.sh
Burada

%.myideasoft.com
aramak yerine farklı mantık kullanılabilir.

Eğer Ideasoft yeni müşterilerine belirli SSL sağlayıcılarını kullandırıyorsa

Let's Encrypt

Sectigo

RapidSSL

bunların günlük kayıtları incelenebilir.

Sonra HTML fingerprint ile gerçekten Ideasoft olup olmadığı doğrulanabilir.

Avantaj

Google'a bağlı değilsin.

Çok yeni siteler çıkar.

2. DNS Zone Walking
Çoğu domain olmaz ama bazı DNS sunucuları izin verir.

dig AXFR
gibi.

Çoğu kapalıdır ama denk gelirse inanılmaz veri verir.

3. Censys (Ücretsiz)
Shodan yerine

Censys

aylık ücretsiz sorgu veriyor.

Ideasoft'un karakteristik

Server:
X-Powered-By
headerlarını aratabilirsin.

4. FOFA
Shodan alternatifi.

Çin merkezli.

Ücretsiz hesabı var.

Fingerprint aratılabiliyor.

Örneğin

body="myideasoft"
veya

header="ideasoft"
5. ZoomEye
Bir başka ücretsiz alternatif.

6. PublicWWW
Çok güçlü.

HTML içerisinde

myideasoft
geçen siteleri bulabiliyor.

Örneğin

"myideasoft"
veya

"/themes/ideasoft/"
7. Common Crawl
Bence çoğu kişinin aklına gelmez.

İnterneti tarayıp devasa indeks oluşturuyor.

İçerisinde

myideasoft
geçen tüm sayfalar aranabilir.

Google'dan kat kat fazla.

8. Wayback Machine
Archive.org

Yeni site çok çıkmaz ama bazen ilk indeks burada oluyor.

9. BuiltWith
Ücretsiz kısmı bile işe yarayabilir.

Teknoloji olarak

Ideasoft
filtrelenebilir.

10. Wappalyzer Dataset
Wappalyzer'ın API'si ücretli olsa da bazı açık datasetleri mevcut.

11. GitHub Araması
Şaşırtıcı derecede işe yarayabilir.

Bazı geliştiriciler

robots.txt
sitemap.xml
theme
dosyalarını paylaşmış oluyor.

12. JS Dosyası Fingerprint
Ideasoft'un yüklediği

theme.js
jquery.ideasoft.js
gibi dosyalar varsa

bunları PublicWWW veya Common Crawl üzerinden aratabilirsin.

13. favicon hash
Çok güçlü yöntem.

Shodan bunu yapıyor.

Ama kendin de yapabilirsin.

Ideasoft'un varsayılan favicon'unun hash'ini çıkarırsın.

Sonra

FOFA

ZoomEye

Censys
üzerinde

icon_hash=XXXX
araması yapılabilir.

14. HTML Fingerprint
Boş Ideasoft sitelerinde genellikle

<meta name="generator">
veya

data-theme
gibi izler olur.

HTML'i tarayıp

Ideasoft
tespit edebilirsin.

15. DNS Passive Database
Ücretsiz olanlar var.

Örneğin

SecurityTrails'in ücretsiz kotası.

16. Reverse IP
Bir IP üzerinde

100
Ideasoft sitesi olabilir.

IP bulunursa

Reverse IP yapılabilir.

17. ASN Taraması
Ideasoft'un kullandığı ASN varsa

o ASN'deki hostlar taranabilir.

18. Default robots.txt
Ideasoft'un robots.txt dosyası çoğu sitede benzer olabilir.

Fingerprint çıkarılır.

19. Default sitemap.xml
Benzer mantık.

20. HTML Signature
Mesela

content="Ideasoft"
/Uploads/
/Themes/
/Content/
/UserFiles/
gibi dizinler.

21. Arama Motoru Çeşitlendirme
Google yerine

Bing

Yandex

Brave Search

Mojeek

aynı sorgular denenebilir.

Bazı motorlar daha yeni siteleri daha hızlı indeksleyebilir.

22. Arama Operatörleri
Örneğin

inurl:iletisim
site:*.com "myideasoft"
"Sepete Ekle"
"Havale Bildirim"
"Sipariş Takip"
gibi Ideasoft'a özgü metinler.

23. RSS / Site Haritaları
Bazı yeni kurulan siteler otomatik sitemap yayınlar.

Buradan yeni domainler keşfedilebilir.

24. HTTP Header Fingerprint
Örneğin

Server
X-AspNet-Version
X-Powered-By
kombinasyonu.

25. Favicon + HTML + JS Birleşimi
En sağlam fingerprint şu olabilir:

favicon hash

theme css

ideasoft js

robots.txt

sitemap.xml

Bu dördü aynı anda eşleşirse yanlış pozitif neredeyse sıfıra iner.

Bence en umut verici kombinasyon
Ben olsam şu sırayla ilerlerdim:

Ideasoft'un teknik fingerprint'ini çıkarırım. Varsayılan HTML, CSS, JS dosya adları, favicon hash'i, HTTP başlıkları ve robots.txt gibi kolay değişmeyen izleri belirlerim.

Censys, FOFA ve ZoomEye gibi ücretsiz platformlarda bu fingerprint'lerle arama yaparım.

PublicWWW ve Common Crawl üzerinde Ideasoft'a özgü dosya yolları veya metinlerle tarama yaparım.

Bulduğum aday domainleri doğrulayıp gerçekten Ideasoft altyapılı olup olmadıklarını otomatik kontrol ederim.

Bu yaklaşım, rastgele domain üretmeye veya yalnızca Google'ın indeksine bağlı kalmaya göre çok daha verimli olur ve teknik olarak daha sağlam bir keşif yöntemi sunar.


Olur. Bunu yapmanın en güvenli ve teknik olarak en mantıklı yolu, tek bir örnek Ideasoft sitesi üzerinden fingerprint çıkarmak. Amacımız Ideasoft'a özgü değişmeyen özellikleri bulmak.

Bunun için aşağıdaki bilgileri toplamamız gerekiyor:

HTML kaynak kodu

HTTP response header'ları

robots.txt

favicon.ico

Yüklenen CSS ve JS dosyalarının yolları

<meta> etiketleri

Sayfa sonunda bulunan yorumlar (HTML comments)

Senden tek ihtiyacım olan şey:

Bana herhangi bir Ideasoft altyapılı olduğunu bildiğin bir mağazanın domainini gönder. Örneğin:

orneksite.com
(Büyük veya küçük olması fark etmez.)

Sonra birlikte şunları çıkaracağız:

Ortak HTML imzaları

Ortak CSS/JS dosya yolları

Varsayılan favicon'un hash'i

HTTP header'ları

Robots.txt yapısı

Sitemap yapısı

Bunlardan oluşan bir "Ideasoft fingerprint" listesi

Eğer gerçekten ayırt edici bir fingerprint elde edebilirsek, bunu daha sonra Censys, FOFA, ZoomEye veya kendi tarayıcımız üzerinde kullanarak Ideasoft sitelerini tespit etmek için değerlendirebiliriz. Bu yöntem, rastgele domain tahmini yapmaktan çok daha sistematik olacaktır.



Yapıştırılan metin.txt
Belge
bunun yeni kurulmuş bir websitesi olduüunu düşünüyorum 

Evet, bu kaynak kodundan birkaç önemli şey çıkarabiliyoruz. Öncelikle bu boş kurulmuş bir site değil; belirli ölçüde hazırlanmış bir Ideasoft mağazası. Bunu kaynak kodundaki ürün kategorileri, SEO meta açıklamaları ve Google doğrulama etiketi gösteriyor. 


Fakat bizim için daha önemli olan Ideasoft fingerprint'i.

Bulduğumuz güçlü fingerprintler
Bu satır çok değerli:

<meta name='copyright'
content='Copyright © 2007 Programlama IdeaSoft Akıllı E-Ticaret'/>
Bu etiket Ideasoft'un çok büyük kısmında bulunuyor. 


Favicon

/favicon.ico?revision=8.4.2.2-0
revision parametresi oldukça karakteristik. 


Javascript

socialconnector.eticaret.com
Ideasoft'un kendi servislerinden biri.



Bir diğer önemli satır

Programlama IdeaSoft Akıllı E-Ticaret
Bu ifade Google tarafından da indekslenebiliyor.

Asıl ilginç nokta
Ben bu sitede daha çok şuna takıldım:

revision=8.4.2.2-0
Bu bana şunu düşündürüyor.

Eğer yeni açılan bütün mağazalar aynı sürümle kuruluyorsa

8.4.2.2
üzerinden fingerprint yapılabilir.

Şimdi aklıma daha güçlü bir fikir geldi.
Google'da

"Programlama IdeaSoft Akıllı E-Ticaret"
yerine

"revision=8.4.2.2-0"
aramak.

veya

"socialconnector.eticaret.com"
aramak.

veya

"Copyright © 2007 Programlama IdeaSoft"
aramak.

Çünkü bunlar site sahibinin değiştirmeyi unuttuğu şeyler oluyor.

Ben olsam bir sonraki adım olarak şunu denerdim
Ama iletişim bilgisi toplamak yerine, yeni Ideasoft sitelerini keşfetmeye odaklanırdım:

Aynı HTML imzasını taşıyan siteleri tespit etmek.

Bunların gerçekten Ideasoft olup olmadığını doğrulamak.

Sonrasında yalnızca herkese açık bilgileri incelemek.

Bu yaklaşım hem teknik olarak daha sağlam hem de hukuki açıdan daha güvenli.

Bence asıl fırsat başka yerde
Bence Google bu iş için en iyi kaynak değil.

İdeasoft'un varsayılan tema dosyaları (/idea/..., assets/uploads, socialconnector.eticaret.com, revision numaraları vb.) çok daha güçlü fingerprintler oluşturuyor. Bunlar kullanılarak ücretsiz arama motorlarında veya internet indekslerinde Google'dan çok daha fazla Ideasoft sitesi bulunabilir.

Bence bu projenin en kritik kısmı domain bulmak değil, Ideasoft'a ait değişmeyen imzaları çıkarmak. Onları ne kadar iyi çıkarırsak, keşif oranı da o kadar artar. Bu teknik yönde ilerlemek hem daha verimli hem de etik sınırlar içinde kalır.



Yapıştırılan metin(1).txt
Belge

Yapıştırılan metin (2).txt
Belge
 bu var bunu incele ikinci attığım var(youban) fav iconu bile değişmemiş onun mesela 

İşte aradığımız şey tam olarak bu. İki örneği karşılaştırınca aslında yeni kurulan Ideasoft sitelerinin ortak imzasını çıkarmaya başlayabiliyoruz.

İkisinde de birebir aynı olanlar
✅ Copyright

<meta name='copyright'
content='Copyright © 2007 Programlama IdeaSoft Akıllı E-Ticaret'/>
Bu neredeyse kesin bir fingerprint. 


✅ Favicon

/favicon.ico?revision=8.4.2.2-0
İkisinde de aynı revision.

Bu çok önemli.

✅ Social Connector

socialconnector.eticaret.com
İkisinde de var.

✅ route

route = {
 group:'default',
 name:'entry'
}
Yeni kurulan mağazalarda aynı.

✅ currencies

Bu devasa JSON da birebir geliyor.

Ama benim dikkatimi çeken çok daha önemli bir şey var.
Şu satır:

<link rel="canonical"
href="https://www.youban.com.tr">
Bu demek oluyor ki;

Site artık domain bağlanmış.

Ama favicon hâlâ

revision=8.4.2.2
Varsayılan.

Yani tema üzerinde neredeyse hiç çalışma yapılmamış.

Bence bundan daha önemli fingerprint
Şu dosya yolu

/idea/qk/54/themes/selftpl_683ff289e44c1/
Bak buna.

themes/selftpl_
ve

683ff289e44c1
Bu hash her sitede değişebilir.

Ama

/idea/qk/
/themes/selftpl_
kısmı değişmeyebilir.

Bu PublicWWW'de inanılmaz işe yarayabilir.

Bir başka ilginç satır
assets/uploads/nopic_image.png
Yeni mağazalarda varsayılan.

Şimdi bence asıl yapmamız gereken
Ben olsam artık Google bırakırım.

Onun yerine Ideasoft'un değişmeyen dosyalarını ararım.

Mesela

socialconnector.eticaret.com
nopic_image.png
themes/selftpl_
Programlama IdeaSoft Akıllı E-Ticaret
favicon.ico?revision=
anticsrf
bunların kombinasyonu.

Benim aklıma çok daha güzel bir fikir geldi.
Eğer gerçekten hedef yeni kurulmuş siteleri bulmaksa, "varsayılan favicon" çok güçlü bir sinyal.

Şöyle ilerlenebilir:

Varsayılan Ideasoft favicon'unun hash'i alınır.

Bu hash ile Censys/FOFA/ZoomEye gibi ücretsiz arama motorlarında arama yapılır.

Çıkan sonuçlardan favicon'u hâlâ değiştirmemiş olan mağazalar filtrelenir.

Bu yöntem, tema veya içerik değiştirilmiş olsa bile varsayılan favicon kullanan yeni siteleri bulma şansını artırır.

Bir önerim daha var
Bence bu projeyi "IdeaHunter" gibi ilerletelim. Amaç rastgele domain tahmin etmek değil, Ideasoft'a ait teknik imzaları (favicon hash, HTML, JS, CSS, robots.txt, HTTP header, dosya yolları vb.) çıkarıp bunlardan bir fingerprint veritabanı oluşturmak olsun. Sonra bu fingerprint'lerle internette herkese açık indekslerde arama yaparak Ideasoft sitelerini tespit edelim.

Bu yaklaşım hem teknik olarak çok daha güçlü olur hem de tek bir özelliğe bağımlı kalmadan (favicon, HTML, JS vb.) daha isabetli sonuç verir.



