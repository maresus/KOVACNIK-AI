#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${1:-http://127.0.0.1:8000}
SESSION_PREFIX=${2:-semantic-smoke-merged}
COUNTER=0

ask() {
  local msg="$1"
  COUNTER=$((COUNTER + 1))
  local session_id="${SESSION_PREFIX}-${COUNTER}"
  echo "\n> $msg"
  curl -s "$BASE_URL/chat" \
    -H 'Content-Type: application/json' \
    -d "{\"session_id\": \"$session_id\", \"message\": \"$msg\"}" | sed 's/^/  /'
}

# Odpiralni čas & splošno
ask "Kdaj ste odprti?"
ask "Ob kateri uri odprete?"
ask "Ali ste odprti ob ponedeljkih?"
ask "Ste odprti ob nedeljah?"
ask "Kakšen je vaš delovni čas?"
ask "Do kdaj ste odprti v soboto?"
ask "Ali imate odprto za praznike?"
ask "Kdaj je zadnji prihod na kosilo?"
ask "Ali moram rezervirati vnaprej?"
ask "Lahko pridem brez rezervacije?"

# Zajtrk
ask "Kaj je za zajtrk?"
ask "Ob kateri uri je zajtrk?"
ask "Ali je zajtrk vključen v ceno?"
ask "Kaj ponujate za zajtrk?"
ask "Ali imate domač zajtrk?"
ask "Je zajtrk bufet ali serviran?"
ask "Imate brezglutenski zajtrk?"
ask "Kaj dobim za zajtrk?"
ask "Ali je zajtrk obvezen?"
ask "Koliko stane zajtrk?"

# Večerja & hrana
ask "Koliko stane večerja?"
ask "Ob kateri uri je večerja?"
ask "Kaj je za večerjo?"
ask "Ali ponujate večerjo?"
ask "Imate vegetarijansko hrano?"
ask "Ali imate brezglutensko hrano?"
ask "Kaj je na jedilniku?"
ask "Kakšna je vikend ponudba?"
ask "Koliko stane kosilo?"
ask "Kaj ponujate za kosilo ob vikendih?"
ask "Imate degustacijski meni?"
ask "Koliko hodov ima degustacijski meni?"
ask "Ali prilagodite hrano za alergike?"
ask "Imate vegansko hrano?"
ask "Ali strežete večerjo ob ponedeljkih?"
ask "Jedilnik?"
ask "Kaj ponujate za kosilo?"

# Sobe & nastanitev
ask "Koliko sob imate?"
ask "Koliko stane nočitev?"
ask "Katere sobe imate?"
ask "Koliko stane soba za 2 osebi?"
ask "Imate družinsko sobo?"
ask "Ali imajo sobe balkon?"
ask "Imate klimatizirane sobe?"
ask "Ali je v sobi wifi?"
ask "Kdaj je prijava?"
ask "Kdaj je odjava?"
ask "Koliko nočitev moram rezervirati?"
ask "Kakšna je minimalna nočitev poleti?"
ask "Ali sprejemete hišne ljubljenčke?"
ask "Lahko pridem s psom?"
ask "Kako plačam?"
ask "Ali sprejemate kartice?"
ask "Imate parkirišče?"
ask "Je parking brezplačen?"
ask "Kaj je vključeno v ceno sobe?"
ask "Katera soba je najboljša za družino?"
ask "Koliko oseb gre v eno sobo?"
ask "Ali je zajtrk vključen?"

# Družina & kmetija
ask "Kdo je gospodar kmetije?"
ask "Povejte mi o družini."
ask "Kdo je Aljaž?"
ask "Kdo je Barbara?"
ask "Kdo kuha pri vas?"
ask "Kdo je Angelca?"
ask "Kako dolgo imate kmetijo?"
ask "Koliko zemlje imate?"
ask "Kakšne živali imate?"
ask "Ali imate krave?"
ask "Lahko otroci vidijo živali?"
ask "Ali lahko božamo zajčke?"
ask "Imate konje?"
ask "Ali lahko jahamo?"
ask "Koliko stane jahanje s ponijem?"
ask "Kdo ste vi?"
ask "Kdo je Julija?"
ask "Kdo je Ana?"

# Lokacija & kontakt
ask "Kje ste?"
ask "Kakšen je vaš naslov?"
ask "Kako vas najdem?"
ask "Koliko ste oddaljeni od Maribora?"
ask "Imate telefon?"
ask "Kakšna je vaša telefonska številka?"
ask "Kakšen je vaš email?"
ask "Na kateri nadmorski višini ste?"
ask "Kako pridem do vas z avtom?"
ask "Imate koordinate za GPS?"
ask "Kako vas najdemo"
ask "Kakšen je naslov"

# Izdelki & trgovina
ask "Kaj prodajate?"
ask "Imate marmelado?"
ask "Katere marmelade imate?"
ask "Koliko stane marmelada?"
ask "Imate domač liker?"
ask "Koliko stane borovničev liker?"
ask "Prodajate bunko?"
ask "Koliko stane pohorska bunka?"
ask "Imate domačo salamo?"
ask "Kje lahko kupim vaše izdelke?"
ask "Ali imate spletno trgovino?"
ask "Prodajate gibanico?"
ask "Kako naročim izdelke?"
ask "Imate darilne bone?"
ask "Koliko stane darilni bon?"
ask "Ali lahko kupim izdelke preko spleta?"

# Vina
ask "Kakšna vina imate?"
ask "Imate vinsko karto?"
ask "Ali ponujate vinsko spremljavo?"
ask "Ali imate lokalna vina?"

# Izleti & okolica
ask "Kaj je v okolici?"
ask "Kam na izlet?"
ask "Kakšen izlet priporočate v bližini?"
ask "Kako pridem do Areha?"
ask "Kako pridem v Rače?"

# Rezervacije
ask "Rad bi rezerviral sobo za vikend."
ask "Ali lahko rezerviram sobo?"
ask "Rad bi rezerviral mizo to nedeljo ob 13:00."
ask "Rezervacija mize za 4 osebe v soboto."
