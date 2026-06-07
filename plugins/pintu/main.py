"""
pintu 插件 - 九宫格拼图游戏 (rqhbot 插件规范适配版)

将独立的 pintu 拼图游戏适配为 rqhbot 的 PluginBase 规范插件。
"""

import asyncio
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from sdk.pluginsystem import PluginBase, filter_registry
from sdk.core.events import GroupMessageEvent

from .config_manager import add_admin, get_admins, is_puzzle_admin, remove_admin

PLUGIN_DIR = Path(__file__).resolve().parent
IMAGE_DIR = PLUGIN_DIR / "tupina"
TEMP_DIR = PLUGIN_DIR / "temp"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CORRECT_ORDER = list(range(1, 10))


@dataclass
class GameSession:
    group_id: int
    active: bool = False
    original_image_path: str = ""
    tiles: List[Image.Image] = field(default_factory=list)
    arrangement: List[int] = field(default_factory=lambda: CORRECT_ORDER.copy())
    scores: Dict[str, int] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    piece_size: Tuple[int, int] = (0, 0)


class PintuPlugin(PluginBase):
    """九宫格拼图游戏插件"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Pintu"
        self.version = "1.0.0"
        self.description = "九宫格拼图游戏，支持多人协作完成拼图"
        self.author = "pintu"
        self.games: Dict[int, GameSession] = {}
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async def on_load(
        self,
        api,
        event_bus,
        plugin_dir: Optional[Path] = None,
    ) -> None:
        """插件加载：初始化"""
        await super().on_load(api, event_bus, plugin_dir)
        print(f"{self.name} 插件已加载")
        print(f"插件版本: {self.version}")

    @filter_registry.group_server()
    async def on_group_message(self, event: GroupMessageEvent) -> None:
        """处理群聊消息 — 拼图游戏指令"""
        text = event.message.plain_text.strip()
        if not text:
            return

        group_id = event.group_id
        user_id = event.user_id

        if text in {"帮助", "/help"}:
            await self._send_help(group_id)
            return

        if text in {"状态", "/puzzle"}:
            await self._send_status(group_id)
            return

        if text in {"得分", "/score"}:
            await self._send_score(group_id)
            return

        if text in {"开拼图", "开始拼图", "/startgame"}:
            await self._start_game(event)
            return

        if text in {"结算", "结束拼图", "/endgame"}:
            await self._end_game(event)
            return

        if text in {"重开", "重置拼图", "/resetpuzzle"}:
            await self._reset_current_puzzle(event)
            return

        if text.startswith("拼图加管"):
            await self._add_puzzle_admin(event, text)
            return

        if text.startswith("拼图删管"):
            await self._remove_puzzle_admin(event, text)
            return

        if text == "拼图管理":
            await self._list_puzzle_admins(event)
            return

        swap = self._parse_swap(text)
        if swap:
            await self._handle_swap(event, *swap)
            return

        if text.startswith("交换") or "换" in text:
            await self.api.send_group_message(group_id, "指令格式错误，示例：9换1 或 交换 4 7")
            return

    # ==================== 游戏管理 ====================

    async def _start_game(self, event: GroupMessageEvent) -> None:
        group_id = event.group_id
        if not await self._is_admin(event):
            await self.api.send_group_message(group_id, "只有拼图管理员可以开始游戏。")
            return

        session = self._get_session(group_id)
        async with session.lock:
            if session.active:
                await self.api.send_group_message(group_id, "已有进行中的游戏，请先使用 结算 结束当前对局。")
                return

            image_path = self._choose_image()
            if not image_path:
                await self.api.send_group_message(group_id, "本地图片文件夹为空，请先向 plugins/pintu/tupina 添加图片。")
                return

            try:
                tiles, piece_size = self._load_tiles(image_path)
            except Exception:
                await self.api.send_group_message(group_id, "图片加载失败，请检查图片文件是否损坏。")
                return

            session.active = True
            session.original_image_path = str(image_path)
            session.tiles = tiles
            session.piece_size = piece_size
            session.scores = {}
            self._shuffle(session)
            image = self._save_puzzle_image(session)

        await self._send_image(group_id, image, '游戏开始！图片已随机选择并打乱。发送"9换1"或"交换 4 7"交换碎片。当前拼图如下：')

    async def _end_game(self, event: GroupMessageEvent) -> None:
        group_id = event.group_id
        if not await self._is_admin(event):
            await self.api.send_group_message(group_id, "只有拼图管理员可以结束游戏。")
            return

        session = self._get_session(group_id)
        async with session.lock:
            if not session.active:
                await self.api.send_group_message(group_id, "当前没有进行中的游戏，无需结束。")
                return

            session.active = False
            scores = session.scores.copy()

        if not scores:
            await self.api.send_group_message(group_id, "游戏结束！本局暂无玩家得分。")
            return

        ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        highest = ranking[0][1]
        winners = [self._mention(uid) for uid, score in ranking if score == highest]
        detail = "，".join(f"{self._mention(uid)}({score}分)" for uid, score in ranking)
        if len(winners) > 1:
            text = f"游戏结束！并列第一：{'，'.join(winners)}，得分 {highest}。完整排行：{detail}。恭喜！"
        else:
            text = f"游戏结束！胜利者：{winners[0]}，得分 {highest}。完整排行：{detail}。恭喜！"
        await self.api.send_group_message(group_id, text)

    async def _reset_current_puzzle(self, event: GroupMessageEvent) -> None:
        group_id = event.group_id
        if not await self._is_admin(event):
            await self.api.send_group_message(group_id, "只有拼图管理员可以重置拼图。")
            return

        session = self._get_session(group_id)
        async with session.lock:
            if not session.active:
                await self.api.send_group_message(group_id, "当前没有进行中的游戏，请管理员使用 开拼图 开始新对局。")
                return
            self._shuffle(session)
            image = self._save_puzzle_image(session)

        await self._send_image(group_id, image, "拼图已重新打乱，游戏继续！")

    async def _handle_swap(self, event: GroupMessageEvent, first: int, second: int) -> None:
        group_id = event.group_id
        user_id = event.user_id

        if first == second:
            await self.api.send_group_message(group_id, "不能交换同一个位置，请输入两个不同的数字。")
            return

        if not 1 <= first <= 9 or not 1 <= second <= 9:
            await self.api.send_group_message(group_id, "交换位置必须在 1~9 范围内。")
            return

        session = self._get_session(group_id)
        gained = False
        completed = False
        score = 0
        async with session.lock:
            if not session.active:
                await self.api.send_group_message(group_id, "当前没有进行中的游戏，请管理员使用 开拼图 开始新对局。")
                return

            before_correct = self._count_correct_tiles(session.arrangement)
            session.arrangement[first - 1], session.arrangement[second - 1] = (
                session.arrangement[second - 1],
                session.arrangement[first - 1],
            )
            after_correct = self._count_correct_tiles(session.arrangement)
            if after_correct > before_correct:
                gained = True
                session.scores[str(user_id)] = session.scores.get(str(user_id), 0) + 1
                score = session.scores[str(user_id)]
            if session.arrangement == CORRECT_ORDER:
                completed = True
                self._shuffle(session)
            image = self._save_puzzle_image(session)

        if completed and gained:
            text = f"{self._mention(user_id)} 操作正确，获得 1 分，当前总分：{score}。拼图已完成并重新打乱，游戏继续！"
        elif gained:
            text = f"{self._mention(user_id)} 操作正确，获得 1 分，当前总分：{score}。"
        else:
            text = f"已交换位置 {first} 和 {second}，本次未得分。"
        await self._send_image(group_id, image, text)

    # ==================== 状态查询 ====================

    async def _send_status(self, group_id: int) -> None:
        session = self._get_session(group_id)
        async with session.lock:
            if not session.active:
                await self.api.send_group_message(group_id, "当前没有进行中的游戏，请管理员使用 开拼图 开始新对局。")
                return
            image = self._save_puzzle_image(session)
        await self._send_image(group_id, image, "当前拼图状态：")

    async def _send_score(self, group_id: int) -> None:
        session = self._get_session(group_id)
        async with session.lock:
            scores = session.scores.copy()
            active = session.active

        if not active:
            await self.api.send_group_message(group_id, "当前没有进行中的游戏，请管理员使用 开拼图 开始新对局。")
            return

        if not scores:
            await self.api.send_group_message(group_id, "当前还没有玩家得分。")
            return

        ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        lines = ["当前得分排行："]
        for index, (uid, score) in enumerate(ranking, 1):
            lines.append(f"{index}. {self._mention(uid)}：{score} 分")
        await self.api.send_group_message(group_id, "\n".join(lines))

    async def _send_help(self, group_id: int) -> None:
        text = (
            "九宫格拼图游戏指令：\n"
            "开拼图：拼图管理员开始新对局\n"
            "结算：拼图管理员结束当前对局并结算\n"
            "重开：拼图管理员重新打乱当前拼图\n"
            "拼图加管 QQ号/@用户：添加拼图管理员\n"
            "拼图删管 QQ号/@用户：移除拼图管理员\n"
            "拼图管理：查看拼图管理员\n"
            "9换1 或 交换 4 7：交换两个位置的碎片\n"
            "状态 或 /puzzle：查看当前拼图\n"
            "得分 或 /score：查看本局得分排行\n"
            "帮助 或 /help：查看本帮助\n"
            "兼容旧命令：/startgame、/endgame、/resetpuzzle"
        )
        await self.api.send_group_message(group_id, text)

    # ==================== 消息发送 ====================

    async def _send_image(self, group_id: int, image_path: Path, text: str) -> None:
        await self.api.send_group_message(group_id, text, image_path=str(image_path))

    # ==================== 权限管理 ====================

    async def _is_admin(self, event: GroupMessageEvent) -> bool:
        return is_puzzle_admin(event.user_id)

    async def _add_puzzle_admin(self, event: GroupMessageEvent, text: str) -> None:
        group_id = event.group_id
        if not await self._is_admin(event):
            await self.api.send_group_message(group_id, "只有拼图管理员可以管理拼图权限。")
            return

        target = self._extract_target_user_id(event, text, "拼图加管")
        if not target:
            await self.api.send_group_message(group_id, "格式错误，请使用：拼图加管 QQ号 或 拼图加管 @用户")
            return

        if add_admin(target):
            await self.api.send_group_message(group_id, f"已将 {target} 添加为拼图管理员。")
        else:
            await self.api.send_group_message(group_id, f"{target} 已经是拼图管理员。")

    async def _remove_puzzle_admin(self, event: GroupMessageEvent, text: str) -> None:
        group_id = event.group_id
        user_id = event.user_id
        if not await self._is_admin(event):
            await self.api.send_group_message(group_id, "只有拼图管理员可以管理拼图权限。")
            return

        target = self._extract_target_user_id(event, text, "拼图删管")
        if not target:
            await self.api.send_group_message(group_id, "格式错误，请使用：拼图删管 QQ号 或 拼图删管 @用户")
            return

        if str(target) == str(user_id) and len(get_admins()) <= 1:
            await self.api.send_group_message(group_id, "不能移除最后一个拼图管理员。")
            return

        if remove_admin(target):
            await self.api.send_group_message(group_id, f"已移除拼图管理员 {target}。")
        else:
            await self.api.send_group_message(group_id, f"{target} 不是拼图管理员。")

    async def _list_puzzle_admins(self, event: GroupMessageEvent) -> None:
        group_id = event.group_id
        if not await self._is_admin(event):
            await self.api.send_group_message(group_id, "只有拼图管理员可以查看拼图权限。")
            return

        admins = get_admins()
        if not admins:
            await self.api.send_group_message(group_id, "暂无拼图管理员。")
            return

        admin_list = "\n".join(f"- {admin}" for admin in admins)
        await self.api.send_group_message(group_id, f"拼图管理员名单：\n{admin_list}")

    def _extract_target_user_id(self, event: GroupMessageEvent, text: str, prefix: str) -> Optional[str]:
        """从 @ 消息段中提取目标用户 ID"""
        for seg in event.message.segments:
            if seg.get("type") == "at":
                qq = seg.get("data", {}).get("qq", "")
                if qq:
                    return str(qq)

        target = text.removeprefix(prefix).strip()
        if target.isdigit():
            return target
        return None

    # ==================== 游戏逻辑 ====================

    def _get_session(self, group_id: int) -> GameSession:
        if group_id not in self.games:
            self.games[group_id] = GameSession(group_id=group_id)
        return self.games[group_id]

    def _choose_image(self) -> Optional[Path]:
        if not IMAGE_DIR.exists():
            return None
        images = [
            path
            for path in IMAGE_DIR.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not images:
            return None
        return random.choice(images)

    def _load_tiles(self, image_path: Path) -> Tuple[List[Image.Image], Tuple[int, int]]:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            width, height = image.size
            piece = min(width, height) // 3
            left = (width - piece * 3) // 2
            top = (height - piece * 3) // 2
            image = image.crop((left, top, left + piece * 3, top + piece * 3))
            tiles = []
            for row in range(3):
                for col in range(3):
                    box = (col * piece, row * piece, (col + 1) * piece, (row + 1) * piece)
                    tiles.append(image.crop(box).copy())
        return tiles, (piece, piece)

    def _shuffle(self, session: GameSession) -> None:
        arrangement = CORRECT_ORDER.copy()
        while arrangement == CORRECT_ORDER:
            random.shuffle(arrangement)
        session.arrangement = arrangement

    def _count_correct_tiles(self, arrangement: List[int]) -> int:
        return sum(1 for index, tile in enumerate(arrangement, 1) if index == tile)

    def _save_puzzle_image(self, session: GameSession) -> Path:
        piece_w, piece_h = session.piece_size
        image = Image.new("RGB", (piece_w * 3, piece_h * 3), "white")
        for index, tile_index in enumerate(session.arrangement):
            row, col = divmod(index, 3)
            image.paste(session.tiles[tile_index - 1], (col * piece_w, row * piece_h))

        draw = ImageDraw.Draw(image)
        font = self._get_font(max(18, piece_w // 6))
        for index in range(9):
            row, col = divmod(index, 3)
            x = col * piece_w
            y = row * piece_h
            draw.rectangle(
                (x, y, x + piece_w - 1, y + piece_h - 1),
                outline=(255, 255, 255),
                width=max(2, piece_w // 80),
            )
            label = str(index + 1)
            bbox = draw.textbbox((0, 0), label, font=font)
            label_w = bbox[2] - bbox[0]
            label_h = bbox[3] - bbox[1]
            padding = max(6, piece_w // 35)
            draw.rectangle(
                (x + padding, y + padding, x + padding * 2 + label_w, y + padding * 2 + label_h),
                fill=(0, 0, 0),
            )
            draw.text(
                (x + padding * 1.5, y + padding * 1.2),
                label,
                fill=(255, 255, 255),
                font=font,
            )

        output = TEMP_DIR / f"puzzle_{session.group_id}.jpg"
        image.save(output, "JPEG", quality=90)
        return output

    @staticmethod
    def _get_font(size: int) -> ImageFont.FreeTypeFont:
        for font_name in ("msyh.ttc", "simhei.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(font_name, size)
            except Exception:
                pass
        return ImageFont.load_default()

    @staticmethod
    def _parse_swap(text: str) -> Optional[Tuple[int, int]]:
        match = re.fullmatch(r"(\d)\s*换\s*(\d)", text)
        if not match:
            match = re.fullmatch(r"交换\s+(\d)\s+(\d)", text)
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def _mention(user_id) -> str:
        return f"[CQ:at,qq={user_id}]"
