"""De verbinding waarover een gebied water uitwisselt met zijn omgeving.

Dit is het object waarin afvoeren, aanvoeren en de ruimtelijke koppeling samenvallen. Een
polder pompt water naar iets en laat water in uit iets, en dat "iets" is ofwel de
buitenwereld ofwel een andere polder. Eén regel:

    to = OUTSIDE      de losse polder, en dus het model zoals het tot nu toe was
    to = "polder B"   de cascade

Er is daarmee geen aparte cascademodus en geen tweede rekenpad. De gevalideerde
eenpolder-casus is de kleinste instantie van het algemene geval.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

OUTSIDE = "OUTSIDE"
"""De randvoorwaardeknoop: oneindige berging, vast peil.

Wat je erin pompt verdwijnt, wat je eruit haalt is er altijd. Dat is precies de aanname
die een model van een losse polder stilzwijgend maakt, en hier staat hij opgeschreven.
"""


class Connection(BaseModel):
    """Een verbinding met twee richtingen en twee capaciteiten.

    Bewust géén enkele capaciteit met een teken. Een gemaal en een inlaat zijn twee
    kunstwerken met twee prijzen en twee levensduren, ze kunnen beide bestaan - de meeste
    polders hebben een gemaal én een inlaat - en dan is er geen enkel getal dat de
    verbinding beschrijft. De gerealiseerde flux wisselt binnen een seizoen wel van teken,
    maar dat is een uitkomst van de simulatie en geen eigenschap van de verbinding.

    De actie die een capaciteit vergroot draagt de richting daarom als eigen veld; zie
    `WaterExchangeAction`. Signed actie, ongesigneerde toestand.
    """

    model_config = ConfigDict(frozen=True)

    to: str = Field(
        OUTSIDE,
        description=(
            "Waar deze verbinding naartoe gaat: OUTSIDE voor de buitenwereld, of de naam "
            "van een andere knoop"
        ),
    )
    capacity_out_m3_per_sec: float = Field(
        0.0, ge=0, description="Gemaalcapaciteit, van dit gebied naar `to` [m3/s]"
    )
    capacity_in_m3_per_sec: float = Field(
        0.0, ge=0, description="Inlaatcapaciteit, van `to` naar dit gebied [m3/s]"
    )
    head_max_m: float | None = Field(
        None,
        gt=0,
        description=(
            "Opvoerhoogte waarbij de capaciteit tot nul is afgenomen [m]. None betekent "
            "peilonafhankelijk, wat het gedrag is zolang er geen cascade is"
        ),
    )

    @property
    def is_boundary(self) -> bool:
        """Gaat deze verbinding naar de buitenwereld in plaats van naar een andere knoop?"""
        return self.to == OUTSIDE


def single_pump_connection(capacity_out_m3_per_sec: float) -> tuple[Connection, ...]:
    """De verbindingen van een losse polder: één gemaal naar de buitenwereld.

    Bestaat als functie zodat er precies één plek is waar de eenpolder-casus in
    netwerktermen wordt uitgedrukt.
    """
    return (Connection(to=OUTSIDE, capacity_out_m3_per_sec=capacity_out_m3_per_sec),)


class ConnectedState(BaseModel):
    """Mixin met de verbindingen en de schaalbare vertaling van en naar één capaciteit.

    Staat apart van `PolderState` zodat de netwerkvorm in WP10 dezelfde vertaling kan
    gebruiken zonder de polderspecifieke velden mee te nemen.
    """

    connections: tuple[Connection, ...] = Field(
        default=(),
        description="De verbindingen waarover dit gebied water uitwisselt",
    )

    @model_validator(mode="before")
    @classmethod
    def _accept_a_single_pump_capacity(cls, data):
        """Laat `pump_capacity_m3_per_sec=` bij constructie een verbinding worden.

        De toolgrens, `from_water_system_input` en een handvol tests geven de
        gemaalcapaciteit als los getal mee. Dat blijft werken: één getal is één verbinding
        naar de buitenwereld. Zonder deze tak zou het verhuizen van een veld naar een
        object een breuk zijn in plaats van een generalisatie.
        """
        if not isinstance(data, dict):
            return data
        if "pump_capacity_m3_per_sec" not in data:
            return data
        capacity = data.pop("pump_capacity_m3_per_sec")
        if data.get("connections"):
            raise ValueError(
                "geef of pump_capacity_m3_per_sec of connections, niet beide: met meer "
                "dan een verbinding is een enkele capaciteit dubbelzinnig"
            )
        data["connections"] = single_pump_connection(capacity)
        return data

    @property
    def connection(self) -> Connection:
        """De enige verbinding.

        Raises zodra er meer dan een is, want dan is elke vraag naar "de" verbinding
        dubbelzinnig en hoort de aanroeper te zeggen welke hij bedoelt.
        """
        if len(self.connections) != 1:
            raise ValueError(
                f"dit gebied heeft {len(self.connections)} verbindingen; noem de "
                "verbinding in plaats van naar 'de' verbinding te vragen"
            )
        return self.connections[0]

    @property
    def pump_capacity_m3_per_sec(self) -> float:
        """De uitgaande capaciteit van de enige verbinding [m3/s].

        Blijft bestaan omdat de toolgrens en een reeks tests hem gebruiken. Heeft het
        gebied meer dan een UITGAANDE verbinding - twee gemalen naar twee bestemmingen, of
        aanvoer uit een ander systeem dan waar de afvoer naartoe gaat - dan heeft "de
        gemaalcapaciteit van dit gebied" geen antwoord, en raist hij.

        Let op wat hier géén twee verbindingen zijn. Een gemaal en een inlaat naar dezelfde
        buur zijn er één, want `Connection` draagt beide capaciteiten. En gebieden die op
        dit gebied lozen geven het geen tweede verbinding: `connections` bevat alleen
        uitgaande kanten. Fan-in en fan-out zijn onbeperkt; dit is een vangrail op een
        dubbelzinnige vraag en geen beperking op de topologie.
        """
        return self.connection.capacity_out_m3_per_sec

    @property
    def supply_capacity_m3_per_sec(self) -> float:
        """De inkomende capaciteit van de enige verbinding [m3/s]."""
        return self.connection.capacity_in_m3_per_sec

    def with_capacity(
        self,
        capacity_out_m3_per_sec: float | None = None,
        capacity_in_m3_per_sec: float | None = None,
    ):
        """Dezelfde toestand met een andere capaciteit op de enige verbinding.

        Bestaat omdat `replace()` op `model_copy` rust en die de validators overslaat; een
        capaciteit kan dus niet meer als los veld worden bijgewerkt.
        """
        current = self.connection
        updated = current.model_copy(
            update={
                key: value
                for key, value in (
                    ("capacity_out_m3_per_sec", capacity_out_m3_per_sec),
                    ("capacity_in_m3_per_sec", capacity_in_m3_per_sec),
                )
                if value is not None
            }
        )
        return self.model_copy(update={"connections": (updated,)})
