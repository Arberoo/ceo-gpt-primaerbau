/* ============================================================
   ablage.js — Cockpit-Tab: automatische Ablage.

   Dateien reinziehen, KI ordnet ein, EIN Klick legt alles ab. Bewusst schlicht:
   Drop-Zone oben, Stapel-Liste darunter, ein Knopf. Kein Bestaetigen pro Datei
   (das waere die Klick-Ermuedung vom 22.08.2026), sondern Korrigieren nur dort,
   wo der Vorschlag danebenliegt.

   Liegt hinter derselben Face-ID-Sperre wie Dokumentenakte/Vermoegen/Budget
   (Server-Gate auf /api/ablage, diese Datei zeichnet nur das Schloss).

   Drei Fallen, die hier beruecksichtigt sind:
   - Die Datei-Auswahl schickt die App kurz weg; beim Zurueckkommen baute der
     Auto-Refresh die Ansicht neu auf. Genau daran starb am 30.07.2026 jeder
     Bild-Upload. `filePickerBusy()` greift automatisch fuer input[type=file];
     waehrend des Uploads sperren wir zusaetzlich ueber setVoiceBusy().
   - `renderGen`: abgeraeumte Aufbauten duerfen nicht in die neue Ansicht
     schreiben (doppelter Kopf, zweimal Face ID - Fehler vom 11.08.2026).
   - Die Bausteine haben feste Signaturen: el(tag, cls, html) nimmt die Klasse
     als STRING, pageHead(root, {...}) haengt selbst an, guard(host, …) auch,
     schlossKnopf() liefert ein ARRAY, und icons() nimmt keine Argumente
     (Icons kommen als <i data-lucide="…">).
   ============================================================ */
import { register, el, esc, icons, apiGet, apiPost, toast, errorBox,
         cacheView, cachedView, setVoiceBusy } from '../core.js';
import { pageHead } from '../ui.js';
import { guard as passkeyGuard, schlossKnopf, status as passkeyStatus } from '../passkey.js';

let renderGen = 0;
let stilDa = false;

function injectStyle() {
  if (stilDa) return; stilDa = true;
  const s = document.createElement('style');
  s.textContent = `
  .ab-drop{border:2px dashed var(--border-strong);border-radius:14px;padding:26px 18px;
    text-align:center;color:var(--color-text-muted);cursor:pointer;
    transition:border-color .15s,background .15s}
  .ab-drop:hover,.ab-drop.an{border-color:var(--color-accent);background:var(--color-surface-2)}
  .ab-drop .ab-gross{font-size:15px;color:var(--color-text);margin-bottom:4px}
  .ab-liste{display:flex;flex-direction:column;border:1px solid var(--border);
    border-radius:14px;overflow:hidden;margin-top:16px}
  .ab-zeile{display:flex;gap:12px;align-items:flex-start;padding:11px 14px;
    border-bottom:1px solid var(--border);flex-wrap:wrap}
  .ab-zeile:last-child{border-bottom:none}
  .ab-zeile.auffang{background:color-mix(in srgb,var(--color-warn) 7%,transparent)}
  .ab-haupt{flex:1 1 260px;min-width:0}
  .ab-name{font-size:13px;color:var(--color-text);word-break:break-all}
  .ab-alt{text-decoration:line-through;color:var(--color-text-muted);margin-right:6px}
  .ab-warum{font-size:12px;color:var(--color-text-muted);margin-top:3px}
  .ab-ziel{flex:0 1 300px;min-width:0}
  .ab-sel{width:100%;background:var(--color-surface);border:1px solid var(--border-strong);
    border-radius:var(--radius-md);color:var(--color-text);padding:6px 9px;font-size:12.5px}
  .ab-weg{flex:0 0 auto;background:none;border:none;color:var(--color-text-muted);
    cursor:pointer;padding:4px;border-radius:6px;line-height:0}
  .ab-weg:hover{color:var(--color-err)}
  .ab-fuss{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:14px}
  .ab-hinweis{font-size:12px;color:var(--color-text-muted);margin-top:16px}
  @media(max-width:760px){.ab-ziel{flex:1 1 100%}}
  `;
  document.head.appendChild(s);
}

const B2 = b => b > 1048576 ? (b / 1048576).toFixed(1) + ' MB'
                            : Math.max(1, Math.round(b / 1024)) + ' KB';

register({
  id: 'ablage', label: 'Ablage', icon: 'folder-input', group: 'du', order: 7,
  warm: [{ key: 'ablage', url: '/api/ablage' }],

  async render(root) {
    const meineGen = ++renderGen;
    const veraltet = () => meineGen !== renderGen;
    injectStyle();

    const host = el('div');
    root.appendChild(host);
    let daten = cachedView('ablage');
    let schlossStatus = null;
    let puls = null;

    async function hole() {
      const d = await apiGet('/api/ablage');
      if (!veraltet()) { daten = d; cacheView('ablage', d); }
      return d;
    }

    function pulsStop() { clearInterval(puls); puls = null; }

    function pulsStart() {
      pulsStop();
      let n = 0;
      puls = setInterval(async () => {
        if (veraltet() || ++n > 40) return pulsStop();
        try { await hole(); } catch (e) { return; }
        if (!veraltet()) zeichne();
        if (daten && daten.vorschlag_id) pulsStop();
      }, 3000);
    }

    async function upload(files) {
      const liste = [...(files || [])].slice(0, 15);
      if (!liste.length) return;
      // Waehrend des Uploads darf der Auto-Refresh die Ansicht nicht abraeumen.
      setVoiceBusy(true);
      try {
        const dateien = [];
        for (const f of liste) {
          const b64 = await new Promise((ok, err) => {
            const r = new FileReader();
            r.onload = () => ok(String(r.result).split(',')[1] || '');
            r.onerror = err;
            r.readAsDataURL(f);
          });
          dateien.push({ name: f.name, daten: b64 });
        }
        const res = await apiPost('/api/ablage/upload', { dateien });
        (res.fehler || []).forEach(f => toast(f, { type: 'warn' }));
        if (res.angenommen) {
          toast(`${res.angenommen} Datei${res.angenommen > 1 ? 'en' : ''} im Eingang, liest…`,
                { type: 'success' });
          await apiPost('/api/ablage/einordnen', {});
          pulsStart();
        }
      } catch (e) {
        toast('Upload fehlgeschlagen: ' + (e.message || e), { type: 'error' });
      } finally {
        setVoiceBusy(false);
        try { await hole(); } catch (e) { /* Anzeige bleibt stehen */ }
        if (!veraltet()) zeichne();
      }
    }

    function zeichneInhalt() {
      const eing = (daten && daten.eingang) || [];
      const orte = (daten && daten.orte) || [];

      // --- Drop-Zone
      const drop = el('div', 'ab-drop',
        '<div class="ab-gross">Dateien hierher ziehen</div>'
        + '<div>PDF, Word, Excel, Scans und Fotos. Bis 15 auf einmal.</div>');
      const feld = el('input');
      feld.type = 'file';
      feld.multiple = true;
      feld.style.display = 'none';
      feld.accept = '.pdf,.docx,.doc,.xlsx,.xls,.png,.jpg,.jpeg,.heic,.webp,.txt,.md,.csv';
      drop.appendChild(feld);
      drop.onclick = () => feld.click();
      feld.onchange = () => { upload(feld.files); feld.value = ''; };
      ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => {
        e.preventDefault(); drop.classList.add('an');
      }));
      ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => {
        e.preventDefault(); drop.classList.remove('an');
      }));
      drop.addEventListener('drop', e => upload(e.dataTransfer && e.dataTransfer.files));
      host.appendChild(drop);

      // --- Stapel
      if (!eing.length) {
        host.appendChild(el('p', 'ab-hinweis', 'Nichts im Eingang.'));
      } else {
        const liste = el('div', 'ab-liste');
        eing.forEach(e => {
          const v = e.vorschlag || {};
          const istAuffang = v.ziel_id === 'auffang';
          const z = el('div', 'ab-zeile' + (istAuffang ? ' auffang' : ''));

          const haupt = el('div', 'ab-haupt');
          const neu = (v.dateiname || '').trim();
          haupt.appendChild(el('div', 'ab-name', neu
            ? `<span class="ab-alt">${esc(e.orig_name)}</span>${esc(neu)}`
            : esc(e.orig_name)));
          const warum = v.beschreibung || e.fehler
            || (e.status === 'neu' || e.status === 'gelesen' ? 'wird gelesen …' : '');
          haupt.appendChild(el('div', 'ab-warum',
            esc(B2(e.groesse || 0)) + (warum ? ' · ' + esc(warum) : '')));
          z.appendChild(haupt);

          const zielBox = el('div', 'ab-ziel');
          const sel = el('select', 'ab-sel');
          orte.forEach(o => {
            const opt = el('option', null, esc(o.label));
            opt.value = o.id;
            if (o.id === v.ziel_id) opt.selected = true;
            sel.appendChild(opt);
          });
          const bh = el('option', null, 'Buchhaltung (eigener Weg)');
          bh.value = 'buchhaltung';
          if (v.ziel_id === 'buchhaltung') bh.selected = true;
          sel.appendChild(bh);
          sel.dataset.eingang = e.id;
          zielBox.appendChild(sel);
          z.appendChild(zielBox);

          const weg = el('button', 'ab-weg', '<i data-lucide="x"></i>');
          weg.title = 'Verwerfen';
          weg.onclick = async () => {
            await apiPost('/api/ablage/verwerfen', { id: e.id });
            await hole(); if (!veraltet()) zeichne();
          };
          z.appendChild(weg);
          liste.appendChild(z);
        });
        host.appendChild(liste);

        const fuss = el('div', 'ab-fuss');
        if (daten.vorschlag_id) {
          const knopf = el('button', 'btn btn-primary',
            `${eing.length} ${eing.length === 1 ? 'Datei' : 'Dateien'} ablegen`);
          knopf.onclick = async () => {
            knopf.disabled = true; knopf.textContent = 'Lege ab …';
            // Korrekturen gehen als geaenderter PAYLOAD mit - derselbe Weg, den
            // auch der Feed benutzt. decide() ersetzt den payload ohnehin.
            const korr = {};
            host.querySelectorAll('select.ab-sel')
                .forEach(s => { korr[s.dataset.eingang] = s.value; });
            const pl = JSON.parse(JSON.stringify(daten.vorschlag_payload || {}));
            (pl.actions || []).forEach(a => {
              const eid = a.args && a.args.eingang_id;
              if (eid && korr[eid] && korr[eid] !== a.args.ziel_id) {
                a.args.ziel_id = korr[eid];
                a.args.dateiname = ''; // von Hand umgelenkt: Originalname behalten
              }
            });
            try {
              await apiPost('/api/agents/proposal/decide',
                { id: daten.vorschlag_id, entscheidung: 'freigeben', payload: pl });
              toast('Abgelegt', { type: 'success' });
            } catch (err) {
              toast('Fehlgeschlagen: ' + (err.message || err), { type: 'error' });
            }
            await hole(); if (!veraltet()) zeichne();
          };
          fuss.appendChild(knopf);
        } else {
          const jetzt = el('button', 'btn', 'Einordnen lassen');
          jetzt.onclick = async () => {
            jetzt.disabled = true; jetzt.textContent = 'Liest …';
            await apiPost('/api/ablage/einordnen', {});
            pulsStart();
          };
          fuss.appendChild(jetzt);
        }
        host.appendChild(fuss);
      }

      // --- Ordner-Pflege: nur EINE Zeile, damit man sich nicht wundert, warum
      // ein frisch angelegter Ordner nie gewaehlt wird.
      const fuss2 = el('div', 'ab-fuss');
      const akt = el('button', 'btn btn-ghost', 'Ordner neu einlesen');
      akt.onclick = async () => {
        akt.disabled = true; akt.textContent = 'Liest …';
        try { await apiGet('/api/ablage/orte'); } catch (e) { /* Anzeige bleibt */ }
        await hole(); if (!veraltet()) zeichne();
      };
      fuss2.appendChild(akt);
      if (daten && daten.ohne_zweck) {
        const zk = el('button', 'btn btn-ghost',
          `${daten.ohne_zweck} Ordner ohne Zweck beschreiben lassen`);
        zk.onclick = async () => {
          zk.disabled = true; zk.textContent = 'Denkt nach …';
          try {
            const r = await apiPost('/api/ablage/zwecke', { aktion: 'vorschlagen' });
            const v = (r && r.vorschlaege) || {};
            if (!Object.keys(v).length) toast('Kein Vorschlag gekommen', { type: 'warn' });
            else {
              await apiPost('/api/ablage/zwecke', { zwecke: v });
              toast(`${Object.keys(v).length} Ordner beschrieben`, { type: 'success' });
            }
          } catch (e) { toast('Fehlgeschlagen', { type: 'error' }); }
          await hole(); if (!veraltet()) zeichne();
        };
        fuss2.appendChild(zk);
      }
      host.appendChild(fuss2);
      icons();
    }

    async function zeichne() {
      if (veraltet()) return;
      host.innerHTML = '';

      const aktionen = [];
      schlossKnopf(schlossStatus, neuLaden).forEach(b => aktionen.push(b));
      pageHead(host, {
        eyebrow: 'Du', title: 'Ablage',
        desc: 'Dateien reinziehen, einordnen lassen, mit einem Klick ablegen.',
        actions: aktionen.length ? aktionen : null,
      });

      if (!daten) { host.appendChild(el('div', 'empty', 'Lädt…')); return; }
      if (daten.error) { host.appendChild(errorBox(daten.error)); return; }
      zeichneInhalt();
    }

    async function neuLaden() {
      try { schlossStatus = await passkeyStatus(); } catch (e) { schlossStatus = null; }
      if (veraltet()) return;
      host.innerHTML = '';
      // Wache VOR dem Zeichnen, auch vor dem Zwischenspeicher: sonst blitzen
      // Dokument-Inhalte aus der letzten Sitzung auf, obwohl gesperrt ist.
      const offen = await passkeyGuard(host, neuLaden, schlossStatus);
      if (veraltet() || !offen) return;
      try { await hole(); } catch (e) {
        if (!veraltet()) { host.innerHTML = ''; host.appendChild(errorBox(e.message || e)); }
        return;
      }
      if (!veraltet()) zeichne();
    }

    await neuLaden();
    return () => { pulsStop(); };
  },
});
