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

# Weevil Underwood'un bocek destesi (40 kart)
INSECT_DECK = [
    # Monster Cards (22)
    48579379,   # Perfectly Ultimate Great Moth
    14141448,   # Great Moth
    91512835,   # Insect Queen
    41456841,   # Metamorphosed Insect Queen
    37957847,   # Insect Princess
    26185991,   # Pinch Hopper
    26185991,   # Pinch Hopper (x2)
    84834865,   # Flying Kamakiri #1
    84834865,   # Flying Kamakiri #1 (x2)
    84834865,   # Flying Kamakiri #1 (x3)
    40240595,   # Cocoon of Evolution
    40240595,   # Cocoon of Evolution (x2)
    27911549,   # Parasite Paracide
    4266839,    # Kiseitai
    14457896,   # Parasite Paranoid
    14457896,   # Parasite Paranoid (x2)
    14457896,   # Parasite Paranoid (x3)
    58192742,   # Petit Moth
    58192742,   # Petit Moth (x2)
    88979991,   # Killer Needle
    3134241,    # Flying Kamakiri #2
    26932788,   # Javelin Beetle

    # Spell Cards (11)
    3492538,    # Insect Armor with Laser Cannon
    3492538,    # Insect Armor with Laser Cannon (x2)
    3492538,    # Insect Armor with Laser Cannon (x3)
    23615409,   # Insect Barrier
    23615409,   # Insect Barrier (x2)
    23615409,   # Insect Barrier (x3)
    22991179,   # Insect Neglect
    83764718,   # Monster Reborn
    41182875,   # Javelin Beetle Pact
    80402389,   # Verdant Sanctuary
    94716515,   # Eradicating Aerosol

    # Trap Cards (7)
    74701381,   # DNA Surgery
    74701381,   # DNA Surgery (x2)
    74701381,   # DNA Surgery (x3)
    13235258,   # Corrosive Scales
    13235258,   # Corrosive Scales (x2)
    13235258,   # Corrosive Scales (x3)
    56051648,   # Spider Egg
]

# Rex Raptor'un dinozor destesi (40 main + 3 extra)
REX_RAPTOR_DECK = [
    # Monster Cards (22)
    81743801,   # Mighty Dino King Rex
    94568601,   # Tyrant Dragon
    6849042,    # Super-Ancient Dinobeast
    38670435,   # Black Tyranno
    55349196,   # Double-Headed Dino King Rex
    79870141,   # Mad Sword Beast
    50834074,   # Kaitoptera
    50834074,   # Kaitoptera (x2)
    50834074,   # Kaitoptera (x3)
    77491079,   # Gale Lizard
    39892082,   # Balloon Lizard
    39892082,   # Balloon Lizard (x2)
    80280944,   # Giant Rex
    80280944,   # Giant Rex (x2)
    45894482,   # Gilasaurus
    45894482,   # Gilasaurus (x2)
    1784619,    # Uraby
    1784619,    # Uraby (x2)
    94119974,   # Two-Headed King Rex
    38289717,   # Crawling Dragon #2
    13069066,   # Sword Arm of Dragon
    75390004,   # Megazowler

    # Spell Cards (10)
    23424603,   # Wasteland
    83764718,   # Monster Reborn
    45141013,   # Heat Wave
    22431243,   # Ultra Evolution Pill
    38179121,   # Double Evolution Pill
    24094653,   # Polymerization
    24094653,   # Polymerization (x2)
    99531088,   # Jurassic Power
    99531088,   # Jurassic Power (x2)
    99531088,   # Jurassic Power (x3)

    # Trap Cards (8)
    4206964,    # Trap Hole
    4206964,    # Trap Hole (x2)
    4206964,    # Trap Hole (x3)
    29401950,   # Bottomless Trap Hole
    29401950,   # Bottomless Trap Hole (x2)
    29401950,   # Bottomless Trap Hole (x3)
    11925569,   # Hunting Instinct
    58272005,   # Survival of the Fittest

    # Extra Deck (3)
    86239173,   # Horned Saurus
    86239173,   # Horned Saurus (x2)
    16507828,   # Bracchio-raidus
]

# Pegasus — Toon destesi (40 main + 6 extra)
PEGASUS_DECK = [
    # Monster Cards (17)
    53183600,   # Blue-Eyes Toon Dragon
    21296502,   # Toon Dark Magician
    99261403,   # Dark Rabbit
    99261403,   # Dark Rabbit (x2)
    99261403,   # Dark Rabbit (x3)
    64116319,   # Toon Harpie Lady
    64116319,   # Toon Harpie Lady (x2)
    14558127,   # Ash Blossom & Joyous Spring
    14558127,   # Ash Blossom & Joyous Spring (x2)
    14558127,   # Ash Blossom & Joyous Spring (x3)
    90960358,   # Toon Dark Magician Girl
    97268402,   # Effect Veiler
    97268402,   # Effect Veiler (x2)
    97268402,   # Effect Veiler (x3)
    91842653,   # Toon Summoned Skull
    31733941,   # Red-Eyes Toon Dragon
    28711704,   # Toon Black Luster Soldier

    # Spell Cards (18)
    88032456,   # Mimicat
    88032456,   # Mimicat (x2)
    88032456,   # Mimicat (x3)
    15259703,   # Toon World
    15259703,   # Toon World (x2)
    15259703,   # Toon World (x3)
    73628505,   # Terraforming
    91500017,   # Toon Bookmark
    91500017,   # Toon Bookmark (x2)
    91500017,   # Toon Bookmark (x3)
    89997728,   # Toon Table of Contents
    89997728,   # Toon Table of Contents (x2)
    89997728,   # Toon Table of Contents (x3)
    27699122,   # Toon Page-Flip
    27699122,   # Toon Page-Flip (x2)
    27699122,   # Toon Page-Flip (x3)
    70560957,   # Toon Rollback
    24224830,   # Called by the Grave

    # Trap Cards (5)
    53094821,   # Toon Terror
    5832914,    # Toon Briefcase
    10045474,   # Infinite Impermanence
    10045474,   # Infinite Impermanence (x2)
    10045474,   # Infinite Impermanence (x3)

    # Extra Deck (6)
    23995346,   # Blue-Eyes Ultimate Dragon
    23995346,   # Blue-Eyes Ultimate Dragon (x2)
    25655502,   # Bickuribox
    25655502,   # Bickuribox (x2)
    11901678,   # Black Skull Dragon
    11901678,   # Black Skull Dragon (x2)
]

# Jaden Yuki'nin Elemental HERO + Neo-Spacian destesi (40 main + 15 extra)
JADEN_DECK = [
    # Monster Cards (20)
    89943723,   # Elemental HERO Neos
    21844576,   # Elemental HERO Avian
    58932615,   # Elemental HERO Burstinatrix
    84327329,   # Elemental HERO Clayman
    20721928,   # Elemental HERO Sparkman
    6480253,    # Wroughtweiler
    79979666,   # Elemental HERO Bubbleman
    86188410,   # Elemental HERO Wildheart
    89252153,   # Elemental HERO Necroshade
    59793705,   # Elemental HERO Bladedge
    89312388,   # Elemental HERO Prisma
    17955766,   # Neo-Spacian Aqua Dolphin
    54959865,   # Neo-Spacian Air Hummingbird
    89621922,   # Neo-Spacian Flare Scarab
    80344569,   # Neo-Spacian Grand Mole
    43237273,   # Neo-Spacian Dark Panther
    17732278,   # Neo-Spacian Glow Moss
    33875961,   # Dark Catapulter
    42256406,   # Card Blocker
    57116033,   # Winged Kuriboh
    98585345,   # Winged Kuriboh LV10

    # Spell Cards (17)
    24094653,   # Polymerization
    18511384,   # Fusion Recovery
    45906428,   # Miracle Fusion
    63035430,   # Skyscraper
    74825788,   # H - Heated Heart
    213326,     # E - Emergency Call
    37318031,   # R - Righteous Justice
    63703130,   # O - Oversoul
    81913510,   # NEX
    82639107,   # Convert Contact
    53046408,   # Emergency Provisions
    14772491,   # Common Soul
    55144522,   # Pot of Greed
    77565204,   # Future Fusion
    37630732,   # Power Bond
    25573054,   # Transcendent Wings (Quick-Play)
    54283059,   # Parallel World Fusion

    # Trap Cards (7)
    22020907,   # Hero Signal
    26647858,   # Hero Ring
    44676200,   # Hero Barrier
    191749,     # Hero Flash!!
    37412656,   # Hero Blast
    78387742,   # Fake Hero
    11913700,   # Instant Neo Space

    # Extra Deck (15)
    35809262,   # Elemental HERO Flame Wingman
    61204971,   # Elemental HERO Thunder Giant
    47737087,   # Elemental HERO Rampart Blaster
    25366484,   # Elemental HERO Shining Flare Wingman
    83121692,   # Elemental HERO Tempest
    10526791,   # Elemental HERO Wildedge
    81197327,   # Elemental HERO Steam Healer
    14225239,   # Elemental HERO Mariner
    81003500,   # Elemental HERO Necroid Shaman
    55615891,   # Elemental HERO Wild Wingman
    29343734,   # Elemental HERO Electrum
    52031567,   # Elemental HERO Mudballman
    41517968,   # Elemental HERO Darkbright
    60493189,   # Elemental HERO Plasma Vice
    31111109,   # Elemental HERO Divine Neos
]


# ============================================================================
# BATTLE CITY MACERASI — 7 anime-sadik deste
# Bot-exclusive kartlar (Slifer, Obelisk, Ra, Red-Eyes vb.) kullaniciya acilmaz.
# ============================================================================

# 1) Seeker (Rare Hunter) — Exodia FTK + stall (50 kart)
SEEKER_DECK = [
    33396948, 33396948, 33396948,
    70903634, 70903634, 70903634,
    7902349, 7902349, 7902349,
    8124921, 8124921, 8124921,
    44519536, 44519536, 44519536,
    58604027, 58604027, 58604027,
    74677422,
    13039848, 13039848,
    78423643,
    30190809, 30190809,
    5640330,
    31812496, 31812496,
    26202165, 26202165, 26202165,
    79571449, 79571449,
    72302403, 72302403,
    4031928,
    35762283, 35762283,
    12580477,
    67775894, 67775894,
    64043465, 64043465,
    35346968, 35346968,
    41420027,
    26905245, 26905245,
    98954106, 98954106,
    83968380,
]

# 2) Strings — Marik'in kuklasi, Slifer (50 main + 4 extra)
STRINGS_DECK = [
    10000020, 10000020, 10000020,
    31709826, 31709826, 31709826,
    46821314, 46821314,
    73216412, 73216412,
    16768387, 16768387,
    79387392, 79387392, 79387392,
    86569121,
    13676474,
    77936940,
    72657739,
    68638985,
    70124586,
    43730887,
    67284107, 67284107,
    70781052,
    78636495, 78636495,
    60694662, 60694662, 60694662,
    42469671,
    21770260, 21770260,
    24094653,
    94163677,
    83764718,
    58775978,
    57953380, 57953380,
    55144522,
    59094601,
    26905245, 26905245,
    21558682, 21558682,
    77414722,
    19252988,
    83968380, 83968380,
    98954106,
    # Extra Deck (4)
    5600127, 5600127,
    42166000, 42166000,
]

# 3) Arkana (Pandora) — Arcana Force + Dark Magician (60 main + 1 extra)
ARKANA_DECK = [
    46986414, 46986414, 46986414,
    83011277,
    97534104,
    72657739, 72657739,
    62892347, 62892347,
    69831560,
    5861892,
    8396952, 8396952,
    35781051, 35781051, 35781051,
    61175706, 61175706, 61175706,
    3376703, 3376703,
    97574404, 97574404,
    34568403, 34568403,
    60953118, 60953118,
    59712426,
    97452817,
    39761418,
    23846921,
    25280974, 25280974,
    99789342,
    63391643, 63391643,
    17896384,
    97120394, 97120394,
    11819473, 11819473, 11819473,
    73206827,
    97342942,
    83764718,
    76302448, 76302448,
    30913809,
    24094653,
    99189322, 99189322,
    36690018, 36690018,
    9287078, 9287078, 9287078,
    3171055, 3171055,
    50078509, 50078509,
    # Extra Deck (1)
    12686296,
]

# 4) Umbra & Lumis — Masked Beast (tek kisi, 47 main)
UMBRA_LUMIS_DECK = [
    48948935, 48948935, 48948935,
    13676474, 13676474, 13676474,
    86569121, 86569121, 86569121,
    49064413, 49064413, 49064413,
    34334692, 34334692, 34334692,
    87303357, 87303357, 87303357,
    11761845, 11761845, 11761845,
    14531242, 14531242, 14531242,
    13945283, 13945283, 13945283,
    16226786, 16226786, 16226786,
    94377247, 94377247, 94377247,
    82432018,
    20765952,
    56948373,
    22610082, 22610082, 22610082,
    62472614,
    50152549,
    46967601,
    42199039,
    98867329,
    75560629,
    29549364,
    57882509,
]

# 5) Yami Bakura — Destiny Board FTK + Dark Necrofear (45 main)
YAMI_BAKURA_DECK = [
    31829185,
    53982768,
    41442341,
    66989694,
    5434080,
    32541773,
    68049471,
    67105242,
    17358176,
    4920010,
    99030164,
    63665875,
    77936940,
    26202165,
    41855169,
    54652250, 54652250,
    15150365,
    51644030,
    33508719,
    78700060,
    55875323,
    28933734,
    16625614,
    78053598,
    30606547,
    97342942,
    5556668,
    43434803,
    70828912,
    83764718,
    55144522,
    31893528,
    67287533,
    94772232,
    30170981,
    4031928,
    14057297,
    93599951, 93599951,
    94212438,
    24068492,
    65743242,
    79852326,
    97077563,
]

# 6) Seto Kaiba (Battle City) — Obelisk + BEWD + XYZ Cannon (41 main + 5 extra)
KAIBA_BATTLECITY_DECK = [
    89631139, 89631139, 89631139,
    30113682,
    86281779,
    14898066,
    62651957,
    97590747,
    24611934,
    10000000,
    52824910,
    31553716,
    17444133,
    76909279,
    81985784,
    39507162,
    65622692,
    64500000,
    17985575,
    54912977,
    47415292,
    51481927,
    59750328,
    23265313,
    39238953,
    83764718,
    24094653,
    42534368,
    68005187,
    43973174,
    98045062,
    55713623,
    52503575,
    14315573,
    3103067,
    86871614,
    57728570,
    36261276,
    85758066,
    83555666,
    54591086,
    # Extra Deck (5)
    23995346,
    91998119,
    99724761,
    2111707,
    25119460,
]

# 7) Yami Marik — Ra + Lava Golem torture (40 main)
YAMI_MARIK_DECK = [
    13676474,
    86569121,
    38445524,
    52090844,
    31709826, 31709826,
    21593977,
    4335645,
    90980792,
    99050989,
    62543393,
    59546797,
    13944422,
    43730887,
    70124586,
    76052811,
    99747800,
    48948935,
    102380,
    10000010,
    51482758,
    83764718,
    55144522,
    22610082,
    86541496,
    98494543,
    65169794,
    70828912,
    95220856,
    5318639,
    44095762,
    93382620,
    2047519,
    1224927,
    37507488,
    12930501,
    21558682,
    54704216,
    65830223,
    26905245,
]
