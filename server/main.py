from fastapi import FastAPI, Request, status, HTTPException, Form, File, UploadFile, Response
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_login import LoginManager
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login.exceptions import InvalidCredentialsException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

import os
import json
import shutil
import pandas as pd
from io import BytesIO
import dbUtils

app= FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

SECRET = "a122c18ce174802f0155a22e6b113f6b853cb42ce9e556e0"
manager = LoginManager(SECRET, '/auth/login', use_cookie=True)
manager.cookie_name = "some-name"

@manager.user_loader
def load_user(username: str):
    if dbUtils.db_check_user_exist(username):
        user = dbUtils.db_get_user(username)
        user = json.loads(user)[0]
    else:
        user = None
    return user

@app.post("/auth/login")
def login(data: OAuth2PasswordRequestForm = Depends()):
    username = data.username
    password = data.password
    user = load_user(username)
    if not user:
        # you can return any response or error of your choice
        raise InvalidCredentialsException
    elif password != user['password']:
        raise HTTPException(status_code=400, detail="密碼錯誤")

    access_token = manager.create_access_token(
        data={'sub': username}
    )
    response = RedirectResponse(url="/home",status_code=status.HTTP_302_FOUND)
    manager.set_cookie(response, access_token)
    return response

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/home")
def home(request: Request, user=Depends(manager)):
    # return templates.TemplateResponse("home.html", {"request": request, "username": user['username']})
    response = RedirectResponse(url="/openup_inv", status_code=status.HTTP_302_FOUND)
    return response

@app.get("/logout", response_class=HTMLResponse)
def protected_route(request: Request):
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    manager.set_cookie(response, "")
    return response

### 新增帳號 ###
@app.get("/create_user", response_class=HTMLResponse)
def load_create_user_page(request: Request, user=Depends(manager)):
    result = ""
    return templates.TemplateResponse("account/create_user.html", {"request": request, "username": user['username'], "result": result})

@app.post("/create_user", response_class=HTMLResponse)
async def create_user(request: Request, newUsername: str = Form(...), newPassword: str = Form(...), user=Depends(manager)):
    if dbUtils.db_check_user_exist(newUsername):
        result = "新增失敗，帳號已被使用!"
    else:
        result = "使用者新增成功!"
        dbUtils.db_create_user(newUsername, newPassword)
    return templates.TemplateResponse("account/create_user.html", {"request": request, "username": user['username'], "result": result})
### 新增帳號 ###

### 刪除帳號 ###
@app.get("/modify_user")
async def load_modify_user_page(request: Request, user=Depends(manager)):
    userList = dbUtils.db_get_all_user_list()
    return templates.TemplateResponse("account/modify_user.html", {"request": request, "username": user['username'], "data": userList})
    # return JSONResponse(content=DB)

@app.post("/modify_user")
async def delete_select_user(request: Request, user=Depends(manager)):
    current_user = user['username']
    form_data = await request.form()
    form_data = jsonable_encoder(form_data)
    form_data = [i for i in form_data.values()]
    if len(form_data) != 0:
        if current_user in form_data:
            userList = dbUtils.db_get_all_user_list()
            return templates.TemplateResponse("account/modify_user.html", {"request": request, "username": current_user, "data": userList, "result": "無法刪除當前使用者!"})
        else:
            dbUtils.db_delete_user_list(form_data)
            userList = dbUtils.db_get_all_user_list()
            return templates.TemplateResponse("account/modify_user.html", {"request": request, "username": current_user, "data": userList})
    else:
        userList = dbUtils.db_get_all_user_list()
        return templates.TemplateResponse("account/modify_user.html", {"request": request, "username": current_user, "data": userList})
### 刪除帳號 ###

### 盤點進度追蹤 ###
@app.get("/select_date")
async def query_date(request: Request, user=Depends(manager)):
    datesList = dbUtils.db_get_all_data_list()
    return templates.TemplateResponse("progress/select_date.html", {"request": request, "username": user['username'], "datesList": datesList})

@app.post("/progress")
async def select_date_progress(request: Request, date: str = Form(...), user=Depends(manager)):
    url = f"/progress/{date}"
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    return response

@app.get("/progress/{date}")
def get_progress_date(request: Request, date: str, user=Depends(manager)):
    progressData = dbUtils.db_get_progress_data(date)
    # print(progressData)
    return templates.TemplateResponse("progress/progress_date.html", {"request": request, "username": user['username'], "date": date, "progressData": progressData})

@app.get("/progress/{date}/{ID}")
def get_progress_date_ID(request: Request, date: str, ID: str, user=Depends(manager)):
    progressDetailData = dbUtils.db_get_progress_data_detail(ID, date)
    # print(progressDetailData)
    return templates.TemplateResponse("progress/progress_date_id.html", {"request": request, "username": user['username'], "progressDetailData": progressDetailData})

### 盤點進度追蹤 ###

### 展開盤點作業 ###
@app.get("/openup_inv")
def openup_inv(request: Request, user=Depends(manager)):
    datesList = dbUtils.db_get_all_data_list()
    return templates.TemplateResponse("inventory/openup_inv.html", {"request": request, "username": user['username'], "datesList": datesList})

@app.get("/inventory/{date}")
def start_inventory(request: Request, date: str, user=Depends(manager)):
    inventoryData = dbUtils.db_get_data_for_inventory(date)
    return templates.TemplateResponse("inventory/start_inventory.html", {"request": request, "username": user['username'], "date": date, "inventoryData": inventoryData})

@app.post("/new_inv")
async def start_new_inv(request: Request, myfile: UploadFile = File(...), invDate: str = Form(...), user=Depends(manager)):
    df = pd.read_excel(BytesIO(myfile.file.read()))
    dbUtils.db_create_data_table(invDate, df)
    url = f"/inventory/{invDate}"
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    return response

@app.post("/continue_inv")
async def start_continue_inv(request: Request, selectDate: str = Form(...), user=Depends(manager)):
    url = f"/inventory/{selectDate}"
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    return response
### 展開盤點作業 ###

### 盤點紀錄log ###
@app.get("/log")
def get_log(request: Request, user=Depends(manager)):
    return templates.TemplateResponse("log/log.html", {"request": request, "username": user['username']})
### 盤點紀錄log ###

### APP ###
@app.get("/appGetUsers")
def app_get_users(request: Request):
    data = dbUtils.db_app_get_users()
    return JSONResponse(data)

@app.get("/appGetQrcodeResults/{qrcode}")
def app_qrcode_get_med_code_name_flag(request: Request, qrcode: str):
    data = dbUtils.db_app_qrcode_result(qrcode)
    headers = {"Charset":"utf-8"}
    return Response(content=data, headers=headers)

### APP ###