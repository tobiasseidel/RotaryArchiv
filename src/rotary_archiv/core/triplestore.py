"""
Triple Store Interface für RDF-Relationen.

NOTE: Vorerst nicht verwendet - kann später wieder aktiviert werden.

Design-Vorgabe Erschließung: Die Quelle (Dokument, DocumentUnit) aus der
relationalen DB wird nicht als Subjekt oder Objekt der Faktentriples verwendet,
sondern nur als Referenz (Provenienz/Beleg). Empfohlenes Prädikat: rotary:belegtIn
mit Objekt rotary:DocumentUnit_<id> bzw. rotary:Document_<id>. Siehe docs/erschliessung.md.
"""

from contextlib import suppress
from pathlib import Path
import re
from typing import Any

import httpx
from rdflib import Graph, Literal, Namespace, URIRef

from src.rotary_archiv.config import settings

# Namespace für RotaryArchiv
ROTARY = Namespace("http://rotaryarchiv.local/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")
# Wikidata property direct (wie bei Wikidata speichern: wdt:P569 etc.)
WDT = Namespace("http://www.wikidata.org/prop/direct/")
SCHEMA = Namespace("http://schema.org/")


class TripleStore:
    """
    Interface für Triple Store (RDF)
    Unterstützt sowohl lokalen RDFLib Graph als auch Fuseki
    """

    def __init__(self, use_fuseki: bool = False, persistence_path: str | None = None):
        """
        Initialisiere Triple Store

        Args:
            use_fuseki: Wenn True, verwende Fuseki SPARQL Endpoint
            persistence_path: Bei use_fuseki=False: Pfad zu Turtle-Datei zum Laden/Speichern (persistent). Bei None: nur In-Memory.
        """
        self.use_fuseki = use_fuseki
        self.persistence_path = persistence_path if not use_fuseki else None
        self.graph = Graph()

        # Bind Namespaces
        self.graph.bind("rotary", ROTARY)
        self.graph.bind("wikidata", WIKIDATA)
        self.graph.bind("wdt", WDT)
        self.graph.bind("schema", SCHEMA)

        if use_fuseki:
            self.fuseki_url = settings.fuseki_url
            self.sparql_endpoint = f"{self.fuseki_url}/sparql"
        else:
            self.sparql_endpoint = None
            if self.persistence_path:
                path = Path(self.persistence_path)
                if path.exists():
                    with suppress(Exception):
                        self.graph.parse(path, format="turtle")

    def add_triple(
        self, subject: str, predicate: str, object_value: str, object_type: str = "uri"
    ) -> None:
        """
        Füge ein Triple hinzu

        Args:
            subject: Subjekt URI (z.B. "rotary:Document_123")
            predicate: Prädikat URI (z.B. "rotary:erwaehnt")
            object_value: Objekt (URI oder Literal)
            object_type: "uri" oder "literal"
        """
        subj = URIRef(subject)
        pred = URIRef(predicate)

        obj = URIRef(object_value) if object_type == "uri" else Literal(object_value)

        self.graph.add((subj, pred, obj))

        if self.use_fuseki:
            self._sync_to_fuseki()
        else:
            self._persist()

    def add_triples(self, triples: list[dict[str, Any]]) -> None:
        """
        Füge mehrere Triples hinzu

        Args:
            triples: Liste von Triple-Dicts mit keys: subject, predicate, object, object_type
        """
        for triple in triples:
            self.add_triple(
                triple["subject"],
                triple["predicate"],
                triple["object"],
                triple.get("object_type", "uri"),
            )

    def query(self, sparql_query: str) -> list[dict[str, Any]]:
        """
        Führe SPARQL Query aus

        Args:
            sparql_query: SPARQL Query String

        Returns:
            Liste von Ergebnis-Dicts
        """
        if self.use_fuseki and self.sparql_endpoint:
            return self._query_fuseki(sparql_query)
        else:
            return self._query_local(sparql_query)

    def _query_local(self, sparql_query: str) -> list[dict[str, Any]]:
        """Führe Query auf lokalem Graph aus"""
        results = []
        for row in self.graph.query(sparql_query):
            result = {}
            for key, value in row.asdict().items():
                result[key] = str(value)
            results.append(result)
        return results

    def _query_fuseki(self, sparql_query: str) -> list[dict[str, Any]]:
        """Führe Query auf Fuseki aus"""
        try:
            response = httpx.post(
                self.sparql_endpoint,
                data={"query": sparql_query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            # Parse SPARQL JSON Results
            results = []
            if "results" in data and "bindings" in data["results"]:
                for binding in data["results"]["bindings"]:
                    result = {}
                    for key, value in binding.items():
                        result[key] = value.get("value", "")
                    results.append(result)
            return results
        except Exception as e:
            raise Exception(f"Fuseki Query fehlgeschlagen: {e}") from e

    def _sync_to_fuseki(self) -> None:
        """Synchronisiere lokalen Graph zu Fuseki"""
        if not self.use_fuseki or not self.sparql_endpoint:
            return

        try:
            # Serialisiere Graph als Turtle
            ttl_data = self.graph.serialize(format="turtle")

            # Update Endpoint für Fuseki
            update_endpoint = f"{self.fuseki_url}/update"
            response = httpx.post(
                update_endpoint,
                data={"update": f"INSERT DATA {{ {ttl_data} }}"},
                headers={"Content-Type": "application/sparql-update"},
                timeout=30.0,
            )
            response.raise_for_status()
        except Exception as e:
            # Log error, aber nicht abbrechen
            print(f"Warnung: Fuseki Sync fehlgeschlagen: {e}")

    def _persist(self) -> None:
        """Speichere Graph in persistence_path (Turtle), falls konfiguriert."""
        if not self.persistence_path:
            return
        try:
            path = Path(self.persistence_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.graph.serialize(destination=str(path), format="turtle")
        except Exception:
            pass

    def add_person(
        self,
        person_uri: str,
        name: str,
        *,
        wikidata_id: str | None = None,
        claim_values: dict[str, Any] | None = None,
    ) -> None:
        """
        Person im Store anlegen (wikidata-aligned).
        person_uri: volle URI (z.B. str(ROTARY["Person_<uuid>"])).
        claim_values: z.B. {"P569": "1952-03-11"} → Triples person_uri wdt:P569 value.
        """
        self.add_triple(person_uri, str(ROTARY["name"]), name, "literal")
        if wikidata_id:
            wd_uri = str(WIKIDATA[wikidata_id])
            self.add_triple(person_uri, str(ROTARY["sameAs"]), wd_uri, "uri")
        if claim_values:
            for prop_id, value in claim_values.items():
                if value is None:
                    continue
                vals: list[str] = (
                    [value]
                    if isinstance(value, str)
                    else list(value)
                    if isinstance(value, (list, tuple))
                    else []
                )
                pred_uri = str(WDT[prop_id])
                for v in vals:
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    val_str = str(v).strip()
                    if re.match(r"^Q\d+$", val_str):
                        self.add_triple(
                            person_uri, pred_uri, str(WIKIDATA[val_str]), "uri"
                        )
                    else:
                        self.add_triple(person_uri, pred_uri, val_str, "literal")

    def add_place(
        self,
        place_uri: str,
        name: str,
        *,
        wikidata_id: str | None = None,
        main_image_url: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> None:
        """
        Ort (Place) im Store anlegen.
        place_uri: volle URI (z.B. str(ROTARY["Place_<uuid>"])).
        """
        self.add_triple(place_uri, str(ROTARY["name"]), name, "literal")
        if wikidata_id:
            wd_uri = str(WIKIDATA[wikidata_id])
            self.add_triple(place_uri, str(ROTARY["sameAs"]), wd_uri, "uri")
        if main_image_url and main_image_url.strip():
            self.add_triple(
                place_uri, str(ROTARY["mainImage"]), main_image_url.strip(), "literal"
            )
        if lat is not None:
            self.add_triple(place_uri, str(ROTARY["lat"]), str(lat), "literal")
        if lon is not None:
            self.add_triple(place_uri, str(ROTARY["lon"]), str(lon), "literal")

    def add_event(
        self,
        event_uri: str,
        name: str,
        *,
        wikidata_id: str | None = None,
        main_image_url: str | None = None,
    ) -> None:
        """Ereignis (Event) im Store anlegen."""
        self.add_triple(event_uri, str(ROTARY["name"]), name, "literal")
        if wikidata_id:
            self.add_triple(
                event_uri, str(ROTARY["sameAs"]), str(WIKIDATA[wikidata_id]), "uri"
            )
        if main_image_url and main_image_url.strip():
            self.add_triple(
                event_uri, str(ROTARY["mainImage"]), main_image_url.strip(), "literal"
            )

    def get_place_details(self, place_uri: str) -> dict[str, Any] | None:
        """
        Hole Orts-Daten aus dem Store (name, wikidata_id, main_image_url, lat, lon).
        place_uri: volle URI des Orts.
        """
        query_base = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?name ?wd ?img ?lat ?lon WHERE {{
            <{place_uri}> rotary:name ?name .
            OPTIONAL {{ <{place_uri}> rotary:sameAs ?wd }} .
            OPTIONAL {{ <{place_uri}> rotary:mainImage ?img }} .
            OPTIONAL {{ <{place_uri}> rotary:lat ?lat }} .
            OPTIONAL {{ <{place_uri}> rotary:lon ?lon }} .
        }}
        LIMIT 1
        """
        results = self.query(query_base)
        if not results:
            return None
        r = results[0]
        name = (r.get("name") or "").strip()
        wd = r.get("wd", "") or ""
        wikidata_id = None
        if "wikidata.org/entity/" in wd:
            wikidata_id = wd.split("entity/")[-1].split("/")[0].split("#")[0]
        main_image_url = (r.get("img") or "").strip() or None
        lat_val, lon_val = r.get("lat"), r.get("lon")
        lat = float(lat_val) if lat_val is not None and str(lat_val).strip() else None
        lon = float(lon_val) if lon_val is not None and str(lon_val).strip() else None
        return {
            "name": name,
            "wikidata_id": wikidata_id,
            "main_image_url": main_image_url,
            "lat": lat,
            "lon": lon,
        }

    def update_place(
        self,
        place_uri: str,
        name: str,
        *,
        wikidata_id: str | None = None,
        main_image_url: str | None = None,
        update_main_image: bool = False,
        lat: float | None = None,
        lon: float | None = None,
    ) -> None:
        """
        Ort im Store aktualisieren (name, optional sameAs, mainImage, lat, lon).
        Entfernt bestehende rotary:name, sameAs, mainImage, lat, lon und setzt die übergebenen Werte.
        mainImage wird nur geändert, wenn update_main_image=True; sonst beibehalten.
        """
        existing = self.get_place_details(place_uri)
        subj = URIRef(place_uri)
        rotary_ns = str(ROTARY)
        for pred_name in ["name", "sameAs", "mainImage", "lat", "lon"]:
            pred_uri = URIRef(rotary_ns + pred_name)
            for obj in list(self.graph.objects(subj, pred_uri)):
                self.graph.remove((subj, pred_uri, obj))
        if self.use_fuseki:
            self._sync_to_fuseki()
        else:
            self._persist()
        self.add_triple(place_uri, str(ROTARY["name"]), name, "literal")
        if wikidata_id:
            self.add_triple(
                place_uri, str(ROTARY["sameAs"]), str(WIKIDATA[wikidata_id]), "uri"
            )
        if update_main_image and main_image_url and main_image_url.strip():
            self.add_triple(
                place_uri, str(ROTARY["mainImage"]), main_image_url.strip(), "literal"
            )
        elif existing and existing.get("main_image_url"):
            self.add_triple(
                place_uri,
                str(ROTARY["mainImage"]),
                existing["main_image_url"],
                "literal",
            )
        if lat is not None:
            self.add_triple(place_uri, str(ROTARY["lat"]), str(lat), "literal")
        if lon is not None:
            self.add_triple(place_uri, str(ROTARY["lon"]), str(lon), "literal")

    def get_place_uri_by_name(self, name: str) -> str | None:
        """Finde einen Ort im Store anhand des Namens (exakter Literal-Match)."""
        name_clean = (name or "").strip()
        if not name_clean:
            return None
        safe = name_clean.replace("\\", "\\\\").replace('"', '\\"')
        rotary_ns = str(ROTARY)
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?uri WHERE {{
            ?uri rotary:name ?name .
            FILTER (?name = "{safe}")
            FILTER (STRSTARTS(STR(?uri), "{rotary_ns}Place_"))
        }}
        LIMIT 1
        """
        results = self.query(query)
        if results and "uri" in results[0]:
            return results[0]["uri"]
        return None

    def get_event_uri_by_name(self, name: str) -> str | None:
        """Finde ein Ereignis anhand des Namens (exakter Literal-Match)."""
        name_clean = (name or "").strip()
        if not name_clean:
            return None
        safe = name_clean.replace("\\", "\\\\").replace('"', '\\"')
        rotary_ns = str(ROTARY)
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?uri WHERE {{
            ?uri rotary:name ?name .
            FILTER (?name = "{safe}")
            FILTER (STRSTARTS(STR(?uri), "{rotary_ns}Event_"))
        }}
        LIMIT 1
        """
        results = self.query(query)
        if results and "uri" in results[0]:
            return results[0]["uri"]
        return None

    def add_mention(
        self,
        mention_uri: str,
        person_uri: str,
        belegt_in_uri: str,
        *,
        role: str | None = None,
    ) -> None:
        """
        Mention anlegen: Verknüpfung Box/Unit ↔ Entität (Person oder Place).
        belegt_in_uri: z.B. str(ROTARY["ErschliessungsBox_123"]) oder DocumentUnit_<id>.
        """
        self.add_triple(mention_uri, str(ROTARY["beziehtSichAuf"]), person_uri, "uri")
        self.add_triple(mention_uri, str(ROTARY["belegtIn"]), belegt_in_uri, "uri")
        if role:
            self.add_triple(mention_uri, str(ROTARY["rolle"]), role, "literal")

    def add_beleg(
        self,
        beleg_uri: str,
        belegt_in_uri: str,
        subject_uri: str,
        predicate_uri: str,
        object_uri: str,
    ) -> None:
        """Beleg-Knoten: Aussage (Subjekt, Prädikat, Objekt) mit Box als Quelle."""
        self.add_triple(beleg_uri, str(ROTARY["belegtIn"]), belegt_in_uri, "uri")
        self.add_triple(beleg_uri, str(ROTARY["aussageSubjekt"]), subject_uri, "uri")
        self.add_triple(
            beleg_uri, str(ROTARY["aussagePraedikat"]), predicate_uri, "uri"
        )
        self.add_triple(beleg_uri, str(ROTARY["aussageObjekt"]), object_uri, "uri")

    def add_statement_with_beleg(
        self,
        statement_uri: str,
        subject_uri: str,
        predicate_uri: str,
        object_uri: str,
        belegt_in_uri: str,
        *,
        page_uri: str | None = None,
    ) -> None:
        """Statement-Knoten mit Quelle (Box/optional Seite) anlegen."""
        self.add_triple(
            statement_uri, str(ROTARY["statementSubject"]), subject_uri, "uri"
        )
        self.add_triple(
            statement_uri, str(ROTARY["statementPredicate"]), predicate_uri, "uri"
        )
        self.add_triple(
            statement_uri, str(ROTARY["statementObject"]), object_uri, "uri"
        )
        self.add_triple(statement_uri, str(ROTARY["belegtIn"]), belegt_in_uri, "uri")
        if page_uri:
            self.add_triple(statement_uri, str(ROTARY["belegtIn"]), page_uri, "uri")

    def remove_statements_by_beleg(self, belegt_in_uri: str) -> int:
        """Entfernt alle Statement-Knoten, die über belegtIn an die Box gebunden sind."""
        stmt_pred = URIRef(str(ROTARY["belegtIn"]))
        stmt_subjects = list(self.graph.subjects(stmt_pred, URIRef(belegt_in_uri)))
        removed = 0
        for stmt in stmt_subjects:
            for s, p, o in list(self.graph.triples((stmt, None, None))):
                self.graph.remove((s, p, o))
                removed += 1
        if removed:
            if self.use_fuseki:
                self._sync_to_fuseki()
            else:
                self._persist()
        return removed

    def get_statement_by_beleg(self, belegt_in_uri: str) -> dict[str, Any] | None:
        """Liefert den ersten Statement-Knoten, der an der Box (belegtIn) hängt."""
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?stmt ?subject ?predicate ?object WHERE {{
            ?stmt rotary:belegtIn <{belegt_in_uri}> .
            ?stmt rotary:statementSubject ?subject .
            ?stmt rotary:statementPredicate ?predicate .
            ?stmt rotary:statementObject ?object .
        }}
        LIMIT 1
        """
        rows = self.query(query)
        if not rows:
            return None
        return {
            "statement_uri": rows[0].get("stmt"),
            "subject_uri": rows[0].get("subject"),
            "predicate_uri": rows[0].get("predicate"),
            "object_uri": rows[0].get("object"),
        }

    def list_statements_for_entity(self, entity_uri: str) -> list[dict[str, Any]]:
        """Alle Statements, in denen die Entität als Subject vorkommt."""
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?stmt ?predicate ?object ?beleg WHERE {{
            ?stmt rotary:statementSubject <{entity_uri}> .
            ?stmt rotary:statementPredicate ?predicate .
            ?stmt rotary:statementObject ?object .
            OPTIONAL {{ ?stmt rotary:belegtIn ?beleg }}
        }}
        """
        return self.query(query)

    def get_person_details(self, person_uri: str) -> dict[str, Any] | None:
        """
        Hole Person-Daten aus dem Store (Name, Wikidata-ID, alle WDT-claim_values, main_image_url).
        person_uri: volle URI der Person.
        """
        wdt_ns = str(WDT)
        # Basis: Name und sameAs
        query_base = f"""
        PREFIX rotary: <{ROTARY}>
        PREFIX wdt: <{wdt_ns}>
        SELECT ?name ?wd WHERE {{
            <{person_uri}> rotary:name ?name .
            OPTIONAL {{ <{person_uri}> rotary:sameAs ?wd }} .
        }}
        LIMIT 1
        """
        results = self.query(query_base)
        if not results:
            return None
        r = results[0]
        name = r.get("name", "").strip()
        wd = r.get("wd", "") or ""
        wikidata_id = None
        if "wikidata.org/entity/" in wd:
            wikidata_id = wd.split("entity/")[-1].split("/")[0].split("#")[0]
        # Alle WDT-Prädikate für diese Person
        query_claims = f"""
        PREFIX wdt: <{wdt_ns}>
        SELECT ?p ?o WHERE {{
            <{person_uri}> ?p ?o .
            FILTER (STRSTARTS(STR(?p), "{wdt_ns}"))
        }}
        """
        claim_results = self.query(query_claims)
        claim_values: dict[str, list[str]] = {}
        for row in claim_results:
            p_uri = row.get("p", "")
            o_val = (row.get("o") or "").strip()
            if p_uri and o_val:
                prop_id = p_uri.replace(wdt_ns, "").strip("/")
                if prop_id:
                    if "wikidata.org/entity/" in o_val:
                        q_id = o_val.split("entity/")[-1].split("/")[0].split("#")[0]
                        claim_values.setdefault(prop_id, []).append(q_id)
                    else:
                        claim_values.setdefault(prop_id, []).append(o_val)
        # mainImage (rotary:mainImage)
        query_img = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?img WHERE {{
            <{person_uri}> rotary:mainImage ?img .
        }}
        LIMIT 1
        """
        img_results = self.query(query_img)
        main_image_url: str | None = None
        if img_results and img_results[0].get("img"):
            main_image_url = img_results[0]["img"].strip()
        # Anzeigenamen pro (Property, Wert): rotary:claimValueLabel mit Literal "prop_id\x1fvalue\x1flabel"
        # Altes Format (claimValueLabel_P27) für Rückwärtskompatibilität mitlesen
        rotary_ns = str(ROTARY)
        claim_value_labels: dict[str, dict[str, str]] = {}
        query_labels_new = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?o WHERE {{
            <{person_uri}> rotary:claimValueLabel ?o .
        }}
        """
        sep = "\x1f"
        for row in self.query(query_labels_new):
            o_val = (row.get("o") or "").strip()
            if o_val and sep in o_val:
                parts = o_val.split(sep, 2)
                if len(parts) >= 3:
                    prop_id, value, label = (
                        parts[0].strip(),
                        parts[1].strip(),
                        parts[2].strip(),
                    )
                    if prop_id and value:
                        claim_value_labels.setdefault(prop_id, {})[value] = label
        prefix_old = rotary_ns + "claimValueLabel_"
        query_labels_old = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?p ?o WHERE {{
            <{person_uri}> ?p ?o .
            FILTER (STRSTARTS(STR(?p), "{prefix_old}"))
        }}
        """
        for row in self.query(query_labels_old):
            p_uri = row.get("p", "")
            o_val = (row.get("o") or "").strip()
            if p_uri and o_val and p_uri.startswith(prefix_old):
                prop_id = p_uri[len(prefix_old) :].split("/")[0].split("#")[0]
                if prop_id:
                    for val in claim_values.get(prop_id, []):
                        if (
                            prop_id not in claim_value_labels
                            or val not in claim_value_labels[prop_id]
                        ):
                            claim_value_labels.setdefault(prop_id, {})[val] = o_val
        return {
            "name": name,
            "wikidata_id": wikidata_id,
            "claim_values": claim_values,
            "claim_value_labels": claim_value_labels,
            "main_image_url": main_image_url,
        }

    def update_person(
        self,
        person_uri: str,
        name: str,
        *,
        wikidata_id: str | None = None,
        claim_values: dict[str, Any] | None = None,
        claim_value_labels: dict[str, str] | None = None,
        main_image_url: str | None = None,
        update_main_image: bool = False,
    ) -> None:
        """
        Person im Store aktualisieren (Name, optional sameAs, alle WDT-claims, optional
        Anzeigenamen für Objekt-Werte, optional mainImage).
        Entfernt alle WDT-Prädikate der Person, dann setzt nur die übergebenen claim_values.
        claimValueLabel_*-Prädikate werden ersetzt durch claim_value_labels.
        mainImage wird nur geändert, wenn update_main_image=True (sonst unverändert gelassen).
        """
        subj = URIRef(person_uri)
        wdt_ns = str(WDT)
        rotary_ns = str(ROTARY)
        claim_value_label_prefix = rotary_ns + "claimValueLabel_"
        # Name immer löschen und neu setzen
        for obj in list(self.graph.objects(subj, URIRef(str(ROTARY["name"])))):
            self.graph.remove((subj, URIRef(str(ROTARY["name"])), obj))
        if wikidata_id is not None:
            for obj in list(self.graph.objects(subj, URIRef(str(ROTARY["sameAs"])))):
                self.graph.remove((subj, URIRef(str(ROTARY["sameAs"])), obj))
        # Alle WDT-Prädikate für diese Person entfernen
        for s, p, o in list(self.graph.triples((subj, None, None))):
            if str(p).startswith(wdt_ns):
                self.graph.remove((s, p, o))
        # Alle claimValueLabel-Triples entfernen (altes und neues Format)
        for s, p, o in list(self.graph.triples((subj, None, None))):
            pstr = str(p)
            if pstr == rotary_ns + "claimValueLabel" or pstr.startswith(
                claim_value_label_prefix
            ):
                self.graph.remove((s, p, o))
        if update_main_image:
            for obj in list(self.graph.objects(subj, URIRef(str(ROTARY["mainImage"])))):
                self.graph.remove((subj, URIRef(str(ROTARY["mainImage"])), obj))
        if self.use_fuseki:
            self._sync_to_fuseki()
        else:
            self._persist()
        self.add_triple(person_uri, str(ROTARY["name"]), name, "literal")
        if wikidata_id:
            wd_uri = str(WIKIDATA[wikidata_id])
            self.add_triple(person_uri, str(ROTARY["sameAs"]), wd_uri, "uri")
        if claim_values:
            for prop_id, value in claim_values.items():
                if value is None:
                    continue
                vals: list[str] = (
                    [value]
                    if isinstance(value, str)
                    else list(value)
                    if isinstance(value, (list, tuple))
                    else []
                )
                pred_uri = str(WDT[prop_id])
                for v in vals:
                    if v is None or (isinstance(v, str) and not v.strip()):
                        continue
                    val_str = str(v).strip()
                    if re.match(r"^Q\d+$", val_str):
                        self.add_triple(
                            person_uri, pred_uri, str(WIKIDATA[val_str]), "uri"
                        )
                    else:
                        self.add_triple(person_uri, pred_uri, val_str, "literal")
        sep = "\x1f"
        if claim_value_labels:
            for prop_id, value_labels in claim_value_labels.items():
                if not prop_id or not isinstance(value_labels, dict):
                    continue
                for value, label in value_labels.items():
                    if isinstance(label, str) and label.strip():
                        self.add_triple(
                            person_uri,
                            str(ROTARY["claimValueLabel"]),
                            f"{prop_id}{sep}{value}{sep}{label.strip()}",
                            "literal",
                        )
        if update_main_image and main_image_url and main_image_url.strip():
            self.add_triple(
                person_uri, str(ROTARY["mainImage"]), main_image_url.strip(), "literal"
            )

    def get_person_uri_by_name(self, name: str) -> str | None:
        """
        Finde eine Person im Store anhand des Namens (exakter Literal-Match nach strip).
        Returns: person_uri (volle URI) oder None.
        """
        name_clean = (name or "").strip()
        if not name_clean:
            return None
        # SPARQL: Literal-Match (Escape Anführungszeichen im Namen)
        safe = name_clean.replace("\\", "\\\\").replace('"', '\\"')
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?person WHERE {{
            ?person rotary:name ?name .
            FILTER (?name = "{safe}")
        }}
        LIMIT 1
        """
        results = self.query(query)
        if results and "person" in results[0]:
            return results[0]["person"]
        return None

    def search_entities(
        self,
        name: str,
        entity_type: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Suche im internen Store nach Entitäten (Person oder Place) mit passendem Namen.
        name: Suchbegriff (Substring); entity_type z.B. "person" oder "place".
        Returns: Liste von {"uri": ..., "name": ...}.
        """
        name_clean = (name or "").strip()
        if not name_clean:
            return []
        safe = name_clean.replace("\\", "\\\\").replace('"', '\\"')
        rotary_ns = str(ROTARY)
        type_filter = ""
        if entity_type == "place":
            type_filter = f'FILTER (STRSTARTS(STR(?uri), "{rotary_ns}Place_"))'
        elif entity_type == "person":
            type_filter = f'FILTER (STRSTARTS(STR(?uri), "{rotary_ns}Person_"))'
        elif entity_type == "event":
            type_filter = f'FILTER (STRSTARTS(STR(?uri), "{rotary_ns}Event_"))'
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?uri ?name WHERE {{
            ?uri rotary:name ?name .
            FILTER (CONTAINS(LCASE(?name), LCASE("{safe}")))
            {type_filter}
        }}
        LIMIT {max(1, min(limit, 50))}
        """
        results = self.query(query)
        return [{"uri": r["uri"], "name": r.get("name", "")} for r in results]

    def get_entity_preview(self, entity_uri: str) -> dict[str, Any] | None:
        """
        Generische Vorschau für Dialoge (person/place/event): Name, sameAs, Bild, einfache claims.
        """
        if not entity_uri:
            return None
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?name ?wd ?img WHERE {{
            <{entity_uri}> rotary:name ?name .
            OPTIONAL {{ <{entity_uri}> rotary:sameAs ?wd }} .
            OPTIONAL {{ <{entity_uri}> rotary:mainImage ?img }} .
        }}
        LIMIT 1
        """
        rows = self.query(query)
        if not rows:
            return None
        row = rows[0]
        wdt_ns = str(WDT)
        claims_q = f"""
        SELECT ?p ?o WHERE {{
            <{entity_uri}> ?p ?o .
            FILTER (STRSTARTS(STR(?p), "{wdt_ns}"))
        }}
        LIMIT 20
        """
        claim_rows = self.query(claims_q)
        claims: dict[str, list[str]] = {}
        for cr in claim_rows:
            p = (cr.get("p") or "").replace(wdt_ns, "").strip("/")
            o = (cr.get("o") or "").strip()
            if p and o:
                if "wikidata.org/entity/" in o:
                    o = o.split("entity/")[-1].split("/")[0].split("#")[0]
                claims.setdefault(p, []).append(o)
        local = entity_uri.split("/")[-1].split("#")[0]
        entity_type = (
            "event"
            if local.startswith("Event_")
            else "place"
            if local.startswith("Place_")
            else "person"
        )
        wikidata_id = None
        wd = row.get("wd") or ""
        if "wikidata.org/entity/" in wd:
            wikidata_id = wd.split("entity/")[-1].split("/")[0].split("#")[0]
        return {
            "entity_uri": entity_uri,
            "entity_type": entity_type,
            "name": (row.get("name") or "").strip(),
            "wikidata_id": wikidata_id,
            "main_image_url": (row.get("img") or "").strip() or None,
            "claim_values": claims,
        }

    def get_document_entities(self, document_id: int) -> list[dict[str, Any]]:
        """
        Hole alle Entitäten für ein Dokument.

        HINWEIS: Entspricht dem alten Modell (Document als Subjekt).
        Für das Referenz-Modell (Quelle nur als Referenz) durch Abfragen
        über rotary:belegtIn / Mention ersetzen oder ergänzen. Siehe docs/erschliessung.md.

        Args:
            document_id: Dokument-ID

        Returns:
            Liste von Entitäten mit Typen
        """
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?entity ?type WHERE {{
            rotary:Document_{document_id} rotary:erwaehnt ?entity .
            ?entity rotary:entityType ?type .
        }}
        """
        return self.query(query)

    def get_entity_documents(self, entity_id: int) -> list[dict[str, Any]]:
        """
        Hole alle Dokumente für eine Entität.

        HINWEIS: Entspricht dem alten Modell (Document als Subjekt).
        Für das Referenz-Modell (Quelle nur als Referenz) durch Abfragen
        über rotary:belegtIn / Mention ersetzen oder ergänzen. Siehe docs/erschliessung.md.

        Args:
            entity_id: Entitäts-ID

        Returns:
            Liste von Dokumenten
        """
        query = f"""
        PREFIX rotary: <{ROTARY}>
        SELECT ?document WHERE {{
            ?document rotary:erwaehnt rotary:Entity_{entity_id} .
        }}
        """
        return self.query(query)

    def save_to_file(self, filepath: str, format: str = "turtle") -> None:
        """
        Speichere Graph in Datei

        Args:
            filepath: Pfad zur Datei
            format: Format (turtle, xml, json-ld, etc.)
        """
        self.graph.serialize(destination=filepath, format=format)

    def load_from_file(self, filepath: str, format: str = "turtle") -> None:
        """
        Lade Graph aus Datei

        Args:
            filepath: Pfad zur Datei
            format: Format (turtle, xml, json-ld, etc.)
        """
        self.graph.parse(filepath, format=format)


# Singleton-Instanz
_triple_store: TripleStore | None = None


def get_triplestore(use_fuseki: bool = False) -> TripleStore:
    """
    Hole Triple Store Instanz (Singleton)

    Args:
        use_fuseki: Verwende Fuseki statt lokalem Graph

    Returns:
        TripleStore Instanz
    """
    global _triple_store
    if _triple_store is None:
        path = None
        if not use_fuseki:
            p = getattr(settings, "triplestore_path", None)
            path = p if p and (not isinstance(p, str) or p.strip()) else None
        _triple_store = TripleStore(use_fuseki=use_fuseki, persistence_path=path)
    return _triple_store
