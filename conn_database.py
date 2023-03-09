import pymysql
from sqlalchemy import create_engine
import pandas as pd
import logging

class ConnDatabase:
    '''连接数据库的操作'''

    def __init__(self):
        self.db = create_engine(
            'mysql+pymysql://..')
        self.conn = self.db.connect()

    def conn(self):
        try:
            self.db.connect()
            print('连接成功')
        except Exception:
            print('连接失败')

    def create_and_insert(self, data: dict[str, pd.DataFrame]):
        '''传入{表名:df}的键值对，导入数据库中'''
        for k, v in data.items():
            print(k)
            v.to_sql(k, con=self.conn, index=False)
        print('导入完成')

    def insert_record(self, data: list[dict], tablename_k: str, value_k: str):
        '''按记录导入'''
        for record in data:
            tablename = record[tablename_k]
            value: pd.DataFrame = record[value_k]
            print(tablename)
            try:
                value.to_sql(tablename, con=self.conn, index=False, method='multi')
                self.alter_table_comment(table_name=tablename, comment=record.get('filename'))
            except Exception as e:
                print(f'导入失败 -> {e}')
                logging.error(f"{tablename} -> {e}")

    def insert_one(self, data: list[dict], tablename_k: str, value_k: str):
        for record in data:
            tablename = record[tablename_k]
            value: pd.DataFrame = record[value_k]
            print(tablename)
            value.to_sql(tablename, con=self.conn, index=False, method='multi')
            self.alter_table_comment(table_name=tablename, comment=record.get('filename'))

    def alter_table_comment(self, table_name, comment):
        sql = f"ALTER TABLE {table_name} COMMENT '{comment}'"
        # print(sql)
        self.conn.execute(sql)

    def query_tables(self):
        sql = "SELECT TABLE_NAME from information_schema.`TABLES` where TABLE_SCHEMA = 'statistics_new'"
        self.table_name = pd.read_sql(sql, con=self.conn)['TABLE_NAME']

    def completion_tables(self, data: list[dict], tablename_k: str, value_k: str):
        '''补全漏掉的表'''
        self.query_tables()
        lack_data = []
        for con in data:
            name = con.get('tablename')
            if not self.table_name.isin([name]).any():
                lack_data.append(con)

        if bool(lack_data):
            self.insert_record(data=lack_data, tablename_k=tablename_k, value_k=value_k)
        else:
            print('不存在遗漏的表')