"""Agent: automatische Ablage auf dem BÜNDEL-Modell (seit 31.08.2026).

Vorgabe: „Ich lade Dokumente hoch, du schaust sie dir vollumfänglich
an (Titel, Metadaten, Inhalt) und ordnest das automatisch ein."

Läuft auf demselben Motor wie die anderen fünf und erbt damit automatisch:
Prime-Fork, die geteilten Regeln, Belege-Gegenprüfung, Recherche-Spur +
Klartext, Lernen aus Entscheidungen, Freigabe-Fluss. NICHTS davon ist hier
nachgebaut - genau deshalb ist ein neuer Agent auf diesem Framework so klein.

EIN STAPEL IST EIN VORSCHLAG, nicht zwölf. Das nutzt das bestehende Bündel-
Modell ohne jede Erweiterung: payload.actions = zwölf `datei_ablegen`,
execute_bundle führt sie mit continue-all aus und schreibt jeden Schritt ins
Audit. Zwölf einzelne Karten wären genau die Klick-Ermüdung vom 22.08.2026
(„wer den ganzen Tag Belangloses bestätigt, klickt die Rückfrage blind weg").

Das URTEIL liegt beim Modell, die SPERREN liegen im Code (ablage.pruefe_aktionen):
gültige ziel_id, Dateiname, Buchhaltungs-Ausschluss, keine vergessene Datei.
"""
from apps.dashboard import ablage, agent_base, branding


class Agent(agent_base.Agent):
    name = "ablage"
    label = "Ablage"
    interval_hours = 0.1 # ~6 Min. Billig: der Lauf schaut nur in die lokale
                             # Eingangs-Tabelle; das LLM startet erst, wenn
                             # wirklich Dateien liegen. Wer etwas reinzieht, will
                             # nicht eine Viertelstunde auf den Vorschlag warten.
    MAX_PER_RUN = 1 # ein Stapel je Lauf

    def voice(self):
        chef = branding.owner()
        return agent_base.stimme(
            f"Du sortierst für {chef} Dokumente in seine Ablage ein: du liest jede "
            "Datei vollständig, erkennst, worum es geht, und legst sie an den Platz, "
            "an dem er sie später sucht.")

    def _system(self, orte):
        from apps.dashboard import agent_prime
        lessons = self.lessons()
        return (agent_prime.get_brief() + "\n\n" + self.voice()
                + (lessons if lessons.strip() else "")
                + ablage.system_regeln(orte))

    def propose(self, eintraege=None, register=True, feedback=None):
        # FRISCH scannen (Vorgabe 31.08.2026): ein Ordner, den er heute
        # angelegt hat, muss heute wählbar sein. Der Scan kostet ein bis zwei
        # Sekunden, der LLM-Aufruf danach zehn bis dreißig.
        from apps.dashboard import ablage_struktur
        orte = ablage_struktur.orte(frisch=True)

        eintraege = eintraege if eintraege is not None else ablage.lesen()
        if not eintraege:
            return None, "Nichts im Eingang.", []

        task = ablage.task(eintraege)
        if feedback:
            task += (f"\n\nWICHTIG: {branding.owner()} hat zu deinem letzten Vorschlag "
                     f"dieses Feedback gegeben: «{feedback}». Setz es VOLLSTÄNDIG um "
                     "und ordne neu ein.")

        text, actions = agent_base.research_actions(
            task, system=self._system(orte), agent=self.name)
        if text is None:
            raise RuntimeError(agent_base.letzter_fehler() or "Lauf gescheitert")

        # DIE SPERRE: gegen die echte Orte-Liste halten, nichts durchrutschen lassen.
        actions = ablage.pruefe_aktionen(actions or [], eintraege, orte)
        if not actions:
            return None, text or "Nichts einzuordnen.", []

        from apps.dashboard.agents import actions_tools as _AT
        optionen = _AT.in_optionen(actions)
        if not optionen:
            return None, text, []
        actions = optionen[0]["actions"]

        for e in eintraege:
            ablage_eintrag = next(
                (a for a in actions if a.get("args", {}).get("eingang_id") == e["id"]), None)
            from apps.dashboard import ablage_eingang
            ablage_eingang.setze_status(e["id"], "vorgeschlagen",
                                        vorschlag=(ablage_eintrag or {}).get("args"))

        n = len(actions)
        summary = (text or "").strip() or "Stapel eingeordnet, Ziele siehe Liste."
        stapel_id = "stapel-" + "-".join(sorted(e["id"][-6:] for e in eintraege))[:60]
        item = None
        if register:
            from apps.dashboard import agent_proposals
            item = agent_proposals.add_proposal(
                agent=self.name, kind="ablage",
                title=f"{n} Dokument{'e' if n != 1 else ''} einordnen",
                summary=summary,
                payload={"stapel_id": stapel_id, "actions": actions,
                         "optionen": optionen if len(optionen) > 1 else None,
                         "anlass": {"von": "Eingangsfach",
                                    "text": "Liegt im Eingang: "
                                            + ", ".join(e.get("orig_name", "?")
                                                        for e in eintraege[:8])}})
        return item, summary, actions

    def recompose_from_payload(self, payload, feedback):
        from apps.dashboard import ablage_eingang
        ids = [a.get("args", {}).get("eingang_id")
               for a in (payload or {}).get("actions") or []]
        eintraege = [ablage_eingang.holen(i) for i in ids if i]
        eintraege = [e for e in eintraege
                     if e and e.get("status") not in ("abgelegt", "abgelehnt")]
        if not eintraege:
            return None, "Die Dateien sind nicht mehr offen.", []
        return self.propose(ablage.lesen([e["id"] for e in eintraege]),
                            register=False, feedback=feedback)

    def run(self, max_n=None):
        from apps.dashboard import agent_proposals
        # Liegt schon ein offener Stapel-Vorschlag, wird kein zweiter gebaut:
        # sonst stünden dieselben Dateien doppelt zur Freigabe.
        offen = [p for p in agent_proposals.raw_proposals()
                 if p.get("agent") == self.name and p.get("status") == "entwurf"]
        if offen:
            return 0
        eintraege = ablage.lesen()
        if not eintraege:
            return 0
        item, _text, _actions = self.propose(eintraege)
        return 1 if item else 0

    def execute(self, proposal):
        from apps.dashboard import agent_actions
        actions = (proposal.get("payload") or {}).get("actions") or []
        if not actions:
            return False, "kein Aktions-Bündel"
        # execute_bundle liefert DREI Werte; der Freigabe-Weg erwartet ZWEI
        # (26.08.2026: roh durchgereicht gab es "too many values to unpack").
        ok, summary, _results = agent_actions.execute_bundle(actions)
        return ok, summary


if __name__ == "__main__":
    # Handlauf: `.venv/bin/python -m apps.dashboard.agents.ablage_agent`
    # (--schreiben legt die Karte an, ohne Flag nur zeigen, was er vorhaette).
    import argparse
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parents[3] / "scripts"))
    import config # noqa: F401 (laedt die Zugangsdaten wie die anderen Handlaeufe)

    ap = argparse.ArgumentParser(description="Eingangsfach einordnen")
    ap.add_argument("--schreiben", action="store_true",
                    help="Vorschlags-Karte anlegen (Freigabe passiert im Cockpit)")
    args = ap.parse_args()

    agent = Agent()
    item, text, actions = agent.propose(register=args.schreiben)
    print("\n=== Begruendung ===")
    print((text or "").strip()[:800])
    print("\n=== Vorgeschlagene Ablage ===")
    for a in actions:
        ar = a.get("args", {})
        print(f" {a.get('beschreibung')}")
        print(f" ziel={ar.get('ziel_id')} neuer Name={ar.get('dateiname') or '(bleibt)'}")
        if ar.get("beschreibung"):
            print(f" warum: {ar['beschreibung'][:160]}")
    if args.schreiben and item:
        print(f"\nKarte angelegt: {item.get('id')} (Freigabe im Cockpit)")
