import os
import os.path as osp

import numpy as np
from PIL import Image
import cv2
import math
import scipy.io as scio
import json
from copy import deepcopy as cdc
from symbol_affiliation import all_symbols


def is_english(char):
    if not ('a'<=char<='z' or 'A'<=char<='Z'):
        return False
    return True

def is_chinese(char):
    if not ('\u4e00'<=char<='\u9fff'):
        return False
    return True

def is_number(char):
    if char.isdigit():
        return True
    return False


def load_img(img_path):
    try:
        img = Image.open(img_path)
        img_shape = np.array(img).shape
        if len(img_shape) == 2:
            img = img.convert('RGB')
        if (len(img_shape) == 3) and (img_shape[2] == 4):
            img = img.convert('RGB')
        img = np.array(img)
    except Exception as e:
        raise ValueError('Failed loading img:', img_path)

    return img


def parse_NWPU_SA(data_dir, gt_dir):

    img_paths, filenames, imgs = [], [], []
    contours, classes, ignores = [], [], []

    for num, gt_file in enumerate(os.listdir(gt_dir)):

        # GT 路径
        img_file = str(gt_file.split('.')[0]) + '.jpg'
        img_path = osp.join(data_dir, img_file)
        # img = load_img(img_path)

        # 初始化 board, text, symbol 
        board_contours, board_classes, board_ignores = [], [], []
        text_contours, text_classes, text_ignores = [], [], []
        symbol_contours, symbol_classes, symbol_ignores = [], [], []

        gt_path = osp.join(gt_dir, gt_file) 
        with open(gt_path,'r',encoding='utf8') as gp:
            json_datas = json.load(gp)
            keys = list(json_datas.keys())  # b0, b1, ...,bn
            # print(keys)
            for key in keys:
                json_data = json_datas[key]
                # print(json_data)
                if key != 'other':
                    board_data, text_data, symbol_data, affiliation_data = \
                            json_data['board'], json_data['text'], json_data['symbol'], json_data['affiliation']

                    # 1. board label processing
                    board_class, board_ignore, board_points = \
                            board_data['class'], board_data['ignore'], board_data['points']
                    if board_ignore == 1:  # 如果指示牌需要被忽略，那里面的元素皆不参与训练
                        board_ignores.append(board_points) # board ignore: 忽略ignore=1的board
                        continue

                    board_classes.append(board_class)
                    board_contours.append(board_points)                    
                else: text_data, symbol_data = json_data['text'], json_data['symbol']
                    
                # 2. text label processing
                for td in text_data:
                    text_id, text_class, text_points = \
                        td['id'], td['class'], td['points']
                    if text_class == '###': 
                        text_ignores.append(text_points)  # text ignore: 忽略‘###’文本
                        continue

                    text_classes.append(text_class)
                    text_contours.append(text_points)

                # 3. symbol label processing
                for sd in symbol_data:
                    symbol_id, symbol_class, symbol_points = \
                            sd['id'], sd['class'], sd['points']

                    symbol_classes.append(symbol_class)
                    symbol_contours.append(symbol_points)
                    
            img_paths.append(img_path)
            filenames.append(img_path.split('/')[-1].split('.')[0])
            # imgs.append(img)

            contours.append([board_contours, text_contours, symbol_contours])
            classes.append([board_classes, text_classes, symbol_classes])
            ignores.append([board_ignores, text_ignores, symbol_ignores])
    

    return [img_paths, filenames, imgs, contours, classes, ignores]


def class_information(classes):
    split_board_class, split_text_class, split_symbol_class = [], [], []
    for split_class in classes:
        split_board_class += split_class[0]
        split_text_class += split_class[1]
        split_symbol_class += split_class[2]
    # print(split_board_class, split_text_class, split_symbol_class)

    split_text_class_char = []
    for ttc in split_text_class:
        split_text_class_char += [t for t in ttc]

    split_board_class_set, split_text_class_set, split_symbol_class_set = \
                set(split_board_class), set(split_text_class_char), set(split_symbol_class)

    chinese_char, english_char, number_char, other_char = [], [], [], []
    for ttcs in split_text_class_set:
        if is_chinese(ttcs): chinese_char.append(ttcs)
        elif is_english(ttcs): english_char.append(ttcs)
        elif is_number(ttcs): number_char.append(ttcs)
        else: other_char.append(ttcs)

    split_board_class_list = np.sort(list(split_board_class_set)).tolist()
    split_text_class_list = [np.sort(number_char).tolist(), 
                            np.sort(english_char).tolist(), 
                            np.sort(chinese_char).tolist(), 
                            np.sort(other_char).tolist()]
    split_symbol_class_list = np.sort(list(split_symbol_class_set)).tolist()

    split_board_dict, split_text_dict, split_symbol_dict = {}, {}, {}
    for tbcl in split_board_class_list:
        split_board_dict[tbcl] = 0
    for ttcl in split_text_class_list:
        for ttc in ttcl: split_text_dict[ttc] = 0
    for tscl in split_symbol_class_list:
        split_symbol_dict[tscl] = 0
        
    for tbc in split_board_class:
        split_board_dict[tbc]+=1
    for ttcc in split_text_class_char:
        split_text_dict[ttcc]+=1
    for tsc in split_symbol_class:
        split_symbol_dict[tsc]+=1

    return [split_board_dict, split_text_dict, split_symbol_dict]


if __name__ == '__main__':
    # DEBUG < INFO < WARNING < ERROR < CRITICAL
    # from config import r18_sa

    file_path = 'dataset_class_4_tongji.json'

    is_generate=1

    if is_generate:
        print('train_parse_NWPU_SA')
        img_paths, filenames, imgs, contours, classes, ignore_masks = \
                                parse_NWPU_SA('train/Image',
                                              'train/GT')

        print('train_class_information')
        train_board_dict, train_text_dict, train_symbol_dict = \
                                class_information(classes)

        print('test_parse_NWPU_SA')
        img_paths, filenames, imgs, contours, classes, ignore_masks = \
                                parse_NWPU_SA('test/Image',
                                              'test/GT')
        print('test_class_information')
        test_board_dict, test_text_dict, test_symbol_dict = \
                                class_information(classes)


        # keys = list(test_text_dict.keys())
        # for key in keys:
        #     if key in text_cha:
        #         print(key,test_text_dict[key])


        all_train_test_dict = \
                    [cdc(train_board_dict), cdc(train_text_dict), cdc(train_symbol_dict)]

        for n, dict_info in enumerate([test_board_dict, test_text_dict, test_symbol_dict]):
            keys = list(dict_info.keys())
            exist_keys = list(all_train_test_dict[n].keys())

            for key in keys:
                if key in exist_keys: all_train_test_dict[n][key]+=dict_info[key]
                else: all_train_test_dict[n][key]=dict_info[key]

        for n, attbd in enumerate(all_train_test_dict):
            keys, values = np.array(list(attbd.keys())), np.array(list(attbd.values()))
            sort_index = np.argsort(keys)
            sort_keys, sort_values = keys[sort_index].tolist(), values[sort_index].tolist()

            all_train_test_dict[n] = dict(zip(sort_keys, sort_values))

        all_train_test_json = {'train':[train_board_dict, train_text_dict, train_symbol_dict], 
                                'test':[test_board_dict, test_text_dict, test_symbol_dict],
                                'all':all_train_test_dict}

        ####### 1. 文件保存 #######
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_train_test_json,f)


    ####### 2. 文件读取 #######
    with open(file_path, 'r') as f:
        json_data = json.load(f)

        train_board, train_text, train_symbol = \
                        json_data['train'][0],json_data['train'][1],json_data['train'][2]

        train_board_keys, train_text_keys, train_symbol_keys = \
                list(train_board.keys()), list(train_text.keys()), list(train_symbol.keys())


        test_board, test_text, test_symbol = \
                        json_data['test'][0],json_data['test'][1],json_data['test'][2]

        test_board_keys, test_text_keys, test_symbol_keys = \
                list(test_board.keys()), list(test_text.keys()), list(test_symbol.keys())


        all_board, all_text, all_symbol = \
                        json_data['all'][0],json_data['all'][1],json_data['all'][2]

        all_board_keys, all_text_keys, all_symbol_keys = \
                list(all_board.keys()), list(all_text.keys()), list(all_symbol.keys())

        print(len(all_board_keys), len(all_symbol_keys))
        print(all_board_keys, all_symbol_keys)

        train_board_tongji, train_symbol_tongji, test_board_tongji, test_symbol_tongji = [], [], [], []

        for abk in all_board_keys:
            if abk in train_board_keys: train_board_tongji.append(train_board[abk])
            else: train_board_tongji.append(0)

            if abk in test_board_keys: test_board_tongji.append(test_board[abk])
            else: test_board_tongji.append(0)


        for ask in all_symbol_keys:
            if ask in train_symbol_keys: print(ask); train_symbol_tongji.append(train_symbol[ask])
            else: train_symbol_tongji.append(0)

            if ask in test_symbol_keys: test_symbol_tongji.append(test_symbol[ask])
            else: test_symbol_tongji.append(0)

        print(train_board_tongji, train_symbol_tongji, test_board_tongji, test_symbol_tongji)
