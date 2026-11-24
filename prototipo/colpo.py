#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GTA TACTICS (titolo di lavoro) — prototipo usa-e-getta di UN colpo.

Serve a una cosa sola: capire se "pianifico e poi guardo" diverte.
Non è la base del gioco in Godot. Usa solo la libreria standard.

Uso:
    python3 colpo.py            nuovo colpo a caso
    python3 colpo.py 4821       rigioca la gioielleria n. 4821
                                (stessa gioielleria, stessa banda disponibile,
                                 stesso magazzino; mazzo e dadi cambiano)
    python3 colpo.py --carte    stampa personaggi, attrezzi, fatti e mazzo ed esce

Il motore (classe Colpo) è separato dall'interfaccia: il notebook analisi.ipynb
lo importa per simulare migliaia di colpi.
"""
from __future__ import annotations

import datetime
import itertools
import math
import os
import random
import sys
import textwrap
from dataclasses import dataclass, replace

# ════════════════════════════════════════════════════════════════════
#  TARATURA — tutti i numeri del gioco stanno qui
# ════════════════════════════════════════════════════════════════════
MEZZE_GIORNATE = 4       # tempo prima che la merce venga spostata: ognuna è un sopralluogo o un riposo
RIPOSO_FINO_A = 0        # il riposo rimette in sesto chi è a pezzi (-1 -> 0), non porta «in forma»
MEMBRI_FUORI = 1         # quanti dei 5 oggi non sono disponibili
ATTREZZI_IN_MAGAZZINO = 2    # già vostri: portarli non costa niente
ATTREZZI_INTROVABILI = 1     # oggi in piazza non si trovano
PREZZI = {"silenziata": 25, "fucile": 10, "disturbatore": 20,   # migliaia di euro, per quelli da comprare
          "trapano": 20, "auto": 25, "scanner": 10}
SOGLIA_ALLARME = 4       # rumore a cui scatta l'allarme
PASSO_FRETTA = 2         # dopo l'allarme, ogni tot rumore in più la polizia arriva una battuta prima
INTERVENTI_BASE = 2      # telefonate dal vivo
MAX_BOTTINO = 3          # battute di bottino al massimo
MAX_PIANI_B = 2
VALORE_SACCA = 50        # migliaia di euro per sacca
COSTO_CALORE = 20        # migliaia per punto di calore: avvocati, mazzette, settimane fermo
COSTO_FERITO = 30        # medico che non fa domande
COSTO_ARRESTO = 50       # avvocato, e silenzio comprato
CONTO_DISASTRO = -200    # tutti dentro

SOGLIA_INGRESSO = 5
SOGLIA_SALA = 5
SOGLIA_EROE = 6
SOGLIA_PANICO = 6
SOGLIA_USCITA_POLIZIA = 7
SOGLIA_FUGA = 5
SOGLIA_CASSAFORTE = {"vecchia": 5, "moderna": 8, "a tempo": 6}
BONUS_TRAPANO = 3
BONUS_FUCILE = 3
BONUS_SILENZIATA = 1
RUMORE_ATTESA = 1        # per ogni battuta di bottino dopo la prima: più restate, più vi notano
SACCHE_CASSAFORTE = (4, 2, 1)   # 1ª, 2ª, 3ª apertura riuscita: il meglio sta sopra
SACCHE_VETRINE = 1       # prova fallita: solo vetrine
MOD_GUARDIA = {"assente": 0, "anziana": 1, "armata": 3}
TESTIMONI = {"vuoto": 0, "qualche cliente": 2, "pieno": 4}
RITARDO_POLIZIA = {"sirena": 2, "centrale": 0, "silenzioso": 1}
RITARDO_DISTURBATORE = 2
RITARDO_OSTAGGIO = 2
FORMA_PESI = {-1: 25, 0: 50, 1: 25}


@dataclass(frozen=True)
class Personaggio:
    id: str
    corto: str
    nome: str
    sf: int        # sangue freddo
    mani: int
    volante: int
    quota: int     # % del bottino
    difetto: str
    nota: str


PERSONAGGI = {p.id: p for p in [
    Personaggio("nico", "Nico", "Nico «il Chirurgo»", 2, 4, 1, 25, "Perfezionista",
                "Alla cassaforte ignora il primo ordine di uscire: fa ancora una battuta di bottino."),
    Personaggio("vera", "Vera", "Vera «la Gelida»", 4, 2, 2, 15, "Ricercata",
                "+2 calore se restano due o più testimoni."),
    Personaggio("tony", "Tony", "Tony «Pompa»", 3, 1, 2, 15, "Grilletto facile",
                "In sala usa sempre il suo ferro, mai silenziato: se fallisce una prova spara. Un ferito, +2 rumore."),
    Personaggio("samir", "Samir", "Samir «il Tassista»", 2, 1, 4, 15, "Nervoso",
                "Al volante: -1 alla fuga per ogni battuta di bottino oltre la prima."),
    Personaggio("lea", "Lea", "Lea «la Nipote»", 2, 3, 3, 10, "Chiacchierona",
                "+1 calore sempre; +2 in più se la arrestano."),
]}
STAT = {"sf": "Sangue freddo", "mani": "Mani", "volante": "Volante"}
FORMA = {-1: "a pezzi", 0: "normale", 1: "in forma"}


def ferito_a(pid):
    return "ferita" if PERSONAGGI[pid].corto.endswith("a") else "ferito"


@dataclass(frozen=True)
class Attrezzo:
    id: str
    nome: str
    prezzo: int    # migliaia di euro, se va comprato
    da: str
    toglie: str


EQUIP = {e.id: e for e in [
    Attrezzo("silenziata", "Pistola silenziata", PREZZI["silenziata"],
             f"Sala +{BONUS_SILENZIATA}. Se si spara alla guardia, non fa rumore.", "Tony non la usa: spara col suo ferro."),
    Attrezzo("fucile", "Fucile a pompa", PREZZI["fucile"],
             f"Sala +{BONUS_FUCILE}.", "+1 calore. Se la sala sfugge parte un colpo: un ferito, +2 rumore."),
    Attrezzo("disturbatore", "Disturbatore", PREZZI["disturbatore"],
             "La polizia arriva 2 battute dopo. Contro la centrale è l'unica cosa che dà tempo.",
             "Inutile se l'allarme è una sirena locale."),
    Attrezzo("trapano", "Trapano termico", PREZZI["trapano"],
             f"Mani +{BONUS_TRAPANO} sulla cassaforte. Apre la moderna e quella a tempo.",
             "+1 rumore a ogni battuta di bottino."),
    Attrezzo("auto", "Auto veloce", PREZZI["auto"],
             "Fuga +2.", "+1 calore: la notano tutti."),
    Attrezzo("scanner", "Scanner radio", PREZZI["scanner"],
             "Vedi il conto alla rovescia della polizia, senti l'allarme silenzioso, +1 intervento.",
             "Non aiuta nessuna prova."),
]}
ARMI = ("silenziata", "fucile")

# fatto -> (titolo, [(valore, peso %, cosa cambia)])
FATTI = {
    "guardia": ("Guardia", [
        ("assente", 40, f"nessuna guardia: sala a soglia {SOGLIA_SALA}."),
        ("anziana", 35, f"sala a soglia {SOGLIA_SALA + MOD_GUARDIA['anziana']}; se la sala sfugge preme "
                        "l'antipanico (+1 rumore)."),
        ("armata", 25, "senza un'arma in sala (pistola, fucile, o Tony col suo ferro) non c'è prova: "
                       f"un ferito e l'allarme. Con un'arma: sala a soglia {SOGLIA_SALA + MOD_GUARDIA['armata']}."),
    ]),
    "allarme": ("Allarme", [
        ("sirena", 34, f"sirena locale: polizia sul posto {RITARDO_POLIZIA['sirena']} battute dopo. Il disturbatore non serve."),
        ("centrale", 33, "collegato alla centrale: se scatta, la polizia è sul posto alla battuta dopo. "
                         f"Solo il disturbatore vi dà tempo ({RITARDO_DISTURBATORE} battute)."),
        ("silenzioso", 33, f"polizia sul posto {RITARDO_POLIZIA['silenzioso']} battuta dopo, e la banda non se ne accorge: il piano B «allarme» "
                           "non scatta, a meno che tu l'abbia verificato o abbia lo scanner."),
    ]),
    "cassaforte": ("Cassaforte", [
        ("vecchia", 40, f"soglia {SOGLIA_CASSAFORTE['vecchia']}."),
        ("moderna", 35, f"si apre solo col trapano, oppure con Nico alla cassaforte (soglia {SOGLIA_CASSAFORTE['moderna']}). "
                        "Altrimenti solo vetrine."),
        ("a tempo", 25, f"soglia {SOGLIA_CASSAFORTE['a tempo']}, ma alla prima battuta di bottino è ancora chiusa: solo vetrine "
                        "(il trapano la apre lo stesso)."),
    ]),
    "affluenza": ("Affluenza", [
        ("vuoto", 30, "nessun testimone, nessun cliente eroe."),
        ("qualche cliente", 45, "2 testimoni."),
        ("pieno", 25, "4 testimoni e sala +1 di soglia."),
    ]),
}

CARTE = {
    "liscio": ("Tutto liscio", "Non succede niente."),
    "pattuglia": ("Pattuglia di passaggio", "+1 rumore. Se esce durante la fuga: fuga -2."),
    "eroe": ("Cliente eroe", "Se siete dentro e c'è gente: prova di Sangue freddo (soglia 6) o +2 rumore; senza un'arma, chi è in sala resta ferito."),
    "telefonino": ("Telefonino", "Qualcuno filma: +2 testimoni (+1 se non c'è nessuno dentro)."),
    "traffico": ("Traffico", "Fuga -1, quando esce esce."),
    "corriere": ("Corriere alla porta", "Se siete dentro: +1 rumore."),
    "nervi": ("Nervi", "+1 rumore per ogni membro della banda a pezzi."),
    "fortuna": ("Colpo di fortuna", "Se siete in sala o sul bottino: +1 sacca."),
}
MAZZO = ["liscio"] * 3 + ["pattuglia", "eroe", "telefonino", "traffico", "corriere", "nervi", "fortuna"]

CONDIZIONI = {
    "allarme": "scatta l'allarme",
    "guardia": "la guardia reagisce",
    "ferito": "un uomo è ferito",
    "sirene": "si sentono le sirene (polizia a una battuta)",
}
RISPOSTE = {
    "fuori": "fuori subito",
    "ostaggio": "prendi un ostaggio",
    "lascia": "lascia il ferito",
    "continua": "continua comunque",
}
RISPOSTE_VALIDE = {
    "allarme": ("fuori", "ostaggio", "continua"),
    "guardia": ("fuori", "ostaggio", "continua"),
    "ferito": ("fuori", "lascia", "continua"),
    "sirene": ("fuori", "ostaggio", "continua"),
}
NOTE_RISPOSTE = {
    "fuori": "si salta all'uscita con quello che c'è.",
    "ostaggio": "la polizia ritarda di 2 battute (o la guardia si arrende); +3 calore, +1 testimone.",
    "lascia": "niente peso in fuga, la sua quota resta a te; ma lo arrestano: +3 calore.",
    "continua": "avanti come da piano, senza prova di panico.",
}
FASI = {"arrivo": "ARRIVO", "ingresso": "INGRESSO", "sala": "SALA",
        "bottino": "BOTTINO", "uscita": "USCITA", "fuga": "FUGA"}


# ════════════════════════════════════════════════════════════════════
#  SCENARIO E PIANO
# ════════════════════════════════════════════════════════════════════
MOTIVI_ASSENZA = [
    "è dentro per una vecchia storia",
    "è in ospedale: dice che è caduto dalle scale",
    "non risponde al telefono da martedì",
    "è al matrimonio della cugina, a Reggio",
    "ha la cavigliera e non può uscire di casa",
]


@dataclass
class Scenario:
    """La situazione di partenza: la gioielleria (fatti nascosti) e cosa ha la banda oggi."""
    seme: int
    fatti: dict                         # fatto -> valore (nascosti finché non li verifichi)
    forma: dict                         # personaggio -> -1 / 0 / +1
    assenti: tuple = ()                 # chi oggi non c'è
    motivo: str = ""
    magazzino: frozenset = frozenset()  # attrezzi già vostri
    introvabili: frozenset = frozenset()
    mezze_giornate: int = MEZZE_GIORNATE

    def disponibili(self) -> list:
        return [p for p in PERSONAGGI if p not in self.assenti]

    def in_piazza(self) -> list:
        return [e for e in EQUIP if e not in self.magazzino and e not in self.introvabili]


def situazione_a_caso(r: random.Random, seme: int = 0, fatti_fissi=None) -> Scenario:
    fatti = {}
    for f, (_, valori) in FATTI.items():
        fatti[f] = r.choices([v[0] for v in valori], [v[1] for v in valori])[0]
    forme, pesi = list(FORMA_PESI), list(FORMA_PESI.values())
    forma = {pid: r.choices(forme, pesi)[0] for pid in PERSONAGGI}
    assenti = tuple(r.sample(list(PERSONAGGI), MEMBRI_FUORI))
    motivo = r.choice(MOTIVI_ASSENZA)
    ids = list(EQUIP)
    r.shuffle(ids)
    magazzino = frozenset(ids[:ATTREZZI_IN_MAGAZZINO])
    introvabili = frozenset(ids[ATTREZZI_IN_MAGAZZINO:ATTREZZI_IN_MAGAZZINO + ATTREZZI_INTROVABILI])
    if fatti_fissi:
        fatti.update(fatti_fissi)
    return Scenario(seme, fatti, forma, assenti, motivo, magazzino, introvabili)


def genera_scenario(seme: int) -> Scenario:
    """Il numero del colpo fissa tutto ciò che trovi: fatti nascosti, forma, chi manca, magazzino."""
    return situazione_a_caso(random.Random(f"gioielleria-{seme}"), seme)


@dataclass
class Piano:
    sala: str
    cassaforte: str
    volante: str
    equip: frozenset = frozenset()
    sopralluoghi: frozenset = frozenset()
    battute: int = 2
    piani_b: dict = None   # condizione -> risposta
    riposi: tuple = ()     # chi ha riposato, una voce per mezza giornata

    def __post_init__(self):
        if self.piani_b is None:
            self.piani_b = {}

    def spesa(self, sc: Scenario) -> int:
        """Migliaia di euro per gli attrezzi che non erano già in magazzino."""
        return sum(EQUIP[e].prezzo for e in self.equip if e not in sc.magazzino)

    def tempo(self) -> int:
        return len(self.sopralluoghi) + len(self.riposi)

    def banda(self):
        return (self.sala, self.cassaforte, self.volante)

    def errori(self, sc: Scenario) -> list:
        err = []
        if len(set(self.banda())) != 3:
            err.append("servono tre persone diverse.")
        for x in self.banda():
            if x in sc.assenti:
                err.append(f"{PERSONAGGI[x].corto} oggi non c'è.")
        for e in self.equip:
            if e in sc.introvabili:
                err.append(f"{EQUIP[e].nome}: oggi non si trova.")
        if self.tempo() > sc.mezze_giornate:
            err.append(f"la preparazione chiede {self.tempo()} mezze giornate, ne hai {sc.mezze_giornate}.")
        if all(a in self.equip for a in ARMI):
            err.append("una sola arma: pistola o fucile.")
        if not 1 <= self.battute <= MAX_BOTTINO:
            err.append(f"battute di bottino tra 1 e {MAX_BOTTINO}.")
        if len(self.piani_b) > MAX_PIANI_B:
            err.append(f"al massimo {MAX_PIANI_B} piani B.")
        for c, r in self.piani_b.items():
            if r not in RISPOSTE_VALIDE.get(c, ()):
                err.append(f"«{r}» non vale per «{c}».")
        return err


def forma_dopo_riposo(sc: Scenario, riposi) -> dict:
    """Ogni mezza giornata di riposo rimette in sesto un membro a pezzi."""
    f = dict(sc.forma)
    for x in riposi:
        if f[x] < RIPOSO_FINO_A:
            f[x] += 1
    return f


@dataclass
class Esito:
    conto: float          # migliaia: netto meno calore, feriti, arresti e attrezzi comprati
    netto: float          # migliaia di euro, dopo le quote
    sacche: int
    feriti: int           # della banda
    arrestati: int
    civili: int           # feriti fuori dalla banda
    testimoni: int
    calore: int
    verdetto: str
    presi: bool
    allarme: bool
    rumore: int
    battute: int
    condizioni: tuple     # condizioni scattate
    piani_b_usati: tuple  # condizioni risolte da un piano B
    panici: int
    voci_calore: tuple    # [(n, causa)]
    spesa: int = 0        # migliaia spese in attrezzi


def utilita(e: Esito) -> float:
    """Il conto finale: il numero solo con cui si confrontano i piani."""
    return e.conto


# ════════════════════════════════════════════════════════════════════
#  MOTORE
# ════════════════════════════════════════════════════════════════════
class Colpo:
    """Esegue un piano su uno scenario. Regole fisse, un solo generatore di sorte.

    decisore: oggetto con prima(colpo, opzioni) -> None|"fuori"|"resta"
              e ripeti(colpo, nome_prova, chi, margine) -> bool.  None = nessun intervento.
    voce:     funzione (tipo, testo) per raccontare. None = silenzioso (simulazioni).
    """

    def __init__(self, scenario: Scenario, piano: Piano, sorte=None, decisore=None, voce=None):
        self.sc, self.p, self.dec, self.voce = scenario, piano, decisore, voce
        self.rng = random.Random(sorte)
        self.forma = forma_dopo_riposo(scenario, piano.riposi)
        self.mazzo = MAZZO[:]
        self.rng.shuffle(self.mazzo)
        f = scenario.fatti
        self.guardia, self.tipo_allarme = f["guardia"], f["allarme"]
        self.cassaforte, self.affluenza = f["cassaforte"], f["affluenza"]
        eq = piano.equip
        self.fucile, self.silenziata = "fucile" in eq, "silenziata" in eq
        self.arma = BONUS_FUCILE if self.fucile else (BONUS_SILENZIATA if self.silenziata else 0)
        self.nome_arma = "fucile a pompa" if self.fucile else ("pistola silenziata" if self.silenziata else "")
        self.trapano, self.auto = "trapano" in eq, "auto" in eq
        self.scanner, self.disturbatore = "scanner" in eq, "disturbatore" in eq
        self.interventi = INTERVENTI_BASE + (1 if self.scanner else 0)

        self.rumore = 0
        self.allarme = False
        self.allarme_noto = False
        self.conto = None            # battute all'arrivo della polizia
        self.no_dec = -1             # battuta in cui il conto non scende
        self.bonus_ritardo = 0
        self.sul_posto = False
        self.sp_uscita = False
        self.fretta = 0
        self.sacche = 0
        self.test_base = 0
        self.test_extra = 0
        self.controllo = None        # sala sotto controllo? None = mai entrati
        self.feriti = []
        self.arrestati = []
        self.civili = 0
        self.ostaggio = False
        self.abbandona = False
        self.inseguimento = False
        self.telecamera = False
        self.presi = False
        self.fucile_usato = False
        self.restanti = piano.battute
        self.fatte = 0
        self.aperture = 0
        self.perf_usato = False
        self.panico = False
        self.aborto = False
        self.ordine_dato = False
        self.mod_fuga = []
        self.pending = []
        self.scattate = []
        self.pb_usati = []
        self.panici = 0
        self.fase = "arrivo"
        self.n = 0
        self.fonti = []              # (n, causa, categoria) solo se raccontato
        self.usati = []              # interventi spesi (solo se raccontato)

    # ── utilità ────────────────────────────────────────────────────
    def val(self, chi, stat):
        v = getattr(PERSONAGGI[chi], stat) + self.forma[chi]
        if chi in self.feriti:
            v -= 2
        return v

    def dico(self, tipo, testo):
        if self.voce:
            self.voce(tipo, testo)

    def piu_rumore(self, n, causa, cat):
        if n <= 0:
            return
        self.rumore += n
        if self.voce:
            self.fonti.append((n, causa, cat))
            self.voce("rumore", f"      Rumore +{n} ({causa}) → {self.rumore}")
        if not self.allarme:
            if self.rumore >= SOGLIA_ALLARME:
                self.scatta_allarme()
        elif self.conto is not None and not self.sul_posto:
            passi = (self.rumore - SOGLIA_ALLARME) // PASSO_FRETTA
            while self.fretta < passi:
                self.fretta += 1
                self.conto -= 1
                if self.allarme_noto or "sirene" in self.scattate:
                    self.dico("evento", "   ⚠ Troppo casino: altre chiamate al 112. La polizia arriva una battuta prima.")

    def scatta_allarme(self):
        self.allarme = True
        rit = RITARDO_POLIZIA[self.tipo_allarme] + self.bonus_ritardo
        if self.disturbatore and self.tipo_allarme != "sirena":
            rit += RITARDO_DISTURBATORE
        self.conto = rit
        self.no_dec = self.n
        self.fretta = (self.rumore - SOGLIA_ALLARME) // PASSO_FRETTA
        self.allarme_noto = (self.tipo_allarme != "silenzioso"
                             or "allarme" in self.p.sopralluoghi or self.scanner)
        if self.allarme_noto:
            if self.voce:
                tipo = {"sirena": "Parte la sirena.",
                        "centrale": "Lampeggia la spia della centrale." + ("" if self.disturbatore else
                                    " Senza disturbatore la chiamata parte subito: la volante è dietro l'angolo."),
                        "silenzioso": "Allarme silenzioso: la banda lo sa e se ne accorge."}[self.tipo_allarme]
                extra = ""
                if self.disturbatore:
                    extra = (" Il disturbatore non può niente contro una sirena."
                             if self.tipo_allarme == "sirena" else " Il disturbatore ritarda la chiamata.")
                self.voce("evento", f"   ⚠ SCATTA L'ALLARME. {tipo}{extra}")
            self.pending.append("allarme")

    def prova(self, nome, titolo, chi, stat, soglia, mods=(), nota=""):
        """Dado a 6 + valore + modificatori contro soglia. Ritorna il margine (>= 0 riuscita)."""
        fisso = self.val(chi, stat) + sum(m[0] for m in mods)
        pg = PERSONAGGI[chi]
        while True:
            if self.voce:
                pezzi = [f"{STAT[stat]} {getattr(pg, stat)}"]
                fo = self.forma[chi]
                if fo:
                    pezzi.append(f"{FORMA[fo]} {fo:+d}")
                if chi in self.feriti:
                    pezzi.append(f"{ferito_a(chi)} -2")
                pezzi += [f"{et} {v:+d}" for v, et in mods if v]
                serve = soglia - fisso
                if serve <= 1:
                    cosa = "riesce con qualsiasi dado"
                elif serve > 6:
                    cosa = "non può riuscire, nemmeno con un 6"
                else:
                    cosa = f"serve {serve} o più al dado"
                self.voce("prova", f"   ▸ {titolo} — {pg.corto}: {', '.join(pezzi)} = {fisso}, "
                                   f"soglia {soglia} → {cosa}{nota}")
            d = self.rng.randint(1, 6)
            marg = fisso + d - soglia
            if self.voce:
                self.voce("dado", f"      Dado {d} → {fisso + d} contro {soglia}: "
                                  f"{'RIUSCITA' if marg >= 0 else 'FALLITA'}")
            if marg >= 0:
                return marg
            if (self.interventi > 0 and self.dec is not None
                    and self.dec.ripeti(self, nome, chi, marg)):
                self.interventi -= 1
                if self.voce:
                    self.usati.append(f"battuta {self.n}: fatta ripetere la prova «{titolo}»")
                    self.voce("evento", "   ☎ Intervento: «Rifallo. Adesso.»")
                continue
            if self.forma[chi] < 0 and self.fase != "fuga":
                self.piu_rumore(1, f"{pg.corto} è a pezzi e fa confusione", "forma")
            return marg

    def ferisci(self, chi):
        if chi in self.feriti:
            return
        self.feriti.append(chi)
        self.dico("evento", f"   ✚ {PERSONAGGI[chi].corto} è {ferito_a(chi)} (-2 a tutte le sue prove).")
        self.pending.append("ferito")

    def arresta(self, chi, come):
        if chi in self.arrestati:
            return
        self.arrestati.append(chi)
        self.dico("evento", f"   ⛓ {PERSONAGGI[chi].corto} {come}.")

    def prendi_ostaggio(self):
        if self.ostaggio:
            return
        self.ostaggio = True
        self.test_extra += 1
        if self.conto is not None:
            self.conto = max(self.conto, 0) + RITARDO_OSTAGGIO
            self.sul_posto = False
            self.no_dec = self.n
        else:
            self.bonus_ritardo += RITARDO_OSTAGGIO

    def ordina_fuori(self):
        self.ordine_dato = True
        if self.fase in ("arrivo", "ingresso", "sala"):
            self.aborto = True
            self.restanti = 0
        elif self.fase == "bottino" and self.restanti > 0:
            if self.p.cassaforte == "nico" and not self.perf_usato:
                self.perf_usato = True
                self.restanti = 1
                self.dico("evento", "   Nico non alza nemmeno la testa: «Un minuto. Ci sono quasi.» "
                                    "(Perfezionista: ancora una battuta di bottino.)")
            else:
                self.restanti = 0

    def reazione(self, c):
        """Una condizione scatta: piano B se c'è, altrimenti prova di panico."""
        self.scattate.append(c)
        r = self.p.piani_b.get(c)
        if r:
            self.pb_usati.append(c)
            self.dico("evento", f"   ⟳ PIANO B — se {CONDIZIONI[c]}: {RISPOSTE[r]}.")
            if r == "fuori":
                self.ordina_fuori()
            elif r == "ostaggio":
                self.prendi_ostaggio()
                self.dico("evento", "      Una commessa finisce con un braccio al collo. Nessuno si muove più.")
            elif r == "lascia":
                self.abbandona = True
            return r
        self.dico("evento", f"   Nessun piano B per «{CONDIZIONI[c]}»: decide chi è in sala.")
        m = self.prova("panico", "Tenere i nervi", self.p.sala, "sf", SOGLIA_PANICO)
        if m >= 0:
            self.dico("testo", "      Tiene. Si va avanti come da piano.")
            return "continua"
        self.panici += 1
        self.panico = True
        self.piu_rumore(2, f"panico: nessun piano B per «{CONDIZIONI[c]}»", "panico")
        if self.restanti > 0 and self.fase in ("ingresso", "sala", "bottino"):
            self.dico("testo", "      Panico: urla, ordini contraddittori. La prossima battuta di bottino va persa.")
        else:
            self.panico = False
            self.dico("testo", "      Panico: urla, ordini contraddittori.")
        return "panico"

    def risolvi(self):
        while self.pending:
            c = self.pending.pop(0)
            if c in self.scattate:
                continue
            if self.fase == "fuga" or (self.fase == "uscita" and c != "ferito"):
                self.scattate.append(c)   # troppo tardi per reagire
                continue
            self.reazione(c)

    def aggiusta_fase(self):
        prima = self.fase
        if self.aborto and self.fase in ("ingresso", "sala"):
            self.fase = "uscita"
        elif self.aborto and self.fase == "arrivo":
            self.fase = "fuga"
        elif self.fase == "bottino" and self.restanti <= 0:
            self.fase = "uscita"
        elif self.fase == "uscita" and self.restanti > 0:
            self.fase = "bottino"
        if self.fase != prima:
            self.dico("evento", f"   → La battuta diventa {FASI[self.fase]}.")

    def prossima(self):
        f = self.fase
        if f == "arrivo":
            return "fuga" if self.aborto else "ingresso"
        if f == "ingresso":
            return "uscita" if self.aborto else "sala"
        if f in ("sala", "bottino"):
            return "bottino" if (self.restanti > 0 and not self.aborto) else "uscita"
        if f == "uscita":
            return "fuga"
        return "fine"

    # ── carte ──────────────────────────────────────────────────────
    def gioca_carta(self, c):
        dentro = self.fase in ("ingresso", "sala", "bottino", "uscita")
        nome = CARTE[c][0]
        if c == "liscio":
            self.dico("carta", f"   Carta: «{nome}».")
        elif c == "pattuglia":
            if self.fase == "fuga":
                self.dico("carta", f"   Carta: «{nome}» — vi incrocia all'incrocio. Fuga -2.")
                self.mod_fuga.append((-2, "pattuglia"))
            else:
                self.dico("carta", f"   Carta: «{nome}» — rallenta davanti alla vetrina.")
                self.piu_rumore(1, "pattuglia di passaggio", "mazzo")
        elif c == "eroe":
            if dentro and self.affluenza != "vuoto" and self.fase != "uscita":
                self.dico("carta", f"   Carta: «{nome}» — un tizio in giacca decide che oggi è il suo giorno.")
                mods = []
                if self.arma:
                    mods.append((self.arma, self.nome_arma))
                if self.controllo:
                    mods.append((1, "sala sotto controllo"))
                m = self.prova("eroe", "Fermare l'eroe", self.p.sala, "sf", SOGLIA_EROE, mods)
                if m < 0:
                    self.piu_rumore(2, "il cliente eroe fa un macello", "mazzo")
                    if not self.parte_un_colpo() and not self.arma:
                        self.dico("evento", "   Colluttazione a mani nude.")
                        self.ferisci(self.p.sala)
            else:
                self.dico("carta", f"   Carta: «{nome}» — ma non c'è nessuno a fare l'eroe.")
        elif c == "telefonino":
            n = 2 if (dentro and self.affluenza != "vuoto") else 1
            self.test_extra += n
            self.dico("carta", f"   Carta: «{nome}» — qualcuno filma. +{n} testimoni.")
        elif c == "traffico":
            self.mod_fuga.append((-1, "traffico"))
            self.dico("carta", f"   Carta: «{nome}» — il viale è un parcheggio. Fuga -1.")
        elif c == "corriere":
            if dentro:
                self.dico("carta", f"   Carta: «{nome}» — suona, risuona, guarda dentro.")
                self.piu_rumore(1, "corriere alla porta", "mazzo")
            else:
                self.dico("carta", f"   Carta: «{nome}» — ma siete in strada: tira dritto.")
        elif c == "nervi":
            giu = [x for x in self.p.banda() if self.forma[x] < 0]
            if giu:
                chi = ", ".join(PERSONAGGI[x].corto for x in giu)
                self.dico("carta", f"   Carta: «{nome}» — {chi} non regge la tensione.")
                self.piu_rumore(len(giu), f"nervi: {chi} a pezzi", "forma")
            else:
                self.dico("carta", f"   Carta: «{nome}» — ma la banda è lucida. Niente.")
        elif c == "fortuna":
            if self.fase in ("sala", "bottino"):
                self.sacche += 1
                self.dico("carta", f"   Carta: «{nome}» — una vetrina lasciata aperta. +1 sacca.")
            else:
                self.dico("carta", f"   Carta: «{nome}» — sprecato: non siete sul bottino.")

    def parte_un_colpo(self):
        """Fucile in sala, o Tony in sala, dopo una prova fallita. Ritorna True se ha sparato."""
        tony = self.p.sala == "tony"
        if not (self.fucile or tony):
            return False
        chi = "Tony ha il grilletto facile" if tony else "col fucile basta un sussulto"
        if self.affluenza == "vuoto":
            self.dico("evento", f"   Parte un colpo ({chi}). Per fortuna non c'è nessuno: intonaco dal soffitto.")
        else:
            self.civili += 1
            self.dico("evento", f"   ✚ Parte un colpo ({chi}): un cliente a terra.")
        if tony or not self.silenziata:
            self.piu_rumore(2, "sparo in sala", "scelta")
        return True

    # ── fasi ───────────────────────────────────────────────────────
    def f_arrivo(self):
        self.dico("testo", "   Il mezzo accosta. Nessuno parla.")

    def f_ingresso(self):
        m = self.prova("ingresso", "Entrare senza farsi notare", self.p.cassaforte, "mani", SOGLIA_INGRESSO)
        if m < 0:
            self.piu_rumore(1, "ingresso maldestro", "dado")

    def f_sala(self):
        sala = self.p.sala
        if self.voce:
            for f in ("guardia", "affluenza"):
                if f not in self.p.sopralluoghi:
                    self.voce("evento", f"   ? Scoprite solo ora — {FATTI[f][0]}: {self.sc.fatti[f]}.")
        self.test_base = TESTIMONI[self.affluenza]
        if self.fucile:
            self.fucile_usato = True
        if self.guardia == "armata" and not self.arma and sala != "tony":
            # serratura senza chiave: non c'è prova che tenga
            self.controllo = False
            self.dico("evento", "   La guardia è armata e voi no. Ha già la mano sulla fondina.")
            r = self.reazione("guardia")
            if r == "fuori":
                return
            if r == "ostaggio":
                self.dico("testo", "      La guardia posa l'arma. La sala però non è vostra: testimoni interi.")
                return
            self.dico("evento", "   La guardia spara. Voi non avete niente con cui rispondere.")
            self.ferisci(sala)
            self.piu_rumore(max(2, SOGLIA_ALLARME - self.rumore),
                            "la guardia armata spara e nessuno aveva un'arma", "fatto:guardia")
            return
        soglia = SOGLIA_SALA + MOD_GUARDIA[self.guardia] + (1 if self.affluenza == "pieno" else 0)
        mods = [(self.arma, self.nome_arma)] if self.arma else []
        m = self.prova("sala", "Tenere la sala", sala, "sf", soglia, mods)
        if m >= 0:
            self.controllo = True
            self.dico("testo", "      Tutti a terra, nessuno fiata. Testimoni dimezzati.")
            return
        self.controllo = False
        self.piu_rumore(2, "la sala sfugge di mano", "dado")
        sparato = False
        r = None
        if self.guardia != "assente":
            r = self.reazione("guardia")
            if r == "fuori":
                return
            if r != "ostaggio":
                if self.guardia == "anziana":
                    self.piu_rumore(1, "la guardia preme l'antipanico", "fatto:guardia")
                else:
                    sparato = True
                    self.civili += 1
                    self.dico("evento", "   ✚ La guardia porta la mano alla fondina. Non fa in tempo: a terra.")
                    if sala == "tony" or not self.silenziata:
                        self.piu_rumore(2, "sparo alla guardia", "scelta")
        if not sparato:
            self.parte_un_colpo()

    def f_bottino(self):
        self.restanti -= 1
        self.fatte += 1
        if self.fatte == 1 and self.voce and "cassaforte" not in self.p.sopralluoghi:
            self.voce("evento", f"   ? Scoprite solo ora — Cassaforte: {self.cassaforte}.")
        if self.fatte > 1:
            self.piu_rumore(RUMORE_ATTESA, "troppo tempo dentro: da fuori qualcuno nota", "scelta")
        if self.panico:
            self.panico = False
            self.dico("testo", "   Battuta persa nel caos: nessuno mette le mani su niente.")
            return
        if self.cassaforte == "a tempo" and self.fatte == 1 and not self.trapano:
            self.sacche += SACCHE_VETRINE
            self.dico("testo", f"   La cassaforte a tempo è ancora chiusa. Solo vetrine: +{SACCHE_VETRINE} sacca.")
        elif self.cassaforte == "moderna" and not self.trapano and self.p.cassaforte != "nico":
            self.sacche += SACCHE_VETRINE
            self.dico("testo", f"   Cassaforte moderna: senza trapano {PERSONAGGI[self.p.cassaforte].corto} non sa "
                               f"da dove cominciare. Solo vetrine: +{SACCHE_VETRINE} sacca.")
        else:
            m = self.prova("bottino", "Aprire la cassaforte", self.p.cassaforte, "mani",
                           SOGLIA_CASSAFORTE[self.cassaforte],
                           [(BONUS_TRAPANO, "trapano termico")] if self.trapano else ())
            if m >= 0:
                n = SACCHE_CASSAFORTE[min(self.aperture, len(SACCHE_CASSAFORTE) - 1)]
                self.aperture += 1
                self.sacche += n
                self.dico("testo", f"      {'Aperta' if self.aperture == 1 else 'Altro ripiano'}. "
                                   f"+{n} sacc{'a' if n == 1 else 'he'}.")
            else:
                self.sacche += SACCHE_VETRINE
                self.dico("testo", f"      Non cede. Si sfondano le vetrine: +{SACCHE_VETRINE} sacca.")
                self.piu_rumore(1, "vetrine sfondate", "dado")
        if self.trapano:
            self.piu_rumore(1, "trapano termico", "scelta")

    def f_uscita(self):
        sala = self.p.sala
        self.sp_uscita = self.sul_posto
        if self.controllo is None:
            self.dico("testo", "   Dietrofront prima ancora di cominciare.")
        if self.sul_posto:
            self.dico("evento", "   Le volanti sono già davanti all'ingresso.")
            m = self.prova("uscita", "Uscire sotto il naso della polizia", sala, "sf", SOGLIA_USCITA_POLIZIA,
                           nota=". Fallire di 1-2: un ferito. Di 3 o più: un arresto")
            if m >= 0:
                self.dico("testo", "      Dal retro, attraverso il cortile. Passati.")
            elif m >= -2:
                self.ferisci(sala)
                self.risolvi()
            else:
                self.arresta(sala, "resta a terra sul marciapiede con le manette")
        else:
            self.dico("testo", "   Fuori dalla porta, passo svelto, niente corse.")
        for f in self.feriti:
            if f in self.arrestati:
                continue
            if self.abbandona:
                self.arresta(f, "viene lasciato lì. Lo raccolgono gli agenti")
            else:
                self.mod_fuga.append((-1, f"{PERSONAGGI[f].corto} {ferito_a(f)} a bordo"))

    def f_fuga(self):
        vol = self.p.volante
        mods = []
        if self.auto:
            mods.append((2, "auto veloce"))
        if self.sp_uscita:
            mods.append((-3, "polizia già sul posto"))
        elif self.sul_posto:
            mods.append((-2, "volanti in zona"))
        elif self.allarme:
            mods.append((-1, "allarme scattato"))
        if vol == "samir" and self.fatte > 1:
            mods.append((-(self.fatte - 1), "Samir nervoso per l'attesa"))
        mods += self.mod_fuga
        if self.allarme:
            nota = ". Fallire di 1-2: inseguimento, si perde un terzo del bottino. Di 3 o più: presi tutti"
        else:
            nota = ". Nessuno vi insegue: se fallisce, al massimo vi riprende una telecamera (+1 calore)"
        m = self.prova("fuga", "Seminare tutti" if self.allarme else "Sparire nel traffico",
                       vol, "volante", SOGLIA_FUGA, mods, nota=nota)
        if m >= 0:
            self.dico("testo", "      Tre svolte e siete un'auto come le altre.")
        elif not self.allarme:
            self.telecamera = True
            self.dico("evento", "   Un rosso bruciato, una sgommata di troppo: una telecamera vi riprende. +1 calore.")
        elif m >= -2:
            self.inseguimento = True
            persi = math.ceil(self.sacche / 3)
            self.sacche -= persi
            self.dico("evento", f"   Inseguimento. Per alleggerire volano dal finestrino {persi} sacche. +2 calore.")
        else:
            self.presi = True
            self.dico("evento", "   Posto di blocco. Fine corsa per tutti.")

    # ── ciclo ──────────────────────────────────────────────────────
    def intervento_pre(self):
        if self.dec is None or self.interventi <= 0:
            return
        opz = []
        if self.fase == "sala" or (self.fase == "bottino" and self.restanti > 0):
            opz.append("fuori")
        if (self.fase == "uscita" and 1 <= self.fatte < MAX_BOTTINO
                and not self.ordine_dato and not self.aborto):
            opz.append("resta")
        if not opz:
            return
        s = self.dec.prima(self, opz)
        if s == "fuori" and "fuori" in opz:
            self.interventi -= 1
            if self.voce:
                self.usati.append(f"battuta {self.n}: ordinato «fuori adesso»")
                self.voce("evento", "   ☎ Intervento: «Fuori. Adesso.»")
            self.ordina_fuori()
        elif s == "resta" and "resta" in opz:
            self.interventi -= 1
            self.restanti = 1
            if self.voce:
                self.usati.append(f"battuta {self.n}: ordinata una battuta di bottino in più")
                self.voce("evento", "   ☎ Intervento: «Ancora un giro. Poi fuori.»")

    def stato_polizia(self):
        if self.sul_posto:
            return "SUL POSTO"
        if self.conto is None or not (self.allarme_noto or "sirene" in self.scattate):
            return "—"
        if self.scanner:
            return f"tra {self.conto} battute"
        return "sirene vicine" if "sirene" in self.scattate else "in arrivo"

    def fine_battuta(self):
        if self.conto is None or self.sul_posto:
            return
        if self.n != self.no_dec:
            self.conto -= 1
            if self.conto == 1 and "sirene" not in self.scattate and "sirene" not in self.pending:
                self.pending.append("sirene")
                if self.fase not in ("uscita", "fuga"):
                    self.dico("evento", "   ♪ In lontananza, sirene.")
        if self.conto <= 0:
            self.sul_posto = True
            if self.fase != "fuga":
                self.dico("evento", "   ⚠ LA POLIZIA È SUL POSTO.")

    def esegui(self) -> Esito:
        while self.fase != "fine":
            self.n += 1
            if self.voce:
                barra = "▮" * min(self.rumore, SOGLIA_ALLARME) + "▯" * max(0, SOGLIA_ALLARME - self.rumore)
                self.voce("battuta",
                          f"━━ Battuta {self.n} · {FASI[self.fase]} " + "━" * (40 - len(FASI[self.fase])) + "\n"
                          f"   Rumore {barra} {self.rumore}/{SOGLIA_ALLARME} · Sacche {self.sacche} · "
                          f"Interventi {self.interventi} · Polizia: {self.stato_polizia()}")
            self.gioca_carta(self.mazzo.pop())
            self.risolvi()
            self.aggiusta_fase()
            self.intervento_pre()
            self.aggiusta_fase()
            getattr(self, "f_" + self.fase)()
            self.risolvi()
            self.fine_battuta()
            self.fase = self.prossima()
        return self.esito()

    # ── esito ──────────────────────────────────────────────────────
    def esito(self) -> Esito:
        banda = self.p.banda()
        if self.presi:
            for x in banda:
                if x not in self.arrestati:
                    self.arrestati.append(x)
            self.sacche = 0
        testimoni = (self.test_base // 2 if self.controllo else self.test_base) + self.test_extra
        quota = sum(PERSONAGGI[x].quota for x in banda if x not in self.arrestati)
        netto = self.sacche * VALORE_SACCA * (100 - quota) / 100

        vc = [(1, "un colpo è un colpo")]
        if self.allarme:
            vc.append((2, "allarme scattato"))
        if testimoni:
            vc.append((math.ceil(testimoni / 2), f"{testimoni} testimon{'e' if testimoni == 1 else 'i'}"))
        if self.civili:
            vc.append((2 * self.civili, f"{self.civili} feriti tra civili e guardie"))
        if self.ostaggio:
            vc.append((3, "ostaggio"))
        if self.arrestati:
            vc.append((3 * len(self.arrestati), f"{len(self.arrestati)} arrestati che possono parlare"))
        if "lea" in banda:
            vc.append((1, "Lea chiacchiera"))
            if "lea" in self.arrestati:
                vc.append((2, "Lea in questura chiacchiera di più"))
        if "vera" in banda and testimoni >= 2:
            vc.append((2, "Vera è ricercata e l'hanno vista"))
        if self.auto:
            vc.append((1, "auto veloce notata"))
        if self.fucile_usato:
            vc.append((1, "fucile a pompa in sala"))
        if self.inseguimento:
            vc.append((2, "inseguimento"))
        if self.telecamera:
            vc.append((1, "ripresi da una telecamera in fuga"))
        calore = min(10, sum(v for v, _ in vc))

        if self.presi:
            verdetto = "DISASTRO"
        elif self.sacche == 0:
            verdetto = "A MANI VUOTE"
        elif self.arrestati or self.feriti or self.civili or calore >= 7:
            verdetto = "COLPO SPORCO"
        elif calore <= 3 and self.sacche >= 5:
            verdetto = "COLPO PULITO"
        else:
            verdetto = "COLPO RIUSCITO A METÀ"
        spesa = self.p.spesa(self.sc)
        if self.presi:
            conto = float(CONTO_DISASTRO - spesa)
        else:
            conto = (netto - COSTO_CALORE * calore - COSTO_FERITO * len(self.feriti)
                     - COSTO_ARRESTO * len(self.arrestati) - spesa)
        return Esito(conto, netto, self.sacche, len(self.feriti), len(self.arrestati), self.civili, testimoni,
                     calore, verdetto, self.presi, self.allarme, self.rumore, self.n,
                     tuple(self.scattate), tuple(self.pb_usati), self.panici, tuple(vc), spesa)


# ════════════════════════════════════════════════════════════════════
#  STRUMENTI PER LE SIMULAZIONI (usati dal notebook)
# ════════════════════════════════════════════════════════════════════
class Istinto:
    """Giocatore automatico: non dà ordini, fa ripetere le prove che contano."""

    def prima(self, colpo, opzioni):
        return None

    def ripeti(self, colpo, nome, chi, margine):
        return nome in ("sala", "fuga", "uscita")


def gioca(scenario: Scenario, piano: Piano, sorte=None, decisore=None) -> Esito:
    return Colpo(scenario, piano, sorte, decisore).esegui()


def con_fatti(sc: Scenario, fatti: dict) -> Scenario:
    """La stessa situazione (banda, magazzino) davanti a una gioielleria diversa."""
    f = dict(sc.fatti)
    f.update(fatti)
    return replace(sc, fatti=f)


def fatti_a_caso(r: random.Random, fissi=None) -> dict:
    f = {k: r.choices([v[0] for v in vals], [v[1] for v in vals])[0] for k, (_, vals) in FATTI.items()}
    f.update(fissi or {})
    return f


def attrezzi_possibili(sc: Scenario) -> list:
    """Tutti gli insiemi di attrezzi che oggi si possono portare (una sola arma)."""
    ids = [e for e in EQUIP if e not in sc.introvabili]
    out = []
    for mask in range(1 << len(ids)):
        scelti = frozenset(ids[k] for k in range(len(ids)) if mask >> k & 1)
        if not all(a in scelti for a in ARMI):
            out.append(scelti)
    return out


def riposa(sc: Scenario, banda, n: int) -> tuple:
    """Come un giocatore sensato userebbe n mezze giornate di riposo: prima chi sta peggio."""
    forma = dict(sc.forma)
    out = []
    for _ in range(n):
        chi = min(banda, key=lambda x: forma[x])
        if forma[chi] >= RIPOSO_FINO_A:
            break
        forma[chi] += 1
        out.append(chi)
    return tuple(out)


def forme_base(sc: Scenario) -> list:
    """Tutte le combinazioni di banda, attrezzi e battute possibili oggi: (sala, cassaforte, volante, attrezzi, battute)."""
    return [(a, b, c, eq, n)
            for a, b, c in itertools.permutations(sc.disponibili(), 3)
            for eq in attrezzi_possibili(sc) for n in range(1, MAX_BOTTINO + 1)]


def costruisci(sc: Scenario, forma_base, noti=(), piani_b=None) -> Piano:
    """Un piano da una forma base: i fatti in «noti» costano mezza giornata l'uno, il resto è riposo."""
    a, b, c, eq, n = forma_base
    return Piano(a, b, c, eq, frozenset(noti), n, dict(piani_b or {}),
                 riposa(sc, (a, b, c), sc.mezze_giornate - len(noti)))


def piano_a_caso(rng: random.Random, sc: Scenario) -> Piano:
    noti = rng.sample(list(FATTI), rng.randint(0, min(len(FATTI), sc.mezze_giornate)))
    a, b, c = rng.sample(sc.disponibili(), 3)
    pb = rng.choice(combinazioni_piani_b())
    return costruisci(sc, (a, b, c, rng.choice(attrezzi_possibili(sc)), rng.randint(1, MAX_BOTTINO)), noti, pb)


def combinazioni_piani_b(_cache=[]) -> list:
    """Tutti i modi di riempire 0, 1 o 2 caselle di piano B."""
    if _cache:
        return _cache
    out = [{}]
    cond = list(CONDIZIONI)
    for c in cond:
        for r in RISPOSTE_VALIDE[c]:
            out.append({c: r})
    for i, c1 in enumerate(cond):
        for c2 in cond[i + 1:]:
            for r1 in RISPOSTE_VALIDE[c1]:
                for r2 in RISPOSTE_VALIDE[c2]:
                    out.append({c1: r1, c2: r2})
    _cache.extend(out)
    return _cache


def media_conto(piano: Piano, scenari, r: random.Random, decisore=None) -> float:
    dec = decisore or Istinto()
    return sum(Colpo(sc, piano, r.random(), dec).esegui().conto for sc in scenari) / len(scenari)


def etichetta(p: Piano) -> str:
    return f"{p.sala}/{p.cassaforte}/{p.volante} · {'+'.join(sorted(p.equip)) or 'niente'} · {p.battute} batt."


def analizza_situazione(seme: int) -> dict:
    """Per una situazione di partenza: quanto rende andare al buio, sapere un fatto, sapere tutto.

    In tutti i casi il tempo che non va in sopralluoghi va in riposo per chi è a pezzi.
    Al buio:  nessun sopralluogo; si sceglie il piano migliore in media su tutte le gioiellerie possibili.
    Un fatto: un sopralluogo; il piano si sceglie sapendo quel fatto.
    Tutto:    quattro sopralluoghi, quindi nessun riposo; il piano si sceglie sapendo com'è la gioielleria.
    Si cerca tra TUTTI i piani possibili quel giorno. Ogni piano viene scelto su un gruppo di colpi
    e misurato su colpi nuovi, così chi ha solo avuto fortuna non viene premiato.
    """
    r = random.Random(f"analisi-{seme}")
    sc = genera_scenario(seme)
    forme = forme_base(sc)

    def migliore(noti, crea_scenari, n1, n2):
        prova = crea_scenari(n1)
        otto = sorted(forme, key=lambda fb: -media_conto(costruisci(sc, fb, noti), prova, r))[:8]
        prova = crea_scenari(n2)
        return max((costruisci(sc, fb, noti) for fb in otto), key=lambda p: media_conto(p, prova, r))

    def a_caso(n, fissi=None):
        return [con_fatti(sc, fatti_a_caso(r, fissi)) for _ in range(n)]

    buio = migliore((), a_caso, 80, 400)
    v_buio = media_conto(buio, a_caso(800), r)

    per_fatto, dettaglio = {}, []
    for f, (nome, valori) in FATTI.items():
        tot_inf = tot_buio = 0.0
        for v, peso, _ in valori:
            mk = lambda n, f=f, v=v: a_caso(n, {f: v})
            scelto = migliore((f,), mk, 20, 300)
            misura = mk(500)
            vi, vb = media_conto(scelto, misura, r), media_conto(buio, misura, r)
            tot_inf += peso / 100 * vi
            tot_buio += peso / 100 * vb
            dettaglio.append({"fatto": nome, "valore": v, "piano": etichetta(scelto),
                              "informato": vi, "al buio": vb})
        per_fatto[nome] = tot_inf - tot_buio

    tot_inf = tot_buio = 0.0
    piani_tutto, casi = [], []
    N = 10
    for _ in range(N):
        ft = fatti_a_caso(r)
        qui = con_fatti(sc, ft)
        mk = lambda n, qui=qui: [qui] * n
        scelto = migliore(tuple(FATTI), mk, 20, 200)
        misura = mk(400)
        vi, vb = media_conto(scelto, misura, r), media_conto(buio, misura, r)
        tot_inf += vi / N
        tot_buio += vb / N
        piani_tutto.append(etichetta(scelto))
        casi.append({"fatti": ft, "informato": vi, "al buio": vb})

    return {
        "colpo": seme,
        "fuori gioco": ", ".join(sc.assenti),
        "a pezzi": ", ".join(p for p in sc.disponibili() if sc.forma[p] < 0) or "nessuno",
        "magazzino": "+".join(sorted(sc.magazzino)),
        "introvabile": "+".join(sorted(sc.introvabili)),
        "piano al buio": etichetta(buio),
        "al buio": v_buio,
        "per fatto": per_fatto,
        "dettaglio": dettaglio,
        "tutto: informato": tot_inf,
        "tutto: al buio": tot_buio,
        "piani informati": piani_tutto,
        "casi": casi,
        "piani possibili": len(forme),
        "piano": buio,          # l'oggetto Piano scelto al buio, per rigiocarlo
    }


def descrivi_piano(p: Piano) -> str:
    eq = "+".join(sorted(p.equip)) or "niente"
    pb = ", ".join(f"{c}→{r}" for c, r in p.piani_b.items()) or "nessuno"
    return (f"sala {p.sala}, cassaforte {p.cassaforte}, volante {p.volante} | {eq} | "
            f"{p.battute} battute | piani B: {pb}")


# ════════════════════════════════════════════════════════════════════
#  INTERFACCIA DA TERMINALE
# ════════════════════════════════════════════════════════════════════
REGISTRO = []
TTY = sys.stdin.isatty()
LARGO = 78


def out(s=""):
    print(s)
    REGISTRO.append(s)


def para(s, rientro="   "):
    for r in textwrap.wrap(s, LARGO, initial_indent=rientro, subsequent_indent=" " * len(rientro)):
        out(r)


def leggi(prompt):
    try:
        r = input(prompt)
    except EOFError:
        r = ""
        print()
    REGISTRO.append(prompt + r)
    return r.strip()


def pausa(prompt="   [Invio] "):
    if TTY:
        try:
            input(prompt)
        except EOFError:
            pass


def scegli(prompt, valide, vuoto=None):
    while True:
        r = leggi(prompt).lower()
        if r == "" and vuoto is not None:
            return vuoto
        if r in valide:
            return r
        if not TTY:
            raise SystemExit(f"Risposta non valida: «{r}»")
        out(f"   Non valido. Scegli tra: {', '.join(valide)}")


def titolo(s):
    out()
    out("═" * LARGO)
    out(f"  {s}")
    out("═" * LARGO)


def mostra_personaggi(sc=None, forma=None):
    out(f"   {'#':<2} {'Nome':<22}{'Freddo':>7}{'Mani':>6}{'Volante':>9}{'Quota':>7}   Oggi")
    ids = sc.disponibili() if sc else list(PERSONAGGI)
    forma = forma or (sc.forma if sc else None)
    for i, pid in enumerate(ids, 1):
        p = PERSONAGGI[pid]
        oggi = ""
        if forma:
            oggi = FORMA[forma[pid]] + (f" ({forma[pid]:+d} a tutto)" if forma[pid] else "")
        out(f"   {i:<2} {p.nome:<22}{p.sf:>7}{p.mani:>6}{p.volante:>9}{p.quota:>6}%   {oggi}")
        para(f"{p.difetto}: {p.nota}", "        ")
    if sc:
        for pid in sc.assenti:
            para(f"Fuori gioco: {PERSONAGGI[pid].nome} {sc.motivo}.", "   ✘  ")


def stato_attrezzo(e, sc=None):
    if sc is None:
        return f"{EQUIP[e].prezzo} mila se va comprato"
    if e in sc.magazzino:
        return "GIÀ VOSTRO, gratis"
    if e in sc.introvabili:
        return "oggi NON SI TROVA"
    return f"in piazza a {EQUIP[e].prezzo} mila"


def mostra_equip(sc=None):
    for i, e in enumerate(EQUIP.values(), 1):
        out(f"   {i}  {e.nome} — {stato_attrezzo(e.id, sc)}")
        para(f"Dà: {e.da}  Toglie: {e.toglie}", "        ")


def mostra_fatti(noti=None, sc=None):
    for i, (f, (nome, valori)) in enumerate(FATTI.items(), 1):
        if noti is not None and f in noti:
            out(f"   {i}  {nome}: {sc.fatti[f].upper()}  (verificato)")
        else:
            out(f"   {i}  {nome}: ?")
        for v, peso, nota in valori:
            segno = "→" if (noti is not None and f in noti and sc.fatti[f] == v) else " "
            para(f"{segno} {v} ({peso}%): {nota}", "       ")


def mostra_mazzo():
    conta = {}
    for c in MAZZO:
        conta[c] = conta.get(c, 0) + 1
    for c, n in conta.items():
        para(f"{n}× {CARTE[c][0]} — {CARTE[c][1]}", "   ")


def mostra_carte():
    titolo("PERSONAGGI (valori da 1 a 4) — a ogni colpo uno è fuori gioco")
    mostra_personaggi()
    titolo(f"ATTREZZI — a ogni colpo {ATTREZZI_IN_MAGAZZINO} sono già vostri e {ATTREZZI_INTROVABILI} non si trova")
    mostra_equip()
    titolo(f"FATTI NASCOSTI — verificarne uno costa mezza giornata (ne hai {MEZZE_GIORNATE})")
    mostra_fatti()
    titolo("MAZZO IMPREVISTI (10 carte, una per battuta)")
    mostra_mazzo()
    titolo("PIANI B")
    for c, nome in CONDIZIONI.items():
        para(f"Se {nome}: " + " / ".join(RISPOSTE[r] for r in RISPOSTE_VALIDE[c]))
    for r, nota in NOTE_RISPOSTE.items():
        para(f"{RISPOSTE[r]}: {nota}", "     ")


def riga_membro(i, pid, forma):
    p = PERSONAGGI[pid]
    fo = forma[pid]
    return (f"   {i}  {p.corto:<6} freddo {p.sf}  mani {p.mani}  volante {p.volante}  "
            f"quota {p.quota}%  {FORMA[fo]}{f' ({fo:+d})' if fo else ''}")


def pianifica(sc: Scenario) -> Piano:
    ids_p = sc.disponibili()
    ids_e = list(EQUIP)
    ids_f = list(FATTI)
    ids_c = list(CONDIZIONI)

    titolo(f"GIOIELLERIA «BELLONI & FIGLI» — colpo n. {sc.seme}")
    para("Via del Corso, angolo cieco, vetrine nuove. Dentro c'è roba che vale la fatica. "
         "Tu non ci metti piede: scegli chi va, con cosa, e cosa fanno quando va storto.")
    para(f"La merce viene spostata tra {sc.mezze_giornate} mezze giornate. Ognuna la usi per un sopralluogo "
         "oppure per rimettere in sesto uno dei tuoi che è a pezzi. Poi si va con quello che c'è: la banda di oggi, gli attrezzi "
         "in magazzino e quelli che decidi di comprare.")
    para(f"Hai 2 piani B e {INTERVENTI_BASE} telefonate dal vivo. Il rumore fa scattare l'allarme a "
         f"{SOGLIA_ALLARME}. Ogni sacca vale {VALORE_SACCA} mila euro, meno le quote della banda.")
    para(f"Alla fine si fa il conto: dal tuo bottino si tolgono gli attrezzi comprati, {COSTO_CALORE} mila per "
         f"ogni punto di calore, {COSTO_FERITO} mila per ogni ferito della banda e {COSTO_ARRESTO} mila per "
         f"ogni arrestato. Se vi prendono tutti: {CONTO_DISASTRO} mila.")

    titolo("LA BANDA DI OGGI — ne scegli 3")
    mostra_personaggi(sc)
    titolo("MAGAZZINO E PIAZZA")
    mostra_equip(sc)
    titolo("IL MAZZO DEGLI IMPREVISTI — sai cosa c'è, non in che ordine")
    mostra_mazzo()

    # 1. preparazione: sopralluoghi e riposo
    noti, riposi = [], []
    while len(noti) + len(riposi) < sc.mezze_giornate:
        forma = forma_dopo_riposo(sc, riposi)
        resta = sc.mezze_giornate - len(noti) - len(riposi)
        titolo(f"1 · PREPARAZIONE — mezze giornate rimaste: {resta}")
        mostra_fatti(noti, sc)
        out()
        stanchi = [pid for pid in ids_p if forma[pid] < RIPOSO_FINO_A]
        out("   La banda: " + ", ".join(f"{PERSONAGGI[pid].corto} {FORMA[forma[pid]]}" for pid in ids_p))
        liberi = [str(i + 1) for i, f in enumerate(ids_f) if f not in noti]
        if not liberi and not stanchi:
            break
        voci = []
        if liberi:
            voci.append("numero = verifichi quel fatto")
        if stanchi:
            voci.append("r = fai riposare chi è a pezzi")
        r = scegli(f"   Questa mezza giornata: [{' / '.join(voci)} / Invio = basta così] ",
                   liberi + (["r"] if stanchi else []), vuoto="")
        if r == "":
            break
        if r == "r":
            for i, pid in enumerate(stanchi, 1):
                out(f"      {i}  {PERSONAGGI[pid].corto}: da {FORMA[forma[pid]]} a {FORMA[forma[pid] + 1]}")
            rr = scegli("      Chi riposa? [numero] ", [str(i) for i in range(1, len(stanchi) + 1)])
            chi = stanchi[int(rr) - 1]
            riposi.append(chi)
            out(f"   ✔ {PERSONAGGI[chi].corto} stacca il telefono e dorme. Ora è {FORMA[forma[chi] + 1]}.")
        else:
            f = ids_f[int(r) - 1]
            noti.append(f)
            out(f"   ✔ {FATTI[f][0]}: {sc.fatti[f].upper()}")
    forma = forma_dopo_riposo(sc, riposi)

    while True:
        # 2. attrezzi
        titolo("2 · ATTREZZI — cosa portate")
        mostra_equip(sc)
        while True:
            r = leggi("   Quali portate? [numeri separati da spazio, Invio = niente] ")
            try:
                numeri = [int(x) for x in r.replace(",", " ").split()]
                if any(x < 1 for x in numeri):
                    raise ValueError
                scelti = frozenset(ids_e[x - 1] for x in numeri)
            except (ValueError, IndexError):
                out("   Non valido.")
                if not TTY:
                    raise SystemExit(1)
                continue
            mancanti = [EQUIP[e].nome for e in scelti if e in sc.introvabili]
            if mancanti:
                out(f"   Oggi non si trova: {', '.join(mancanti)}.")
            elif all(a in scelti for a in ARMI):
                out("   Una sola arma: pistola o fucile.")
            else:
                break
            if not TTY:
                raise SystemExit(1)
        spesa = sum(EQUIP[e].prezzo for e in scelti if e not in sc.magazzino)
        out(f"   Spesa in piazza: {spesa} mila." if spesa else "   Niente da comprare: tutto dal magazzino.")

        # 3. ruoli
        titolo("3 · RUOLI")
        para("Sala usa il Sangue freddo, cassaforte le Mani, volante il Volante.")
        for i, pid in enumerate(ids_p, 1):
            out(riga_membro(i, pid, forma))
        ruoli = {}
        presi = []
        for ruolo, etichetta_r in (("sala", "in sala"), ("cassaforte", "alla cassaforte"), ("volante", "al volante")):
            liberi = [str(i + 1) for i, pid in enumerate(ids_p) if pid not in presi]
            r = scegli(f"   Chi va {etichetta_r}? [{'/'.join(liberi)}] ", liberi)
            ruoli[ruolo] = ids_p[int(r) - 1]
            presi.append(ruoli[ruolo])

        # 4. battute
        titolo("4 · QUANTO RESTANO SUL BOTTINO")
        para(f"Ogni battuta una prova di Mani: se riesce la cassaforte rende {SACCHE_CASSAFORTE[0]} sacche la "
             f"prima volta, poi {SACCHE_CASSAFORTE[1]}, poi {SACCHE_CASSAFORTE[2]}; se fallisce solo vetrine, "
             f"+{SACCHE_VETRINE} sacca e +1 rumore. Dalla seconda battuta in poi, +{RUMORE_ATTESA} rumore "
             "a battuta solo per il tempo che passa.")
        battute = int(scegli(f"   Quante battute? [1-{MAX_BOTTINO}] ",
                             [str(i) for i in range(1, MAX_BOTTINO + 1)]))

        # 5. piani B
        titolo(f"5 · PIANI B — fino a {MAX_PIANI_B}")
        para("Per le condizioni senza piano B decide il Sangue freddo di chi è in sala (soglia "
             f"{SOGLIA_PANICO}): se fallisce è panico, +2 rumore e una battuta di bottino persa.")
        for r_id, nota in NOTE_RISPOSTE.items():
            para(f"{RISPOSTE[r_id]}: {nota}", "     · ")
        piani_b = {}
        while len(piani_b) < MAX_PIANI_B:
            out()
            liberi = []
            for i, c in enumerate(ids_c, 1):
                if c not in piani_b:
                    out(f"   {i}  Se {CONDIZIONI[c]}")
                    liberi.append(str(i))
            r = scegli(f"   Piano B n. {len(piani_b) + 1}: per quale condizione? [numero, Invio = basta] ",
                       liberi, vuoto="")
            if r == "":
                break
            c = ids_c[int(r) - 1]
            valide = RISPOSTE_VALIDE[c]
            for i, r_id in enumerate(valide, 1):
                out(f"      {i}  {RISPOSTE[r_id]}")
            rr = scegli("      Allora… [numero] ", [str(i) for i in range(1, len(valide) + 1)])
            piani_b[c] = valide[int(rr) - 1]

        piano = Piano(ruoli["sala"], ruoli["cassaforte"], ruoli["volante"], scelti,
                      frozenset(noti), battute, piani_b, tuple(riposi))

        titolo("IL PIANO")
        mostra_piano(piano, sc)
        if piano.errori(sc):
            for e in piano.errori(sc):
                out(f"   ✘ {e}")
        elif scegli("   Si va? [s = si va / n = rifaccio dal punto 2] ", ["s", "n"], vuoto="s") == "s":
            return piano


def mostra_piano(p: Piano, sc: Scenario):
    forma = forma_dopo_riposo(sc, p.riposi)

    def chi(pid):
        fo = forma[pid]
        return f"{PERSONAGGI[pid].nome}{f' ({FORMA[fo]})' if fo else ''}"
    out(f"   Sala:        {chi(p.sala)}")
    out(f"   Cassaforte:  {chi(p.cassaforte)}")
    out(f"   Volante:     {chi(p.volante)}")
    nomi = [EQUIP[e].nome + ("" if e in sc.magazzino else f" ({EQUIP[e].prezzo} mila)") for e in EQUIP if e in p.equip]
    out(f"   Attrezzi:    {', '.join(nomi) or 'nessuno'}")
    if p.spesa(sc):
        out(f"   Spesa:       {p.spesa(sc)} mila")
    noti = ", ".join(f"{FATTI[f][0].lower()} {sc.fatti[f]}" for f in FATTI if f in p.sopralluoghi)
    out(f"   Sopralluogo: {noti or 'nessuno, si va al buio'}")
    if p.riposi:
        out(f"   Riposo:      {', '.join(PERSONAGGI[x].corto for x in p.riposi)}")
    out(f"   Bottino:     {p.battute} battut{'a' if p.battute == 1 else 'e'}")
    if p.piani_b:
        for c, r in p.piani_b.items():
            out(f"   Piano B:     se {CONDIZIONI[c]} → {RISPOSTE[r]}")
    else:
        out("   Piano B:     nessuno")
    quota = sum(PERSONAGGI[x].quota for x in p.banda())
    out(f"   Quote banda: {quota}% — a te resta il {100 - quota}%")


class Umano:
    """Le telefonate dal vivo."""

    def prima(self, colpo, opzioni):
        if "fuori" in opzioni:
            r = scegli(f"   ☎ Interventi rimasti: {colpo.interventi}. [Invio = lasci fare / f = «Fuori adesso»] ",
                       ["f"], vuoto="")
            return "fuori" if r == "f" else None
        r = scegli(f"   ☎ Stanno per uscire con {colpo.sacche} sacche. Interventi rimasti: {colpo.interventi}. "
                   "[Invio = escono / r = «Ancora una battuta»] ", ["r"], vuoto="")
        return "resta" if r == "r" else None

    def ripeti(self, colpo, nome, chi, margine):
        r = scegli(f"   ☎ Fallita di {-margine}. Spendi un intervento per farla ripetere? "
                   f"(rimasti: {colpo.interventi}) [s/N] ", ["s", "n"], vuoto="n")
        return r == "s"


def voce_terminale(tipo, testo):
    if tipo == "battuta":
        pausa()
        out()
        out(testo)
    elif tipo == "prova":
        for w in textwrap.wrap(testo, LARGO, subsequent_indent="      "):
            out(w)
        pausa("      [Invio: tira il dado] ")
    else:
        for i, r in enumerate(testo.split("\n")):
            rientro = " " * (len(r) - len(r.lstrip()) + (0 if i == 0 else 0))
            for w in textwrap.wrap(r, LARGO, subsequent_indent=rientro + "   ") or [""]:
                out(w)


def rapporto(c: Colpo, e: Esito, sc: Scenario, p: Piano):
    titolo(f"ESITO — {e.verdetto}")
    quota = sum(PERSONAGGI[x].quota for x in p.banda() if x not in c.arrestati)
    if e.presi:
        out("   Bottino:    sequestrato")
    else:
        out(f"   Bottino:    {e.sacche} sacche = {e.sacche * VALORE_SACCA} mila euro; "
            f"tolte le quote ({quota}%) ti restano {e.netto:.0f} mila")
    nomi = lambda l: ", ".join(PERSONAGGI[x].corto for x in l)
    out(f"   Feriti:     {e.feriti} della banda{f' ({nomi(c.feriti)})' if c.feriti else ''}, {e.civili} tra civili e guardie")
    if c.arrestati:
        out(f"   Arrestati:  {nomi(c.arrestati)}")
    out(f"   Testimoni:  {e.testimoni}")
    out(f"   Calore:     {e.calore}/10")
    for v, causa in e.voci_calore:
        out(f"                 +{v} {causa}")
    out()
    if e.presi:
        out(f"   CONTO FINALE: {e.conto:+.0f} mila — tutti dentro: cauzioni e avvocati.")
    else:
        pezzi = [f"{e.netto:.0f} di bottino", f"- {COSTO_CALORE * e.calore} per il calore ({e.calore} × {COSTO_CALORE})"]
        if e.feriti:
            pezzi.append(f"- {COSTO_FERITO * e.feriti} per curare i feriti")
        if e.arrestati:
            pezzi.append(f"- {COSTO_ARRESTO * e.arrestati} per gli arrestati")
        if e.spesa:
            pezzi.append(f"- {e.spesa} di attrezzi comprati")
        out(f"   CONTO FINALE: {e.conto:+.0f} mila  ({' '.join(pezzi)})")

    titolo("LA GIOIELLERIA, A CARTE SCOPERTE")
    for f, (nome, valori) in FATTI.items():
        nota = next(n for v, _, n in valori if v == sc.fatti[f])
        stato = "verificato" if f in p.sopralluoghi else "NON verificato"
        para(f"{nome}: {sc.fatti[f]} ({stato}) — {nota}")
    if e.allarme and not c.allarme_noto:
        para("L'allarme era silenzioso ed è scattato senza che la banda se ne accorgesse.")

    titolo("DA DOVE È VENUTO IL RUMORE")
    if not c.fonti:
        out("   Nessun rumore: un lavoro da manuale.")
    else:
        gruppi = {"scelta": "dalle tue scelte (attrezzi, armi, tempo dentro)", "dado": "da prove fallite",
                  "mazzo": "dal mazzo degli imprevisti", "forma": "da gente a pezzi che hai portato",
                  "panico": "da panico senza piano B", "fatto": "da fatti della gioielleria"}
        tot = {}
        for n, causa, cat in c.fonti:
            k = cat.split(":")[0]
            tot.setdefault(k, []).append((n, causa, cat))
        out(f"   Rumore totale {c.rumore} (allarme a {SOGLIA_ALLARME}):")
        for k, voci in tot.items():
            out(f"   · {sum(v[0] for v in voci)} {gruppi[k]}")
            for n, causa, cat in voci:
                extra = ""
                if ":" in cat and cat.split(":")[1] not in p.sopralluoghi:
                    extra = " — fatto che non avevi verificato"
                out(f"        +{n} {causa}{extra}")
    if c.pb_usati or c.panici or c.usati:
        out()
        for cnd in c.pb_usati:
            out(f"   Piano B scattato: se {CONDIZIONI[cnd]} → {RISPOSTE[p.piani_b[cnd]]}")
        senza = [x for x in c.scattate if x not in c.pb_usati]
        if senza:
            out(f"   Condizioni scattate senza piano B: {', '.join(CONDIZIONI[x] for x in senza)}")
        for u in c.usati:
            out(f"   Intervento — {u}")
    scartati = [x for x in p.piani_b if x not in c.pb_usati]
    if scartati:
        out(f"   Piani B mai scattati: {', '.join(CONDIZIONI[x] for x in scartati)}")


def salva_registro(seme):
    cartella = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partite")
    os.makedirs(cartella, exist_ok=True)
    nome = f"colpo_{seme}_{datetime.datetime.now():%Y%m%d-%H%M%S}.txt"
    percorso = os.path.join(cartella, nome)
    with open(percorso, "w", encoding="utf-8") as f:
        f.write("\n".join(REGISTRO) + "\n")
    return percorso


def main(argv):
    if "--carte" in argv:
        mostra_carte()
        return
    args = [a for a in argv if not a.startswith("-")]
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return
    try:
        seme = int(args[0]) if args else random.randint(1000, 9999)
    except ValueError:
        raise SystemExit("Il numero del colpo deve essere un intero, es.: python3 colpo.py 4821")
    sc = genera_scenario(seme)
    try:
        piano = pianifica(sc)
        titolo("ESECUZIONE — ora guardi")
        para("Una battuta alla volta. Premi Invio per andare avanti. Le telefonate sono poche: usale bene.")
        colpo = Colpo(sc, piano, sorte=None, decisore=Umano(), voce=voce_terminale)
        esito = colpo.esegui()
        pausa()
        rapporto(colpo, esito, sc, piano)
        out()
        para(f"Per rigiocare la stessa gioielleria con un altro piano: python3 colpo.py {seme}")
        nota = leggi("   Una riga a caldo, prima di dimenticarla (Invio per saltare): ")
        if nota:
            REGISTRO.append(f"NOTA A CALDO: {nota}")
    except KeyboardInterrupt:
        out()
        out("   Interrotto.")
    finally:
        if len(REGISTRO) > 5:
            print(f"\n   Partita salvata in: {salva_registro(seme)}")


if __name__ == "__main__":
    main(sys.argv[1:])
