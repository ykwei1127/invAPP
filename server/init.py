import dbUtils
import pandas as pd

dbUtils.db_set_default_user('admin', '123')
print("[預設使用者建立成功] Username: admin, Password: 123")

dic = {
    "計價單位": [
        "10 mL", "Amp", "Bag", "Bot", "Box", "Bucc", "CART", "Cap", 
        "Dose", "Drop", "IU", "Kit", "L/mir", "Pack", "Patcl", "Pce",
        "Pcs", "Pen", "Pow", "Puff", "Supp", "Syrin", "Tab", "Time", 
        "Tube", "U", "UDV", "Vial", "g", "kg", "mCi", "mL",
        "mcg", "mg", "qs", "spray", "ug"
    ],
    "中文計價單位": [
        "10 毫升", "安瓶", "袋", "瓶", "盒", "口頰溶片", "卡匣", "粒",
        "劑", "滴", "國際單位", "組", "公升/分", "包", "片", "支",
        "個", "筆", "粉包", "吸", "栓劑", "支", "錠", "次",
        "管", "單位", "吸入劑", "小瓶", "公克", "公斤", "毫居里", "毫升",
        "微克", "毫克", "適量", "噴", "微克"
    ]
}
df = pd.DataFrame(dic)
dbUtils.db_set_salesUnit(df)
print("[計價單位對照表建立成功]")