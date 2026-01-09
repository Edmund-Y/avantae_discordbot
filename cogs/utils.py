import discord
from discord import app_commands
from discord.ext import commands
import logging

# 로거 설정
logger = logging.getLogger("utils")

class Utils(commands.Cog):
    """유틸리티 기능"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="메시지지우기", description="이 채널에서 봇이 보낸 메시지를 최근 100개 중에서 찾아 삭제합니다")
    async def delete_bot_messages(self, interaction: discord.Interaction):
        """봇 메시지 삭제 명령어"""
        # 처리에 시간이 걸릴 수 있으므로 defer
        await interaction.response.defer(ephemeral=True)
        
        channel = interaction.channel
        deleted_count = 0
        
        try:
            # 최근 100개의 메시지 확인
            async for message in channel.history(limit=100):
                if message.author == self.bot.user:
                    try:
                        # 봇 자신의 메시지 삭제
                        await message.delete()
                        deleted_count += 1
                    except discord.Forbidden:
                        continue
                    except discord.HTTPException:
                        continue
                        
            await interaction.followup.send(f"✅ {deleted_count}개의 메시지를 삭제했습니다.", ephemeral=True)
            logger.info(f"[메시지 삭제] 사용자: {interaction.user.name} | 채널: {channel} | 삭제 수: {deleted_count}")
            
        except Exception as e:
            logger.error(f"[메시지 삭제 오류] {e}")
            await interaction.followup.send("❌ 메시지 삭제 중 오류가 발생했습니다.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utils(bot))
