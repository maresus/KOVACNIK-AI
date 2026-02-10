# Brand-specific configuration constants (Kovačnik)
# NOTE: Keep this file free of business logic.

BRAND_ID = "kovacnik"
DISPLAY_NAME = "Domačija Kovačnik"

FARM_INFO = {
    "name": "Turistična kmetija Kovačnik",
    "address": "Planica 9, 2313 Fram",
    "phone": "02 601 54 00",
    "mobile": "031 330 113",
    "email": "info@kovacnik.com",
    "website": "www.kovacnik.com",
    "location_description": "Na pohorski strani, nad Framom, približno 15 min iz doline",
    "parking": "Brezplačen parking ob hiši za 10+ avtomobilov",
    "directions": {
        "from_maribor": (
            "Iz avtoceste A1 (smer Maribor/Ljubljana) izvoz Fram. Pri semaforju v Framu proti cerkvi sv. Ane, "
            "naravnost skozi vas proti Kopivniku. V Kopivniku na glavni cesti zavijete desno (tabla Kmetija Kovačnik) "
            "in nadaljujete še približno 10 minut. Od cerkve v Framu do kmetije je slabih 15 minut."
        ),
        "coordinates": "46.5234, 15.6123",
    },
    "opening_hours": {
        "restaurant": "Sobota in nedelja 12:00-20:00 (zadnji prihod na kosilo 15:00)",
        "rooms": "Sobe: prijava 14:00, odjava 10:00 (pon/torki kuhinja zaprta)",
        "shop": "Po dogovoru ali spletna trgovina 24/7",
        "closed": "Ponedeljek in torek (kuhinja zaprta, večerje za nočitvene goste po dogovoru)",
    },
    "facilities": [
        "Brezplačen WiFi",
        "Klimatizirane sobe",
        "Brezplačen parking",
        "Vrt s pogledom na Pohorje",
        "Otroško igrišče",
    ],
    "activities": [
        "Sprehodi po Pohorju",
        "Kolesarjenje (izposoja koles možna)",
        "Ogled kmetije in živali",
        "Degustacija domačih izdelkov",
    ],
}

INFO_RESPONSES = {
    "pozdrav": """Pozdravljeni pri Domačiji Kovačnik! 😊

Lahko pomagam z vprašanji o sobah, kosilih, izletih ali domačih izdelkih.""",
    "smalltalk": "Hvala, dobro.",
    "kdo_si": """Sem vaš digitalni pomočnik Domačije Kovačnik.

Z veseljem odgovorim na vprašanja o nastanitvi, kosilih, izletih ali izdelkih.""",
    "odpiralni_cas": """Odprti smo ob **sobotah in nedeljah med 12:00 in 20:00**.

Zadnji prihod na kosilo je ob **15:00**.
Ob ponedeljkih in torkih smo zaprti.

Za skupine (15+ oseb) pripravljamo tudi med tednom od srede do petka – pokličite nas! 📞""",
    "zajtrk": """Zajtrk servíramo med **8:00 in 9:00** in je **vključen v ceno nočitve**.

Kaj vas čaka? 🥐
- Sveže pomolzeno mleko
- Zeliščni čaj babice Angelce
- Kruh iz krušne peči
- Pohorska bunka, salama, pašteta
- Domača marmelada in med od čebelarja Pislak
- Skuta, maslo, sir iz kravjega mleka
- Jajca z domače reje
- Kislo mleko, jogurt z malinami po receptu gospodinje Barbare

Vse domače, vse sveže! ☕""",
    "vecerja": """Večerja se streže ob **18:00** in stane **25 €/osebo**.

Kaj dobite?
- **Juha** – česnova, bučna, gobova, goveja, čemaževa ali topinambur
- **Glavna jed** – meso s prilogami (skutni štruklji, narastki, krompir)
- **Sladica** – specialiteta hiše: pohorska gibanica babice Angelce

Prilagodimo za vegetarijance, vegane in celiakijo! 🌿

⚠️ **Ob ponedeljkih in torkih večerje ne strežemo** – takrat priporočamo bližnji gostilni Framski hram ali Karla.""",
    "sobe": """Imamo **3 sobe**, vse poimenovane po naših otrocih:

🛏️ **ALJAŽ** – soba z balkonom (2+2)
🛏️ **JULIJA** – družinska soba z balkonom (2 odrasla + 2 otroka)  
🛏️ **ANA** – družinska soba z dvema spalnicama (2+2)

Vsaka soba ima:
✅ Predprostor, spalnico, kopalnico s tušem
✅ Pohištvo iz lastnega lesa
✅ Klimatizacijo
✅ Brezplačen Wi-Fi
✅ Satelitsko TV
✅ Igrače za otroke

Zajtrk je vključen v ceno! 🥐""",
    "cena_sobe": """**Cenik nastanitve:**

🛏️ **Nočitev z zajtrkom:** 50 €/osebo/noč (min. 2 noči)
🍽️ **Večerja:** 25 €/osebo
🏷️ **Turistična taksa:** 1,50 €

**Popusti:**
- Otroci do 5 let: **brezplačno** (z zajtrkom in večerjo)
- Otroci 5-12 let: **50% popust**
- Otroška posteljica: **brezplačno**
- Doplačilo za enoposteljno: **+30%**""",
    "klima": "Da, vse naše sobe so **klimatizirane** in udobne tudi v poletni vročini.",
    "wifi": "Da, na voljo imamo **brezplačen Wi-Fi** v vseh sobah in skupnih prostorih.",
    "prijava_odjava": """**Prijava (check-in):** od 14:00
**Odjava (check-out):** do 10:00""",
    "parking": "Parkirišče je brezplačno in na voljo neposredno pri domačiji.",
    "zivali": "Hišni ljubljenčki na naši domačiji **niso dovoljeni**. Na kmetiji pa lahko ob obisku vidite domače živali.",
    "placilo": "Sprejemamo gotovino in večino plačilnih kartic.",
    "kontakt": "Kontakt: **02 601 54 00** / **031 330 113**\nEmail: **info@kovacnik.com**",
    "lokacija": "Nahajamo se na: **Planica 9, 2313 Fram** (Pohorska stran nad Framom). \nParking je brezplačen pri domačiji.",
    "min_nocitve": """Minimalno bivanje je:
- **3 nočitve** v juniju, juliju in avgustu
- **2 nočitvi** v ostalih mesecih""",
    "kapaciteta_mize": "Jedilnica 'Pri peči' sprejme do 15 oseb, 'Pri vrtu' pa do 35 oseb.",
    "alergije": "Seveda, prilagodimo jedi za alergije (gluten, laktoza) in posebne prehrane (vegan/vegetarijan).",
    "vina": "Na voljo so lokalna vina s Pohorja.",
    "turizem": "V okolici so odlične možnosti za izlete (Pohorje, slapovi, razgledišča).",
    "smucisce": "Najbližja smučišča so Mariborsko Pohorje in Areh (približno 25–35 minut vožnje).",
    "terme": "Najbližje terme so Terme Zreče in Terme Ptuj (približno 30–40 minut vožnje).",
    "kolesa": "Izposoja koles je možna po dogovoru. Za več informacij nas kontaktirajte.",
    "skalca": "Slap Skalca je prijeten izlet v bližini – priporočamo sprehod ob potočku.",
    "darilni_boni": "Na voljo imamo darilne bone. Sporočite znesek in pripravimo bon za vas.",
    "jedilnik": "Jedilnik se spreminja glede na sezono. Če želite, vam pošljemo aktualno vikend ponudbo.",
    "druzina": "Pri nas smo družinska domačija in radi sprejmemo družine. Imamo tudi igrala za otroke.",
    "kmetija": "Domačija Kovačnik je turistična kmetija na Pohorju z nastanitvijo, kosili in domačimi izdelki.",
    "gibanica": "Pohorska gibanica je naša specialiteta. Priporočam, da jo poskusite ob obisku!",
    "izdelki": "Imamo domače izdelke: marmelade, likerje/žganja, mesnine, čaje, sirupe in darilne pakete.",
    "priporocilo": "Trenutno nimam priporočil brez dodatnih informacij.",
}

BOOKING_RELEVANT_KEYS = {"sobe", "vecerja", "cena_sobe", "min_nocitve", "kapaciteta_mize"}
CRITICAL_INFO_KEYS = {
    "odpiralni_cas",
    "prazniki",
    "rezervacija_vnaprej",
    "zajtrk",
    "vecerja",
    "jedilnik",
    "cena_sobe",
    "min_nocitve",
    "prijava_odjava",
    "placilo",
    "parking",
    "kontakt",
    "sobe",
    "kapaciteta_mize",
}

ROOM_PRICING = {
    "base_price": 50,
    "min_adults": 2,
    "min_nights_summer": 3,
    "min_nights_other": 2,
    "dinner_price": 25,
    "dinner_includes": "juha, glavna jed, sladica",
    "child_discounts": {
        "0-4": 100,
        "4-12": 50,
    },
    "breakfast_included": True,
    "check_in": "14:00",
    "check_out": "10:00",
    "breakfast_time": "8:00-9:00",
    "dinner_time": "18:00",
    "closed_days": ["ponedeljek", "torek"],
}

WINE_LIST = {
    "penece": [
        {"name": "Doppler DIONA brut 2013", "type": "zelo suho", "grape": "100% Chardonnay", "price": 30.00, "desc": "Penina po klasični metodi, eleganca, lupinasto sadje, kruhova skorja"},
        {"name": "Opok27 NYMPHA rose brut 2022", "type": "izredno suho", "grape": "100% Modri pinot", "price": 26.00, "desc": "Rose frizzante, jagodni konfit, češnja, sveže"},
        {"name": "Leber MUŠKATNA PENINA demi sec", "type": "polsladko", "grape": "100% Rumeni muškat", "price": 26.00, "desc": "Klasična metoda, 18 mesecev zorenja, svež vonj limone in muškata"},
    ],
    "bela": [
        {"name": "Greif BELO zvrst 2024", "type": "suho", "grape": "Laški rizling + Sauvignon", "price": 14.00, "desc": "Mladostno, zeliščne in sadne note, visoke kisline"},
        {"name": "Frešer SAUVIGNON 2023", "type": "suho", "grape": "100% Sauvignon", "price": 19.00, "desc": "Aromatičen, zeliščen, črni ribez, koprive, mineralno"},
        {"name": "Frešer LAŠKI RIZLING 2023", "type": "suho", "grape": "100% Laški rizling", "price": 18.00, "desc": "Mladostno, mineralno, note jabolka in suhih zelišč"},
        {"name": "Greif LAŠKI RIZLING terase 2020", "type": "suho", "grape": "100% Laški rizling", "price": 23.00, "desc": "Zoreno 14 mesecev v hrastu, zrelo rumeno sadje, oljnata tekstura"},
        {"name": "Frešer RENSKI RIZLING Markus 2019", "type": "suho", "grape": "100% Renski rizling", "price": 22.00, "desc": "Breskev, petrolej, mineralno, zoreno v hrastu"},
        {"name": "Skuber MUŠKAT OTTONEL 2023", "type": "polsladko", "grape": "100% Muškat ottonel", "price": 17.00, "desc": "Elegantna muškatna cvetica, harmonično, ljubko"},
        {"name": "Greif RUMENI MUŠKAT 2023", "type": "polsladko", "grape": "100% Rumeni muškat", "price": 17.00, "desc": "Mladostno, sortno, note sena in limete"},
    ],
    "rdeca": [
        {"name": "Skuber MODRA FRANKINJA 2023", "type": "suho", "grape": "100% Modra frankinja", "price": 16.00, "desc": "Rubinasta, ribez, murva, malina, polni okus"},
        {"name": "Frešer MODRI PINOT Markus 2020", "type": "suho", "grape": "100% Modri pinot", "price": 23.00, "desc": "Višnje, češnje, maline, žametno, 12 mesecev v hrastu"},
        {"name": "Greif MODRA FRANKINJA črešnjev vrh 2019", "type": "suho", "grape": "100% Modra frankinja", "price": 26.00, "desc": "Zrela, temno sadje, divja češnja, zreli tanini"},
    ],
}

WINE_KEYWORDS = {
    "vino",
    "vina",
    "vin",
    "rdec",
    "rdeca",
    "rdeče",
    "rdece",
    "belo",
    "bela",
    "penin",
    "penina",
    "peneč",
    "muskat",
    "muškat",
    "rizling",
    "sauvignon",
    "frankinja",
    "pinot",
}

SEASONAL_MENUS = [
    {
        "months": {3, 4, 5},
        "label": "Marec–Maj (pomladna srajčka)",
        "items": [
            "Pohorska bunka in zorjen Frešerjev sir, hišna suha salama, paštetka iz domačih jetrc, zaseka, bučni namaz, hišni kruhek",
            "Juhe: goveja župca z rezanci in jetrnimi rolicami, koprivna juhica s čemažem",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice z zelišči, mlado goveje meso z rdečim vinom",
            "Priloge: štukelj s skuto, ričota s pirino kašo, pražen krompir, mini pita s porom, ocvrte hruške, pomladna solata",
            "Sladica: Pohorska gibanica babice Angelce",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
    {
        "months": {6, 7, 8},
        "label": "Junij–Avgust (poletna srajčka)",
        "items": [
            "Pohorska bunka, zorjen sir, hišna suha salama, paštetka iz jetrc z žajbljem, bučni namaz, kruhek",
            "Juhe: goveja župca z rezanci, kremna juha poletnega vrta",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice, mlado goveje meso z rabarbaro in rdečim vinom",
            "Priloge: štukelj s skuto, ričota s pirino kašo, mlad krompir z rožmarinom, mini pita z bučkami, ocvrte hruške, poletna solata",
            "Sladica: Pohorska gibanica babice Angelce",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
    {
        "months": {9, 10, 11},
        "label": "September–November (jesenska srajčka)",
        "items": [
            "Dobrodošlica s hišnim likerjem ali sokom; lesena deska s pohorsko bunko, salamo, namazi, Frešerjev sirček, kruhek",
            "Juhe: goveja župca z rezanci, bučna juha s kolerabo, sirne lizike z žajbljem",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice, mlado goveje meso z rabarbaro in rdečo peso",
            "Priloge: štukelj s skuto, ričota s pirino kašo, pražen krompir iz šporheta, mini pita s porom, ocvrte hruške, jesenska solatka",
            "Sladica: Pohorska gibanica (porcijsko)",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
    {
        "months": {12, 1, 2},
        "label": "December–Februar (zimska srajčka)",
        "items": [
            "Pohorska bunka, zorjen sir, hišna suha salama, paštetka iz jetrc s čebulno marmelado, zaseka, bučni namaz, kruhek",
            "Juhe: goveja župca z rezanci, krompirjeva juha s krvavico",
            "Meso: pečenka iz pujskovega hrbta, hrustljavi piščanec, piščančje kroglice, mlado goveje meso z rdečim vinom",
            "Priloge: štukelj s skuto, ričota s pirino kašo, pražen krompir iz pečice, mini pita z bučkami, ocvrte hruške, zimska solata",
            "Sladica: Pohorska gibanica babice Angelce",
            "Cena: 36 EUR odrasli, otroci 4–12 let -50%",
        ],
    },
]

WEEKLY_MENUS = {
    4: {
        "name": "4-HODNI DEGUSTACIJSKI MENI",
        "price": 36,
        "wine_pairing": 15,
        "wine_glasses": 4,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
    5: {
        "name": "5-HODNI DEGUSTACIJSKI MENI",
        "price": 43,
        "wine_pairing": 20,
        "wine_glasses": 5,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Frešer Renski rizling 2019 (suho)", "dish": "Ričotka pirine kaše z jurčki in zelenjavo"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
    6: {
        "name": "6-HODNI DEGUSTACIJSKI MENI",
        "price": 53,
        "wine_pairing": 25,
        "wine_glasses": 6,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Frešer Renski rizling 2019 (suho)", "dish": "Ričotka pirine kaše z jurčki in zelenjavo"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Modra frankinja 2020 (suho)", "dish": "Štrukelj s skuto naše krave Miške, goveje meso iz Kovačnikove proste reje, rdeča pesa, rabarbara, naravna omaka"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
    7: {
        "name": "7-HODNI DEGUSTACIJSKI MENI",
        "price": 62,
        "wine_pairing": 29,
        "wine_glasses": 7,
        "courses": [
            {"wine": "Penina Doppler Diona 2017 (zelo suho, 100% chardonnay)", "dish": "Pozdrav iz kuhinje"},
            {"wine": "Frešer Sauvignon 2024 (suho)", "dish": "Kiblflajš s prelivom, zelenjava s Kovačnikovega vrta, zorjen Frešerjev sir, hišni kruh z drožmi"},
            {"wine": None, "dish": "Juha s kislim zeljem in krvavico"},
            {"wine": "Greif Laški rizling Terase 2020 (suho)", "dish": "An ban en goban – Jurčki, ajda, ocvirki, korenček, peteršilj"},
            {"wine": "Frešer Renski rizling 2019 (suho)", "dish": "Ričotka pirine kaše z jurčki in zelenjavo"},
            {"wine": "Šumenjak Alter 2021 (suho)", "dish": "Krompir iz naše njive, zelenjavni pire, pohan pišek s kmetije Pesek, solatka iz vrta gospodinje Barbare"},
            {"wine": "Greif Modra frankinja 2020 (suho)", "dish": "Štrukelj s skuto naše krave Miške, goveje meso iz Kovačnikove proste reje, rdeča pesa, rabarbara, naravna omaka"},
            {"wine": "Greif Rumeni muškat 2024 (polsladko)", "dish": "Pohorska gibanica babice Angelce ali domač jabolčni štrudl ali pita sezone, hišni sladoled"},
        ],
    },
}

WEEKLY_INFO = {
    "days": "sreda, četrtek, petek",
    "time": "od 13:00 naprej",
    "min_people": 6,
    "contact": {"phone": "031 330 113", "email": "info@kovacnik.com"},
    "special_diet_extra": 8,
}
