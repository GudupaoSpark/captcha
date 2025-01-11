from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import captcha

app = FastAPI()

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="./static"), name="static")

# 包含路由
app.include_router(captcha.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0",reload=True, port=8000)