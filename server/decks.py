# Yuki — Browser-Based Duel Game
# Copyright (C) 2026 Yuki Contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# decks.py — Hazir test desteleri

# Yugi Muto'nun klasik destesi (gorseldeki 40 kart)
YUGI_DECK = [
    # Monster Cards (24)
    46986414,   # Dark Magician
    75347539,   # Valkyrion the Magna Warrior
    78193831,   # Buster Blader
    38033121,   # Dark Magician Girl
    14778250,   # The Tricky
    65240384,   # Big Shield Gardna
    71413901,   # Breaker the Magical Warrior
    34710660,   # Electromagnetic Turtle
    64788463,   # King's Knight
    52077741,   # Obnoxious Celtic Guard
    73752131,   # Skilled Dark Magician
    73752131,   # Skilled Dark Magician (x2)
    45141844,   # Old Vindictive Magician
    40640057,   # Kuriboh
    99785935,   # Alpha The Magnet Warrior
    39256679,   # Beta The Magnet Warrior
    11549357,   # Gamma The Magnet Warrior
    67724379,   # Koumori Dragon
    15025844,   # Mystical Elf
    25652259,   # Queen's Knight
    87796900,   # Winged Dragon, Guardian of the Fortress #1
    90876561,   # Jack's Knight
    70781052,   # Summoned Skull
    5405694,    # Black Luster Soldier

    # Spell Cards (13)
    42664989,   # Card of Sanctity
    4031928,    # Change of Heart
    99789342,   # Dark Magic Curtain
    79571449,   # Graceful Charity
    83764718,   # Monster Reborn
    74848038,   # Monster Reincarnation
    24094653,   # Polymerization
    55144522,   # Pot of Greed
    72302403,   # Swords of Revealing Light
    63391643,   # Thousand Knives
    28553439,   # Magical Dimension
    5318639,    # Mystical Space Typhoon
    55761792,   # Black Luster Ritual

    # Trap Cards (3)
    62279055,   # Magic Cylinder
    44095762,   # Mirror Force
    18807108,   # Spellbinding Circle
]

# Bastion Misawa'nin destesi (40 kart)
BASTION_DECK = [
    # Monster Cards (19)
    22587018,   # Hydrogeddon
    22587018,   # Hydrogeddon (x2)
    22587018,   # Hydrogeddon (x3)
    58071123,   # Oxygeddon
    58071123,   # Oxygeddon (x2)
    43017476,   # Duoterion
    43017476,   # Duoterion (x2)
    15981690,   # Carboneddon
    85066822,   # Water Dragon
    6022371,    # Water Dragon Cluster
    41386308,   # Mathematician
    62397231,   # Hyozanryu
    72566043,   # Litmus Doom Swordsman
    51826619,   # Magnet Warrior Sigma Plus
    87814728,   # Magnet Warrior Sigma Minus
    86289475,   # Magnet Warrior Omega Plus
    24431911,   # Tellusion the Magna Warrior
    44839512,   # Conduction Warrior Linear Magnum Plus Minus

    # Spell Cards (13)
    55144522,   # Pot of Greed
    79571449,   # Graceful Charity
    83764718,   # Monster Reborn
    5318639,    # Mystical Space Typhoon
    8955148,    # Litmus Doom Ritual
    28596933,   # A Wingbeat of Giant Dragon
    24096228,   # Double Spell
    45898858,   # Bonding - H2O
    45898858,   # Bonding - H2O (x2)
    79402185,   # Bonding - D2O
    34959756,   # Living Fossil
    47325505,   # Fossil Dig
    65514302,   # Magnet Bonding

    # Trap Cards (8)
    83555666,   # Ring of Destruction
    62279055,   # Magic Cylinder
    14315573,   # Negate Attack
    53239672,   # Spirit Barrier
    74701381,   # DNA Surgery
    56769674,   # DNA Transplant
    6890729,    # Bonding - DHO
    58851034,   # Cursed Seal of the Forbidden Spell

    # Extra Deck (1)
    47247792,   # Conduction Warrior Plasma Magnum
]

# Seto Kaiba'nin destesi (43 kart)
KAIBA_DECK = [
    # Monster Cards (22)
    5053103,    # Battle Ox
    89631133,   # Blue-Eyes White Dragon
    89631133,   # Blue-Eyes White Dragon (x2)
    89631133,   # Blue-Eyes White Dragon (x3)
    86281779,   # Gadget Soldier
    62397231,   # Hyozanryu
    97590747,   # La Jinn the Mystical Genie of the Lamp
    24611934,   # Ryu-Kishin Powered
    66602787,   # Saggi the Dark Clown
    50005633,   # Swordstalker
    14898066,   # Vorse Raider
    62651957,   # X-Head Cannon
    65622692,   # Y-Dragon Head
    64500000,   # Z-Metal Tank
    39507162,   # Blade Knight
    52824910,   # Kaiser Glider
    17444133,   # Kaiser Sea Horse
    17985575,   # Lord of D.
    48948935,   # Masked Beast Des Gardius
    31786629,   # Thunder Dragon
    31786629,   # Thunder Dragon (x2)
    31786629,   # Thunder Dragon (x3)

    # Spell Cards (15)
    59750328,   # Card of Demise
    23265313,   # Cost Down
    98045062,   # Enemy Controller
    24874630,   # Fiend's Sanctuary
    39238953,   # Lullaby of Obedience
    83764718,   # Monster Reborn
    24094653,   # Polymerization
    55144522,   # Pot of Greed
    58641905,   # Ring of Defense
    55713623,   # Shrink
    42534368,   # Silent Doom
    68005187,   # Soul Exchange
    63102017,   # Stop Defense
    43973174,   # The Flute of Summoning Dragon
    43973174,   # The Flute of Summoning Dragon (x2)

    # Trap Cards (6)
    36261276,   # Interdimensional Matter Transporter
    83555666,   # Ring of Destruction
    54591086,   # Virus Cannon
    86871614,   # Cloning
    57728570,   # Crush Card Virus
    52503575,   # Final Attack Orders

    # Extra Deck (4)
    23995346,   # Blue-Eyes Ultimate Dragon
    91998119,   # XYZ-Dragon Cannon
    2111707,    # XY-Dragon Cannon
    54752875,   # Twin-Headed Thunder Dragon
]

# Ancient Gear destesi (40 main + 1 extra)
ANCIENT_GEAR_DECK = [
    # Monster Cards (20)
    83104731,   # Ancient Gear Golem
    83104731,   # Ancient Gear Golem (x2)
    83104731,   # Ancient Gear Golem (x3)
    31557782,   # Ancient Gear
    31557782,   # Ancient Gear (x2)
    31557782,   # Ancient Gear (x3)
    56094445,   # Ancient Gear Soldier
    56094445,   # Ancient Gear Soldier (x2)
    56094445,   # Ancient Gear Soldier (x3)
    10509340,   # Ancient Gear Beast
    80045583,   # Ancient Gear Cannon
    39303359,   # Ancient Gear Knight
    1953925,    # Ancient Gear Engineer
    60953949,   # Ancient Gear Box
    50933533,   # Ancient Gear Gadjiltron Dragon
    86321248,   # Ancient Gear Gadjiltron Chimera
    41172955,   # Green Gadget
    86445415,   # Red Gadget
    13839120,   # Yellow Gadget
    38479725,   # The Trojan Horse

    # Spell Cards (16)
    55144522,   # Pot of Greed
    79571449,   # Graceful Charity
    83764718,   # Monster Reborn
    5318639,    # Mystical Space Typhoon
    19613556,   # Heavy Storm
    70828912,   # Premature Burial
    40830387,   # Ancient Gear Fist
    30435145,   # Ancient Gear Factory
    4446672,    # Ancient Gear Explosive
    37457534,   # Ancient Gear Tank
    59811955,   # Ancient Gear Workshop
    313513,     # Spell Gear
    92001300,   # Ancient Gear Castle
    23171610,   # Limiter Removal
    24094653,   # Polymerization
    17375316,   # Confiscation

    # Trap Cards (4)
    28378427,   # Damage Condenser
    65810489,   # Statue of the Wicked
    65810489,   # Statue of the Wicked (x2)
    83133491,   # Zero Gravity

    # Extra Deck (1)
    12652643,   # Ultimate Ancient Gear Golem
]

# Joey Wheeler'in destesi (40 main + 5 extra)
JOEY_DECK = [
    # Monster Cards (30)
    74677422,   # Red-Eyes Black Dragon
    49003308,   # Gagagigo
    26378150,   # Rude Kaiser
    14977074,   # Garoozis
    18246479,   # Battle Steer
    10538007,   # Leogun
    48305365,   # Axe Raider
    1184620,    # Kojikocy
    15480588,   # Armored Lizard
    73481154,   # Destroyer Golem
    49791927,   # Tiger Axe
    49417509,   # Wolf
    68846917,   # Rock Ogre Grotto #1
    63432835,   # Stone Armadiller
    89904598,   # Anthrosaurus
    41218256,   # Claw Reacher
    55550921,   # Battle Warrior
    10071456,   # Protector of the Throne
    89272878,   # Guardian of the Labyrinth
    44287299,   # Masaki the Legendary Swordsman
    34460851,   # Flame Manipulator
    56342351,   # M-Warrior #1
    92731455,   # M-Warrior #2
    88819587,   # Baby Dragon
    71625222,   # Time Wizard
    40453765,   # Swamp Battleguard
    20394040,   # Lava Battleguard
    93969023,   # Black Metal Dragon
    40640057,   # Kuriboh
    26376390,   # Copycat

    # Spell Cards (5)
    24094653,   # Polymerization
    52097679,   # Shield & Sword
    32268901,   # Salamandra
    5318639,    # Mystical Space Typhoon
    52684508,   # Inferno Fire Blast

    # Trap Cards (5)
    61705417,   # Graverobber
    37390589,   # Kunai with Chain
    68540058,   # Metalmorph
    4206964,    # Trap Hole
    75902998,   # Trap Hole of Spikes

    # Extra Deck (5)
    11901678,   # Black Skull Dragon
    41462083,   # Thousand Dragon
    51828629,   # Giltia the D. Knight
    45231177,   # Flame Swordsman
    54541900,   # Karbonala Warrior
]

# Mai Valentine'in destesi (43 main)
MAI_DECK = [
    # Monster Cards (19)
    6924874,    # Harpie's Pet Baby Dragon
    31764353,   # Familiar-Possessed - Wynn
    80316585,   # Cyber Harpie Lady
    91932350,   # Harpie Lady 1
    76812113,   # Harpie Lady
    52040216,   # Harpie's Pet Dragon
    52040216,   # Harpie's Pet Dragon (x2)
    45547649,   # Birdface
    75064463,   # Harpie Queen
    12206212,   # Harpie Lady Sisters
    12206212,   # Harpie Lady Sisters (x2)
    68815132,   # Harpie Dancer
    79106360,   # Morphing Jar #2
    75582395,   # Faith Bird
    41396436,   # Blue-Winged Crown
    30532390,   # Sky Scout
    34100324,   # Harpie Girl
    34100324,   # Harpie Girl (x2)
    10202894,   # Skull Red Bird

    # Spell Cards (17)
    12181376,   # Triangle Ecstasy Spark
    63224564,   # Cyber Shield
    18144506,   # Harpie's Feather Duster
    75782277,   # Harpies' Hunting Ground
    90219263,   # Elegant Egotist
    90219263,   # Elegant Egotist (x2)
    90219263,   # Elegant Egotist (x3)
    19337371,   # Hysteric Sign
    86308219,   # Harpie Lady Phoenix Formation
    12580477,   # Raigeki
    53129443,   # Dark Hole
    45778932,   # Rising Air Current
    72302403,   # Swords of Revealing Light
    83764718,   # Monster Reborn
    55321970,   # Gust Fan
    98252586,   # Follow Wind
    70828912,   # Premature Burial

    # Trap Cards (7)
    14315573,   # Negate Attack
    77778835,   # Hysteric Party
    77414722,   # Magic Jammer
    83555666,   # Ring of Destruction
    44095762,   # Mirror Force
    22359980,   # Mirror Wall
    95132338,   # Aqua Chorus
]

# Syrus Truesdale'in destesi (40 main + 12 extra)
SYRUS_DECK = [
    # Monster Cards (20)
    36378213,   # Ambulanceroid
    71218746,   # Drillroid
    71218746,   # Drillroid (x2)
    71218746,   # Drillroid (x3)
    984114,     # Expressroid
    984114,     # Expressroid (x2)
    984114,     # Expressroid (x3)
    18325492,   # Gyroid
    43697559,   # Jetroid
    24311595,   # Rescueroid
    98049038,   # Stealthroid
    44729197,   # Steamroid
    44729197,   # Steamroid (x2)
    44729197,   # Steamroid (x3)
    99861526,   # Submarineroid
    99861526,   # Submarineroid (x2)
    99861526,   # Submarineroid (x3)
    61538782,   # Truckroid
    61538782,   # Truckroid (x2)
    7602840,    # UFOroid

    # Spell Cards (13)
    95286165,   # De-Fusion
    53046408,   # Emergency Provisions
    23171610,   # Limiter Removal
    5318639,    # Mystical Space Typhoon
    24094653,   # Polymerization
    24094653,   # Polymerization (x2)
    24094653,   # Polymerization (x3)
    37630732,   # Power Bond
    55144522,   # Pot of Greed
    30683373,   # Shield Crush
    23299957,   # Vehicroid Connection Zone
    23299957,   # Vehicroid Connection Zone (x2)
    10035717,   # Weapon Change

    # Trap Cards (7)
    97077563,   # Call of the Haunted
    62279055,   # Magic Cylinder
    60306104,   # No Entry!!
    97705809,   # Supercharge
    97705809,   # Supercharge (x2)
    97705809,   # Supercharge (x3)
    4206964,    # Trap Hole

    # Extra Deck (12)
    98927491,   # Ambulance Rescueroid
    98927491,   # Ambulance Rescueroid (x2)
    16114248,   # Pair Cycroid
    16114248,   # Pair Cycroid (x2)
    36256625,   # Super Vehicroid Jumbo Drill
    36256625,   # Super Vehicroid Jumbo Drill (x2)
    3897065,    # Super Vehicroid - Stealth Union
    3897065,    # Super Vehicroid - Stealth Union (x2)
    5368615,    # Steam Gyroid
    5368615,    # Steam Gyroid (x2)
    5368615,    # Steam Gyroid (x3)
    32752319,   # UFOroid Fighter
]

# Tyranno Hassleberry'nin destesi (44 main + 1 extra)
DINO_DECK = [
    # Monster Cards (22)
    15894048,   # Ultimate Tyranno
    41753322,   # Sauropod Brachion
    38670435,   # Black Tyranno
    65287621,   # Dark Driceratops
    83235263,   # Tyranno Infinity
    37265642,   # Sabersaurus
    36042004,   # Babycerasaurus
    82946847,   # Petiteranodon
    63259351,   # Miracle Jurassic Egg
    45894482,   # Gilasaurus
    2671330,    # Hyper Hammerhead
    92755808,   # Element Saurus
    77491079,   # Gale Lizard
    18372968,   # Razor Lizard
    79409334,   # Black Stego
    90654356,   # Black Ptera
    50896944,   # Black Brachios
    52319752,   # Black Veloci
    39396763,   # Dyna Base
    80280944,   # Giant Rex
    80186010,   # Destroyersaurus
    85520851,   # Super Conductor Tyranno

    # Spell Cards (14)
    22431243,   # Ultra Evolution Pill
    84808313,   # Big Evolution Pill
    10080320,   # Jurassic World
    10080320,   # Jurassic World (x2)
    83682725,   # Tail Swipe
    47325505,   # Fossil Dig
    82828051,   # Earthquake
    34959756,   # Living Fossil
    39041729,   # Spacetime Transcendence
    38179121,   # Double Evolution Pill
    55144522,   # Pot of Greed
    83764718,   # Monster Reborn
    24094653,   # Polymerization
    5318639,    # Mystical Space Typhoon

    # Trap Cards (8)
    23869735,   # Fossil Excavation
    11925569,   # Hunting Instinct
    79569173,   # Seismic Shockwave
    58419204,   # Survival Instinct
    65430834,   # Jurassic Impact
    42175079,   # Volcanic Eruption
    58272005,   # Survival of the Fittest
    60082869,   # Dust Tornado

    # Extra Deck (1)
    75780818,   # Dyna Tank
]
