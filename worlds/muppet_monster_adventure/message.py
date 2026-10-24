from typing import TYPE_CHECKING
from .addresses.structs import AddressTable
import worlds._bizhawk as bizhawk

if TYPE_CHECKING:
    from . import BizHawkClientContext

class MessageDisplay:
    addressTable: AddressTable

    def __init__(self, addressTable: AddressTable):
        self.addressTable = addressTable

    def convertMemoryAddress(self, address: bytes):
        """Converts a memory address from bytes into the equivalent int"""
        i = int.from_bytes(address)
        return int.from_bytes(i.to_bytes(3, 'little'))

    def revertMemoryAddress(self, address: int):
        """Reverts an int address to Big Endian"""
        return address.to_bytes(3, 'big')
    
    async def updateHubMessage(self, ctx: "BizHawkClientContext"):
        # Add a custom message for each mini-game
        message = bytearray('Loading retrieved items... Loading... Loading... Loading... Loading... Loading... Loading... Loading...', 'ASCII')
        message.extend(b'\x00')
        await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.addressTable.level_hub_message, message, "MainRAM"),
                ],
            )

    async def updateMiniGameMessages(self, ctx: "BizHawkClientContext", levelName: str):
        """Sets the Start Message for all mini-games to a known string"""
        if levelName not in self.addressTable.level_minigame_data:
            return
        gameAddresses = self.addressTable.level_minigame_data[levelName]

        for minigame in gameAddresses.minigames:
            # Add a custom message for each mini-game
            startGame = bytearray(minigame.name, 'ASCII')
            startGame.extend(b'\x0A')
            startGame.extend(b'Press % to play or & to cancel')
            startGame.extend(b'\x00')
            await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (minigame.start, startGame, "MainRAM"),
                        (minigame.retry, startGame, "MainRAM"),
                    ],
                )

    async def clearPepeMessage(self, ctx: "BizHawkClientContext"):
        await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (self.addressTable.pepe_message_ui_counter, (0).to_bytes(4, "little"), "MainRAM"),
                    (self.addressTable.pepe_message_message_pointer, (0).to_bytes(4, "little"), "MainRAM"),
                ],
            )

    async def disablePepeMessages(self, ctx: "BizHawkClientContext", levelName: str):
        """Disables Pepe's UI messages"""
        data = await bizhawk.read(
            ctx.bizhawk_ctx,
            [(self.addressTable.pepe_message_message_pointer, 4, "MainRAM")]
        )

        messageAddress = data[0]
        # strip the \x80 from the message address pointer
        messageAddress = messageAddress[:-1]

        # Ignore any "blank" messages
        if messageAddress == b'\x00\x00\x00':
            return
        converted = self.convertMemoryAddress(messageAddress)
        
        # Ignore any levels that aren't valid
        if levelName not in self.addressTable.level_minigame_data:
            await self.clearPepeMessage(ctx)
            return

        gameAddresses = self.addressTable.level_minigame_data[levelName]

        isMiniGame = False
        for minigame in gameAddresses.minigames:
            if converted == minigame.start or converted == minigame.retry:
                isMiniGame = True
                break

        # don't block mini-game messages
        if isMiniGame:
            return

        #TODO: Remove this debug once all the mini-games are found and tested
        print('Memory: ' + str(converted))
        print(self.revertMemoryAddress(converted))
        await self.clearPepeMessage(ctx)
