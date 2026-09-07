"""Een netwerk van knopen: de rekenvorm van de toestand.

`PolderState` is de leesbare vorm en blijft dat. `SystemState` is dezelfde informatie als
arrays over knopen, want de rekenkern moet over duizenden knopen tegelijk kunnen. Dezelfde
scheiding als op de tijdas: de fysica neemt losse getallen en arrays aan, geen
pydantic-model - nu ook over de breedte.

De vectorisatie zit in de **breedte** en de passes in de **diepte**: knopen op dezelfde
topologische diepte gaan in een scan, en het aantal sequentiele passes is de diepte van de
graaf en niet het aantal knopen. Voor Nederland is die diepte 3 a 4 - peilvak, polderboezem,
boezem, zee - tegen een breedte van duizenden.
"""

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from talk_with_the_engineer.core.connection import OUTSIDE
from talk_with_the_engineer.core.state import PolderState

BOUNDARY = -1
"""Index van de randvoorwaardeknoop in `downstream`.

`OUTSIDE` is geen rij in de arrays: hij heeft oneindige berging en een vast peil, dus er is
niets aan hem uit te rekenen. Water dat hier naartoe gaat verlaat het systeem.
"""


@dataclass(frozen=True)
class SystemState:
    """Struct-of-arrays over de knopen. Een rij per polder, geen object per polder.

    Elke knoop heeft ten hoogste **een uitgaande** verbinding. Fan-in is onbeperkt - zoveel
    polders als je wilt mogen op dezelfde boezem lozen - maar fan-out niet, en dat is een
    bewuste beperking en geen vergissing. Twee gemalen naar twee bestemmingen roept de
    vraag op hoe het water zich over die twee verdeelt, en dat is een toewijzingsvraag van
    dezelfde soort als de verdringingsreeks: die hoort bij `allocation.py` en niet in de
    topologie. De Nederlandse schematisatie heeft hem ook niet nodig: een polder heeft een
    gemaal naar zijn boezem.
    """

    area_ha: np.ndarray
    pct_open_water: np.ndarray
    retention_fraction: np.ndarray
    days_to_retain: np.ndarray
    days_to_discharge: np.ndarray
    """Over hoeveel dagen de neerslag per knoop tot afvoer komt; per gebied verschillend."""
    target_level_rise_m: np.ndarray
    level_margin_m: np.ndarray

    capacity_out_m3_per_sec: np.ndarray
    capacity_in_m3_per_sec: np.ndarray
    head_max_m: np.ndarray
    """Opvoerhoogte waarbij de capaciteit nul is; `inf` betekent peilonafhankelijk."""
    downstream: np.ndarray
    """Index van de benedenstroomse knoop, of `BOUNDARY`."""

    names: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.area_ha)

    @property
    def area_open_water_ha(self) -> np.ndarray:
        return self.pct_open_water / 100.0 * self.area_ha

    @property
    def area_land_ha(self) -> np.ndarray:
        return self.area_ha - self.area_open_water_ha

    @property
    def metres_per_m3_per_sec(self) -> np.ndarray:
        """Waterstandverandering per uur bij een debiet van 1 m3/s, per knoop."""
        return 3600.0 / (self.area_open_water_ha * 1e4)

    @property
    def has_derating(self) -> bool:
        """Hangt er ergens een capaciteit aan de benedenstroomse stand?

        Zo niet, dan is een pass per topologische diepte exact en hoeft er niet te worden
        geitereerd. Dat is niet alleen sneller maar ook een ander soort antwoord: geen
        tolerantie, geen convergentievraag.
        """
        return bool(np.isfinite(self.head_max_m).any())

    @classmethod
    def from_polders(
        cls, polders: Sequence[PolderState], names: Sequence[str] | None = None
    ) -> "SystemState":
        """Bouw het netwerk uit losse polders; hun verbindingen vormen de graaf.

        De namen zijn de sleutels waarmee `Connection.to` wordt opgezocht. Zonder
        opgegeven namen krijgen de knopen hun index als naam, wat alleen bruikbaar is voor
        een systeem dat volledig op de rand uitkomt.
        """
        names = (
            tuple(names)
            if names is not None
            else tuple(str(index) for index in range(len(polders)))
        )
        if len(names) != len(polders):
            raise ValueError("evenveel namen als polders nodig")
        if len(set(names)) != len(names):
            raise ValueError("knoopnamen moeten uniek zijn")
        index_of = {name: index for index, name in enumerate(names)}

        capacity_out, capacity_in, head_max, downstream = [], [], [], []
        for name, polder in zip(names, polders):
            if len(polder.connections) > 1:
                raise ValueError(
                    f"knoop {name!r} heeft {len(polder.connections)} uitgaande "
                    "verbindingen; een netwerk draagt er een per knoop, zie SystemState"
                )
            if not polder.connections:
                capacity_out.append(0.0)
                capacity_in.append(0.0)
                head_max.append(np.inf)
                downstream.append(BOUNDARY)
                continue
            connection = polder.connections[0]
            capacity_out.append(connection.capacity_out_m3_per_sec)
            capacity_in.append(connection.capacity_in_m3_per_sec)
            head_max.append(
                np.inf if connection.head_max_m is None else connection.head_max_m
            )
            if connection.to == OUTSIDE:
                downstream.append(BOUNDARY)
            elif connection.to in index_of:
                downstream.append(index_of[connection.to])
            else:
                raise ValueError(
                    f"knoop {name!r} loost op {connection.to!r}, en die bestaat niet"
                )

        state = cls(
            area_ha=np.array([p.area_ha for p in polders], dtype=float),
            pct_open_water=np.array([p.pct_open_water for p in polders], dtype=float),
            retention_fraction=np.array(
                [p.retention_fraction for p in polders], dtype=float
            ),
            days_to_retain=np.array([p.days_to_retain for p in polders], dtype=int),
            days_to_discharge=np.array(
                [p.days_to_discharge for p in polders], dtype=int
            ),
            target_level_rise_m=np.array(
                [p.target_level_rise_m for p in polders], dtype=float
            ),
            level_margin_m=np.array([p.level_margin_m for p in polders], dtype=float),
            capacity_out_m3_per_sec=np.array(capacity_out, dtype=float),
            capacity_in_m3_per_sec=np.array(capacity_in, dtype=float),
            head_max_m=np.array(head_max, dtype=float),
            downstream=np.array(downstream, dtype=int),
            names=names,
        )
        state.topological_levels()  # cyclus meteen afwijzen, niet pas tijdens het rekenen
        return state

    def topological_levels(self) -> tuple[np.ndarray, ...]:
        """De knoopindices per topologische diepte, van bron naar rand. Gecacht.

        De cache zit in `__dict__` en niet in een veld, omdat deze dataclass `frozen` is en
        `__setattr__` dus dicht zit; `__dict__` schrijven omzeilt dat, net zoals
        `functools.cached_property` het doet. Legitiem, want de topologie is onveranderlijk:
        `downstream` kan niet wijzigen zonder een nieuwe `SystemState`.

        Waarom het uitmaakt: dit is een python-lus over de knoop-as - de enige in de kern -
        en hij kost bij 8500 knopen 3,7 ms. `simulate_network` riep hem elke iteratie opnieuw
        aan en `allocate` elke aanroep. Dat is geen bug maar het is gratis weg te halen.

        En hij MOET een python-lus blijven. De topologie is statisch, dus hij hoort buiten het
        getraceerde deel van een latere JAX-backend; hem vectoriseren zou hem juist naar
        binnen halen.
        """
        cached = self.__dict__.get("_topological_levels")
        if cached is None:
            cached = self._compute_topological_levels()
            self.__dict__["_topological_levels"] = cached
        return cached

    def _compute_topological_levels(self) -> tuple[np.ndarray, ...]:
        """De ongecachte berekening; zie `topological_levels`.

        De diepte is de **langste** pad-afstand tot een bron en niet de kortste. Dat is
        geen detail: neem A -> C, B -> C, A -> D, D -> C. Met kortste-pad-diepte komt C op
        diepte 1 te staan, samen met D, en dan wordt C gerekend terwijl D - die water in C
        loost - nog niet klaar is. Alleen langste-pad-indeling geeft de invariant waar de
        hele pass-structuur op rust:

            elke voorganger van een knoop ligt op een strikt kleinere diepte

        Raises bij een cyclus. Een lus in de afwatering betekent water dat rondgaat, en dat
        is geen graaf meer maar een gekoppeld stelsel; dat vraagt een ander schema.
        """
        depth = np.zeros(self.size, dtype=int)
        for _ in range(self.size):
            changed = False
            for upstream, down in enumerate(self.downstream):
                if down == BOUNDARY:
                    continue
                if depth[down] < depth[upstream] + 1:
                    depth[down] = depth[upstream] + 1
                    changed = True
            if not changed:
                break
        else:
            raise ValueError(
                "de afwateringsgraaf bevat een cyclus; water dat rondgaat vraagt een "
                "gekoppeld stelsel en niet een pass per diepte"
            )
        return tuple(
            np.flatnonzero(depth == level) for level in range(int(depth.max()) + 1)
        )

    def to_polders(self) -> tuple[PolderState, ...]:
        """De leesbare projectie terug, zodat een tooluitvoer een `PolderState` kan zijn."""
        from talk_with_the_engineer.core.connection import (
            Connection,
        )

        polders = []
        for index in range(self.size):
            down = int(self.downstream[index])
            head_max = float(self.head_max_m[index])
            polders.append(
                PolderState(
                    area_ha=float(self.area_ha[index]),
                    pct_open_water=float(self.pct_open_water[index]),
                    retention_fraction=float(self.retention_fraction[index]),
                    days_to_retain=int(self.days_to_retain[index]),
                    days_to_discharge=int(self.days_to_discharge[index]),
                    target_level_rise_m=float(self.target_level_rise_m[index]),
                    level_margin_m=float(self.level_margin_m[index]),
                    connections=(
                        Connection(
                            to=OUTSIDE if down == BOUNDARY else self.names[down],
                            capacity_out_m3_per_sec=float(
                                self.capacity_out_m3_per_sec[index]
                            ),
                            capacity_in_m3_per_sec=float(
                                self.capacity_in_m3_per_sec[index]
                            ),
                            head_max_m=None if np.isinf(head_max) else head_max,
                        ),
                    ),
                )
            )
        return tuple(polders)
