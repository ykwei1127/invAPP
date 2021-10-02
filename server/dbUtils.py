from sqlite3.dbapi2 import DatabaseError
import pandas as pd
import sqlite3
import json

from pandas.io.sql import read_sql


userDB = "db/userDB.db"
dataDB = "db/dataDB.db"

def default(username):
    # 連資料庫
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    ###
    
    ###
    conn.commit()
    conn.close()
    return

# 將新使用者的username和password新增到user table
def db_create_user(username, password):
    # 連資料庫
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    # 確認user表是否已創建，若無則建立
    # listOfTables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'").fetchall()
    # if listOfTables == []:
    #     cursor.execute("CREATE TABLE IF NOT EXISTS user (username TEXT PRIMARY KEY UNIQUE, password TEXT)")
    #     cursor.execute("CREATE INDEX idx1 ON user(username)")
    # 插入使用者資料進table中
    cursor.execute("INSERT INTO user VALUES (?,?)", (username,password))
    conn.commit()
    conn.close()
    return

# 取得特定user的username和password
def db_get_user(username):
    # 連資料庫
    conn = sqlite3.connect(userDB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE username=?",[username])
    data = cursor.fetchall()
    data = json.dumps([dict(ix) for ix in data])
    conn.close()
    return data

# 取得user table中所有user的username
def db_get_all_user_list():
    # 連資料庫
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM user")
    data = cursor.fetchall()
    data = json.dumps([user[0] for user in data], indent=4)
    conn.close()
    return data

# 將輸入的users從user table中刪除
def db_delete_user_list(usersToDelete):
    # 連資料庫
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    for user in usersToDelete:
        cursor.execute("DELETE FROM user WHERE username=?",[user])
    conn.commit()
    conn.close()
    return   

# 查看username在user table是否存在
def db_check_user_exist(username):
    # 連資料庫
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE username=?",[username])
    data = cursor.fetchall()
    if (data == []):
        conn.close()
        return False
    else:
        conn.close()
        return True

# 取出data database所有table名稱
def db_get_all_data_list():
    # 連資料庫
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '%-%' AND name NOT LIKE 'sqlite_sequence'AND name NOT LIKE 'salesUnit'")
    data = cursor.fetchall()
    data = json.dumps([d[0] for d in data], indent=4)
    conn.close()
    return data

# 將輸入excel檔寫入data database中，建立名稱為盤點日期的table
def db_create_data_table(date, rawDataFrame):
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    # 用來建parent table盤點進度追蹤的table
    query = "DROP TABLE IF EXISTS temp"
    cursor.execute(query)
    query = "CREATE TABLE IF NOT EXISTS temp (盤點日,單位,組別,代碼,藥名,計價單位,預包數量 INTEGER,預包單位) "
    cursor.execute(query)
    conn.commit()
    rawDataFrame['單位'] = rawDataFrame['單位'].str.replace(" ","")
    rawDataFrame['組別'] = rawDataFrame['組別'].str.replace(" ","")
    rawDataFrame['代碼'] = rawDataFrame['代碼'].str.strip()
    rawDataFrame['藥名'] = rawDataFrame['藥名'].str.strip()
    rawDataFrame['計價單位'] = rawDataFrame['計價單位'].str.strip()
    rawDataFrame['預包數量'] = rawDataFrame['預包數量'].fillna(0)
    rawDataFrame['預包單位'] = rawDataFrame['預包單位'].fillna("無")
    rawDataFrame.to_sql("temp", conn, if_exists='append', index=False)
    # 從 temp table取出數量建成盤點進度的table
    query = "SELECT 盤點日,單位,組別,COUNT(*) AS 藥品總數 FROM temp GROUP BY 盤點日,單位,組別"
    progressData = pd.read_sql(query, conn)
    query = "DROP TABLE IF EXISTS {}".format(f"'{date}-progress'")
    cursor.execute(query)
    query = "CREATE TABLE IF NOT EXISTS {} (ID INTEGER PRIMARY KEY AUTOINCREMENT, 盤點日, 單位, 組別, 藥品總數 REAL, 已盤點數 REAL DEFAULT 0.0, 盤點進度 INTEGER GENERATED ALWAYS AS (round(已盤點數/藥品總數*100)) STORED)".format(f"'{date}-progress'") #建立資料表
    cursor.execute(query)
    conn.commit()
    progressTableName = date+"-progress"
    progressData.to_sql(progressTableName, conn, if_exists='append', index=False)
    # 將raw資料建成完整data table
    query = "SELECT ID,盤點日,單位,組別,代碼,藥名,計價單位,預包數量,預包單位 FROM {} INNER JOIN temp USING (盤點日,單位,組別)".format(f"'{date}-progress'")
    inventoryData = pd.read_sql(query, conn)
    cursor.execute("DROP TABLE IF EXISTS temp")
    conn.commit()
    query = "DROP TABLE IF EXISTS {}".format(f"'{date}'")
    cursor.execute(query)
    query = "CREATE TABLE IF NOT EXISTS {0} (\
        ID INTEGER, \
        盤點日, \
        單位, \
        組別, \
        代碼, \
        藥名, \
        計價單位, \
        預包數量 INTEGER, \
        預包單位, \
        App盤點預包數量 INTEGER DEFAULT 0, \
        App盤點數量 INTEGER DEFAULT 0, App盤點總數量 INTEGER GENERATED ALWAYS AS (預包數量*App盤點預包數量+App盤點數量) STORED, \
        是否盤點 INTEGER GENERATED ALWAYS AS (CASE WHEN App盤點總數量>0 THEN 1 ELSE 0 END) STORED, \
        CONSTRAINT con_primary_key PRIMARY KEY(盤點日, 單位, 組別, 代碼), \
        FOREIGN KEY (ID) REFERENCES {1} (ID) \
    )".format(f"'{date}'", f"'{date}-progress'") #建立資料表
    cursor.execute(query)
    conn.commit()
    inventoryData.to_sql(date, conn, if_exists='append', index=False)
    return

# 盤點日,單位,組別,藥品總數,以盤點數,完成百分比從progress table以json的格式讀出來，給盤點進度追蹤html顯示表格
def db_get_progress_data(date):
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    query = "UPDATE {0} SET 已盤點數=temp.已盤點數 FROM (SELECT COUNT(*) AS 已盤點數, ID FROM {1} WHERE 是否盤點>0 GROUP BY ID) AS temp WHERE {0}.ID=temp.ID".format(f"'{date}-progress'", f"'{date}'")
    # UPDATE '1100814-progress' SET 已盤點數=測試.已盤點數 FROM (SELECT ID,SUM(是否盤點) AS 已盤點數 FROM '1100814' GROUP BY ID) AS 測試 WHERE '1100814-progress'.ID=測試.ID;
    # UPDATE '1100814-progress' SET 已盤點數=測試.已盤點數 FROM (SELECT COUNT(*) AS 已盤點數, ID FROM '1100814' WHERE 是否盤點>0 GROUP BY ID) AS 測試 WHERE '1100814-progress'.ID=測試.ID;
    cursor.execute(query)
    conn.commit()
    sql = "SELECT ID,盤點日,單位,組別,藥品總數,已盤點數,盤點進度 FROM {}".format(f"'{date}-progress'")
    cursor.execute(sql)
    data = cursor.fetchall()
    conn.close()
    return json.dumps(data)

# 展開盤點進度追蹤點取位置的所有藥品
def db_get_progress_data_detail(id, date):
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "SELECT 盤點日, 單位, 組別, 代碼, 藥名, App盤點總數量, 是否盤點 FROM {0} WHERE ID={1}".format(f"'{date}'", f"'{id}'")
    cursor.execute(sql)
    data = cursor.fetchall()
    conn.close()
    return json.dumps(data)

# [暫定]將選定日期的全部data從盤點的table讀出來，給展開盤點作業html顯示表格
def db_get_data_for_inventory(date):
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "SELECT 盤點日, 單位, 組別, 代碼, 藥名, App盤點總數量 FROM {}".format(f"'{date}'")
    cursor.execute(sql)
    data = cursor.fetchall()
    conn.close()
    return json.dumps(data)

#----- DEFAULT for Initiation -----#

# 設定初始使用者admin可以登入
def db_set_default_user(username, password):
    # 連資料庫
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    # 確認user表是否已創建，若無則建立
    listOfTables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'").fetchall()
    if listOfTables == []:
        cursor.execute("CREATE TABLE IF NOT EXISTS user (username TEXT PRIMARY KEY UNIQUE, password TEXT)")
        cursor.execute("CREATE INDEX idx1 ON user(username)")
    # 插入使用者資料進table中
    cursor.execute("INSERT INTO user VALUES (?,?)", (username,password))
    conn.commit()
    conn.close()
    return

# 設定中英文計價單位對照表
def db_set_salesUnit(df):
    conn = sqlite3.connect(dataDB)
    df.to_sql('salesUnit', conn, if_exists = 'replace', index=False)
#----- DEFAULT for Initiation -----#

# SELECT *, COUNT(*) FROM '1100814' GROUP BY 盤點日,單位,組別
# SELECT ID,盤點日,單位,組別,PID FROM '1100814' INNER JOIN '1100814-progress' USING (盤點日,單位,組別);
# SELECT ID,盤點日,單位,組別,代碼,藥名,計價單位,預包數量,預包單位 FROM '1100814-progress' INNER JOIN '1100814' USING (盤點日,單位,組別);
# SELECT ID,COUNT(*) AS 已盤點數 FROM '1100814' WHERE 是否盤點>0 GROUP BY ID ;
# query = "SELECT ID,SUM(是否盤點) AS 已盤點數 FROM {}  GROUP BY ID".format(f"'{date}'")

#---------------APP---------------#

# APP登入時取得資料庫中所有使用者及密碼
def db_app_get_users():
    conn = sqlite3.connect(userDB)
    cursor = conn.cursor()
    sql = "SELECT * from user"
    data = pd.read_sql(sql, conn)
    data = data.to_json(orient='records')
    data = json.loads(data)
    jsonObject = {}
    for d in data:
        jsonObject[d['username']] = d
    return jsonObject

# 掃QECODE取得位置後，回傳位置所有藥品的代碼及藥名
def db_app_qrcode_result(qrcode):
    position = qrcode.split()
    unit = position[0]
    group = position[1]
    date = get_latest_inventory_date()

    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "SELECT 代碼, 藥名, 是否盤點 FROM {0} WHERE 單位={1} AND 組別={2}".format(f"'{date}'", f"'{unit}'", f"'{group}'")
    data = pd.read_sql(sql, conn)
    data = data.to_json(orient='records')
    return data

# 利用藥品位置及藥碼取得預包的單位
def db_app_qrcode_unit_info(unit, group, code):
    date = get_latest_inventory_date()
    conn = sqlite3.connect(dataDB)
    sql = "SELECT * From salesUnit"
    unitComparisonTable = pd.read_sql(sql, conn).set_index("計價單位").T.to_dict("list")
    sql = "SELECT 計價單位, 預包數量, 預包單位 FROM {0} WHERE 單位={1} AND 組別={2} AND 代碼={3}".format(f"'{date}'", f"'{unit}'", f"'{group}'", f"'{code}'")
    df = pd.read_sql(sql, conn)
    df["計價單位"] = unitComparisonTable[df["計價單位"].values[0]][0]
    data = df.to_json(orient='records')
    return data

# 將App位置藥碼的盤點預包數量及盤點數量更新至database
def db_app_invent(dict):
    date = get_latest_inventory_date()
    unit = dict["單位"]
    group = dict["組別"]
    code = dict["代碼"]
    prePackedNum = dict["App盤點預包數量"]
    num = dict["App盤點數量"]

    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "UPDATE {0} SET App盤點預包數量={1}, App盤點數量={2} WHERE 單位={3} AND 組別={4} AND 代碼={5}".format(f"'{date}'", f"'{prePackedNum}'", f"'{num}'", f"'{unit}'", f"'{group}'", f"'{code}'")
    cursor.execute(sql)
    conn.commit()
    conn.close()
    return

# 加減單一藥品數量，查詢關鍵字，將符合關鍵字藥品的藥碼及藥名回傳
def db_app_search_result(query):
    date = get_latest_inventory_date()
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "SELECT 代碼, 藥名 FROM {0} WHERE 藥名 LIKE {1} GROUP BY 藥名".format(f"'{date}'", f"'%{query}%'")
    data = pd.read_sql(sql, conn)
    data = data.to_json(orient='records')
    return data

# 加減單一藥品數量，回傳選取藥品所在的所有位置及盤點量是否盤點
def db_app_select_result(code):
    date = get_latest_inventory_date()
    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "SELECT 單位, 組別, App盤點總數量, 是否盤點 FROM {0} WHERE 代碼={1}".format(f"'{date}'", f"'{code}'")
    data = pd.read_sql(sql, conn)
    data = data.to_json(orient='records')
    return data

# 加減單一藥品數量，回傳藥品的計價單位
def db_app_single_unit_info(unit, group, code):
    date = get_latest_inventory_date()
    conn = sqlite3.connect(dataDB)
    sql = "SELECT * From salesUnit"
    unitComparisonTable = pd.read_sql(sql, conn).set_index("計價單位").T.to_dict("list")
    sql = "SELECT 計價單位 FROM {0} WHERE 單位={1} AND 組別={2} AND 代碼={3}".format(f"'{date}'", f"'{unit}'", f"'{group}'", f"'{code}'")
    df = pd.read_sql(sql, conn)
    df["計價單位"] = unitComparisonTable[df["計價單位"].values[0]][0]
    data = df.to_json(orient='records')
    return data

# 加減單一藥品數量，將App位置藥碼輸入的App盤點數量，運算更新加減幾顆至資料庫中
def db_app_update_single_amount(dict):
    date = get_latest_inventory_date()
    unit = dict["單位"]
    group = dict["組別"]
    code = dict["代碼"]
    amount = int(dict["App盤點數量"])

    conn = sqlite3.connect(dataDB)
    cursor = conn.cursor()
    sql = "SELECT App盤點數量 FROM {0} WHERE 單位={1} AND 組別={2} AND 代碼={3}".format(f"'{date}'", f"'{unit}'", f"'{group}'", f"'{code}'")
    databaseAmount = int(cursor.execute(sql).fetchone()[0])
    result = databaseAmount + amount
    sql = "UPDATE {0} SET App盤點數量={1} WHERE 單位={2} AND 組別={3} AND 代碼={4}".format(f"'{date}'", f"'{result}'", f"'{unit}'", f"'{group}'", f"'{code}'")
    cursor.execute(sql)
    conn.commit()
    conn.close()
    return 

# 取得"最新一天"的盤點日期
def get_latest_inventory_date():
    date = db_get_all_data_list()
    date = json.loads(date)
    date = max(date)
    return date
#---------------APP---------------#