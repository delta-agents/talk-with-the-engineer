# talk-with-the-engineer

## Werkafspraken

Dezelfde als in talkwithoptimalen en kennisbank-zzl. Ze worden afgedwongen, niet alleen gevraagd: door de review
vóór elke commit (`.claude/settings.json`), door pre-commit en door CI (`.github/workflows/`).

- **Taal:** Nederlands in documentatie, commentaar, commitberichten en issues.
- **Commits en PR's:** een commitbericht is altijd één korte regel. Geen `Co-Authored-By`,
  geen "Generated with Claude Code" of andere toevoegingen, ook niet in PR-beschrijvingen.
- **PR-beschrijving:** kort en to the point: wat en waarom. Geen verslag van lokale tests; dat doet CI.
- **Review vóór elke commit** (hook in `.claude/settings.json`): a) kan het minder verbose, b) kan het slimmer en
  compacter (een beetje "black voodoo" op de juiste plek mag), c) geen bouwgeschiedenis in de code, d) comments en
  docstrings functioneel, zonder verwijzingen naar issues, praatplaten, planning of markdown in de repo. De
  geschiedenis staat in `docs/plannen/`, niet in de code.
- **Kritisch meedenken:** denk mee voorbij de vraag. Zie je dat een naam, opzet of keuze niet meer past bij waar het
  werk naartoe gaat, of dat een wijziging elders iets meeneemt (namen, links, docs, tests, talks), breng het in
  met een voorstel, liefst voordat het gemerged is.
- **Controleren voor een commit:** `pixi run pre-commit` en `pixi run test`, en bij wijzigingen aan de docs
  `pixi run quarto-render`. Elke wijziging die in de browser te zien is, loop je daar ook na.
- **Geen fallbacks in de code.** Het werkt, of het geeft een error. Dus geen standaardwaarden voor
  instellingen (`os.environ["X"]`, niet `os.environ.get("X", ...)`), geen `except` die een fout wegmoffelt.
  Een error is een signaal dat we iets moeten oplossen.
- **Geen monkeypatch in tests.** Test met echte invoer: geef afhankelijkheden mee als argument, gebruik `tmp_path`.
