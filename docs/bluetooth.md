# Bluetooth MaixCam2 + manette Xbox

## Activation

```shell
bluetoothctl power on
bluetoothctl pairable on
```

## Firmware manette (OBLIGATOIRE)

Les manettes Xbox Wireless (surtout Series X/S, PID `0B13`) **doivent** avoir le
firmware à jour via **Windows → Xbox Accessories** (Microsoft Store).

Sans MAJ firmware, sur le noyau MaixCAM **4.19** on voit typiquement :

- logo Xbox qui **clignote en continu** alors que BlueZ dit `Connected: yes`
- boucle `Connected: yes` / `Connected: no`
- journal BlueZ : `HID Information read failed` / `unlikely error`
- `/dev/input/event*` qui apparaît puis disparaît

Après une MAJ firmware : **oublier** la manette sur la cam
(`bluetoothctl remove MAC` ou bouton **PAIR** de l’app) puis re-pairer avec **SYNC**.
L’ancien bond est souvent inutilisable.

Aussi : **oublier la manette sur le PC** pendant le pair (sinon elle reste collée au PC).

## Pairing chiffré (obligatoire pour le joystick)

Sans bond chiffré, BlueZ peut afficher `Connected: yes` + UUID HID **sans** créer
`/dev/input/event*` pour la manette. Les sticks ne marchent pas.

L’app démarre un **bluetoothctl PTY** au lancement (`agent NoInputNoOutput`) et
le laisse vivant jusqu’à la sortie. Contournement noyau 4.19 : `disable_ertm=Y`
(appliqué au démarrage de l’app).

- **PAIR** = retire l’ancien bond + nouveau bond chiffré (hold **SYNC**, logo clignote vite)
- **CONNECT** = reconnecte un bond déjà bon (logo Xbox court, pas SYNC)

Succès réel = logo **fixe** + `HID reports flowing` dans les logs (pas seulement `Connected: yes`).

### Pairing manuel (SSH)

```shell
python3 /root/pair_xbox_encrypted.py 78:86:2E:AC:8D:03 90
```

Ou depuis le PC :

```powershell
scp tools\pair_xbox_encrypted.py root@10.17.43.1:/root/
ssh root@10.17.43.1 "python3 /root/pair_xbox_encrypted.py 78:86:2E:AC:8D:03 90"
```

Vérifier :

```shell
cat /proc/bus/input/devices | grep -i xbox
ls /dev/input/event*
```

## Application

`maixcam/roverMecanum/` : PAIR / CONNECT UI + evdev.

```powershell
.\tools\deploy_rover_mecanum.ps1 -DeployOnly
```

## Erreurs fréquentes

- Scan vide → SYNC clignotement rapide, <1 m, manette oubliée sur le PC
- Logo clignote + Connected yes/no → firmware Xbox pas à jour, ou re-PAIR après MAJ
- HID UUID sans event → PAIR (remove + bond chiffré)
- Ne jamais `bluetoothctl disconnect` (éteint souvent la manette)
