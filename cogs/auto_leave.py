import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from typing import Dict
import asyncio
import logging
import os

# 로그 설정
log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file = os.path.join(log_dir, "bot.log")

# 로거 생성
logger = logging.getLogger("auto_leave")
logger.setLevel(logging.INFO)

# 파일 핸들러
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.INFO)

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 포맷 설정
formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


class TimeInputModal(discord.ui.Modal, title="⏰ 자동 나가기 시간 설정"):
    """시간 입력을 위한 모달"""
    
    minutes = discord.ui.TextInput(
        label="몇 분 후에 나가시겠습니까?",
        placeholder="예: 30",
        required=True,
        min_length=1,
        max_length=4,
        style=discord.TextStyle.short
    )
    
    def __init__(self, cog: "AutoLeave"):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = int(self.minutes.value)
            if minutes <= 0:
                await interaction.response.send_message(
                    "❌ 1분 이상의 값을 입력해주세요!", 
                    ephemeral=True
                )
                return
            if minutes > 1440:  # 24시간 제한
                await interaction.response.send_message(
                    "❌ 최대 1440분(24시간)까지 설정 가능합니다!", 
                    ephemeral=True
                )
                return
                
            await self.cog.set_timer(interaction, minutes)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ 올바른 숫자를 입력해주세요!", 
                ephemeral=True
            )


class AutoLeaveView(discord.ui.View):
    """취소 및 시간 변경 버튼이 있는 View"""
    
    def __init__(self, cog: "AutoLeave", user_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id
    
    @discord.ui.button(label="🚫 취소", style=discord.ButtonStyle.danger, custom_id="cancel_timer")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 본인만 취소할 수 있습니다!", ephemeral=True)
            return
            
        await self.cog.cancel_timer(interaction)
    
    @discord.ui.button(label="⏱️ 시간 변경", style=discord.ButtonStyle.primary, custom_id="change_time")
    async def change_time_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 본인만 변경할 수 있습니다!", ephemeral=True)
            return
            
        modal = TimeInputModal(self.cog)
        await interaction.response.send_modal(modal)


class AutoLeave(commands.Cog):
    """자동 나가기 기능"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 사용자별 타이머 정보 저장
        self.timers: Dict[int, dict] = {}
        self.update_embeds.start()
        logger.info("AutoLeave Cog 초기화 완료")
    
    def cog_unload(self):
        self.update_embeds.cancel()
        # 모든 타이머의 태스크 취소
        for timer_info in self.timers.values():
            if timer_info.get("task"):
                timer_info["task"].cancel()
        logger.info("AutoLeave Cog 언로드")
    
    @tasks.loop(seconds=1)
    async def update_embeds(self):
        """1초마다 모든 활성 타이머의 embed 업데이트"""
        now = datetime.now()
        expired_users = []
        
        for user_id, timer_info in list(self.timers.items()):
            end_time = timer_info["end_time"]
            remaining = end_time - now
            
            # 타이머 만료 체크
            if remaining.total_seconds() <= 0:
                expired_users.append(user_id)
                continue
            
            # Embed 업데이트
            message = timer_info.get("message")
            if message:
                try:
                    embed = self.create_timer_embed(
                        timer_info["minutes"], 
                        end_time,
                        remaining
                    )
                    view = AutoLeaveView(self, user_id)
                    await message.edit(embed=embed, view=view)
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    pass
        
        # 만료된 타이머 처리
        for user_id in expired_users:
            await self.execute_auto_leave(user_id)
    
    @update_embeds.before_loop
    async def before_update_embeds(self):
        await self.bot.wait_until_ready()
    
    async def execute_auto_leave(self, user_id: int):
        """자동 나가기 실행"""
        timer_info = self.timers.pop(user_id, None)
        if not timer_info:
            return
        
        user = self.bot.get_user(user_id)
        if not user:
            return
        
        # 사용자가 음성 채널에 있는지 확인
        voice_state = None
        guild_name = None
        for guild in self.bot.guilds:
            member = guild.get_member(user_id)
            if member and member.voice:
                voice_state = member.voice
                guild_name = guild.name
                break
        
        try:
            if voice_state and voice_state.channel:
                # 음성 채널에서 연결 해제
                member = voice_state.channel.guild.get_member(user_id)
                if member:
                    channel_name = voice_state.channel.name
                    await member.move_to(None)
                    
                    logger.info(f"[자동나가기 실행] 사용자: {user.name}({user_id}) | 서버: {guild_name} | 채널: {channel_name}")
                    
                    # 완료 Embed
                    embed = discord.Embed(
                        title="✅ 자동 나가기 완료",
                        description=f"**{channel_name}** 채널에서 연결이 해제되었습니다.",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                logger.info(f"[타이머 종료] 사용자: {user.name}({user_id}) | 음성 채널 미접속")
                
                # 음성 채널에 없는 경우
                embed = discord.Embed(
                    title="ℹ️ 타이머 종료",
                    description="설정한 시간이 되었지만 음성 채널에 접속해 있지 않습니다.",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # 메시지 업데이트
            if timer_info.get("message"):
                try:
                    await timer_info["message"].edit(embed=embed, view=None)
                except:
                    await user.send(embed=embed)
                    
        except discord.Forbidden:
            logger.warning(f"[권한 부족] 사용자: {user.name}({user_id}) | 음성 채널 연결 해제 실패")
            try:
                embed = discord.Embed(
                    title="❌ 권한 부족",
                    description="권한이 부족하여 음성 채널에서 연결을 해제할 수 없습니다.",
                    color=discord.Color.red()
                )
                if timer_info.get("message"):
                    await timer_info["message"].edit(embed=embed, view=None)
            except:
                pass
        except Exception as e:
            logger.error(f"[오류] 사용자: {user.name}({user_id}) | 오류: {e}")
    
    def create_timer_embed(self, minutes: int, end_time: datetime, remaining: timedelta = None) -> discord.Embed:
        """타이머 정보 Embed 생성"""
        embed = discord.Embed(
            title="🔔 자동 나가기 설정됨",
            color=discord.Color.orange()
        )
        
        # 남은 시간 계산
        if remaining is None:
            remaining = end_time - datetime.now()
        
        total_seconds = max(0, int(remaining.total_seconds()))
        mins = total_seconds // 60
        secs = total_seconds % 60
        
        # 프로그레스 바 생성
        total_seconds_original = minutes * 60
        progress = total_seconds / total_seconds_original if total_seconds_original > 0 else 0
        bar_length = 10
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        embed.add_field(
            name="⏳ 남은 시간",
            value=f"```\n{mins:02d}:{secs:02d}\n{bar}\n```",
            inline=False
        )
        embed.add_field(
            name="⏰ 설정 시간",
            value=f"`{minutes}분`",
            inline=True
        )
        embed.add_field(
            name="📅 종료 예정",
            value=f"`{end_time.strftime('%H:%M:%S')}`",
            inline=True
        )
        embed.set_footer(text="음성 채널에 접속 중이면 자동으로 연결이 해제됩니다")
        
        return embed
    
    async def set_timer(self, interaction: discord.Interaction, minutes: int):
        """타이머 설정"""
        user_id = interaction.user.id
        user_name = interaction.user.name
        end_time = datetime.now() + timedelta(minutes=minutes)
        remaining = timedelta(minutes=minutes)
        
        # 새 임베드 및 뷰 생성
        embed = self.create_timer_embed(minutes, end_time, remaining)
        view = AutoLeaveView(self, user_id)
        
        # 기존 타이머가 있으면 해당 메시지 업데이트
        if user_id in self.timers:
            old_minutes = self.timers[user_id].get("minutes", 0)
            logger.info(f"[타이머 변경] 사용자: {user_name}({user_id}) | {old_minutes}분 → {minutes}분")
            
            message = self.timers[user_id].get("message")
            if message:
                try:
                    # 기존 메시지 수정 (새 시간으로)
                    await message.edit(embed=embed, view=view)
                    
                    # 타이머 정보 업데이트
                    self.timers[user_id]["end_time"] = end_time
                    self.timers[user_id]["minutes"] = minutes
                    
                    # 요청자에게는 임시 메시지로 완료 알림
                    if not interaction.response.is_done():
                        await interaction.response.send_message("✅ 시간이 변경되었습니다!", ephemeral=True)
                    return
                except Exception as e:
                    logger.warning(f"[메시지 수정 실패] {e}, 새 메시지로 전송합니다.")
                    # 실패 시 아래의 새 메시지 전송 로직으로 진행
        else:
            logger.info(f"[타이머 설정] 사용자: {user_name}({user_id}) | {minutes}분")
        
        # 새 타이머 설정
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=view)
            message = await interaction.original_response()
            
            self.timers[user_id] = {
                "end_time": end_time,
                "message": message,
                "minutes": minutes
            }
    
    async def cancel_timer(self, interaction: discord.Interaction):
        """타이머 취소"""
        user_id = interaction.user.id
        user_name = interaction.user.name
        
        if user_id not in self.timers:
            await interaction.response.send_message("❌ 설정된 타이머가 없습니다!", ephemeral=True)
            return
        
        timer_info = self.timers.pop(user_id)
        logger.info(f"[타이머 취소] 사용자: {user_name}({user_id}) | 설정: {timer_info.get('minutes', 0)}분")
        
        embed = discord.Embed(
            title="🚫 자동 나가기 취소됨",
            description="타이머가 취소되었습니다.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @app_commands.command(name="자동나가기", description="지정한 시간 후 음성 채널에서 자동으로 나갑니다")
    @app_commands.dm_only()
    async def auto_leave(self, interaction: discord.Interaction):
        """자동 나가기 명령어 (DM 전용)"""
        modal = TimeInputModal(self)
        await interaction.response.send_modal(modal)
    
    @app_commands.command(name="자동나가기취소", description="설정된 자동 나가기 타이머를 취소합니다")
    @app_commands.dm_only()
    async def auto_leave_cancel(self, interaction: discord.Interaction):
        """자동 나가기 취소 명령어 (DM 전용)"""
        user_id = interaction.user.id
        
        if user_id not in self.timers:
            await interaction.response.send_message("❌ 설정된 타이머가 없습니다!", ephemeral=True)
            return
        
        timer_info = self.timers.pop(user_id)
        logger.info(f"[타이머 취소] 사용자: {interaction.user.name}({user_id}) | 명령어")
        
        # 이전 메시지 업데이트
        if timer_info.get("message"):
            try:
                embed = discord.Embed(
                    title="🚫 자동 나가기 취소됨",
                    description="타이머가 취소되었습니다.",
                    color=discord.Color.red()
                )
                await timer_info["message"].edit(embed=embed, view=None)
            except:
                pass
        
        await interaction.response.send_message("✅ 자동 나가기가 취소되었습니다!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLeave(bot))
