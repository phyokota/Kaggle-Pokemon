import os

from cg.api import AreaType, Observation, Option, OptionType, SelectContext, to_observation_class


# Card IDs from EN_Card_Data.csv. The simulator only understands these numbers,
# so we give the important cards readable names here.
RIOLU = 677
LUCARIO = 678
LUNATONE = 675
SOLROCK = 676
MAKUHITA = 673
HARIYAMA = 674
MEOWTH = 1071

FIGHTING_ENERGY = 6
FIGHTING_GONG = 1142
UNFAIR_STAMP = 1080
POKE_PAD = 1152
PREMIUM_POWER_PRO = 1141
BLACK_BELT_TRAINING = 1211
AIR_BALLOON = 1174
JUDGE = 1213
LILLIE = 1227
ULTRA_BALL = 1121
WALLYS_COMPASSION = 1229
BOSSES_ORDERS = 1182
GRAVITY_MOUNTAIN = 1252

# Basic Pokemon that can be played directly onto the board.
BASIC_POKEMON = {RIOLU, LUNATONE, SOLROCK, MAKUHITA, MEOWTH}

# Which Pokemon we prefer when choosing our starting Active Pokemon.
STARTER_PRIORITY = {
    RIOLU: 700,
    SOLROCK: 600,
    MAKUHITA: 500,
    LUNATONE: 400,
    MEOWTH: 50,
}

# Which Pokemon we want to find first when a Trainer searches the deck.
POKEMON_SEARCH_PRIORITY = {
    RIOLU: 700,
    LUCARIO: 650,
    SOLROCK: 600,
    LUNATONE: 550,
    MAKUHITA: 500,
    HARIYAMA: 450,
    MEOWTH: 50,
}

# Which Pokemon should receive manual Energy attachments first.
ENERGY_TARGET_PRIORITY = {
    RIOLU: 700,
    LUCARIO: 650,
    SOLROCK: 600,
    MAKUHITA: 500,
    HARIYAMA: 450,
    LUNATONE: 400,
    MEOWTH: 50,
}

# Which Benched Pokemon should become Active after our Active is Knocked Out.
# Meowth is intentionally very low because we want to keep it out of the Active Spot.
BENCH_PROMOTION_PRIORITY = {
    LUCARIO: 900,
    SOLROCK: 700,
    HARIYAMA: 600,
    MAKUHITA: 500,
    LUNATONE: 400,
    MEOWTH: -1000,
}

# Highest attack Energy cost for each Pokemon in this deck.
MAX_ATTACK_COST = {
    RIOLU: 1,
    LUCARIO: 2,
    LUNATONE: 2,
    SOLROCK: 1,
    MAKUHITA: 2,
    HARIYAMA: 3,
    MEOWTH: 3,
}

# How much we want to play each Trainer during the main turn.
# Situational Trainers start lower and get boosted later when attacking is possible.
PLAY_TRAINER_PRIORITY = {
    FIGHTING_GONG: 700,
    POKE_PAD: 650,
    AIR_BALLOON: 600,
    ULTRA_BALL: 550,
    GRAVITY_MOUNTAIN: 500,
    LILLIE: 300,
    JUDGE: 280,
    UNFAIR_STAMP: 260,
    PREMIUM_POWER_PRO: 220,
    BLACK_BELT_TRAINING: 210,
    BOSSES_ORDERS: 200,
    WALLYS_COMPASSION: 150,
}

# When the game asks us to discard cards, higher numbers mean "discard this first."
# Fighting Energy is high because Mega Lucario can reuse it from the discard pile.
DISCARD_PRIORITY = {
    FIGHTING_ENERGY: 700,
    GRAVITY_MOUNTAIN: 500,
    JUDGE: 440,
    LILLIE: 430,
    UNFAIR_STAMP: 420,
    WALLYS_COMPASSION: 410,
    AIR_BALLOON: 350,
    PREMIUM_POWER_PRO: 300,
    BLACK_BELT_TRAINING: 290,
    BOSSES_ORDERS: 280,
    MEOWTH: 180,
    HARIYAMA: 160,
    MAKUHITA: 140,
    LUNATONE: 130,
    SOLROCK: 120,
    LUCARIO: 60,
    RIOLU: 40,
}


def read_deck_csv() -> list[int]:
    """Read deck.csv.
    
    Returns:
        list[int]: A list of card IDs in the deck.
    """
    file_path = "deck.csv"
    if not os.path.exists(file_path):
        file_path = "/kaggle_simulations/agent/" + file_path
    with open(file_path, "r") as file:
        csv = file.read().split("\n")
    deck = []
    for i in range(60):
        deck.append(int(csv[i]))
    return deck


# Get our player state from the observation.
def _your_state(obs: Observation):
    if obs.current is None:
        return None
    return obs.current.players[obs.current.yourIndex]


# Get the opponent's player state from the observation.
def _opponent_state(obs: Observation):
    if obs.current is None:
        return None
    return obs.current.players[1 - obs.current.yourIndex]


# Return the IDs of our Pokemon already in play, both Active and Benched.
def _pokemon_ids_in_play(obs: Observation) -> set[int]:
    player = _your_state(obs)
    if player is None:
        return set()
    ids = {pokemon.id for pokemon in player.bench}
    ids.update(pokemon.id for pokemon in player.active if pokemon is not None)
    return ids


# Return the IDs of cards currently in our hand.
def _hand_ids(obs: Observation) -> list[int]:
    player = _your_state(obs)
    if player is None or player.hand is None:
        return []
    return [card.id for card in player.hand]


# Convert an option's area/index pair into the actual card object it points at.
# The simulator stores cards in different areas like HAND, DECK, ACTIVE, and BENCH.
def _card_from_area(obs: Observation, area: AreaType | int | None, index: int | None, player_index: int | None):
    if obs.current is None or area is None or index is None:
        return None

    if area == AreaType.LOOKING and obs.current.looking is not None:
        if 0 <= index < len(obs.current.looking):
            return obs.current.looking[index]
        return None

    if area == AreaType.DECK and obs.select is not None and obs.select.deck is not None:
        if 0 <= index < len(obs.select.deck):
            return obs.select.deck[index]
        return None

    if player_index is None:
        player_index = obs.current.yourIndex

    player = obs.current.players[player_index]
    if area == AreaType.HAND and player.hand is not None:
        if 0 <= index < len(player.hand):
            return player.hand[index]
    elif area == AreaType.DISCARD:
        if 0 <= index < len(player.discard):
            return player.discard[index]
    elif area == AreaType.ACTIVE:
        if 0 <= index < len(player.active):
            return player.active[index]
    elif area == AreaType.BENCH:
        if 0 <= index < len(player.bench):
            return player.bench[index]
    elif area == AreaType.PRIZE:
        if 0 <= index < len(player.prize):
            return player.prize[index]
    elif area == AreaType.STADIUM:
        if 0 <= index < len(obs.current.stadium):
            return obs.current.stadium[index]
    return None


# Find the card ID connected to a selectable option.
# For PLAY options, the option index points into our hand.
def _card_id_for_option(obs: Observation, option: Option) -> int | None:
    if option.type == OptionType.PLAY:
        card = _card_from_area(obs, AreaType.HAND, option.index, obs.current.yourIndex)
    else:
        card = _card_from_area(obs, option.area, option.index, option.playerIndex)
    return None if card is None else card.id


# Find the Pokemon being targeted by an option, such as an Energy attachment target.
def _target_id_for_option(obs: Observation, option: Option) -> int | None:
    card = _card_from_area(obs, option.inPlayArea, option.inPlayIndex, obs.current.yourIndex)
    return None if card is None else card.id


def _pokemon_has_max_energy(pokemon) -> bool:
    # Stop attaching Energy once a Pokemon can pay for its most expensive attack.
    if pokemon is None or not hasattr(pokemon, "energies"):
        return False
    max_cost = MAX_ATTACK_COST.get(pokemon.id)
    if max_cost is None:
        return False
    return len(pokemon.energies) >= max_cost


def _can_find_lucario_next_turn(obs: Observation) -> bool:
    # Riolu is a better Active candidate when we can evolve it soon.
    hand = set(_hand_ids(obs))
    return LUCARIO in hand or ULTRA_BALL in hand


def _bench_promotion_score(obs: Observation, card_id: int) -> int:
    # Apply the KO replacement order, with Riolu boosted only when Lucario is reachable.
    if card_id == RIOLU:
        return 800 if _can_find_lucario_next_turn(obs) else 350
    return BENCH_PROMOTION_PRIORITY.get(card_id, STARTER_PRIORITY.get(card_id, 0))


def _hariyama_switch_needed(obs: Observation) -> bool:
    # Hariyama's evolution Ability matters most when we need to pull up a Bench target.
    opponent = _opponent_state(obs)
    if opponent is None or not opponent.bench:
        return False
    return not _active_can_be_knocked_out(obs, 270)


# Check whether a given damage amount would Knock Out the opponent's Active Pokemon.
def _active_can_be_knocked_out(obs: Observation, damage: int) -> bool:
    opponent = _opponent_state(obs)
    if opponent is None or len(opponent.active) == 0 or opponent.active[0] is None:
        return False
    return opponent.active[0].hp <= damage


# Check whether attacking is currently one of our legal choices.
def _has_attack_option(obs: Observation) -> bool:
    return any(option.type == OptionType.ATTACK for option in obs.select.option)


# Score yes/no prompts, like "do you want to go first?"
def _score_yes_no(obs: Observation, option: Option) -> int:
    if option.type == OptionType.YES:
        if obs.select.context == SelectContext.IS_FIRST:
            return 1000
        card_id = None
        if obs.select.contextCard is not None:
            card_id = obs.select.contextCard.id
        elif obs.select.effect is not None:
            card_id = obs.select.effect.id
        if card_id == LUNATONE:
            return 900
        if card_id == MEOWTH:
            return 100
        return 600
    if option.type == OptionType.NO:
        if obs.select.context == SelectContext.IS_FIRST:
            return 0
        card_id = None
        if obs.select.contextCard is not None:
            card_id = obs.select.contextCard.id
        elif obs.select.effect is not None:
            card_id = obs.select.effect.id
        if card_id == MEOWTH:
            return 500
        return 100
    return 0


# Score card-picking prompts, such as setup choices, search targets,
# discard costs, and choosing which Pokemon receives an effect.
def _score_card_selection(obs: Observation, option: Option) -> int:
    if option.type == OptionType.NUMBER:
        return option.number or 0

    card_id = _card_id_for_option(obs, option)
    if card_id is None:
        if option.type == OptionType.ENERGY:
            return option.count or 0
        return 0

    if obs.select.context == SelectContext.SETUP_ACTIVE_POKEMON:
        return STARTER_PRIORITY.get(card_id, 0)

    if obs.select.context == SelectContext.SETUP_BENCH_POKEMON:
        if card_id == MEOWTH:
            return 25
        return STARTER_PRIORITY.get(card_id, 0)

    if obs.select.context in {SelectContext.TO_HAND, SelectContext.LOOK}:
        # Search effects prefer the core attackers, plus Energy when it unlocks setup.
        in_play = _pokemon_ids_in_play(obs)
        hand = set(_hand_ids(obs))
        if card_id == FIGHTING_ENERGY:
            has_energy = FIGHTING_ENERGY in hand
            has_riolu_or_solrock = bool({RIOLU, SOLROCK} & in_play)
            has_lunar_cycle = {LUNATONE, SOLROCK}.issubset(in_play)
            return 680 if not has_energy and (has_riolu_or_solrock or has_lunar_cycle) else 300
        if card_id in POKEMON_SEARCH_PRIORITY:
            if card_id not in in_play:
                return POKEMON_SEARCH_PRIORITY[card_id]
            return max(100, POKEMON_SEARCH_PRIORITY[card_id] - 350)
        if card_id in {LILLIE, JUDGE, BOSSES_ORDERS, BLACK_BELT_TRAINING, WALLYS_COMPASSION}:
            return 250

    if obs.select.context == SelectContext.DISCARD:
        return DISCARD_PRIORITY.get(card_id, 200)

    if obs.select.context == SelectContext.TO_ACTIVE:
        # Usually this means replacing a Knocked Out Active Pokemon.
        return _bench_promotion_score(obs, card_id)

    if obs.select.context == SelectContext.SWITCH:
        # Switch choices use the same Active preference, while still avoiding Meowth.
        return _bench_promotion_score(obs, card_id)

    if obs.select.context == SelectContext.ATTACH_TO:
        # Effects that attach Energy should not overfill a Pokemon past its attack needs.
        target = _card_from_area(obs, option.area, option.index, option.playerIndex)
        if _pokemon_has_max_energy(target):
            return -200
        return ENERGY_TARGET_PRIORITY.get(card_id, STARTER_PRIORITY.get(card_id, 0))

    return POKEMON_SEARCH_PRIORITY.get(card_id, DISCARD_PRIORITY.get(card_id, 0))


# Score main-turn actions like Attack, Evolve, Attach Energy, Play a card,
# use an Ability, Retreat, or End Turn.
def _score_main_action(obs: Observation, option: Option) -> int:
    if option.type == OptionType.ATTACK:
        # Prefer Mega Lucario's strongest attack when it finishes the opponent's Active.
        if option.attackId == 1210 and _active_can_be_knocked_out(obs, 270):
            return 1000
        if option.attackId == 1209:
            return 900
        if option.attackId == 1210:
            return 850
        return 800

    if option.type == OptionType.EVOLVE:
        # Bench evolutions are safer, and Hariyama waits until its switch Ability matters.
        target_id = _target_id_for_option(obs, option)
        card_id = _card_id_for_option(obs, option)
        target_bonus = 250 if option.inPlayArea == AreaType.BENCH else 0
        if card_id == LUCARIO and target_id == RIOLU:
            return 780 + target_bonus
        if card_id == HARIYAMA and target_id == MAKUHITA:
            if _hariyama_switch_needed(obs):
                return 650 + target_bonus
            return 100 + target_bonus
        return 600 + target_bonus

    if option.type == OptionType.ATTACH:
        # Manual attachments follow target priority unless that Pokemon is already capped.
        card_id = _card_id_for_option(obs, option)
        target = _card_from_area(obs, option.inPlayArea, option.inPlayIndex, obs.current.yourIndex)
        target_id = None if target is None else target.id
        if target is not None and _pokemon_has_max_energy(target):
            return -200
        if card_id == FIGHTING_ENERGY:
            return 700 + ENERGY_TARGET_PRIORITY.get(target_id, 0)
        return 300 + ENERGY_TARGET_PRIORITY.get(target_id, 0)

    if option.type == OptionType.ABILITY:
        card_id = _card_id_for_option(obs, option)
        if card_id == LUNATONE:
            return 730
        if card_id == MEOWTH:
            return 250
        return 500

    if option.type == OptionType.PLAY:
        card_id = _card_id_for_option(obs, option)
        hand = _hand_ids(obs)
        
        # --- RULE 1: MEOWTH RESTRICTION ---
        if card_id == MEOWTH:
            opponent = _opponent_state(obs)
            # Check for low hand size OR rough heuristic for "winning game with ability"
            opp_active_low = opponent and opponent.active and opponent.active[0] and opponent.active[0].hp <= 30
            if len(hand) <= 3 or opp_active_low:
                return 850
            return -1000

        # --- RULES 4 & 5: TRAINER PLAY PRIORITIES ---
        priority_items = {FIGHTING_GONG, POKE_PAD, ULTRA_BALL}
        has_priority_item = any(item in hand for item in priority_items)
        
        if card_id in priority_items:
            return 2000
            
        draw_supporters = {UNFAIR_STAMP, LILLIE, JUDGE}
        if card_id in draw_supporters:
            if not has_priority_item:
                return 1900
            else:
                return PLAY_TRAINER_PRIORITY.get(card_id, 200)

        # Standard play logic for other cards
        if card_id in BASIC_POKEMON:
            return STARTER_PRIORITY.get(card_id, 0)
            
        if card_id in PLAY_TRAINER_PRIORITY:
            score = PLAY_TRAINER_PRIORITY[card_id]
            if card_id == PREMIUM_POWER_PRO and _has_attack_option(obs):
                score = 980
            elif card_id == BLACK_BELT_TRAINING and _has_attack_option(obs):
                score = 960
            elif card_id == BOSSES_ORDERS and _has_attack_option(obs):
                score = 940
            if card_id == WALLYS_COMPASSION:
                your = _your_state(obs)
                active = your.active[0] if your and your.active else None
                if active is not None and active.id == LUCARIO and active.hp <= active.maxHp // 2:
                    score += 500
            return score
            
        return 250

    if option.type == OptionType.RETREAT:
        your = _your_state(obs)
        if your is not None and your.active and your.active[0] is not None:
            active_id = your.active[0].id
            active_priority = BENCH_PROMOTION_PRIORITY.get(active_id, STARTER_PRIORITY.get(active_id, 0))
            
            bench_ids = [p.id for p in your.bench if p is not None]
            bench_priorities = [BENCH_PROMOTION_PRIORITY.get(bid, STARTER_PRIORITY.get(bid, 0)) for bid in bench_ids]
            
            # --- RULE 2: SWAP IF LUCARIO EXISTS ON BENCH ---
            if LUCARIO in bench_ids and active_id != LUCARIO:
                return 1500
                
            # --- RULE 3: SWAP IF BENCH HAS HIGHER PRIORITY ---
            if bench_priorities and max(bench_priorities) > active_priority:
                return 1400
                
        return 120

    if option.type == OptionType.END:
        return -100

    return 0


# Route each legal option to the correct scoring function based on option type.
def _score_option(obs: Observation, option: Option) -> int:
    if option.type in {OptionType.YES, OptionType.NO}:
        return _score_yes_no(obs, option)
    if option.type in {
        OptionType.CARD,
        OptionType.TOOL_CARD,
        OptionType.ENERGY_CARD,
        OptionType.ENERGY,
        OptionType.SKILL,
        OptionType.SPECIAL_CONDITION,
        OptionType.NUMBER,
    }:
        return _score_card_selection(obs, option)
    return _score_main_action(obs, option)


# Pick the highest-scoring legal option indexes.
# If the simulator allows choosing zero cards, we only choose positively scored options.
def choose_options(obs: Observation) -> list[int]:
    scored_options = [
        (_score_option(obs, option), index)
        for index, option in enumerate(obs.select.option)
    ]
    scored_options.sort(reverse=True)

    chosen_count = obs.select.maxCount
    if obs.select.minCount == 0:
        positive_count = sum(1 for score, _ in scored_options if score > 0)
        chosen_count = min(obs.select.maxCount, positive_count)

    chosen_count = max(obs.select.minCount, chosen_count)
    return [index for _, index in scored_options[:chosen_count]]


# Kaggle calls this function every time the bot must make a decision.
# First call: return the 60-card deck. Later calls: choose from legal options.
def agent(obs_dict: dict) -> list[int]:
    """Implement Your Pokémon Trading Card Game Agent.

    Each element in the returned list must be >= 0 and < len(obs.select.option).
    The list length must be between obs.select.minCount and obs.select.maxCount (inclusive), with no duplicate elements.
    
    Returns:
        list[int]: A list of option index.
    """
    obs: Observation = to_observation_class(obs_dict)
    if obs.select == None:
        # In the initial selection, the obs.select is None, and it is necessary to return the deck.
        # The deck is a list of 60 card IDs.
        # The deck must comply with the Pokémon Trading Card Game rules.
        return read_deck_csv()
    
    return choose_options(obs)