import json
with open(r'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\building_data.json', 'r', encoding='utf-8') as f:
    buiding_dct = json.load(f)

formulas_dct = {}
workshop_formulas = buiding_dct['workshopFormulas']
for formula_id, formula_dct in workshop_formulas.items():
    formulas_dct[formula_id] = {}
    formulas_dct[formula_id]['sortId'] = formula_dct['sortId']
    formulas_dct[formula_id]['formulaId'] = formula_dct['formulaId']
    formulas_dct[formula_id]['itemId'] = formula_dct['itemId']
    formulas_dct[formula_id]['count'] = formula_dct['count']
    formulas_dct[formula_id]['goldCost'] = formula_dct['goldCost']
    formulas_dct[formula_id]['extraOutcomeRate'] = formula_dct['extraOutcomeRate']
    formulas_dct[formula_id]['extraOutcomeGroup'] = formula_dct['extraOutcomeGroup']
    formulas_dct[formula_id]['costs'] = formula_dct['costs']
with open('data/formulas.json', 'w', encoding='utf-8') as f:
    json.dump(formulas_dct, f, ensure_ascii=False, indent=4)
