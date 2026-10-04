# Step 11: scoring x geometry ablation (proposed by the Codex review)

Planted strength 0.212 of the grain (step-7 definition), 3 disjoint blank patches x 5 withheld phrases = 15 trials per cell; 200 random strings + every one-letter variant per phrase. Grain PSD for whitening estimated on 286 tiles to the right of the test patches.

## blur x1

| scoring / geometry | first | top ten | median rank | top-1 letter error | localised |
|---|---|---|---|---|---|
| ncc/oracle | 0/15 | 0/15 | 85 | 0.38 | 15/15 |
| ncc/known_geometry | 0/15 | 0/15 | 121 | 0.60 | 14/15 |
| ncc/free_geometry | 0/15 | 0/15 | 118 | 0.63 | 14/15 |
| ncc_hp/oracle | 0/15 | 0/15 | 91 | 0.38 | 15/15 |
| ncc_hp/known_geometry | 0/15 | 0/15 | 117 | 0.57 | 14/15 |
| ncc_hp/free_geometry | 0/15 | 0/15 | 106 | 0.52 | 15/15 |
| whitened/oracle | 0/15 | 0/15 | 83 | 0.38 | 15/15 |
| whitened/known_geometry | 0/15 | 0/15 | 103 | 0.62 | 14/15 |
| whitened/free_geometry | 0/15 | 0/15 | 115 | 0.62 | 14/15 |

## blur x2

| scoring / geometry | first | top ten | median rank | top-1 letter error | localised |
|---|---|---|---|---|---|
| ncc/oracle | 0/15 | 0/15 | 48 | 0.21 | 15/15 |
| ncc/known_geometry | 0/15 | 0/15 | 61 | 0.22 | 15/15 |
| ncc/free_geometry | 0/15 | 0/15 | 59 | 0.12 | 15/15 |
| ncc_hp/oracle | 0/15 | 0/15 | 53 | 0.17 | 15/15 |
| ncc_hp/known_geometry | 0/15 | 0/15 | 58 | 0.22 | 15/15 |
| ncc_hp/free_geometry | 0/15 | 0/15 | 58 | 0.17 | 15/15 |
| whitened/oracle | 0/15 | 0/15 | 48 | 0.16 | 15/15 |
| whitened/known_geometry | 0/15 | 0/15 | 52 | 0.22 | 15/15 |
| whitened/free_geometry | 0/15 | 0/15 | 52 | 0.17 | 15/15 |

## blur x4

| scoring / geometry | first | top ten | median rank | top-1 letter error | localised |
|---|---|---|---|---|---|
| ncc/oracle | 0/15 | 4/15 | 18 | 0.12 | 15/15 |
| ncc/known_geometry | 0/15 | 3/15 | 18 | 0.12 | 15/15 |
| ncc/free_geometry | 0/15 | 3/15 | 18 | 0.12 | 15/15 |
| ncc_hp/oracle | 1/15 | 3/15 | 18 | 0.16 | 15/15 |
| ncc_hp/known_geometry | 0/15 | 2/15 | 18 | 0.12 | 15/15 |
| ncc_hp/free_geometry | 0/15 | 2/15 | 18 | 0.12 | 15/15 |
| whitened/oracle | 0/15 | 3/15 | 17 | 0.17 | 15/15 |
| whitened/known_geometry | 0/15 | 3/15 | 17 | 0.12 | 15/15 |
| whitened/free_geometry | 0/15 | 3/15 | 17 | 0.12 | 15/15 |

## sharp x1

| scoring / geometry | first | top ten | median rank | top-1 letter error | localised |
|---|---|---|---|---|---|
| ncc/oracle | 0/15 | 2/15 | 36 | 0.12 | 15/15 |
| ncc/known_geometry | 0/15 | 1/15 | 38 | 0.17 | 13/15 |
| ncc/free_geometry | 0/15 | 0/15 | 39 | 0.27 | 13/15 |
| ncc_hp/oracle | 0/15 | 1/15 | 36 | 0.12 | 15/15 |
| ncc_hp/known_geometry | 0/15 | 1/15 | 38 | 0.17 | 13/15 |
| ncc_hp/free_geometry | 0/15 | 1/15 | 38 | 0.27 | 13/15 |
| whitened/oracle | 14/15 | 15/15 | 1 | 0.01 | 15/15 |
| whitened/known_geometry | 14/15 | 15/15 | 1 | 0.01 | 15/15 |
| whitened/free_geometry | 14/15 | 15/15 | 1 | 0.01 | 15/15 |

## Blank controls (nothing planted; known geometry)

| phrase | ncc | ncc_hp | whitened |
|---|---|---|---|
| MAJOR MARCEL | rank 254 of 476 | rank 351 of 476 | rank 296 of 476 |
| BRAZEL RANCH | rank 169 of 476 | rank 173 of 476 | rank 191 of 476 |
| EIGHTH AIR FORCE | rank 218 of 551 | rank 345 of 551 | rank 365 of 551 |
| DISC | rank 70 of 301 | rank 108 of 301 | rank 85 of 301 |
| KQXV ZWPJT | rank 224 of 426 | rank 355 of 426 | rank 375 of 426 |

## Blur sweep at the measured strength (known geometry)

| letter blur sigma (full-res px) | ncc first / median rank | ncc_hp first / median rank | whitened first / median rank |
|---|---|---|---|
| 2.4 | 0/6 / 46.5 | 0/6 / 44 | 5/6 / 1 |
| 6 | 0/6 / 67 | 0/6 / 67.5 | 0/6 / 75.5 |
| 10 | 0/6 / 89 | 0/6 / 82 | 0/6 / 82 |
| 14 | 0/6 / 86 | 0/6 / 77 | 0/6 / 74 |
| 20 | 0/6 / 153 | 0/6 / 132 | 0/6 / 118.5 |
