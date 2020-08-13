import json
shop = []
with open('D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\item_table.json', 'r', encoding='utf-8') as f:
    items_dct = json.load(f)

items_id_dct = {}
for _, item in items_dct['items'].items():
    items_id_dct[item['name']] = item['itemId']

with open('shop.txt', 'r', encoding='utf-8') as f:
    for line in f.readlines():
        if line == '4005\n' or line == '4004\n' or line == '4006\n' or line == 'EPGS_COIN\n':
            current = line[:-1]
        else:
            s = line.split()
            # print(s)
            if current == '4005':
                name, price, availCount = s
                price, availCount = int(price), int(availCount)
                x = {'id': items_id_dct[name], 'count': 1, 'costs': [{
                    'id': current, 'count': price}], 'availCount': availCount}
            elif current == '4004':
                name, price = s
                price = int(price)
                x = {'id': items_id_dct[name], 'count': 1, 'costs': [{
                    'id': current, 'count': price}]}
            elif current == '4006':
                name, price = s
                price = int(price)
                x = {'id': items_id_dct[name], 'count': 1, 'costs': [{
                    'id': current, 'count': price}]}
            else:
                name, price, count = s
                price, count = int(price), int(count)
                x = {'id': items_id_dct[name], 'count': count, 'costs': [{
                    'id': current, 'count': price}]}
            shop.append(x)
with open('data/shop.json', 'w', encoding='utf-8') as f:
    json.dump(shop, f)
