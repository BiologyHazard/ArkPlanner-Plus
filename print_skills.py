import json

character_table_path = 'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\character_table.json'
skill_table_path = 'D:\ChenXu\Documents\Arknights\ArknightsGameData-master\zh_CN\gamedata\excel\skill_table.json'
chars_lst = ['char_504_rguard', 'char_507_rsnipe', 'char_506_rmedic', 'char_505_rcast',
             'char_508_aguard', 'char_511_asnipe', 'char_509_acast', 'char_510_amedic']
fc = open(character_table_path, 'r', encoding='utf-8')
fs = open(skill_table_path, 'r', encoding='utf-8')
chars_dct = json.load(fc)
skills_dct = json.load(fs)

for char_id, char_dct in chars_dct.items():
    if char_id in chars_lst:
        char_name = char_dct['name']
        # print('干员', char_dct['name'])
        for phase, phase_dct in enumerate(char_dct['phases']):
            for key_frame_dct in phase_dct['attributesKeyFrames']:
                pass
                # print('%s\t%d\t%d\t%d\t%d\t%d\t%.2f\t%d\t%d\t%.2f' %
                #       (char_dct['name'], phase, key_frame_dct['level'], key_frame_dct['data']['maxHp'], key_frame_dct['data']['atk'], key_frame_dct['data']['def'], key_frame_dct['data']['magicResistance'], key_frame_dct['data']['cost'], key_frame_dct['data']['blockCnt'], key_frame_dct['data']['baseAttackTime']))
        if char_dct['talents']:
            for talent_id, talent_dct in enumerate(char_dct['talents']):
                for candidate_dct in talent_dct['candidates']:
                    pass
                    # print('干员%s，天赋%d：%s，描述：%s' %
                    #   (char_name, talent_id + 1, candidate_dct['name'], candidate_dct['description']))
        for 