# Candidate emojis for five-symbol device linking

Status: non-normative candidates for review. This is not an interoperability table, an approved verification alphabet,
or a claim that every pair is visually distinguishable. See [the linking proposal](../multi-device.md).

The list contains 512 unique emoji subjects: Matrix's 64 SAS symbols first, in their original order, then 448
extensions grouped for review. A five-symbol sequence from 512 uniformly distributed choices carries 45 bits.
The eventual device-group spec owns the reviewed derivation, fixed mapping and alphabet agreement.

## Sources and selection

- The first 64 symbols and labels come from [Matrix's SAS source table](https://github.com/matrix-org/matrix-spec/blob/main/data-definitions/sas-emoji.json), under Apache-2.0. Its existing translations can be reused for those symbols; the extensions still need localized labels.
- Extensions use [Unicode's emoji test data](https://unicode.org/Public/emoji/latest/emoji-test.txt), Emoji 18.0. They are fully qualified, single base characters with an optional emoji presentation selector, introduced in Emoji 13.0 or earlier. Source age helps compatibility; it does not guarantee font support.
- Selection favors animals, food, places, activities, objects and a few body parts. It excludes new skin-tone or gender variants, national flags, color-only variants, clock faces, and many close alternatives. The original Matrix selection is retained.
- This list supplies characters and names, not licensed artwork. Use consistent, separately licensed artwork for comparisons. Source license copies and attribution are in [emoji-source-licenses.txt](emoji-source-licenses.txt).

## Review before adoption

Review every symbol at the actual phone and desktop display sizes, in both themes and grayscale. Test all single-symbol
mismatches, repeated symbols, different writing directions and screen-reader labels. Pay particular attention to animal
silhouettes, food bowls, buildings, tools and media equipment. Distinct names and Unicode characters do not guarantee
distinct pictures. Automated uniqueness checks do not substitute for recognition testing.

Replace confusable entries before fixing a mapping. If 512 symbols cannot meet the comparison criteria, keep the
reviewed smaller set and a longer sequence instead of claiming 45 bits from five symbols in a smaller set. Once the
alphabet is fixed in the spec, clients cannot substitute or reorder symbols from later Unicode or Matrix releases.

## Candidate list

### Matrix SAS set

| Emoji | Label |
| --- | --- |
| 🐶 | Dog |
| 🐱 | Cat |
| 🦁 | Lion |
| 🐎 | Horse |
| 🦄 | Unicorn |
| 🐷 | Pig |
| 🐘 | Elephant |
| 🐰 | Rabbit |
| 🐼 | Panda |
| 🐓 | Rooster |
| 🐧 | Penguin |
| 🐢 | Turtle |
| 🐟 | Fish |
| 🐙 | Octopus |
| 🦋 | Butterfly |
| 🌷 | Flower |
| 🌳 | Tree |
| 🌵 | Cactus |
| 🍄 | Mushroom |
| 🌏 | Globe |
| 🌙 | Moon |
| ☁️ | Cloud |
| 🔥 | Fire |
| 🍌 | Banana |
| 🍎 | Apple |
| 🍓 | Strawberry |
| 🌽 | Corn |
| 🍕 | Pizza |
| 🎂 | Cake |
| ❤️ | Heart |
| 😀 | Smiley |
| 🤖 | Robot |
| 🎩 | Hat |
| 👓 | Glasses |
| 🔧 | Spanner |
| 🎅 | Santa |
| 👍 | Thumbs Up |
| ☂️ | Umbrella |
| ⌛ | Hourglass |
| ⏰ | Clock |
| 🎁 | Gift |
| 💡 | Light Bulb |
| 📕 | Book |
| ✏️ | Pencil |
| 📎 | Paperclip |
| ✂️ | Scissors |
| 🔒 | Lock |
| 🔑 | Key |
| 🔨 | Hammer |
| ☎️ | Telephone |
| 🏁 | Flag |
| 🚂 | Train |
| 🚲 | Bicycle |
| ✈️ | Aeroplane |
| 🚀 | Rocket |
| 🏆 | Trophy |
| ⚽ | Ball |
| 🎸 | Guitar |
| 🎺 | Trumpet |
| 🔔 | Bell |
| ⚓ | Anchor |
| 🎧 | Headphones |
| 📁 | Folder |
| 📌 | Pin |

### Animals & Nature

| Emoji | Label |
| --- | --- |
| 🐵 | monkey face |
| 🦍 | gorilla |
| 🦧 | orangutan |
| 🐺 | wolf |
| 🦊 | fox |
| 🦝 | raccoon |
| 🐅 | tiger |
| 🦓 | zebra |
| 🦌 | deer |
| 🦬 | bison |
| 🐮 | cow face |
| 🐗 | boar |
| 🐐 | goat |
| 🐪 | camel |
| 🦙 | llama |
| 🦒 | giraffe |
| 🦏 | rhinoceros |
| 🦛 | hippopotamus |
| 🐭 | mouse face |
| 🐿️ | chipmunk |
| 🦫 | beaver |
| 🦔 | hedgehog |
| 🦇 | bat |
| 🐻 | bear |
| 🐨 | koala |
| 🦥 | sloth |
| 🦨 | skunk |
| 🦘 | kangaroo |
| 🐾 | paw prints |
| 🦃 | turkey |
| 🐣 | hatching chick |
| 🕊️ | dove |
| 🦅 | eagle |
| 🦆 | duck |
| 🦢 | swan |
| 🦉 | owl |
| 🪶 | feather |
| 🦩 | flamingo |
| 🦚 | peacock |
| 🦜 | parrot |
| 🐸 | frog |
| 🐊 | crocodile |
| 🦎 | lizard |
| 🐍 | snake |
| 🐉 | dragon |
| 🦕 | sauropod |
| 🦖 | T-Rex |
| 🐳 | spouting whale |
| 🐬 | dolphin |
| 🦭 | seal |
| 🐡 | blowfish |
| 🦈 | shark |
| 🐚 | spiral shell |
| 🦀 | crab |
| 🦞 | lobster |
| 🦐 | shrimp |
| 🦑 | squid |
| 🦪 | oyster |
| 🐌 | snail |
| 🐜 | ant |
| 🐝 | honeybee |
| 🐞 | lady beetle |
| 🦗 | cricket |
| 🪳 | cockroach |
| 🕷️ | spider |
| 🕸️ | spider web |
| 🦂 | scorpion |
| 🦟 | mosquito |
| 🪰 | fly |
| 🪱 | worm |
| 🦠 | microbe |
| 💐 | bouquet |
| 🌸 | cherry blossom |
| 🌹 | rose |
| 🌻 | sunflower |
| 🌱 | seedling |
| 🪴 | potted plant |
| 🌲 | evergreen tree |
| 🌴 | palm tree |
| 🌾 | sheaf of rice |
| 🍀 | four leaf clover |
| 🍁 | maple leaf |

### Food & Drink

| Emoji | Label |
| --- | --- |
| 🍇 | grapes |
| 🍉 | watermelon |
| 🍊 | tangerine |
| 🍋 | lemon |
| 🍍 | pineapple |
| 🥭 | mango |
| 🍐 | pear |
| 🍑 | peach |
| 🍒 | cherries |
| 🥝 | kiwi fruit |
| 🫒 | olive |
| 🥥 | coconut |
| 🥑 | avocado |
| 🍆 | eggplant |
| 🥔 | potato |
| 🥕 | carrot |
| 🌶️ | hot pepper |
| 🥒 | cucumber |
| 🥬 | leafy green |
| 🥦 | broccoli |
| 🧄 | garlic |
| 🧅 | onion |
| 🥜 | peanuts |
| 🌰 | chestnut |
| 🍞 | bread |
| 🥐 | croissant |
| 🥖 | baguette bread |
| 🥨 | pretzel |
| 🥯 | bagel |
| 🥞 | pancakes |
| 🧇 | waffle |
| 🧀 | cheese wedge |
| 🍖 | meat on bone |
| 🍗 | poultry leg |
| 🥩 | cut of meat |
| 🥓 | bacon |
| 🍔 | hamburger |
| 🍟 | french fries |
| 🌭 | hot dog |
| 🥪 | sandwich |
| 🌮 | taco |
| 🌯 | burrito |
| 🥚 | egg |
| 🍳 | cooking |
| 🥗 | green salad |
| 🍿 | popcorn |
| 🧈 | butter |
| 🧂 | salt |
| 🥫 | canned food |
| 🍱 | bento box |
| 🍙 | rice ball |
| 🍚 | cooked rice |
| 🍜 | steaming bowl |
| 🍝 | spaghetti |
| 🍣 | sushi |
| 🍡 | dango |
| 🥟 | dumpling |
| 🥠 | fortune cookie |
| 🥡 | takeout box |
| 🍨 | ice cream |
| 🍩 | doughnut |
| 🍪 | cookie |
| 🧁 | cupcake |
| 🥧 | pie |
| 🍫 | chocolate bar |
| 🍬 | candy |
| 🍭 | lollipop |
| 🍯 | honey pot |
| 🍼 | baby bottle |
| 🥛 | glass of milk |
| ☕ | hot beverage |
| 🫖 | teapot |
| 🍾 | bottle with popping cork |
| 🍷 | wine glass |
| 🍸 | cocktail glass |
| 🍺 | beer mug |
| 🥤 | cup with straw |
| 🧃 | beverage box |
| 🧊 | ice |
| 🥢 | chopsticks |
| 🍴 | fork and knife |
| 🥄 | spoon |
| 🔪 | kitchen knife |
| 🏺 | amphora |

### Travel & Places

| Emoji | Label |
| --- | --- |
| 🌐 | globe with meridians |
| 🗺️ | world map |
| 🧭 | compass |
| ⛰️ | mountain |
| 🌋 | volcano |
| 🏕️ | camping |
| 🏖️ | beach with umbrella |
| 🏜️ | desert |
| 🏝️ | desert island |
| 🏟️ | stadium |
| 🧱 | brick |
| 🪨 | rock |
| 🪵 | wood |
| 🏠 | house |
| 🏭 | factory |
| 🏯 | Japanese castle |
| 🏰 | castle |
| 🗼 | Tokyo tower |
| 🗽 | Statue of Liberty |
| 🕌 | mosque |
| ⛩️ | shinto shrine |
| 🕋 | kaaba |
| ⛲ | fountain |
| ⛺ | tent |
| 🌅 | sunrise |
| ♨️ | hot springs |
| 🎠 | carousel horse |
| 🎡 | ferris wheel |
| 🎢 | roller coaster |
| 💈 | barber pole |
| 🎪 | circus tent |
| 🚌 | bus |
| 🚑 | ambulance |
| 🚒 | fire engine |
| 🚗 | automobile |
| 🚚 | delivery truck |
| 🚜 | tractor |
| 🏍️ | motorcycle |
| 🦽 | manual wheelchair |
| 🛺 | auto rickshaw |
| 🛴 | kick scooter |
| 🛹 | skateboard |
| 🛼 | roller skate |
| 🚏 | bus stop |
| 🛣️ | motorway |
| 🛤️ | railway track |
| 🛢️ | oil drum |
| ⛽ | fuel pump |
| 🚦 | vertical traffic light |
| 🛑 | stop sign |
| 🚧 | construction |
| ⛵ | sailboat |
| 🛶 | canoe |
| 🚢 | ship |
| 🪂 | parachute |
| 💺 | seat |
| 🚁 | helicopter |
| 🚟 | suspension railway |
| 🛰️ | satellite |
| 🛸 | flying saucer |
| 🛎️ | bellhop bell |
| 🧳 | luggage |
| ⌚ | watch |
| ⏱️ | stopwatch |
| 🌡️ | thermometer |
| ☀️ | sun |
| 🪐 | ringed planet |
| ⭐ | star |
| 🌠 | shooting star |
| ⛅ | sun behind cloud |
| 🌪️ | tornado |
| 🌀 | cyclone |
| 🌈 | rainbow |
| ⚡ | high voltage |
| ❄️ | snowflake |
| ☃️ | snowman |
| 💧 | droplet |
| 🌊 | water wave |

### Activities

| Emoji | Label |
| --- | --- |
| 🎃 | jack-o-lantern |
| 🎄 | Christmas tree |
| 🎆 | fireworks |
| 🧨 | firecracker |
| ✨ | sparkles |
| 🎈 | balloon |
| 🎉 | party popper |
| 🎎 | Japanese dolls |
| 🎏 | carp streamer |
| 🎐 | wind chime |
| 🎀 | ribbon |
| 🎫 | ticket |
| 🏅 | sports medal |
| 🏀 | basketball |
| 🏈 | american football |
| 🎾 | tennis |
| 🥏 | flying disc |
| 🎳 | bowling |
| 🏏 | cricket game |
| 🏓 | ping pong |
| 🏸 | badminton |
| 🥊 | boxing glove |
| 🥋 | martial arts uniform |
| 🥅 | goal net |
| ⛳ | flag in hole |
| ⛸️ | ice skate |
| 🎣 | fishing pole |
| 🤿 | diving mask |
| 🎿 | skis |
| 🛷 | sled |
| 🥌 | curling stone |
| 🎯 | bullseye |
| 🪀 | yo-yo |
| 🪁 | kite |
| 🔫 | water pistol |
| 🎱 | pool 8 ball |
| 🔮 | crystal ball |
| 🪄 | magic wand |
| 🎮 | video game |
| 🕹️ | joystick |
| 🎰 | slot machine |
| 🎲 | game die |
| 🧩 | puzzle piece |
| 🧸 | teddy bear |
| 🪅 | piñata |
| 🪆 | nesting dolls |
| ♠️ | spade suit |
| ♦️ | diamond suit |
| ♣️ | club suit |
| ♟️ | chess pawn |
| 🃏 | joker |
| 🀄 | mahjong red dragon |
| 🎴 | flower playing cards |
| 🎭 | performing arts |
| 🖼️ | framed picture |
| 🎨 | artist palette |
| 🧵 | thread |
| 🪡 | sewing needle |
| 🧶 | yarn |
| 🪢 | knot |

### Objects

| Emoji | Label |
| --- | --- |
| 🥽 | goggles |
| 🥼 | lab coat |
| 👔 | necktie |
| 👕 | t-shirt |
| 👖 | jeans |
| 🧣 | scarf |
| 🧤 | gloves |
| 🧦 | socks |
| 👗 | dress |
| 👘 | kimono |
| 🩳 | shorts |
| 👙 | bikini |
| 👛 | purse |
| 🛍️ | shopping bags |
| 🎒 | backpack |
| 👟 | running shoe |
| 👠 | high-heeled shoe |
| 👑 | crown |
| 🎓 | graduation cap |
| 🪖 | military helmet |
| 📿 | prayer beads |
| 💄 | lipstick |
| 💍 | ring |
| 💎 | gem stone |
| 📣 | megaphone |
| 🎼 | musical score |
| 🎶 | musical notes |
| 🎤 | microphone |
| 📻 | radio |
| 🎷 | saxophone |
| 🪗 | accordion |
| 🎹 | musical keyboard |
| 🎻 | violin |
| 🪕 | banjo |
| 🥁 | drum |
| 📱 | mobile phone |
| 📟 | pager |
| 📠 | fax machine |
| 🔋 | battery |
| 🔌 | electric plug |
| 💻 | laptop |
| 🖥️ | desktop computer |
| 🖨️ | printer |
| ⌨️ | keyboard |
| 🖱️ | computer mouse |
| 💾 | floppy disk |
| 💿 | optical disk |
| 🧮 | abacus |
| 🎥 | movie camera |
| 🎞️ | film frames |
| 📽️ | film projector |
| 🎬 | clapper board |
| 📺 | television |
| 📷 | camera |
| 📼 | videocassette |
| 🔍 | magnifying glass tilted left |
| 🕯️ | candle |
| 🔦 | flashlight |
| 🏮 | red paper lantern |
| 📖 | open book |
| 📜 | scroll |
| 📰 | newspaper |
| 🔖 | bookmark |
| 🪙 | coin |
| 💰 | money bag |
| 💵 | dollar banknote |
| 💳 | credit card |
| 🧾 | receipt |
| ✉️ | envelope |
| 📤 | outbox tray |
| 📦 | package |
| 📮 | postbox |
| 🗳️ | ballot box with ballot |
| 🖌️ | paintbrush |
| 💼 | briefcase |
| 📅 | calendar |
| 📈 | chart increasing |
| 📋 | clipboard |
| 📏 | straight ruler |
| 📐 | triangular ruler |
| 🗄️ | file cabinet |
| 🗑️ | wastebasket |
| 🪓 | axe |
| ⛏️ | pick |
| 🗡️ | dagger |
| 💣 | bomb |
| 🪃 | boomerang |
| 🏹 | bow and arrow |
| 🛡️ | shield |
| 🪚 | carpentry saw |
| 🪛 | screwdriver |
| 🔩 | nut and bolt |
| ⚙️ | gear |
| 🗜️ | clamp |
| ⚖️ | balance scale |
| 🦯 | white cane |
| 🔗 | link |
| ⛓️ | chains |
| 🧰 | toolbox |
| 🧲 | magnet |
| 🪜 | ladder |
| ⚗️ | alembic |
| 🧪 | test tube |
| 🧫 | petri dish |
| 🧬 | dna |
| 🔬 | microscope |
| 🔭 | telescope |
| 📡 | satellite antenna |
| 💉 | syringe |
| 🩸 | drop of blood |
| 💊 | pill |
| 🩹 | adhesive bandage |
| 🩺 | stethoscope |
| 🚪 | door |
| 🛗 | elevator |
| 🪞 | mirror |
| 🛏️ | bed |
| 🛋️ | couch and lamp |
| 🪑 | chair |
| 🚽 | toilet |
| 🪠 | plunger |
| 🚿 | shower |
| 🛁 | bathtub |
| 🪤 | mouse trap |
| 🪒 | razor |
| 🧹 | broom |
| 🧺 | basket |
| 🧻 | roll of paper |
| 🪣 | bucket |
| 🧼 | soap |
| 🪥 | toothbrush |
| 🧽 | sponge |
| 🧯 | fire extinguisher |
| 🛒 | shopping cart |
| 🚬 | cigarette |
| ⚰️ | coffin |
| 🪦 | headstone |
| ⚱️ | funeral urn |
| 🗿 | moai |
| 🪧 | placard |

### Body parts

| Emoji | Label |
| --- | --- |
| 🦶 | foot |
| 👂 | ear |
| 🧠 | brain |
| 🦷 | tooth |

