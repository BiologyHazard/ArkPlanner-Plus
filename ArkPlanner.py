import json
import os
import time
import urllib.request
import numpy as np
import scipy.optimize

penguin_url = 'https://penguin-stats.io/PenguinStats/api/v2/'
matrix_url = 'result/matrix?show_closed_zones=true'
formula_url = 'formula'
stages_url = 'stages'

matrix_path = 'matrix.json'
formula_path = 'formula.json'
stages_path = 'stages.json'
requirements_path = 'requirements.txt'

full_requirements_path = 'data/full_requirements.json'
item_table_path = 'data/item_table.json'
shop_path = 'data/shop.json'

time_path = 'cache/last_update_time.txt'
headers = {'User-Agent': 'ArkPlanner+'}


class ArkPlanner(object):
    def __init__(self,
                 url=penguin_url,
                 path='cache/',
                 update=False):
        self.ctime = time.time()
        self.get_items(item_table_path)
        self.get_full_requirements(full_requirements_path)
        self.get_shop(shop_path)
        self.get_data(url, path, update)

    def get_items(self, item_table_path):
        self.items_dct = load_data(item_table_path)
        self.items_name_to_id = {
            item['name']: item_id for item_id, item in self.items_dct.items()}
        self.items_id_to_idx = {item_id: index for index,
                                item_id in enumerate(self.items_dct)}
        self.items_lst = [item_id for item_id,
                          item_dct in self.items_dct.items()]

    def get_full_requirements(self, full_requirements_path):
        self.full_requirements = load_data(full_requirements_path)

    def get_requirements(self, requirements_path=requirements_path):
        req_dct = {}
        with open(requirements_path, 'r', encoding='utf-8') as fr:
            for line in fr.readlines():
                l = line.split()
                name = l[0]
                item_id = self.items_name_to_id[name]
                req = int(l[1]) if int(l[1]) != - \
                    1 else self.full_requirements[item_id]
                try:
                    req -= int(l[2])
                    try:
                        c_req == int(l[3]) if int(
                            l[3]) != '-1' else self.full_requirements[item_id] - int(l[2])
                    except:
                        c_req = req
                except:
                    c_req = req
                req_dct[item_id] = {'req': req, 'cal': c_req}
        return req_dct

    def get_shop(self, shop_path):
        self.shop = load_data(shop_path)

    def get_data(self, url=penguin_url, path='cache/', from_web=False):
        if not from_web:
            try:
                self.drop_matrix = load_data(path + matrix_path)
                self.formulas = load_data(path + formula_path)
                self.stages = load_data(path + stages_path)
                self.updated = False
            except:
                self.update_data(url, path)
        else:
            self.update_data(url, path)

        if self.updated:
            with open(time_path, 'w', encoding='utf-8') as f:
                f.write('%f\n%s' % (self.ctime, time.strftime(
                    '%Y/%m/%d %H:%M:%S', time.localtime(self.ctime))))

    def update_data(self, url=penguin_url, path='cache/'):
        self.drop_matrix = request_data(url + matrix_url)
        self.formulas = request_data(url + formula_url)
        self.stages = request_data(url + stages_url)
        save_data(self.drop_matrix, path + matrix_path)
        save_data(self.formulas, path + formula_path)
        save_data(self.stages, path + stages_path)
        self.updated = True

    def process_data(self,
                     filter_freq=200,
                     blacklist=None,
                     contains_activity=True,
                     show_history=False,
                     byproduct_rate=0.18):
        t1 = time.time()
        if blacklist == None:
            blacklist = []
        self.stages_id_to_name = {stage['stageId']: stage['code']
                                  for stage in self.stages}
        self.stages_name_to_id = {name: stage_id for stage_id,
                                  name in self.stages_id_to_name.items()}
        self.idx_in_stages = {stage['stageId']: idx for idx,
                              stage in enumerate(self.stages)}

        self.stages_lst = []
        for drop in self.drop_matrix['matrix']:
            sid = drop['stageId']
            if ((sid not in self.stages_lst) and  # 未在self.stages_lst中
                # 理智消耗不为0
                (self.stages[self.idx_in_stages[sid]]['apCost'] > 0) and
                # 不在黑名单中
                (self.stages_id_to_name[sid] not in blacklist) and
                # 掉落统计量满足要求
                (drop['times'] >= filter_freq) and
                # 判断是否需要排除活动图
                (contains_activity or self.stages[self.idx_in_stages[sid]]['stageType']
                 != 'ACTIVITY') and
                # 排除物资补给
                (self.stages[self.idx_in_stages[sid]]['zoneId'] != 'gachabox') and
                # 判断是否需要排除已经关闭的活动图
                    (show_history or 'end' not in drop or drop['end'] >= self.ctime*1000)):
                self.stages_lst.append(sid)

        self.stages_id_to_idx = {
            stage_id: stage_idx for stage_idx, stage_id in enumerate(self.stages_lst)}

        self.stages_ap_cost = dict()
        for stage in self.stages:
            if stage['stageId'] in self.stages_lst:
                self.stages_ap_cost[stage['stageId']] = stage['apCost']

        self.droprate_matrix = [
            [0.0 for j in range(len(self.items_dct))] for i in range(len(self.stages_lst))]
        self.update_stage()
        for drop in self.drop_matrix['matrix']:
            sid = drop['stageId']
            iid = drop['itemId']
            if sid in self.stages_lst and iid in self.items_dct:
                # and iid != 'furni' and iid != '4001_1000' and iid != '4001_1500' and iid != '4001_2000':
                self.droprate_matrix[self.stages_id_to_idx[sid]][self.items_id_to_idx[iid]] = (
                    drop['quantity'] / drop['times'])

        # 添加龙门币获取
        for stage_id, stage_idx in self.stages_id_to_idx.items():
            self.droprate_matrix[stage_idx][self.items_id_to_idx['4001']
                                            ] = self.stages_ap_cost[stage_id] * 12
        self.update_droprate()

        # 添加formula
        self.update_conversion()
        self.formulas_matrix = []
        for formula in self.formulas:
            formula_vector = [0.0 for i in range(len(self.items_dct))]
            formula_vector[self.items_id_to_idx[formula['id']]] += 1
            formula_vector[self.items_id_to_idx['4001']] -= formula['goldCost']
            for cost in formula['costs']:
                formula_vector[self.items_id_to_idx[cost['id']]
                               ] -= cost['count']
            total_weight = formula['totalWeight']
            for extra_outcome in formula['extraOutcome']:
                formula_vector[self.items_id_to_idx[extra_outcome['id']]
                               ] += extra_outcome['weight'] * extra_outcome['count'] / total_weight * byproduct_rate
            self.formulas_matrix.append(formula_vector)

        # 添加shop
        self.shop_matrix = []
        self.shop_bounds = []
        for deal in self.shop:
            deal_vector = [0.0 for i in range(len(self.items_dct))]
            deal_vector[self.items_id_to_idx[deal['id']]] += 1
            for cost in deal['costs']:
                deal_vector[self.items_id_to_idx[cost['id']]] -= cost['count']
            if 'availCount' in deal:
                bound = (0, deal['availCount'])
            else:
                bound = (0, None)
            self.shop_matrix.append(deal_vector)
            self.shop_bounds.append(bound)

        assert len(self.items_name_to_id) == len(self.items_lst) == len(
            self.items_dct) == len(self.items_id_to_idx)
        assert len(self.stages_ap_cost) == len(self.stages_lst) == len(
            self.stages_id_to_idx)
        # self._print()

    def update_stage(self):
        self.update_stage_processing('LS-1', 10, 'wk_kc_1')
        self.update_stage_processing('LS-2', 15, 'wk_kc_2')
        self.update_stage_processing('LS-3', 20, 'wk_kc_3')
        self.update_stage_processing('LS-4', 25, 'wk_kc_4')
        self.update_stage_processing('LS-5', 30, 'wk_kc_5')
        self.update_stage_processing('CE-1', 10, 'wk_melee_1')
        self.update_stage_processing('CE-2', 15, 'wk_melee_2')
        self.update_stage_processing('CE-3', 20, 'wk_melee_3')
        self.update_stage_processing('CE-4', 25, 'wk_melee_4')
        self.update_stage_processing('CE-5', 30, 'wk_melee_5')

    def update_stage_processing(self, stage_name, ap_cost, stage_id):
        if stage_id not in self.stages_lst:
            self.stages_lst.append(stage_id)
            self.stages_id_to_idx[stage_id] = len(self.stages_lst) - 1
            self.stages_name_to_id[stage_name] = stage_id
            self.stages_id_to_name[stage_id] = stage_name
            self.stages_ap_cost[stage_id] = ap_cost
            self.droprate_matrix.append(
                [0.0 for i in range(len(self.items_dct))])

    def update_droprate(self):
        self.update_droprate_processing('S4-6', '龙门币', 3480)
        self.update_droprate_processing('S5-2', '龙门币', 2700)
        self.update_droprate_processing('S6-4', '龙门币', 2700)
        self.update_droprate_processing('CE-1', '龙门币', 1700, True)
        self.update_droprate_processing('CE-2', '龙门币', 2800, True)
        self.update_droprate_processing('CE-3', '龙门币', 4100, True)
        self.update_droprate_processing('CE-4', '龙门币', 5700, True)
        self.update_droprate_processing('CE-5', '龙门币', 7500, True)
        self.update_droprate_processing('LS-1', '经验', 1600)
        self.update_droprate_processing('LS-2', '经验', 2800)
        self.update_droprate_processing('LS-3', '经验', 3900)
        self.update_droprate_processing('LS-4', '经验', 5900)
        self.update_droprate_processing('LS-5', '经验', 7400, True)

    def update_droprate_processing(self, stage_name, item_name, droprate, force=False):
        stage_id = self.stages_name_to_id[stage_name]
        item_id = self.items_name_to_id[item_name]
        if force:
            stage_idx = self.stages_id_to_idx[stage_id]
            item_idx = self.items_id_to_idx[item_id]
            self.droprate_matrix[stage_idx][item_idx] = droprate
        else:
            if stage_id in self.stages_lst:
                stage_idx = self.stages_id_to_idx[stage_id]
                item_idx = self.items_id_to_idx[item_id]
                self.droprate_matrix[stage_idx][item_idx] = droprate

    def update_conversion(self):
        self.update_conversion_processing(
            ('经验', 200), 0, {'基础作战记录': 1}, ({}, 0, 1))
        self.update_conversion_processing(
            ('经验', 400), 0, {'初级作战记录': 1}, ({}, 0, 1))
        self.update_conversion_processing(
            ('经验', 1000), 0, {'中级作战记录': 1}, ({}, 0, 1))
        self.update_conversion_processing(
            ('经验', 2000), 0, {'高级作战记录': 1}, ({}, 0, 1))
        self.update_conversion_processing(
            ('经验', 400), 0, {'赤金': 1}, ({}, 0, 1))

    def update_conversion_processing(self, target_item, cost, source_item, extraOutcome):
        toAppend = dict()
        Outcome, rate, totalWeight = extraOutcome
        toAppend['costs'] = [{'count': x[1]/target_item[1],
                              'id':self.items_name_to_id[x[0]], 'name':x[0]} for x in source_item.items()]
        toAppend['extraOutcome'] = [{'count': rate, 'id': self.items_name_to_id[x[0]],
                                     'name': x[0], 'weight': x[1]/target_item[1]} for x in Outcome.items()]
        toAppend['goldCost'] = cost/target_item[1]
        toAppend['id'] = self.items_name_to_id[target_item[0]]
        toAppend['name'] = target_item[0]
        toAppend['totalWeight'] = totalWeight
        self.formulas.append(toAppend)

    def get_plan(self,
                 req_dct,
                 print_output=True,
                 filter_freq=200,
                 blacklist=None,
                 contains_activity=True,
                 show_history=False,
                 byproduct_rate=0.18):
        self.process_data(filter_freq=filter_freq,
                          blacklist=blacklist,
                          contains_activity=contains_activity,
                          show_history=show_history,
                          byproduct_rate=byproduct_rate)
        b_stage_1 = [0 for i in range(len(self.items_dct))]
        b_stage_2 = [0 for i in range(len(self.items_dct))]
        for item_id, req in req_dct.items():
            iidx = self.items_id_to_idx[item_id]
            b_stage_1[iidx] = req['cal']
            b_stage_2[iidx] = req['req']
        self.stages_count = len(self.stages_lst)
        formulas_start = self.stages_count
        A_T = self.droprate_matrix + self.formulas_matrix
        A = turn(A_T)
        c = [1e-4 for i in range(len(A_T))]
        for stage_id, ap_cost in self.stages_ap_cost.items():
            c[self.stages_id_to_idx[stage_id]] = ap_cost
        stage_1_solution = scipy.optimize.linprog(c=c,
                                                  A_ub=negative(A),
                                                  b_ub=negative(b_stage_1),
                                                  method='revised simplex')
        assert stage_1_solution.status == 0, stage_1_solution.message
        c_stage_2 = c[:]
        for cidx, count in enumerate(stage_1_solution.x):
            if count < 0.001:
                c_stage_2[cidx] = 1e10

        primal_solution = scipy.optimize.linprog(c=c_stage_2,
                                                 A_ub=negative(A),
                                                 b_ub=negative(b_stage_2),
                                                 method='revised simplex')
        assert stage_1_solution.status == 0, stage_1_solution.message
        dual_solution = scipy.optimize.linprog(c=negative(b_stage_2),
                                               A_ub=A_T,
                                               b_ub=c_stage_2,
                                               method='revised simplex')
        assert stage_1_solution.status == 0, stage_1_solution.message
        # print(primal_solution)
        # print(dual_solution)
        primal_x = primal_solution.x
        dual_x = dual_solution.x
        if print_output:
            print('转化：')
            for cidx, count in enumerate(primal_x):
                if abs(count) > 0.001:
                    if cidx < formulas_start:
                        print('刷图:', self.stages_id_to_name[self.stages_lst[cidx]], round(
                            count, 2), '次')
                    else:
                        print('合成:', self.formulas[cidx -
                                                   formulas_start]['name'], round(count, 2), '次')
            print('\n材料价值：')
            for iidx, value in enumerate(dual_x):
                if abs(value) >= 0.001:
                    print(
                        self.items_dct[self.items_lst[iidx]]['name'], round(value, 5))
            print('\n关卡效率：')
            for sidx, stage_id in enumerate(self.stages_lst):
                g = 0
                for iidx, value in enumerate(dual_x):
                    g += self.droprate_matrix[sidx][iidx]*value
                print(self.stages_id_to_name[self.stages_lst[sidx]], round(
                    g / self.stages_ap_cost[stage_id], 3))
                # assert (
                # g / self.stages_ap_cost[stage_id] < 0.999) or (primal_x[sidx] > 0.001)

        result = dict()
        return result

    def _print(self):  # 用于调试
        dct = dict()
        ddct = dict()
        for sidx, sid in enumerate(self.stages_lst):
            sdct = dict()
            sdct['id'] = sid
            sdct['理智消耗'] = self.stages_ap_cost[sid]
            sdct['类型'] = self.stages[self.idx_in_stages[sid]]['stageType']
            sdct['区域'] = self.stages[self.idx_in_stages[sid]]['zoneId']
            sdct['掉落'] = dict()
            for iidx, iid in enumerate(self.items_lst):
                if self.droprate_matrix[sidx][iidx] != 0.0:
                    sdct['掉落'][self.items_dct[iid]['name']
                               ] = round(self.droprate_matrix[sidx][iidx], 3)
            ddct[self.stages_id_to_name[sid]] = sdct
        fdct = dict()
        for fidx, formula in enumerate(self.formulas_matrix):
            sdct = dict()
            sdct['idx'] = fidx
            for iidx, iid in enumerate(self.items_lst):
                if formula[iidx] != 0.0:
                    sdct[self.items_dct[iid]['name']
                         ] = formula[iidx]
            fdct['合成：' + self.formulas[fidx]['name']] = sdct

        dct['刷图'] = ddct
        dct['合成'] = fdct
        # dct.update({'': self.formulas})
        json.dump(dct, f, ensure_ascii=False, indent=4)
        # json.dump(self.formulas_matrix, f, indent=4)


def save_data(data, path):
    try:
        os.makedirs(os.path.dirname(path))
    except:
        pass
    with open(path, 'w', encoding='utf-8') as fw:
        json.dump(data, fw, ensure_ascii=False, indent=4)


def load_data(path):
    with open(path, 'r', encoding='utf-8') as fr:
        return json.load(fr)


def request_data(url, print_process=True):
    if print_process:
        print(f'Requesting data from {url} ...')
    req = urllib.request.Request(url, None, headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if print_process:
                print('Done!')
            return json.loads(response.read().decode())
    except urllib.error.URLError as err:
        raise TimeoutError(
            f'Timed out when requesting data from {url}.\nPlease try again.')


def auto_update(secs=86400, path=time_path):
    try:
        os.makedirs(os.path.dirname(path))
    except:
        pass
    try:
        with open(path, 'r', encoding='utf-8') as f:
            last_update_time = float(f.readline())
        if time.time() - last_update_time <= secs:
            update = False
    except:
        update = True
    return update


def turn(mat):
    if mat == []:
        return []
    rows = len(mat)
    cols = len(mat[0])
    if cols == 0:
        return []
    '''res = []
    for i in range(cols):
        line = []
        for j in range(rows):
            line.append(mat[j][i])'''

    return [[mat[j][i] for j in range(rows)] for i in range(cols)]


def negative(mat):
    if type(mat) != list:
        return - mat
    res = []
    for line in mat:
        res.append(negative(line))
    return(res)


if __name__ == "__main__":
    f = open('output.json', 'w', encoding='utf-8')
    ap = ArkPlanner(update=False)
    req_dct = ap.get_requirements(requirements_path)
    ap.get_plan(req_dct, show_history=False,
                filter_freq=200, byproduct_rate=0.18)
    # bp = ArkPlanner(update=False)
    # bp.get_plan(dict(), filter_freq=1000, show_history=False)
    f.close()
