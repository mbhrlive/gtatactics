# Colpo alla gioielleria — regole del prototipo

Prototipo usa-e-getta per rispondere a una domanda sola: **pianificare e poi guardare diverte?**
I numeri veri stanno nel blocco `TARATURA` in cima a `colpo.py`: se li cambi lì, questa pagina va aggiornata a mano.

```
python3 colpo.py          nuovo colpo a caso
python3 colpo.py 4821     rigioca la gioielleria n. 4821 con un altro piano
python3 colpo.py --carte  stampa tutte le carte
```

Il numero del colpo fissa i 4 fatti nascosti e la forma del giorno della banda. Mazzo e dadi cambiano a ogni partita.

## 1. Cosa decidi prima

Hai **6 punti** da dividere tra sopralluogo e attrezzi, **2 piani B** e **2 interventi dal vivo**.

### Banda: scegli 3 su 5 e assegni i ruoli

Sala usa il Sangue freddo, cassaforte le Mani, volante il Volante.

| Chi | Freddo | Mani | Volante | Quota | Difetto |
|---|---|---|---|---|---|
| Nico «il Chirurgo» | 2 | 4 | 1 | 25% | Perfezionista: alla cassaforte ignora il primo ordine di uscire e fa ancora una battuta |
| Vera «la Gelida» | 4 | 2 | 2 | 15% | Ricercata: +2 calore se restano due o più testimoni |
| Tony «Pompa» | 3 | 1 | 2 | 15% | Grilletto facile: in sala, se fallisce una prova spara (un ferito, +2 rumore, mai silenziato) |
| Samir «il Tassista» | 2 | 1 | 4 | 15% | Nervoso: al volante, -1 alla fuga per ogni battuta di bottino oltre la prima |
| Lea «la Nipote» | 2 | 3 | 3 | 10% | Chiacchierona: +1 calore sempre, +2 in più se la arrestano |

**Forma del giorno**, visibile e sorteggiata per ognuno: in forma (+1 a tutto, 25%), normale (50%), a pezzi (-1 a tutto e +1 rumore a ogni prova fallita, 25%).

### Sopralluogo: 4 fatti nascosti, 1 punto l'uno

| Fatto | Valori e probabilità | Cosa cambia |
|---|---|---|
| Guardia | assente 40%, anziana 35%, armata 25% | Soglia della sala 5 / 6 / 8. Se la sala sfugge: l'anziana preme l'antipanico (+1 rumore); l'armata spara (senza un'arma: un ferito e +2 rumore) |
| Allarme | sirena 34%, centrale 33%, silenzioso 33% | Polizia sul posto dopo 2 / 1 / 1 battute. Contro la sirena il disturbatore non serve. Quello silenzioso la banda non lo sente, se non l'hai verificato o non hai lo scanner |
| Cassaforte | vecchia 40%, moderna 35%, a tempo 25% | Soglia 5 / 8 / 6. Quella a tempo è chiusa alla prima battuta di bottino (il trapano la apre lo stesso) |
| Affluenza | vuoto 30%, qualche cliente 45%, pieno 25% | Testimoni 0 / 2 / 4. Col pieno la sala ha +1 di soglia. Col vuoto niente cliente eroe |

Quello che non verifichi lo scopri entrando.

### Attrezzi

| Carta | Costo | Dà | Toglie |
|---|---|---|---|
| Pistola silenziata | 2 | Sala +1; se si spara alla guardia non fa rumore | Costa cara; Tony non la usa |
| Fucile a pompa | 1 | Sala +3 | +1 calore; se la sala sfugge parte un colpo (un ferito, +2 rumore) |
| Disturbatore | 2 | Polizia 2 battute più tardi | Inutile contro la sirena |
| Trapano termico | 2 | Mani +3 sulla cassaforte; apre anche quella a tempo | +1 rumore a ogni battuta di bottino |
| Auto veloce | 2 | Fuga +2 | +1 calore |
| Scanner radio | 1 | Vedi il conto alla rovescia, senti l'allarme silenzioso, +1 intervento | Non aiuta nessuna prova |

Una sola arma: pistola o fucile.

### Battute di bottino: 1, 2 o 3

A ogni battuta una prova di Mani. Se riesce, la cassaforte rende **4 sacche** la prima volta, poi **2**, poi **1**. Se fallisce: solo vetrine, +1 sacca e +1 rumore. Dalla seconda battuta in poi, **+1 rumore** a battuta per il solo tempo che passa.

### Piani B: fino a 2, "se… allora…"

| Se… | Allora puoi scegliere |
|---|---|
| scatta l'allarme | fuori subito / prendi un ostaggio / continua comunque |
| la guardia reagisce (la sala è sfuggita e c'è una guardia) | fuori subito / prendi un ostaggio / continua comunque |
| un uomo è ferito | fuori subito / lascia il ferito / continua comunque |
| si sentono le sirene (polizia a una battuta) | fuori subito / prendi un ostaggio / continua comunque |

- **Fuori subito**: si salta all'uscita con quello che c'è.
- **Prendi un ostaggio**: la polizia ritarda di 2 battute, oppure la guardia si arrende. +3 calore, +1 testimone.
- **Lascia il ferito**: niente peso in fuga e la sua quota resta a te, ma lo arrestano.
- **Continua comunque**: avanti come da piano, senza prova di panico.

**Senza piano B** per una condizione che scatta, decide il Sangue freddo di chi è in sala, soglia 6. Se fallisce è **panico**: +2 rumore e la prossima battuta di bottino va persa.

## 2. Cosa succede durante

Sei battute fisse, più le battute di bottino: **arrivo, ingresso, sala, bottino (1-3), uscita, fuga**.

A ogni battuta esce una carta dal **mazzo imprevisti**. Sono 10, sai quali, non in che ordine:

| Carte | Effetto |
|---|---|
| 3× Tutto liscio | Niente |
| Pattuglia di passaggio | +1 rumore; se esce in fuga, fuga -2 |
| Cliente eroe | Se siete dentro e c'è gente: Sangue freddo soglia 6, o +2 rumore; senza un'arma chi è in sala resta ferito |
| Telefonino | +2 testimoni (+1 se dentro non c'è nessuno) |
| Traffico | Fuga -1 |
| Corriere alla porta | Se siete dentro: +1 rumore |
| Nervi | +1 rumore per ogni membro a pezzi |
| Colpo di fortuna | In sala o sul bottino: +1 sacca |

**Prove**: dado a 6 + valore + modificatori contro una soglia. Soglia e numero che serve sono mostrati prima del tiro.

| Battuta | Chi | Soglia | Se fallisce |
|---|---|---|---|
| Ingresso | Mani di chi va alla cassaforte | 5 | +1 rumore |
| Sala | Sangue freddo + arma | 5, più guardia e pieno | +2 rumore, reagisce la guardia, testimoni interi |
| Bottino | Mani (+3 col trapano) | 5 / 8 / 6 | Solo vetrine, +1 rumore |
| Uscita (solo se la polizia è sul posto) | Sangue freddo di chi è in sala | 7 | Di 1-2: un ferito. Di 3 o più: un arresto |
| Fuga | Volante (+2 con l'auto) | 5 | Vedi sotto |

Se la sala riesce, i testimoni si dimezzano.

**Rumore, allarme, polizia.** A rumore **4** scatta l'allarme e parte il conto alla rovescia. Dopo l'allarme, ogni 2 punti di rumore in più la polizia arriva una battuta prima.

**Fuga.** Modificatori: allarme scattato -1, polizia arrivata dopo che siete usciti -2, polizia già sul posto all'uscita -3, ferito a bordo -1.
- Senza allarme nessuno vi insegue: se fallisce, +1 calore.
- Con l'allarme: fallire di 1-2 è un inseguimento (perdi un terzo delle sacche, +2 calore); di 3 o più vi prendono tutti.

**Interventi dal vivo**: 2 in tutto (3 con lo scanner). Ognuno è una di queste cose:
- «Fuori adesso», all'inizio della sala o di una battuta di bottino.
- «Ancora una battuta», quando stanno per uscire.
- Far ripetere una prova appena fallita.

## 3. Come finisce

Quattro numeri: **bottino, feriti, testimoni, calore** (da 0 a 10).

Calore: 1 di base, +2 se è scattato l'allarme, +1 ogni due testimoni (arrotondato in su), +2 per ogni ferito tra civili e guardie, +3 per l'ostaggio, +3 per ogni arrestato, +2 per l'inseguimento, più i difetti e gli attrezzi che lo alzano.

**Conto finale**, in migliaia di euro: ogni sacca vale 50, meno le quote di chi non è stato arrestato; poi si tolgono 20 per ogni punto di calore, 30 per ogni ferito della banda, 50 per ogni arrestato. Se vi prendono tutti: -200.

| Verdetto | Quando |
|---|---|
| Disastro | Presi tutti |
| A mani vuote | Zero sacche |
| Colpo sporco | Un ferito o un arrestato, oppure calore 7 o più |
| Colpo pulito | Calore 3 o meno e almeno 5 sacche |
| Colpo riuscito a metà | Tutto il resto |

A fine partita il gioco mostra i fatti nascosti e da dove è venuto ogni punto di rumore: tue scelte, prove fallite, mazzo, gente a pezzi, panico.

## 4. Cosa guardare mentre giochi

Sono le condizioni del documento di progetto. Segnale d'allarme se:

- dopo due partite fai sempre lo stesso piano;
- durante l'esecuzione ti annoi;
- quando va male te la prendi col dado e non con una tua scelta;
- i piani B non scattano mai, o scattano sempre e risolvono tutto;
- finito il colpo non ti viene voglia di raccontarlo.

Ogni partita viene salvata in `partite/`, con la riga di commento a caldo che scrivi alla fine.
