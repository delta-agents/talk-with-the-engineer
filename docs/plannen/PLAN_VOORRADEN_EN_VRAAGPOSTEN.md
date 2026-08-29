# Plan van aanpak — de drie vraagposten, de bodemvoorraad en de verzilting

Eén plan voor #59, #55 en #58. De drie issues stellen dezelfde vraag van drie kanten:
**welke voorraden kent dit model, hoe snel zijn ze beschikbaar, en welke vraag bedienen ze?**
Los oplossen betekent dat begrip drie keer invoeren, en waarschijnlijk drie keer anders.

De volgorde komt uit de review in #55 en staat niet ter discussie: eerst weten wélke vraag je
bedient, dan de voorraad ernaast zetten.

---

## 0. Wat er wordt gebouwd, in één tabel

| deel | issue | wat het doet | raakt de rekenkern |
|---|---|---|---|
| 1 | #59 | de watervraag valt uiteen in doorspoeling, peilbeheer en beregening | nee |
| 2 | #55 | de bodem als voorraad met een plafond, en de traagste schakel als antwoord | ja, `simulate_deficit` |
| 3 | #58 | verzilting als caveat, categorie 1 uitgelegd, en de waterprijs van peilopzet | nee |

Wat er **niet** wordt gebouwd staat in §5, met de reden erbij.

---

## 1. Deel 1 — de vraag valt uiteen in drie posten (#59)

### 1.1 Waarom dit eerst

Ons `deficit_mm_per_day` is een verdampingstekort dat uit het oppervlaktewater wordt gedekt.
Dat is **beregening**: landelijk 9–19 % van de watervraag, in West 5–9 %. Peilbeheer (40–55 %)
en doorspoeling (32–46 %) zitten helemaal niet in het model. Een voorraad toevoegen aan een
vraag die 7 % van het probleem is, is de verkeerde volgorde.

### 1.2 De data: alleen verhoudingen, want oppervlakken zijn er niet

De werkopgave staat in Mm³/zomer per DPZW-regio, onze statistiek in mm over een gebied.
Zonder regio-oppervlakken is dat niet om te rekenen, en die oppervlakken zijn niet gevonden.
Wat wél overzet is de **vorm**: aandelen tussen posten zijn dimensieloos.

`scripts/build_demand_posts.py` → `demand_posts.json`, per regio × scenario × herhaaltijd:

* `demand_share` — het aandeel van elke post in de totale watervraag;
* `coverage` — `Levering / Vraag` per post: welke post werkelijk tekortkomt;
* `shortfall_share` — het aandeel van elke post in het totale tekort.

Alle drie dimensieloos. Geen enkel absoluut volume gaat de code in, en dat is geen
voorzichtigheid maar de enige lezing die de bron draagt.

### 1.3 De as is een eigen as, en dat wordt niet stil gemapt

De werkopgave rust op BP18 / KNMI'14, onze droogtestatistiek op KNMI'23. De KNMI-factor
tussen die twee loopt van 0,94 tot 1,42 en valt juist bij T5 en T10 hoger uit — precies het
bereik dat de werkopgave dekt. En de methode is geen fit maar het gemiddelde van de vier
jaren die op het **totaal** rond de herhaaltijd zaten, dus T20 is de bovengrens van wat de
reeks draagt.

Daarom een **eigen tripel**, in dezelfde vorm als het droogtetripel: `demand_region`,
`demand_scenario`, `demand_return_period`, alle drie of geen van drie. Geen automatische
vertaling van `drought_scenario` naar `S2050`: dat zou twee klimaatproducten gelijkstellen.

### 1.4 Wat het antwoord ermee doet

**Op de aanvoertools** — `data.demand_posts` plus een caveat. De caveat staat er op elke
droogtevraag (de vraagkant is smal, ook zonder tripel) en wordt concreet zodra het tripel er
staat: dan noemt hij het aandeel voor deze regio en dat onze vraag *beregening plus een deel
van peilbeheer* is. Dat laatste is geen detail: `simulate_deficit` trekt het tekort ook van
het open water af, en dat stuk zit in de werkopgave onder peilbeheer. Wie de posten naast
elkaar zet zonder dat te weten, telt dubbel.

**Op de verdelingstool** — dit is de winst. `AllocationNode` krijgt:

* `demand_post` — de post die deze afnemer is. Vult `category` in als die is weggelaten, uit
  een tabel met de wettelijke grondslag erbij. Beide opgeven wordt geweigerd;
* `add_regional_demand_posts` — leest `deficit_mm_per_day` als de **beregeningspost** en zet
  peilbeheer en doorspoeling ernaast in de verhouding die de werkopgave voor deze regio
  geeft, elk met zijn eigen categorie.

Dat tweede maakt de klem zichtbaar die #58 in de praktijk vond: peilbeheer is categorie 1 en
verdringt beregening, categorie 4. Vandaag moet de beller die categorieën zelf verzinnen.

---

## 2. Deel 2 — de bodem als voorraad met een plafond (#55)

### 2.1 Niet de twee bakken, maar twee getallen

De review stelde drie fysische schakels vast waar het plan er twee had, en dat maakt een
procesmodel ingewikkelder in plaats van eenvoudiger. De natte kant heeft dit probleem al
opgelost en niet met fysica: één vaste gebiedseigenschap (`SUMMER_LOSS_MM`) en een lookup met
drie curves waarachter een doorrekening zit die wij niet doen.

Dezelfde vorm, met de correctie die het uitwerken opleverde: een curve die tot 1 sommeert
houdt geen stand, want *met* aanvoer levert de bodem meer dan er in zit — dat is water dat de
sloot erin heeft gepompt, en dat modelleren we al. Wat overblijft zijn **twee getallen**:

| grootheid | wat het is |
|---|---|
| voorraad [mm] | wat de bodem geeft en wat niet wordt aangevuld; komt náást `buffer_mm` |
| plafond [mm/dag] | hoe snel water bij het gewas kan komen; `min(sloot→bodem, capillair)` |

De curve volgt uit die twee: voorraad gedeeld door plafond is hoe lang hij meegaat.

### 2.2 De vijf gebiedstypen

| gebiedstype | voorraad | plafond | traagste schakel |
|---|---|---|---|
| veenweide | 5,8 mm | 0,64 mm/d | sloot → bodem |
| kleipolder | 14,5 mm | 1,45 mm/d | sloot → bodem |
| zandgrond met slootinvloed | 57,9 mm | 2,00 mm/d | bodem → wortelzone |
| zandgrond zonder slootinvloed | 86,8 mm | 2,00 mm/d | voorraad |
| droogtegevoelig zand | 45,0 mm | 4,00 mm/d | voorraad |

μ, de toegestane zakking, de infiltratieweerstand en de capillaire grens zitten **in** de
tabel en niet aan de toolgrens. Daarmee verdwijnen vier dingen die de review terecht
afkeurde: de valse gevoeligheidsband over μ, de onhaalbare zakking van 0,8 m in veen, de
asymmetrie van γ als vraag aan de beller, en de derde schakel als apart begrip.

De getallen zijn indicatief en dragen geen bron; dat staat in een caveat en niet in stilte.

### 2.3 Wat er in de rekenkern verandert

Twee dingen, en `clamped_scan` kan ze allebei al:

1. **een tweede klem.** De bodemvoorraad ligt onder de open-waterbuffer: de ondergrens van de
   band zakt met de voorraad, uitgedrukt als peil over het open water. Daarmee wordt de bodem
   pas aangesproken als de peilband leeg is — precies het doorgeefluik-gedrag dat de
   doorrekening laat zien: met aanvoer blijft de voorraad staan, zonder aanvoer is het
   geleverde exact de voorraad;
2. **een plafond op de landvraag.** Wat het plafond niet doorlaat is onvervulde vraag, en het
   is nadrukkelijk niet minder vraag. Anders zou een trage bodem in de uitvoer als winst
   verschijnen. Een grotere inlaat verandert er niets aan, en dat is de hele uitspraak.

Het open water verdampt door: dat is vraag in de watergang en niet door de bodem.

### 2.4 Wat eruit komt

| veld | wat het zegt |
|---|---|
| `soil_store_mm` | de voorraad die de bodem toevoegt, naast `buffer_mm` |
| `soil_transfer_mm_per_day` | het plafond |
| `soil_supplied_mm` | wat er in deze periode werkelijk uit de bodem is gekomen |
| `unreachable_mm` | vraag die het plafond niet doorlaat |
| `days_until_soil_empty` | wanneer de bodemvoorraad op is |
| `binding_link` | de traagste schakel tussen de bron en de wortelzone |

`binding_link` is de winst: één vocabulaire voor "welke schakel knelt", op dezelfde manier
als `binding_is_capacity_not_availability` dat voor bron-tegen-inlaat doet. Knelt het
plafond, dan helpt onderwaterdrainage en een grotere inlaat niet; knelt de voorraad, dan
helpt alleen water van buiten.

### 2.5 Toetsen

1. weglaten verandert niets — bit voor bit het huidige antwoord;
2. massabalans — `demand = supplied + buffer + soil_supplied + shortfall`;
3. zonder aanvoer is het geleverde exact de voorraad; met aanvoer blijft de voorraad staan;
4. het plafond blijft onder de capillaire grens, behalve bij het droogtegevoelige type waar
   het water uit de wortelzone zelf komt;
5. rangorde — veen heeft het laagste plafond en de kleinste voorraad;
6. `binding_link` slaat om als de traagste schakel omslaat, en een grotere inlaat verandert
   het antwoord niet zolang het plafond knelt;
7. half opgeven wordt geweigerd, met de naam van het ontbrekende veld erbij.

---

## 3. Deel 3 — verzilting, categorie 1, en de waterprijs (#58)

Drie dingen die geen rekenkern nodig hebben en die wél ontbreken:

* **een verziltingscaveat** op de aanvoer- en verdelingstools. Bij schaarste is de volgende
  stap in de praktijk niet "minder inlaten" maar "zouter inlaten", en dat is een andere
  beslissing met een andere schade. Het model kent chloride niet, en de aanvoercapaciteit van
  een verziltende polder is bovendien gedimensioneerd op doorspoeling — 32 tot 46 % van de
  vraag — en dus op waterkwaliteit;
* **categorie 1 uitgelegd** in `read_me`. Peilhandhaving tegen dijkuitdroging en tegen
  verzilting van een veenpakket hoort aantoonbaar in "veiligheid en onomkeerbare schade", en
  dat is niet vanzelfsprekend voor wie de tool voor het eerst gebruikt. Erbij: dat een
  bergingsgebied aan de natte kant niet als cascadeknoop te stellen is, zodat niemand op het
  vals-negatief van 0 cm stuit;
* **de waterprijs van peilopzet.** Peilopzet koopt bij ons voorraad en de prijs die we noemen
  is drooglegging. In veenweide verhoogt peilopzet óók de watervraag voor peilbeheer, met
  ongeveer 4 %: je moet water aanvoeren om dat hogere peil te handhaven. Beide zijn waar en
  wij noemen er één. Zelfde patroon bij de bodemmaatregel: onderwaterdrainage ontsluit in
  veenweide 5,8 mm en kost 6–77 mm per jaar aan extra infiltratie, dus de maatregel kan meer
  water vragen dan de voorraad die hij vrijmaakt.

---

## 4. Waar het aangrijpt

| bestand | wat erbij komt |
|---|---|
| `scripts/build_demand_posts.py` | de bouw van de aandelen uit de werkopgave |
| `demand_posts.json` | de aandelen, per regio × scenario × herhaaltijd |
| `models/.../demand.py` | het vraagpost-tripel en de categorietabel |
| `models/.../soil.py` | de vijf gebiedstypen |
| `models/.../supply.py` | de drie bodemvelden en de zes uitvoervelden |
| `models/.../allocation.py` | `demand_post` en `add_regional_demand_posts` op de knoop |
| `models/.../base_rule_of_thumb.py` | vier caveats en twee prijsloze posten |
| `tools/.../utils_demand.py` | de toegang tot het databestand |
| `tools/.../simulate.py` | de tweede klem en het plafond |
| `tools/.../supply.py`, `allocation.py` | de uitvoer erbij |
| `tools/.../read_me.py` | vier modules bijgewerkt |
| `tests/src/tools/test_vraagposten.py` | deel 1 |
| `tests/src/tools/test_bodemvoorraad.py` | deel 2 |
| `tests/src/tools/test_verzilting.py` | deel 3 |

---

## 5. Wat er niet in zit, en waarom

**Een drempelgestuurde inlaat op `CascadeNode`** (#58, punt 3). Een bergingsgebied krijgt zijn
water doordat de boezem het er in een piek ín duwt, en de boezem staat *benedenstrooms*. De
natte kern rekent per topologische laag van boven naar beneden; een flux tegen die richting in
maakt van een exacte enkele pass een vast-puntiteratie. Die iteratie bestaat al voor de
kopafhankelijke capaciteit, maar hij convergeert doordat de capaciteit nooit mag stijgen — een
monotone constructie die je bij een drempelinlaat niet gratis krijgt: de berging vult, de
boezem zakt, de inlaat sluit, de boezem stijgt. En de conservatieve keuze staat hier de
verkeerde kant op: water uit de boezem halen is optimistisch over de boezemstand en dus
onveilig, terwijl het meten van de winst van de berging juist de vraag is. Dat is een eigen
ontwerpstap en geen veld erbij.

**Een bergingsknoop op de verdelingstool** (#58, punt 4). Vraagt eerst een tijd-as: zonder
die as is "eerst vullen, dan uitgeven" niet te onderscheiden, en dan verdwijnt precies wat de
maatregel ís. Het issue vraagt er zelf een besluit over.

Voor beide geldt: `read_me` zegt nu waarom een berging niet te stellen is, zodat het gemis
zichtbaar is in plaats van stil.

**Verzilting als grootheid.** Er komt een caveat en geen chloridebalans. Een zoutgehalte
verzinnen zou hier erger zijn dan het niet hebben.

**De pakketzoeker.** Een bodemmaatregel in `optimize` is een maatregel zonder mechanisme
zolang deel 2 niet staat. Hij komt hier niet in.
