import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# .env 파일에서 환경 변수 로드
load_dotenv()

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"[OK] {bot.user.name} 준비 완료!")
    print(f"[ID] 봇 ID: {bot.user.id}")
    print(f"[SERVER] 서버 수: {len(bot.guilds)}")
    
    # 슬래시 커맨드 동기화
    try:
        synced = await bot.tree.sync()
        print(f"[SYNC] {len(synced)}개의 슬래시 커맨드 동기화 완료")
    except Exception as e:
        print(f"[ERROR] 슬래시 커맨드 동기화 실패: {e}")


async def load_cogs():
    """Cog 로드"""
    await bot.load_extension("cogs.auto_leave")
    print("[COG] auto_leave Cog 로드 완료")
    await bot.load_extension("cogs.utils")
    print("[COG] utils Cog 로드 완료")


async def main():
    async with bot:
        await load_cogs()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("[ERROR] DISCORD_TOKEN이 설정되지 않았습니다!")
            print("        .env 파일에 DISCORD_TOKEN=your_token 형식으로 설정해주세요.")
            return
        await bot.start(token)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
