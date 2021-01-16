import json
import re


with open(r'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\item_table.json', 'r', encoding='utf-8') as f:
    items_dct = json.load(f)

pattern = r'^[2-4,7]\d+$|^AP_GAMEPLAY$|^EPGS_COIN$'
items = {}
items['EXP'] = {'itemId': 'EXP', 'name': '经验', 'rarity': 3, 'sortId': 10004}
items['BASE_CAP'] = {'itemId': 'BASE_CAP',
                     'name': '基建产能', 'rarity': 2, 'sortId': -10000}
for _, item in items_dct['items'].items():
    if re.match(pattern, item['itemId']) != None:
        i = {}
        i['itemId'] = item['itemId']
        i['name'] = item['name']
        i['rarity'] = item['rarity']
        i['sortId'] = item['sortId']
        items[item['itemId']] = i
with open('data/item_table.json', 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=4)
