***Adressing Patterns***

But : 

Création d'une base de paterns à projeter sur la scène. Après segmentation de l'image on retourne une liste
de patterns dans un certain ordre.

Input : 

Image RGB de la scène capturée par camera RB PI/scène à photographier
Paramètres connection serveur (ip, password, user_id, port = 22). Ne pas oublier d'autoriser SSH sur le serveur.

Output : 

liste de string :["vegetation", "background"]
liste de tableau numpy :[mask_vege.npy, mask_back.npy]

Serveur/communication :

Création d'une connection SSH depuis la raspberry Pi vers le serveur GPU. Une fois la connection établie, on peut 
lancer des commandes SCP (add/get) afin d'up/download des fichiers(image RGB, masques) vers ce serveur de façon
sécurisée.

Caméra : 

Prise d'une photo RGB puis enregistrement de celle-ci, la photo RGB est  prise pendant que le vidéo projecteur
affiche une image noir afin de ne pas saturer la caméra.

***2_RX_RGB_gpu__process_TX_mask_to_onepix*** #notebook gpu 

But : 

Produire une segmentation de la scène en trois classes distinctes : les plantes, les adventices et le sol.
Une fois la segmentation faite il faut pouvoir en enregistrer les 3 masques en format numpy. Ici, nous travaillons 
avec seulement deux classes car l'algorithme a du mal a différencier mauvaises herbes/plantes (entrainement réalisé
seulement sur un petit jeu de donnés qui ne contient pas les mêmes scène que lors de l'inférence). En effet,
il fautdrait pouvoir s'entrainer sur beaucoup plus d'images afin d'avoir un algorithme fiable quant à la prédiction
des classes.

Input : 

Image RGB de la scène capturée par camera RB PI.

Output :

2 masques un cachant le sol et l'autre cachant la végétation (format numpy) + masque cachant sol (format jpg).