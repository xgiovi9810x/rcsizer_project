# rcsizer — WP0

Core per il tool di dimensionamento RC (specifica v2). Include:
1. `DesignState` immutabile, serializzabile, con provenance per valore derivato.
2. Schema di input (sez. 3) in Pydantic v2: SI interni, `{value, unit}` accettati.
3. Conversione mm/g/deg -> SI al bordo di I/O (units.py).
4. Preset per tipo da `config/presets/`, materiali da `config/materials/`.
5. Registro moduli auto-scansionato (`modules/`) con interfaccia name/version/requires/provides/run.
6. Motore pipeline da `pipeline.yaml` con topo-sort e fallback su cicli.
7. Coefficienti empirici [E] isolati in `coefficients.yaml`.
8. Test di accettazione: rifiuto input errato, round-trip JSON, modulo finto con una sola cartella.
9. `schema.json` generabile via `scripts/generate_schema.py`.
10. CLI minima: `python -m rcsizer input.json [pipeline.yaml]`.
