"""De beloning: wat een pad beter maakt dan een ander.

Dit is `R`, en het is het enige lid van de tuple dat nog geen antwoord geeft. Wat hier
staat is de VORM van de som en waarom hij nu niet gemaakt kan worden - opgeschreven op de
plek waar hij hoort, zodat de leegte een uitspraak is en geen omissie.

**Wat er vandaag in plaats van R staat.** De pakketzoeker minimaliseert investeringskosten
onder harde eisen (`Constraints`). Dat is iets anders dan een beloning: een eis verbiedt en
een beloning weegt af. Zolang de eis van buiten komt - een inundatienorm die is
vastgesteld - is dat de juiste vorm, en dan is de vraag "wat is de goedkoopste manier om
eraan te voldoen". Maar het antwoord op "waar zou de norm moeten liggen" zit er niet in, en
dat is precies de vraag die de kostencurve oproept.

**De som.** Van Dantzig (1956), en na hem Eijgenraam, zetten de investering tegen de
resterende verwachte schade en tellen die twee op:

    totaal(x) = investering(x) + verwachte_jaarschade(x) / discontovoet

Het optimum ligt waar die som minimaal is. Wij kunnen alleen de eerste term tekenen; zie
`scripts/gen_kostencurve.py`, dat die halve curve juist maakt om de andere helft zichtbaar
te missen.

**Waarom de tweede term er niet is.** Er is geen schadefunctie in dit model. Een
inundatiediepte is er wel - `dh_total_above_original_datum_m` - maar wat een centimeter
water op een hectare van een gegeven gebruikstype aan schade doet, is een tabel die hier
niet staat en die we niet moeten verzinnen. `PricelessPost` bestaat om precies die reden:
een verzonnen bedrag is erger dan geen bedrag, want het ziet uit als kennis.

**En γ heeft nog een tweede lege plek nodig.** Disconteren gaat over WANNEER je bouwt, en
die vraag bestaat alleen als er iets verandert terwijl je wacht: zeespiegelstijging,
bodemdaling, veranderend landgebruik. Dat is de trend-familie uit `core/exogenous/trend.py`,
en die is ook leeg. De twee horen bij elkaar: een discontovoet zonder trend rekent uit dat
later altijd goedkoper is, want er wordt niets slechter. Dat is niet voorzichtig maar
verkeerd.

Wat er dus moet komen, in deze volgorde:

1. een schadefunctie - inundatiediepte en gebruikstype naar euro's per jaar;
2. de eerste trend, zodat wachten iets kost;
3. de som hierboven, met de discontovoet als expliciete aanname en niet als default.
"""

from talk_with_the_engineer.core.state import PolderState


def expected_annual_damage(state: PolderState) -> float:
    """De verwachte jaarschade van deze polder [EUR/jaar].

    Nog niet te maken. Deze functie bestaat met zijn signatuur erin zodat de plek vastligt
    en zodat een aanroeper die R nodig heeft een fout krijgt in plaats van een nul: nul zou
    betekenen dat er geen schade is, en dat is het antwoord op een andere vraag.

    Wat hij nodig heeft om te bestaan: een schadefunctie over inundatiediepte en
    gebruikstype, en de frequentielijn van deze polder om over te integreren. Die tweede
    heeft het model wel - zie `scripts/gen_frequentielijn.py` - dus het is de eerste die
    ontbreekt.
    """
    raise NotImplementedError(
        "Er is geen schadefunctie in dit model, dus de verwachte jaarschade is niet te "
        "berekenen. Zie de moduledocstring van `core/reward.py` voor wat er nodig is en "
        "waarom hier geen getal staat: een verzonnen schadebedrag ziet uit als kennis."
    )


def total_cost_of_ownership(
    state: PolderState,
    investment: float,
    discount_rate: float,
) -> float:
    """De som van Van Dantzig: investering plus gekapitaliseerde restschade [EUR].

    Nog niet te maken, want de tweede term niet. De signatuur staat er wel, en met opzet
    met `discount_rate` als VERPLICHT argument zonder standaardwaarde: welke voet je kiest
    bepaalt de uitkomst sterker dan de meeste hydrologie in dit model, en een default zou
    die keuze onzichtbaar maken.

    De vorm zegt ook waar de tijd binnenkomt. Deze som weegt een investering NU tegen
    schade over alle jaren erna; hij vergelijkt geen twee momenten. Om te kunnen zeggen
    wanneer je moet bouwen, moet de toestand tussen die momenten kunnen verschuiven, en dat
    is `core/exogenous/trend.py`.
    """
    raise NotImplementedError(
        "De som investering + restschade is niet te maken zonder schadefunctie; zie "
        "`expected_annual_damage`. En zonder een trend die de toestand verschuift, zegt "
        "een discontovoet alleen dat later goedkoper is."
    )
