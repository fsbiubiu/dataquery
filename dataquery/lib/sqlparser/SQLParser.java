import java.util.*;

import com.alibaba.druid.stat.TableStat;
import com.alibaba.druid.sql.ast.SQLStatement;
import com.alibaba.druid.sql.dialect.mysql.parser.MySqlStatementParser;
import com.alibaba.druid.sql.dialect.mysql.visitor.MySqlSchemaStatVisitor;
import py4j.GatewayServer;


public class SQLParser {
    List<String> tables = new ArrayList<String>();
    List<Map<String, String>> columns = new ArrayList<Map<String, String>>();
    Map<String, String> alias = new HashMap<String, String>();

    public List<String> get_tables(){
        return tables;
    }
    public List<Map<String, String>> get_columns(){
        return columns;
    }
    public Map<String, String> get_alias(){
        return alias;
    }

    public void init(){
        //一个类要重新初始化
        tables = new ArrayList<String>();
        columns = new ArrayList<Map<String, String>>();
        alias = new HashMap<String, String>();
    }
    public void parse(String sql){

        MySqlStatementParser parser = new MySqlStatementParser(sql);
        List<SQLStatement> statementList = parser.parseStatementList();
        SQLStatement statemen = statementList.get(0);

        MySqlSchemaStatVisitor visitor = new MySqlSchemaStatVisitor();
        statemen.accept(visitor);

        // tables
        //Map<TableStat.Name, TableStat> itables = visitor.getTables();
        for ( TableStat.Name name : visitor.getTables().keySet() ) {
            tables.add(name.getName());
        }

        // columns
        for (TableStat.Column column : visitor.getColumns()){
            // System.out.println( column.toString() );
            HashMap<String, String> map = new HashMap<String, String>();
            map.put("column_name", column.getName());
            map.put("table_name", column.getTable());
            map.put("is_select", String.valueOf(column.isSelect()));
            columns.add(map);
        }

        // alias
        alias = visitor.getAliasMap();

        System.out.println("SQL: " + sql + "\nTables: " + tables + "\nColumns: " + columns + "\nAlias: " + alias);
    }

    public static void main(String[] args){
        GatewayServer gatewayServer = new GatewayServer(new SQLParser());
        gatewayServer.start();
        System.out.println("Gateway Server Started");
    }
}
