# coding: utf-8

from py4j.java_gateway import JavaGateway


class Parser(object):
    def __init__(self, sql):
        self.sql = sql
        self.gateway = JavaGateway()
        self.gateway.entry_point.init()
        self.gateway.entry_point.parse(sql)

        self.tables = self.get_tables()
        self.columns = self.get_columns()
        self.alias = self.get_alias()
        self.columns_table = {}
        for c in self.columns:
            if c['column_name'] in self.columns_table:
                self.columns_table[c['column_name']].append(c['table_name'])
            else:
                self.columns_table[c['column_name']] = [c['table_name']]

        # print(self.tables)
        # print(self.columns)
        # print(self.alias)

    def get_tables(self):
        tables_list = self.gateway.entry_point.get_tables()
        # 直接过滤掉数据库名，只查单库数据
        tables = []
        for table in tables_list:
            tables.append(table.split('.')[-1])

        return tables

    def get_columns(self):
        """ 未标记的字段表为UNKNOWN """
        columns_list = self.gateway.entry_point.get_columns()
        # 只看查询字段
        return [c for c in columns_list if c['is_select'] == 'true']

    def get_alias(self):
        """ 字段别名a和表别名a相同会冲突 """
        alias_map = self.gateway.entry_point.get_alias()
        return dict(alias_map)
