import pandas as pd
import numpy as np
import os
import re
import copy
import shutil
import openpyxl
import logging
logging.basicConfig(
    filename='errors.log',
    format='%(asctime)s - %(name)s - %(levelname)s -%(module)s:  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %p',
    level=10
)

CITY = 'shenzhen'


class Find_files:
    '''读取和筛选文件夹'''

    def __init__(self) -> None:
        pass

    # @staticmethod
    def get_files(self, path) -> pd.DataFrame:
        '''获取目录下的所有文件名及路径'''
        p = []
        f = []
        for a, b, c in os.walk(path):
            for d in c:
                p.append(os.path.join(a, d))
                f.append(d)
        self.df = pd.DataFrame({'path': p, 'name': f})
        self.df['year'] = self.df.path.str.extract(
            '[^\d]+(\d{4})', expand=False)
        return self.df

    def filter_file(self, colname: str, pattern: str):
        '''根据正则表达式筛选出文件'''
        pattern = '({})'.format(pattern)
        self.filter_df = self.df[self.df[colname] == self.df[colname].str.extract(
            pattern, expand=False)].copy()
        self.filter_df.name = self.filter_df.year + '_' + \
            (self.filter_df.groupby('year').year.cumcount() +
             1).astype(str) + '-' + self.filter_df.name
        return self.filter_df

    def copy_files(self, col_path, col_filename, target, df: pd.DataFrame = None):
        '''
        根据传入的 df 将文件复制到目标文件夹并重命名
        col_path: 包涵文件路径和文件名的 df 列
        col_filename: 复制后文件名的 df 列
        target: 目标目录
        '''
        if df is None:
            df = self.filter_df

        for idx, row in df[[col_path, col_filename]].iterrows():
            # print(row[col_path])
            print(row[col_filename])
            shutil.copy2(row[col_path], os.path.join(
                target, row[col_filename]))
        # return df

    def xls_to_xlsx(self, path: str):
        '''将excel文件改成新格式'''
        import xlwings as xw
        import stat
        app = xw.App(visible=False, add_book=False)
        del_list = []
        for fname in os.listdir(path):
            if ~fname.startswith('~') and fname.lower().endswith('xls'):
                print(fname)
                wb = app.books.open(os.path.join(path, fname))
                new_name = os.path.splitext(fname)[0]
                wb.save(os.path.join(path, new_name + '.xlsx'))
                wb.close()
                del_list.append(os.path.join(path, fname))
        app.kill()
        # 删除旧文件
        for fname in del_list:
            print('delete', fname)
            try:
                os.remove(fname)
            except PermissionError:
                print('取消只读')
                os.chmod(fname, stat.S_IWRITE)
                os.remove(fname)


class ClearUpExcel:
    '''负责读取、清理和规整 Excel 文件'''

    def __init__(self) -> None:
        pass

    def unmerge_excel_cells(self, exl_name) -> 'workbook':
        '''取消、填充合并单元格'''
        wb = openpyxl.load_workbook(exl_name, data_only=True)
        sheet = wb.active
        mc_range_list = [str(item) for item in sheet.merged_cells.ranges]

        # 批量取消合并单元格，填充数据
        for mc_range in mc_range_list:
            # 取得左上角值的坐标
            top_left, bot_right = mc_range.split(":")  # ["A1", "A12"]
            # (1, 1,)
            top_left_col, top_left_row = sheet[top_left].column, sheet[top_left].row
            # (1, 12,)
            bot_right_col, bot_right_row = sheet[bot_right].column, sheet[bot_right].row
            # 记下该合并单元格的值
            cell_value = sheet[top_left].value
            # 取消合并单元格
            sheet.unmerge_cells(mc_range)
            # 批量给子单元格赋值
            # 遍历列
            for col_idx in range(top_left_col, bot_right_col+1):
                # 遍历行
                for row_idx in range(top_left_row+1, bot_right_row+1):
                    sheet[f"{chr(col_idx+64)}{row_idx}"] = cell_value

                    sheet[f"{chr(col_idx+64)}{row_idx}"] = cell_value
        return wb

    def remove_en_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        '''删除英文列'''
        en_num = (
            df.fillna('')
            .astype(str)
            .apply(lambda x: x.str.contains('[a-zA-Z]{3,}') & ~x.str.contains('[一-龟]{2,}'))
            .sum() / df.shape[0]  # 英文行所占比例
        )
        return df[en_num[en_num < 0.7].index]

    def read_exl(self, exl_name) -> pd.DataFrame:
        '''读取excel文件'''
        # exl = pd.read_excel(self.unmerge_excel_cells(exl_name), engine='openpyxl')
        exl = pd.read_excel(exl_name, engine='openpyxl')
        if (exl.filter(like='Unnamed').shape[1] / exl.shape[1]) < 0.5:
            # exl = pd.read_excel(self.unmerge_excel_cells(exl_name), engine='openpyxl', header=None)
            exl = pd.read_excel(exl_name, engine='openpyxl', header=None)
        exl = self.remove_en_cols(df=exl)
        exl = exl.dropna(axis=1, how='all')
        return exl

    def fin_coord(self, df: pd.DataFrame):
        '''查找表格内容的坐标'''
        if  df.iloc[:, int(df.shape[1] / 2):].isna().all(1).tail(1).iloc[0]:
            # 末端无效列的起始索引
            idx_invalid = df.iloc[:, int(df.shape[1] / 2):].isna().all(1)[lambda x: ~x].tail(1).index[0]
            df = df.loc[:idx_invalid]
        idx_col = (
            df.iloc[:, 1:].fillna('')
            .astype(str)
            .apply(
                lambda x: 
                x.str.strip().str.contains('^\d+') & ~x.str.contains('[一-龟]+')
            )
            .sum()
            .pipe(lambda x: x / df.shape[0])
            [lambda x: x > 0.3]
            .index[0]
        )
        print(idx_col)

        nums_row = (
            df[idx_col].head(20)
            # .dropna()
            .astype(str)
            .str.strip()
            [lambda x: (x != '') & (x.str.contains('^\d+'))]
            .pipe(lambda x: df[idx_col].loc[x.index[0]: x.index[-1]])
            .astype(str)
            .str.strip()
        )

        is_year = False
        yn = (
            nums_row.str.strip()
            .str.replace('\s+', '', regex=True)
            .str.extract('^([\d\.]+)', expand=False)
            .str.extract('(^\d{4}.?\d*)', expand=False)
            .astype(float)
            .dropna()
            .pipe(lambda x: x[(x - x.astype(int)) == 0])
            [lambda x: (x > 1950) & (x < 2030)]
            .drop_duplicates(keep='last')
        )
        print(f'yn -> {yn}')

        if not yn.empty:
            is_year = True
            print(is_year)
            idx_row = nums_row.loc[yn.index[0]+1:].index[0]
        else:
            idx_row = nums_row.index[0]
        print(idx_row)
        return idx_col, idx_row, is_year

    def find_idx(self, exf: pd.DataFrame) -> tuple[int, bool]:
        '''获取第一个有效内容的索引'''
        is_year = False
        try:
            col_idx = (
                exf.iloc[:, 0].astype(str)
                .str.replace('\s+', '', regex=True)
                .str.contains('^\d+$')[lambda x: x].index[0]
            )
            return col_idx, is_year
        except IndexError:
            _, col_idx, is_year = self.fin_coord(df=exf)
            # col_idx = (
            #     exf.iloc[:, 0]
            #     .where(
            #         lambda x: x.isna(),
            #         lambda x: x.isna().cumsum()
            #     )
            #     [lambda x: x == x.value_counts().index.max()]
            #     .index[0]
            # )
            return col_idx, is_year

    def find_trs_table(self, df: pd.DataFrame):
        '''寻找需要转置的表'''
        for k, v in df.iloc[:, 1:].iterrows():
            v = (
                v
                .dropna()
                .astype(str)
                .replace('#|，|\s+|\.', '', regex=True)
                .str.cat()
            )
            if bool(v):
                char_ratio_col = len(v) / (df.shape[1]-1)  # 字符与列的比
                num_ratio = len(''.join(re.findall('\d+', v))
                                ) / len(v)  # 数字与总字符之比
                if (char_ratio_col > 2) and (num_ratio >= 0.5) and (df.shape[1] > 5):
                    print(k)
                    print(v)
                    print(num_ratio)
                    return self.transpose(df=df.copy(), idx=k)
                if (char_ratio_col > 2) and (num_ratio < 0.9):
                    print(v)
                    print(num_ratio)
                    return self.refactor_df(
                        df=df,
                        col_idx=self.find_idx(exf=df)
                    )

    def transpose(self, df: pd.DataFrame, idx: int):
        '''转置表格
        :idx: 第一个有效的行号
        '''
        # 找到列号
        print('idx -> ', idx)
        col_idx = (
            df.loc[idx]
            .reset_index(drop=True)
            .astype(str)
            .str.strip()
            .str.contains('^[\d\.]+$', na=False)
            [lambda x: x]
            .head(1)
            .index[0]
        )
        print('colidx', col_idx)
        df.iloc[:, 0] = df.iloc[:, 0].ffill()
        df = df[~df.iloc[:, int(df.shape[1] / 2):].isna().all(1)]  # 末尾无效行
        df = df.drop_duplicates(subset=df.columns[0], keep='last')
        self.tem_df = df
        df = df.T.reset_index(drop=True).copy()
        # df.iloc[col_idx-1, 0] = '年份'
        df.iloc[0, 0] = '年份'
        if col_idx > 1:
            df = df.drop(index=col_idx-1).reset_index(drop=True)
            return self.refactor_df(df=df, col_idx=col_idx-1)
        return self.refactor_df(df=df, col_idx=col_idx)

    def refactor_df(self, df: pd.DataFrame, col_idx: int, is_merging: bool = True) -> pd.DataFrame:
        '''重新设置表头并生成新dataframe
        :is_merging: 是否有合并单元格, 使用不同的处理逻辑
        '''

        def alter_col_type(x: any) -> str:
            '''格式化表头为文本'''
            try:
                x = str(int(float(x)))
                return x
            except ValueError:
                x = str(x)
                return x

        def align_down(t: pd.Series, first_col_name: str = None):
            '''忽略表头中的空白单元,将文字向下对齐
            :first_col_name: 第一列只保留一个有效内容
            '''
            # print('name', t.name)
            if t.name == first_col_name:
                content = t[t != ''].to_list()[-1:]  # 导出有效内容
            else:
                content = t[t != ''].to_list()  # 导出有效内容
            blank = [''] * (len(t) - len(content))  # 加入空白单元
            blank.extend(content)  # 将内容放置到最后
            return pd.Series(blank, index=t.index)

        def ffill_bank(s: pd.Series):
            '''填充空白单元'''
            return s.where(s != '').ffill()

        if is_merging:
            first_col_name = df.columns[0]
            colname = (
                df.loc[:col_idx-1]
                .applymap(alter_col_type)
                .apply(
                    lambda x: x.str.replace(
                        '（.+）|\(.+\)|nan|#|[a-zA-Z]|，|\s+|．|\-|单位：.+|单位:.+', '', regex=True)
                    .str.strip()
                    .replace({'其中': ''})
                    .str.replace('[\(\)]|其中：|／|~①', '', regex=True)
                )
                .apply(lambda x: align_down(t=x, first_col_name=first_col_name))
                .apply(ffill_bank, axis=1)
                .dropna(axis=0, how='all')
                .fillna('')
                .apply(
                    lambda x: x
                    .drop_duplicates(keep='last')
                    .str.cat()
                )
                # .replace({'.*年份$':'年份'}, regex=True)  # 结尾是年份的作替换
                .to_list()
            )
        else:
            colname = (
                df.loc[:col_idx-1]
                .applymap(alter_col_type)
                .apply(
                    lambda x: x.str.replace(
                        '（.+）|\(.+\)|nan|#|[a-zA-Z]|，', '', regex=True).str.strip()
                    [lambda x: ~x.isin([np.nan, ''])]
                    .tail(1)
                    .reset_index(drop=True),
                    axis=0
                )
                .iloc[0, :]
                .str.replace('\s+', '', regex=True)
                .to_list()
            )
        df = df.rename(columns=dict(zip(df.columns, colname))).loc[col_idx:]
        # print(colname)
        # df.columns = colname
        df = df[~df.iloc[:, int(df.shape[1] / 2):].isna().all(1)]
        df.iloc[:, 0] = df.iloc[:, 0].astype(
            str).str.replace('\s+', '', regex=True)
        # 清除一些未被清理掉的零星字符
        df.columns = (
            df.columns
            .str.replace('(?<=[^\d]{1})\d{1}$|附:|附：', '', regex=True)
            .str.replace('\.|.+、|\?|\'|。|^\d{1,2}(?!\d+)|’|\,|—|~|＆|&|）|：|:', '', regex=True)
            .str.replace('.*(\d{4})年[为比](\d{4}).+', '\g<1>%\g<2>', regex=True)
            .str.replace('(?<!\d)\d{1,3}$|(?<!\d)\d{1,3}(?!\d+)', '', regex=True)
            .str.replace('[±％±%（/=]', '', regex=True)
        )
        # 填充一些已知的空白列名
        if df.iloc[0, 0] == '全市':
            df.columns = ['区'] + df.columns.to_list()[1:]
        return df

    def to_process_en_columns(self, df: pd.DataFrame, idx: int) -> pd.DataFrame:
        '''处理全英文的字段名'''
        col_name = (
            df.iloc[0, 1:]
            .str.strip()
            .str.replace('（.+）|\(.+\)', '', regex=True)
            .str.replace('[_—-]', '', regex=True)
            .apply(lambda x: '_'.join(re.split('(?<!^)(?=[A-Z])', x)))
            .str.lower()
            .str[:64]
            .pipe(lambda x: ['年份'] + x.to_list())
        )

        df.columns = col_name
        df = df.iloc[idx:].reset_index(drop=True)
        return df

    def single_file_test(self, file_path):
        '''用于测试文件处理后的效果'''
        df = self.read_exl(file_path)
        # idx = self.find_idx(df)
        return self.find_trs_table(df=df)
    def single_file(self, df: pd.DataFrame):
        '''单个文件处理后'''
        # df = self.read_exl(file_path)
        is_year = False
        idx, is_year = self.find_idx(df)
        return self.refactor_df(df=df, col_idx=idx), is_year


class Tools:
    def __init__(self) -> None:
        self.col_map = pd.read_excel(
            './BasicInfo/col_name.xlsx')[['k', 'v']].set_index('k')['v']
        self.file_name_map = pd.read_excel('./BasicInfo/fname.xlsx')

    @staticmethod
    def update_col_file(filename: str):
        '''更新映射字段名的文件'''
        (
            pd.read_excel(filename)
            .assign(v=lambda y: y.b.str.replace('，', '')
                    .apply(
                lambda x: '_'.join(re.findall('[A-Z][^A-Z]+', x))
            ).str.lower()
            )
        ).to_excel(f'{os.path.splitext(filename)[0]}_2.xlsx', index=False)
        print('更新完成')

    @staticmethod
    def transform_type(df: pd.DataFrame) -> pd.DataFrame:
        '''将数值转换成正确的数据类型'''
        # for name in  ((df.dtypes == 'object')[lambda x: x]).index:
        # for col_idx in range(df.shape[1]):
        for col_idx, is_obj in zip(range(df.shape[1]), (df.dtypes == 'object').to_list()):
            if is_obj:
                val: pd.Series = df.iloc[:, col_idx]
                name = val.name
                # print(name)
                # print(val)
                val = (
                    val.astype(str)
                    .str.replace('\s+', '', regex=True)
                    .str.replace('．', '.', regex=False)
                    .str.strip()
                )
                try:
                    val = val.astype(int)
                except ValueError:
                    try:
                        val = val.astype(float)
                    except ValueError as e:
                        print(f'\n{name}{e}')
                df.iloc[:, col_idx] = val
        return df

    def merge_exl(
        self,
        folder,
        is_sheetname: bool = False,
        sheetname_perfix: str = '',
        is_merging=True
    ):
        '''
        提取文件夹中的所有文件并合并
        folder: 文件目录
        sheetname_perfix: 自定义sheet名的前缀
        '''
        cue = ClearUpExcel()
        self.source_tables = {}  # 原表
        self.res_tables = {}  # 没有更新过列名的表
        self.res_dic = {}  # 已经更新过列名的表
        self.res_record = []

        files = [f for f in os.listdir(folder) if not f.startswith('~') and (
            f.lower().endswith('xlsx') or f.lower().endswith('xls'))]
        for xlname in files:
            try:
                record = {
                    'filename': xlname,
                    'perfix': sheetname_perfix
                }
                sht_name = xlname.split('-')[0]
                record['sht_name'] = sht_name
                print(sht_name, xlname)
                df = cue.read_exl(os.path.join(folder, xlname))
                self.source_tables[sht_name + '_0'] = df
                # res = cue.find_trs_table(df=df)
                res, is_year = cue.single_file(df=df)
                self.res_tables[sht_name] = res
                if is_sheetname:
                    res = self.transform_type(res)
                    res = self.find_lateral_table(res)
                    record['is_year'] = is_year
                    if is_year: # 需要转置
                        res = self.trans_record(df=res)
                    res = res.rename(columns=self.col_map)
                    record['value'] = res
                    
                    if sheetname_perfix == '':
                        kw = self.file_name_map[self.file_name_map.kw.apply(
                            lambda x: x in xlname)].perfix
                        if kw.empty:
                            pass
                        else:
                            perfix = kw.iloc[0]
                            record['perfix'] = perfix
                            name = sht_name.split('_')[0]
                            self.res_dic[perfix + name] = res
                    else:
                        self.res_dic[sheetname_perfix + sht_name] = res
                self.res_record.append(record)
                # 拆分纵向表
                split_kw = ['年份']
                pat = '|'.join(split_kw)
                if ('year' in res.columns) and (res['year'].astype(str).str.contains(pat).any()):
                    print('split A')
                    sub, df, is_split = self.split_vertical_table(df=res, pat=pat)
                    if is_split:
                        print('split_vertical_table')
                        self.res_record[-1]['value'] = df
                        sub_record = copy.deepcopy(self.res_record[-1])
                        sub_record['value'] = sub
                        self.res_record.append(sub_record)
                elif 'project' in res.columns:
                    print('split B')
                    self.res_record[-1]['value'] = res[~res['project'].str.contains('^项目|Item')]
                elif '续表年份' in res.columns:
                    print('split C')
                    split_idx = res.columns.to_list().index('续表年份')
                    df, sub = np.split(res, [split_idx], axis=1)
                    sub.columns = sub.columns.str.replace('续表', '', regex=True)
                    sub = sub.rename(columns=self.col_map)
                    df = df[~df.iloc[:, int(df.shape[1] / 2):].isna().all(1)]  # 末尾无效行
                    sub = sub[~sub.iloc[:, int(sub.shape[1] / 2):].isna().all(1)]
                    self.res_record[-1]['value'] = df
                    sub_record = copy.deepcopy(self.res_record[-1])
                    sub_record['value'] = sub
                    self.res_record.append(sub_record)
                else:
                    print('split None')

            except Exception as e:
                logging.error(f"{xlname} -> {e}")
                print(f"{xlname} -> {e}")
                continue
        if is_sheetname:
            self.update_res_record()

    def split_vertical_table(self, df: pd.DataFrame, pat) -> tuple:
        cue = ClearUpExcel()
        idx = df['year'].str.contains(pat)[lambda x: x].index[0]
        sub = df.loc[idx:].copy()

        if sub['year'].str.contains('^\d+').sum() / sub.shape[0] > 0.5:
            sub = sub.reset_index(drop=True)
            col_idx = sub['year'].str.contains('^\d+')[lambda x: x].index[0]
            sub = cue.refactor_df(df=sub, col_idx=col_idx)
            sub = sub.rename(columns=self.col_map)
            sub = self.transform_type(df=sub)
            df = df.loc[:idx-1].copy()
            df = self.transform_type(df=df)
            df = df.dropna(subset=df.columns[0])
            return sub, df, True
        else:
            return None, None, False

    def trans_record(self, df: pd.DataFrame):
        '''转置'''
        cue = ClearUpExcel()
        # 转置前删除单位列
        unit_col = df.columns[df.columns.str.contains('^单位')]
        if not unit_col.empty:
            df = df.drop(columns=unit_col[0])

        df = df[~df.iloc[:, 0].isin(['nan', ''])]
        df = df.drop_duplicates(subset=df.columns[0])
        df = df.T.reset_index()
        df.iloc[0, 0] = '年份'
        # 判断是否为全英文字段
        is_en_columns = df.iloc[0, 1:].str.contains('[一-龟]{2,}').any()
        if not is_en_columns:
            df = cue.to_process_en_columns(df=df, idx=1)
        else:
            df = cue.refactor_df(df=df, col_idx=1)
        # 转置后删除单位列
        exclude_kw = ['计量单位']
        if df['年份'].isin(exclude_kw).any():
            df = df[~df['年份'].isin(['计量单位'])].copy()
            df.loc[:, '年份'] = df['年份'].str.replace('计量单位', '', regex=True)

        return df

    def update_res_record(self):
        '''更新结果中的数据'''
        tbnames = {}
        for con in self.res_record:
            con['city'] = CITY
            comm = (
                self.file_name_map
                [self.file_name_map.kw.apply(
                    lambda x: x in con.get('filename'))]
                [['title', 'perfix']]
            )
            if comm.empty:
                con['comment'] = ''
            else:
                comm_per = comm['title'][lambda x: x.str.len()
                                         == x.str.len().max()].iloc[0]
                con['comment'] = comm_per + '_' + \
                    con.get('city') + '_' + con.get('sht_name').split('_')[0]
                con['perfix'] = comm[lambda x: x['title'].str.len(
                ) == x['title'].str.len().max()]['perfix'].iloc[0]

            con['tablename'] = con.get(
                'perfix') + '_' + con.get('city') + '_' + con.get('sht_name').split('_')[0]
            # 处理文件重名
            tbname = con['tablename']
            if tbname in tbnames:
                con['tablename'] = tbname + '_' + str(tbnames.get(tbname)+1)
                tbnames[tbname] += 1
            else:
                tbnames[tbname] = 1
            # 处理重复列
            con['value'] = con['value'].loc[:, ~con['value'].columns.duplicated()]
            # 处理无效行
            con['value'] = con['value'][~con['value'].iloc[:, 0].isin(['nan', ''])]
            # 无效列处理
            for s in ['＆', '&', '', ':']:
                if s in con['value'].columns:
                    # print(s)
                    con['value'] = con['value'].drop(columns=s)

            pat = '^续表年份\d+|^年份\d{6,}'
            if con['value'].columns.str.contains(pat).any():
                col_idx = con['value'].columns.get_indexer_for(con['value'].columns[con['value'].columns.str.contains(pat)])[0]
                con['value'] = con['value'].iloc[:, :col_idx]

    def export_exl(
        self,
        save_name: str,
        folder,
        is_source: bool = False,
        is_sheetname: bool = False,
        sheetname_perfix: str = ''
    ):
        '''
        导出excel文件
        :save_name: 合并excel的文件名
        folder: 文件目录
        is_source: 是否需要导出原文件
        is_sheetname: 自定义sheet名, 导出的表会被统一字段名
        sheetname_perfix: 自定义sheet名的前缀
        '''
        self.merge_exl(
            folder=folder,
            is_sheetname=is_sheetname,
            sheetname_perfix=sheetname_perfix,
            is_merging=True
        )

        exfw = pd.ExcelWriter(save_name, engine='openpyxl')
        if is_source:
            for soruce_name, res_name, rsd_name in zip(self.source_tables, self.res_tables, self.res_dic):
                self.source_tables[soruce_name].to_excel(
                    exfw, sheet_name=soruce_name + '_0', index=False
                )
                self.res_tables[res_name].to_excel(
                    exfw, sheet_name=soruce_name, index=False
                )
                self.res_dic[rsd_name].to_excel(
                    exfw, sheet_name=rsd_name + '2', index=False
                )
        elif is_sheetname:
            for sht_name, df in self.res_dic.items():
                df.to_excel(
                    exfw, sheet_name=sheetname_perfix + sht_name, index=False
                )
        else:
            for sht_name, df in self.res_tables.items():
                df.to_excel(exfw, sheet_name=sht_name, index=False)

        exfw.save()

    def find_lateral_table(self, table: pd.DataFrame):
        '''判断是否为横向排列的表格'''
        white_list = ['年份', '项目']  # 不计入重复的列
        cols_num = table.columns.value_counts()
        max_col_num = cols_num[~cols_num.index.isin(white_list)].max()
        # 重复的字段小于2个的不属于横向表
        if 0 < (cols_num > 1).sum() < 2:
            # for colname in cols_num[cols_num > 1].index:
                # table = self.merge_special_col(df=table, colname=colname)
            return table.loc[:, ~table.columns.duplicated()]
        # 大于1的做纵向处理 不再需要去重
        if max_col_num > 1:
            print(max_col_num)
            return self.split_and_regroup(df=table, chunk=max_col_num)

        # 白名单里的字段大于2的合并处理
        if cols_num[cols_num.index.isin(white_list) & (cols_num > 1)].count():
            for key_word in white_list:
                table = self.merge_special_col(df=table, colname=key_word)
            return table
        return table

    def split_and_regroup(self, df: pd.DataFrame, chunk: int) -> pd.DataFrame:
        '''将横向排列的表拆分后重组成纵向
        :chunk: 需要拆分成多少块, 数量必须与列数等比
        '''
        # chunk = self.find_lateral_table(table=df)
        # if chunk > 1:
        try:
            line = np.linspace(0, df.shape[1], chunk+1)[1:-1].astype(int)
            df_ls = np.split(df, line, axis=1)
            for df_chunk in df_ls[1:]:
                df_chunk.columns = df_ls[0].columns

            return pd.concat(df_ls, ignore_index=True)
        except Exception as e:
            logging.error(f"{df} -> {e}")
            # 无法重组的 去重处理
            return df.loc[:, ~df.columns.duplicated()]
    # else:
    #     return df

    def merge_special_col(self, df: pd.DataFrame, colname: str) -> pd.DataFrame:
        '''合并特殊字段, 比如年份'''
        df = pd.concat(
            [df[colname].iloc[:, 0], df.drop(columns=colname)], axis=1)
        return df

    def check_datas(self, data: dict):
        '''导入前的数据检查'''
        if isinstance(data, dict):
            for name, df in data.items():
                col_count = df.columns.value_counts()[lambda x: x > 1]
                if col_count.count():
                    print(name, '有重复列\n', col_count)
                else:
                    print(name, '没有重复列')
        elif isinstance(data, list):
            for con in data:
                df = con.get('value')
                name = con.get('tablename')
                col_count = df.columns.value_counts()[lambda x: x > 1]
                if col_count.count():
                    print(name, f'有重复列\n', col_count)
                else:
                    print(name, f'没有重复列 len {len(name)}')
