import json
import re
import urllib.request


def init_req_dct(items_dct):
    '''
    初始化需求字典(req_dct)
    '''
    req_dct = dict()
    pattern = '^\d+$|^AP_GAMEPLAY$|^EPGS_COIN$'
    req_dct['EXP'] = 0
    items_dct['items']['EXP'] = {'itemId': 'EXP',
                                 'name': '经验', 'rarity': 3, 'sortId': 10004}
    for _, item in items_dct['items'].items():
        item_id = item['itemId']
        if re.match(pattern, item_id) != None:
            req_dct[item_id] = 0
            if item['name'] == '龙门币':
                gold_id = item['itemId']
    return req_dct, gold_id


'''def init_from_web(items_lst):
    '''
'''根据从api上获得的数据，初始化需求字典(req_dct)'''
'''
    req_dct = dict()
    pattern = '^\d+$|^AP_GAMEPLAY$|^EPGS_COIN$'
    req_dct['EXP'] = 0
    req_dct['4001'] = 0
    # items_dct['items']['EXP'] = {'itemId': 'EXP',
    #                              'name': '经验', 'rarity': 3, 'sortId': 10004}
    gold_id = '4001'
    for item in items_lst:
        item_id = item['itemId']
        if re.match(pattern, item_id) != None:
            req_dct[item_id] = 0
            if item['name'] == '龙门币':
                gold_id = item['itemId']
    return req_dct, gold_id
'''


def cal_exp_gold(const_dct):
    '''
    用于计算各星极干员升到满级需求的经验和龙门币，
    因此项不在character_table中，故需单独计算。
    '''
    maxLevel = const_dct['maxLevel']
    characterExpMap = const_dct['characterExpMap']
    characterUpgradeCostMap = const_dct['characterUpgradeCostMap']
    evolveGoldCost = const_dct['evolveGoldCost']
    exp_req_lst = []
    gold_req_lst = []
    for rarity, max_lvl_lst in enumerate(maxLevel):
        exp_req = 0
        gold_req = 0
        for phase, max_lvl in enumerate(max_lvl_lst):
            for lvl in range(max_lvl - 1):
                exp_req += characterExpMap[phase][lvl]
                gold_req += characterUpgradeCostMap[phase][lvl]
            if phase > 0:
                gold_req += evolveGoldCost[rarity][phase - 1]
        exp_req_lst.append(exp_req)
        gold_req_lst.append(gold_req)
    return exp_req_lst, gold_req_lst


def list_char(chars_dct):
    '''
    暂时未用上，请忽略
    '''
    chars_list = list()
    index = 0

    for char_id, char_dct in chars_dct.items():
        if char_id.startswith('char'):
            chars_list.append(dict())
            chars_list[index]['id'] = char_id
            index += 1
    print(chars_list)


def print_item_table(items_dct, file_path='item_table.txt'):
    '''
    暂时未用上，请忽略
    '''
    fw = open(file_path, 'w', encoding='utf-8')
    items_lst = []
    for _, item in items_dct['items'].items():
        items_lst.append(item)
        items_lst.sort(key=lambda item: item['sortId'])
        # fw.write(item['itemId'] + '\t' + str(item['rarity'] + 1) +
        #  '\t' + item['name'] + '\t' + str(item['sortId']) + '\n')
    # fw.write(str(items_lst))
    # fw.write('\n'*10)
    for item in items_lst:
        fw.write(item['itemId'] + '\t' + str(item['rarity'] + 1) +
                 '\t' + item['name'] + '\t' + str(item['sortId']) + '\n')


if __name__ == '__main__':
    local_file_path = {
        'gamedata_const':
        'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\gamedata_const.json',
        'character_table':
        'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\character_table.json',
        'item_table':
        'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\item_table.json'
    }
    penguin_stats_url = 'https://penguin-stats.io/PenguinStats/api/v2/items'
    headers = {'User-Agent': 'ArkPlanner+'}
    try:
        with open(local_file_path['gamedata_const'], 'r', encoding='utf-8') as fr:
            const_dct = json.load(fr)
            fr.close()
    except:
        exp_req_lst = [9800, 9800, 115400, 484000, 734400, 1111400]
        gold_req_lst = [6043, 6043, 104040, 482003, 819325, 1334796]
    else:
        exp_req_lst, gold_req_lst = cal_exp_gold(const_dct)

    with open(local_file_path['character_table'], 'r', encoding='utf-8') as fr:
        chars_dct = json.load(fr)
        fr.close()

    '''try:
        with open(local_file_path['item_table'], 'r', encoding='utf-8') as fr:
            items_dct = json.load(fr)
            fr.close()
    except:
        request = urllib.request.Request(penguin_stats_url, None, headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            items_lst = json.loads(response.read().decode())
        req_dct, gold_id = init_from_web(items_lst)
    else:
        req_dct, gold_id = init_req_dct(items_dct) '''
    with open(local_file_path['item_table'], 'r', encoding='utf-8') as fr:
        items_dct = json.load(fr)
        fr.close()
    req_dct, gold_id = init_req_dct(items_dct)
    fw = open('reqirements.txt', 'w', encoding='utf-8')

    for char_id, char_dct in chars_dct.items():
        if char_id.startswith('char'):
            # 添加经验和龙门币的需求
            req_dct['EXP'] += exp_req_lst[char_dct['rarity']]
            req_dct[gold_id] += gold_req_lst[char_dct['rarity']]
            # 添加精英化的需求
            for phase_dct in char_dct['phases']:
                evolve_cost = phase_dct['evolveCost']
                if evolve_cost != None:
                    for item in evolve_cost:
                        req_dct[item['id']] += item['count']
            # 添加技能专精的需求
            for skill_dct in char_dct['skills']:
                for skill_level_dct in skill_dct['levelUpCostCond']:
                    for item in skill_level_dct['levelUpCost']:
                        req_dct[item['id']] += item['count']
            # 添加技能升级的需求
            for all_skill_lvl_up_dct in char_dct['allSkillLvlup']:
                for item in all_skill_lvl_up_dct['lvlUpCost']:
                    req_dct[item['id']] += item['count']

    for item_id, count in req_dct.items():
        # if count != 0:
        fw.write(item_id + '\t' +
                 items_dct['items'][item_id]['name'] + '\t' + str(count) + '\n')
