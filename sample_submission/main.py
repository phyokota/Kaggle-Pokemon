import os

from cg.api import AreaType, Observation, Option, OptionType, SelectContext, to_observation_class


RIOLU = 1208
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

BASIC_POKEMON = {RIOLU, LUNATONE, SOLROCK, MAKUHITA, MEOWTH}
STARTER_PRIORITY = {
    RIOLU: 700,
    SOLROCK: 600,
    MAKUHITA: 500,
    LUNATONE: 400,
    MEOWTH: 50,
}

POKEMON_SEARCH_PRIORITY = {
    RIOLU: 700,
    LUCARIO: 650,
    SOLROCK: 600,
    LUNATONE: 550,
    MAKUHITA: 500,
    HARIYAMA: 450,
    MEOWTH: 50,
}

ENERGY_TARGET_PRIORITY = {
    RIOLU: 700,
    LUCARIO: 650,
    SOLROCK: 600,
    MAKUHITA: 500,
    HARIYAMA: 450,
    LUNATONE: 400,
    MEOWTH: 50,
}

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


def _your_state(obs: Observation):
    if obs.current is None:
        return None
    return obs.current.players[obs.current.yourIndex]


def _opponent_state(obs: Observation):
    if obs.current is None:
        return None
    return obs.current.players[1 - obs.current.yourIndex]


def _pokemon_ids_in_play(obs: Observation) -> set[int]:
    player = _your_state(obs)
    if player is None:
        return set()
    ids = {pokemon.id for pokemon in player.bench}
    ids.update(pokemon.id for pokemon in player.active if pokemon is not None)
    return ids


def _hand_ids(obs: Observation) -> list[int]:
    player = _your_state(obs)
    if player is None or player.hand is None:
        return []
    return [card.id for card in player.hand]


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


def _card_id_for_option(obs: Observation, option: Option) -> int | None:
    if option.type == OptionType.PLAY:
        card = _card_from_area(obs, AreaType.HAND, option.index, obs.current.yourIndex)
    else:
        card = _card_from_area(obs, option.area, option.index, option.playerIndex)
    return None if card is None else card.id


def _target_id_for_option(obs: Observation, option: Option) -> int | None:
    card = _card_from_area(obs, option.inPlayArea, option.inPlayIndex, obs.current.yourIndex)
    return None if card is None else card.id


def _active_can_be_knocked_out(obs: Observation, damage: int) -> bool:
    opponent = _opponent_state(obs)
    if opponent is None or len(opponent.active) == 0 or opponent.active[0] is None:
        return False
    return opponent.active[0].hp <= damage


def _has_attack_option(obs: Observation) -> bool:
    return any(option.type == OptionType.ATTACK for option in obs.select.option)


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

    if obs.select.context in {SelectContext.ATTACH_TO, SelectContext.TO_ACTIVE, SelectContext.SWITCH}:
        return ENERGY_TARGET_PRIORITY.get(card_id, STARTER_PRIORITY.get(card_id, 0))

    return POKEMON_SEARCH_PRIORITY.get(card_id, DISCARD_PRIORITY.get(card_id, 0))


def _score_main_action(obs: Observation, option: Option) -> int:
    if option.type == OptionType.ATTACK:
        if option.attackId == 1210 and _active_can_be_knocked_out(obs, 270):
            return 1000
        if option.attackId == 1209:
            return 900
        if option.attackId == 1210:
            return 850
        return 800

    if option.type == OptionType.EVOLVE:
        target_id = _target_id_for_option(obs, option)
        card_id = _card_id_for_option(obs, option)
        if card_id == LUCARIO and target_id == RIOLU:
            return 780
        if card_id == HARIYAMA and target_id == MAKUHITA:
            return 650
        return 600

    if option.type == OptionType.ATTACH:
        card_id = _card_id_for_option(obs, option)
        target_id = _target_id_for_option(obs, option)
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
        if card_id == MEOWTH:
            return 80
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
        return 120

    if option.type == OptionType.END:
        return -100

    return 0


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
