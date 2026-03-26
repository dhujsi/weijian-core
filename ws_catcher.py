import asyncio
import websockets

async def handler(ws):
    print("NapCat connected")
    try:
        async for msg in ws:
            print(msg)  # 这里就是你要的“真实事件样例”
    except Exception as e:
        print("ws closed:", e)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8095):
        print("WS catcher on :8095")
        await asyncio.Future()

asyncio.run(main())