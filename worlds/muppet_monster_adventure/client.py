from typing import TYPE_CHECKING

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

if TYPE_CHECKING:
    from CommonClient import logger
    from worlds._bizhawk.context import BizHawkClientContext

from .constants import base_id, game_name


class MMAClient(BizHawkClient):
    game = game_name
    system = "PSX"
    items_handling = 0b111

    def __init__(self):
        super().__init__()

    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            # Check ROM name/patch version
            rom_name = ((await bizhawk.read(ctx.bizhawk_ctx, [(0x009274, 11, "ROM")]))[0]).decode("ascii")
            if rom_name != "SLUS_012.38":
                return False
        except bizhawk.RequestFailedError:
            return False

        ctx.game = self.game
        ctx.items_handling = self.items_handling
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.125
        self.loading_bios_msg = False

        return True

    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        return
